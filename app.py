from threading import Thread, Lock
import re
import shutil
import os
import subprocess
from cmd import Cmd
import settings
from utils import get_next_free_port

class LogLocation(object):
    LOCATION_REGEX = re.compile(r'location(?P<id>[1-9][0-9]*)')
    assert(LOCATION_REGEX.groups == 1)

    def __init__(self, log, location):
        super().__init__()
        self.log = log
        self.id = self.LOCATION_REGEX.match(location).group('id')
        self.folder = os.path.join(self.log.folder, location)
        self.port = 0
        self.process = None

    def start_osc(self):
        """Start oscilloscope for this location."""

        # If process is already running, print the port on which it can be
        # found
        if self.process is not None:
            print('{}.{} -> {}'.format(self.log.node_name, self.id, self.port))
            return

        print('Starting oscilloscope on node {} location {}...'\
                                          .format(self.log.node_name, self.id))
        self.port = App.get_free_port()

        # Set the oscilloscope port and file paths to use
        osc_options = '-p {}'.format(self.port)
        osc_files = ' '.join([os.path.join(self.folder, 'ipstrc.' + ext)
                              for ext in ['drw', 'dmp']])
        osc_cmd = 'oscilloscope.exe {} {}'.format(osc_options, osc_files)

        print('{}.{} -> {}'.format(self.log.node_name, self.id, self.port))
        self.process = subprocess.Popen(osc_cmd,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
        browser_cmd = '{}http://localhost:{}'\
                        .format(settings.settings._browser_start_string, self.port)
        subprocess.Popen(browser_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        shell=True)

class Log(object):
    def __init__(self, archive):
        """Log constructor.

        Arguments:
            archive {str} -- Path to the archive to create log for.
        """

        super().__init__()
        pattern = re.compile(settings.settings._archive_regex)
        self.archive = archive
        self.node_name = pattern.match(self.archive).group(1).capitalize()
        self.folder = settings.settings.folder_format % self.node_name
        self.locations = {}

    def extract(self):
        """Extract the archive to a folder."""

        # If the folder exists at the current path, remove it.
        if self.folder in os.listdir():
            if settings.settings.verbose_level > 1:
                print('Removing existing folder {}.'.format(self.folder))
            shutil.rmtree(self.folder)

        # Extract the archive.
        if settings.settings.verbose_level > 1:
            print('Extracting archive {} to {}.'.format(self.archive,
                                                        self.folder))
        shutil.unpack_archive(self.archive, self.folder)

        # Remove the archive if needed.
        if not settings.settings.keep_archives:
            if settings.settings.verbose_level > 1:
                print('Removing archive {}'.format(self.archive))
            os.remove(self.archive)

        # Create the node locations objects.
        self.__init_locations()
    
    def start_osc(self, location_id):
        """Start oscilloscope on the specified location.

        Arguments:
            location_id {str} -- The location id on which to start
                                 oscilloscope.
        """
        try:
            self.locations[location_id].start_osc()
        except KeyError:
             print('Location {} does not exist on node {}.'.format(location_id,
                                                               self.node_name))

    def __init_locations(self):
        """Create the locations for this node log."""

        # Get the location folders directly under the log folder.
        subdirs = next(os.walk(self.folder))[1]
        locations = filter(lambda x: LogLocation.LOCATION_REGEX.match(x),
                           subdirs)

        for location in locations:
            log_location = LogLocation(self, location)
            self.locations[log_location.id] = log_location

class App(Cmd):
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
            self.__lock = Lock()
            App._next_free_port = settings.settings.first_port
            App.__instance = self

    @classmethod
    def getInstance(cls):
        """Get the App instance.

        Returns:
            App -- the App instance
        """
        if cls.__instance is None:
            cls()
        return cls.__instance

    def start_osc(self, node, location_id):
        """Start oscilloscope on the specified node and location.

        Arguments:
            node {str} -- The node name.  Examples: 'Ap', 'P1'
            location_id {str} -- The location ID.  Examples: '1', '2'.
        """

        if not os.path.exists(settings.settings.osc_path):
            print('Oscilloscope not present at {}.'.format(settings.settings.osc_path))
            return

        node = node.lower()

        try:
            self.logs[node].start_osc(location_id)
        except KeyError:
            print('Node {} does not exist.'.format(node.capitalize()))
            return

    @classmethod
    def get_free_port(cls):
        """Get an available port number.

        Returns:
            int -- Available port number.
        """
        with cls.__lock:
            port = get_next_free_port(cls._next_free_port)
            cls._next_free_port = port + 1
        return port

    def extract_archives(self):
        """Extract archives to folders."""

        # Get all the archives matching the given pattern
        p = re.compile(settings.settings._archive_regex)
        archives = filter(lambda x: p.match(x), os.listdir())

        if settings.settings.verbose_level > 0:
            print('Extracting archives...')

        # Build the Log objects and start threads to extract them.
        threads = []
        for arch in archives:
            log = Log(arch)
            self.logs[log.node_name.lower()] = log
            threads.append(Thread(target=log.extract))
            threads[-1].start()

        for t in threads:
            t.join()

        if settings.settings.verbose_level > 0:
            print('Extraction complete.')
    
    def start(self):
        self.extract_archives()
        self.cmdloop()