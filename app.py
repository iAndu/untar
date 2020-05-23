from threading import Thread, Lock
from log import Log
import re
import os
from cmd import Cmd
import settings
from utils import get_next_free_port

class App(Cmd):
    __instance = None
    __lock = Lock()
    _next_free_port = None
    COMMANDS = ['oscilloscope', 'exit']

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
        # Match on folders based on the folder format given, placing a group in
        # order to get the name of the node.  Append a look-behind at the end
        # to exclude the archives, if they exist and match on the pattern.
        p = re.compile((settings.settings.folder_format % '(.*)') +
                                                                 '(?<!\.tgz)$')
        existing_logs = filter(lambda x: p.match(x), os.listdir())

        # Create the Log objects and map their locations.
        for log in existing_logs:
            log = Log(p.match(log).group(1))._map_locations()
            self.logs[log.node_name.lower()] = log

        return self

    def extract_archives(self):
        """Extract archives to folders."""

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

        if not settings.settings.no_open:
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

    def do_oscilloscope(self, args):
        """Run oscilloscope command for the given arguments.

        Arguments:
            args {None, str} -- String containing the command parameters.
            
        Returns:
            bool -- False in order to continue the CLI loop.
        """

        if not os.path.exists(settings.settings.osc_path):
            print('Oscilloscope not present at {}.'\
                  .format(settings.settings.osc_path))
            return False

        if not args:
            # Create a list of dictionaries containing all available nodes.
            log_dicts = map(lambda x: {'node': x, 'location_id': None},
                            self.logs.keys())
        else:
            # Get a list of {node, location_id} that match in the arguments
            p = re.compile(r'(?P<node>[\w\d]+)(?:\.(?P<location_id>.*))?')
            matches = filter(lambda x: x != '' and p.match(x), args.split(' '))
            log_dicts = list(map(lambda x: p.match(x).groupdict(default='1'),
                                 matches))

            # * is a wildcard for locations which should match all available
            # locations.  We change the '*' to None in order to start all
            # locations.
            for log_dict in log_dicts:
                if log_dict['location_id'] == '*':
                    log_dict['location_id'] = None

        # Start oscilloscope on the matching nodes
        threads = []
        for log_dict in log_dicts:
            threads.append(Thread(target=self.start_osc,
                                  args=(log_dict.values())))
            threads[-1].start()
        for t in threads:
            t.join()

        return False

    def do_exit(self, args):
        """Close the CLI interface.

        Arguments:
            args {None, str} -- Arguments - will be ignored.

        Returns:
            bool -- True in order to stop the CLI loop.
        """

        return True