import re
import os
import subprocess
import settings
import shutil
from threading import Thread
from utils import get_next_free_port

class Log(object):
    ARCHIVE_REGEX = re.compile(r'node(.*)_log\.tgz')
    assert(ARCHIVE_REGEX.groups == 1)

    def __init__(self, node_name, archive=None):
        """Log constructor.

        Arguments:
            node_name {str} -- The name of the node.

        Keyword Arguments:
            archive {str} -- The name of the archive for the node.
                             (default: {None})
        """

        super().__init__()
        self.archive = archive
        self.node_name = node_name.capitalize()
        self.folder = settings.settings.folder_format % self.node_name
        self.locations = {}

    def extract(self):
        """Extract the archive to a folder.

        Raises:
            Exception: The log has no archive to extract.
            
        Returns:
            Log -- self
        """

        if self.archive is None:
            raise Exception('No archive found for node {}.'\
                            .format(self.node_name))

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
        return self._map_locations()
    
    def start_osc(self, location_id=None):
        """Start oscilloscope on the specified location.

        Arguments:
            location_id {str} -- The location id on which to start
                                 oscilloscope.
        Returns:
            Log -- self
        """

        if location_id is not None:
            try:
                self.locations[location_id.lower()].start_osc()
            except KeyError:
                print('Location {} does not exist on node {}.'\
                                          .format(location_id.capitalize(),
                                                  self.node_name.capitalize()))
        else:
            threads = []
            for location in self.locations.values():
                threads.append(Thread(target=location.start_osc))
                threads[-1].start()
            for t in threads:
                t.join()

        return self

    def stop_osc(self, location_id=None):
        """Stop oscilloscope process for the given location.

        Keyword Arguments:
            location_id {str} -- The location on which to stop the process.  If
                                 None, stops on all processes
                                 (default: {None})

        Returns:
            Log -- self
        """

        if location_id is not None:
            try:
                self.locations[location_id.lower()].stop_osc()
            except KeyError:
                print('Location {} does not exist on node {}.'\
                                          .format(location_id.capitalize(),
                                                  self.node_name.capitalize()))
        else:
            for location in self.locations.values():
                location.stop_osc()

        return self

    def _map_locations(self):
        """Create the locations for this node log.
        
        Returns:
            Log -- self
        """

        # Get the location folders directly under the log folder.
        subdirs = next(os.walk(self.folder))[1]
        locations = filter(lambda x: self.LogLocation.LOCATION_REGEX.match(x),
                           subdirs)

        for location in locations:
            log_location = self.LogLocation(self, location)
            self.locations[log_location.id.lower()] = log_location
        
        return self

    class LogLocation(object):
        LOCATION_REGEX = re.compile(r'location(?P<id>[1-9][0-9]*)')
        assert(LOCATION_REGEX.groups == 1)

        def __init__(self, log, location):
            """LogLocation constructor.

            Arguments:
                log {Log} -- Reference to the log containing this location.
                location {str} -- Name of the location folder.
            """

            super().__init__()
            self.log = log
            self.id = self.LOCATION_REGEX.match(location).group('id')
            self.folder = os.path.join(self.log.folder, location)
            self.port = None
            self.process = None

        def start_osc(self):
            """Start oscilloscope for this location.
            
            Returns:
                LogLocation -- self
            """

            # If process is already running, print the port on which it can be
            # found
            if self.process is not None:
                print('{}.{} -> {}'.format(self.log.node_name.capitalize(),
                                        self.id.capitalize(),
                                        self.port))
                return self

            print('Starting oscilloscope on node {} location {}...'\
                                       .format(self.log.node_name.capitalize(),
                                               self.id.capitalize()))
            if self.port is None:
                self.port = get_next_free_port()

            # Set the oscilloscope port and file paths to use
            osc_options = '-p {}'.format(self.port)
            osc_files = ' '.join([os.path.join(self.folder, 'ipstrc.' + ext)
                                for ext in ['drw', 'dmp']])
            osc_cmd = 'oscilloscope.exe {} {}'.format(osc_options, osc_files)

            print('{}.{} -> {}'.format(self.log.node_name.capitalize(),
                                    self.id.capitalize(),
                                    self.port))
            self.process = subprocess.Popen(osc_cmd,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.STDOUT,
                                            shell=True)
            browser_cmd = '{}http://localhost:{}'\
                            .format(settings.settings._browser_start_string,
                                    self.port)
            subprocess.Popen(browser_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT,
                            shell=True)
            
            return self

        def stop_osc(self):
            """Stop oscilloscope process.

            Returns:
                LogLocation -- self
            """

            if self.process is not None:
                self.process.kill()
                self.process = None
            
            return self
