from threading import Thread, Lock
from log import Log
import re
import os
from cmd import Cmd
import settings
from utils import get_next_free_port

class App(Cmd):
    COMMANDS = ['oscilloscope', 'exit', 'kill']

    prompt = '> '
    intro = 'CLI started'
    __instance = None
    __lock = Lock()
    _next_free_port = None

    def __init__(self):
        assert(settings.settings is not None)

        if App.__instance != None:
            raise Exception('This class is a singleton!')
        else:
            super().__init__()
            self.logs = {}
            App._next_free_port = settings.settings.first_port
            App.__instance = self

    @classmethod
    def get_instance(cls):
        """Get the App instance.

        Returns:
            App -- the App instance
        """

        if cls.__instance is None:
            cls()
        return cls.__instance

    def start_osc(self, node, location_id=None):
        """Start oscilloscope on the specified node and location.

        Arguments:
            node {str} -- The node name.
            location_id {None, str} -- The location ID.
        """

        try:
            self.logs[node.lower()].start_osc(location_id)
        except KeyError:
            print('Node {} does not exist.'.format(node.capitalize()))
        finally:
            return self

    def load_existing_logs(self):
        """Load the already extracted nodes.

        Returns:
            App -- self
        """

        # Match on folders based on the folder format given, placing a group in
        # order to get the name of the node.  Append a look-behind at the end
        # to exclude the archives, if they exist and match on the pattern.
        folder_format = settings.settings.folder_format
        p = re.compile((folder_format % r'(.*)') + r'(?<!\.tgz)$')
        existing_logs = filter(lambda x: p.match(x), os.listdir())

        # Create the Log objects and map their locations.
        for log in existing_logs:
            log = Log(p.match(log).group(1))
            self.logs[log.node_name.lower()] = log

        return self

    def extract_archives(self):
        """Extract archives to folders.

        Returns:
            App -- self
        """

        # Get all the archives matching the given pattern
        p = Log.ARCHIVE_REGEX
        archives = filter(lambda x: p.match(x), os.listdir())

        if settings.settings.verbose_level > 0:
            print('Extracting archives...')

        # Build the Log objects and start threads to extract them
        threads = []
        for arch in archives:
            log = Log(p.match(arch).group(1), arch)
            self.logs[log.node_name.lower()] = log
            threads.append(Thread(target=log.extract))
            threads[-1].start()

        for t in threads:
            t.join()

        if settings.settings.verbose_level > 0:
            print('Extraction complete.')
        
        return self

    def preloop(self):
        """Hook method executed once when the cmdloop() method is called."""

        self.load_existing_logs().extract_archives()

        if settings.settings.start_all:
            self.do_oscilloscope(None)

    def postloop(self):
        for node in self.logs.values():
            node.stop_osc(None)

    def parseline(self, line):
        """Parse the line into a command name and a string containing the
        arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.
        If 'command' is a prefix of a command from App.COMMANDS, that one will
        be returned.

        Arguments:
            line {str} -- The line input given by user.

        Returns:
            {tuple} -- The tuple of (command, args, line)
        """
        
        cmd, arg, line = super().parseline(line)

        if cmd is not None:
            possible_commands = list(filter(lambda x: x.startswith(cmd),
                                            self.COMMANDS))
            if len(possible_commands) == 1:
                cmd = possible_commands[0]
        
        return cmd, arg, line

    def emptyline(self):
        """Called when empty line is entered.  Does nothing."""
        pass

    @staticmethod
    def __parse_node_args(args):
        """Get a list of {node, location_id} dictionaries containing the
        information present in args for the matching tokens, ignoring the
        others.

        Arguments:
            args {str} -- String containing the arguments.

        Returns:
            list -- List of mentioned dictionaries.
        """

        # Get a list of {node, location_id} that match in the arguments.
        # Currently, nodes can contain only characters in the \w metacharacter,
        # while the location can be any string as long as it's continuous.
        p = re.compile(r'(?P<node>[\w]+)(?:\.(?P<location_id>.*))?')
        matches = filter(lambda x: x != '' and p.match(x), args.split(' '))
        log_dicts = list(map(lambda x: p.match(x).groupdict(default='1'),
                             matches))

        # * is a wildcard for locations which should match all available
        # locations.  We change the '*' to None in order to start all
        # locations.
        for log_dict in log_dicts:
            if log_dict['location_id'] == '*':
                log_dict['location_id'] = None

        return log_dicts

    def do_oscilloscope(self, args):
        """\
        Run oscilloscope command for the given arguments. If no arguments are
        passed, start oscilloscope on all available nodes and locations.

        Arguments:
            args {None, str} -- String containing the command arguments.  Must
                                follow a format of {node}.{location}, with an
                                empty space between multiple inputs.  If only
                                the {node} is specified, it will start
                                oscilloscope on the {location} with id '1'.
                                {node}.* can also be used as an argument in
                                order to start oscilloscope process on all 
                                available locations on {node}.  Both {node} and
                                {location} are case-insensitive.

                                Examples: 'ap.1 p2 F.*'.
        """

        if not os.path.exists(settings.settings.osc_path):
            print('Oscilloscope not present at {}.'\
                  .format(settings.settings.osc_path))
            return False

        # Parse the args string to retreive the node-location pairs.  If the
        # args is None or empty, we're going to run oscilloscope on all nodes,
        # so we create a list of {node, location_id} dictionaries where the
        # location_id is None in order to start oscilloscope on all available
        # locations.
        if not args:
            log_dicts = map(lambda x: {'node': x, 'location_id': None},
                            self.logs.keys())
        else:
            log_dicts = self.__parse_node_args(args)

        # Start oscilloscope on the matching node-location pairs.
        threads = []
        for log_dict in log_dicts:
            threads.append(Thread(target=self.start_osc,
                                  args=(log_dict.values())))
            threads[-1].start()
        for t in threads:
            t.join()

        return False

    def do_exit(self, args):
        """\
        Close the CLI interface.
        """

        return True

    def do_kill(self, args):
        """\
        Stop oscilloscope process on the given arguments.

        Arguments:
            args {str} -- String containing the command arguments.  Must follow
                          a format of {node}.{location}, with an empty space
                          empty spaces between multiple inputs.  If only the
                          {node} is specified, it will stop oscilloscope on the
                          {location} with id '1'.  {node}.* can also be used as
                          an argument in order to stop oscilloscope process on
                          all available locations on {node}.  Both {node} and
                          {location} are case-insensitive.

                          Examples: 'ap.1 p2 F.*'.
        """

        if args is not None:
            log_dicts = self.__parse_node_args(args)
            
            for log in log_dicts:
                try:
                    self.logs[log['node'].lower()].stop_osc(log['location_id'])
                except KeyError:
                    print('Node {} does not exist.'\
                                             .format(log['node'].capitalize()))
        return False