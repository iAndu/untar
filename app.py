from threading import Thread, Lock
import re
import shutil
import os
import subprocess
import socket

class LogLocation(object):
    def __init__(self, log, id):
        self.log = log
        self.id = id
        self.folder = os.path.join(self.log.folder, 'location{}'.format(self.id))
        self.port = 0
        self.process = None

    def start_osc(self):
        if self.process is not None:
            print('{}.{} -> {}'.format(self.log.node_name, self.id, self.port))
            return

        self.port = App._get_next_free_port()

        osc_options = '-p {}'.format(self.port)
        osc_files = ' '.join([os.path.join(self.folder, 'ipstrc.' + ext) for ext in ['drw', 'dmp']])

        self.process = subprocess.Popen('oscilloscope.exe {} {}'.format(osc_options, osc_files))
        print('{}.{} -> {}'.format(self.log.node_name, self.id, self.port))
        subprocess.run('{}http://localhost:{}'.format(App.settings._browser_start_string, self.port),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        shell=True)

class Log(object):
    default_node = 1

    def __init__(self, archive):
        self.archive = archive

        pattern = App.settings._archive_regex
        try:
            self.node_name = pattern.match(self.archive).group(1).capitalize()
        except:
            print('Archive {} does not match pattern {}. Using default name {}'.format(self.archive, pattern, self.default_node))
            self.node_name = str(self.default_node)
            self.default_node += 1

        self.folder = App.settings.folder_format % (self.node_name)
        self.locations = {}

    def extract(self):
        if self.folder in os.listdir():
            if App.settings.verbose_level > 1:
                print('Removing existing folder {}.'.format(self.folder))
            shutil.rmtree(self.folder)

        if App.settings.verbose_level > 1:
            print('Extracting archive {} to {}.'.format(self.archive, self.folder))
        shutil.unpack_archive(self.archive, self.folder)

        if not App.settings.keep_archives:
            if App.settings.verbose_level > 1:
                print('Removing archive {}'.format(self.archive))
            os.remove(self.archive)

        self.__init_locations()
    
    def start_osc(self, locationId):
        if not os.path.exists('oscilloscope.exe'):
            print('Oscilloscope not present in root folder. First copy it there.')
            return

        if locationId not in self.locations:
            print('Location {} does not exist on node {}.'.format(locationId, self.node_name))
            return

        self.locations[locationId].start_osc()

    def __init_locations(self):
        subdirs = next(os.walk(self.folder))[1]
        location_regex = re.compile(r'location([0-9]+)')
        locations = [ subdir for subdir in subdirs if location_regex.match(subdir) ]

        for location in locations:
            locationId = location_regex.match(location).group(1)
            log_location = LogLocation(self, locationId)
            self.locations[locationId] = log_location

class App(object):
    class Settings(object):
        def __init__(self, 
                     browser='chrome',
                     keep_archives=False, 
                     folder_format='%s',
                     verbose_level=1,
                     first_port=8080):
            self.browser = browser

            self._browser_start_string = 'start '
            if self.browser == "edge":
                self._browser_start_string += "microsoft-edge:"
            else:
                self._browser_start_string += self.browser + " "

            self.keep_archives = keep_archives

            if '%s' not in folder_format:
                print('Folder format invalid. Defaulting to "%s".')
            else:
                self.folder_format = folder_format

            self._archive_regex = re.compile(r'node(.*)_log\.tgz')
            self.verbose_level = verbose_level
            self.first_port = first_port

    settings = Settings()
    _logs = {}
    _current_port = settings.first_port
    __lock = Lock()

    @classmethod
    def start_osc(cls, node, locationId):
        node = node.lower()

        if node not in cls._logs:
            print('Node {} does not exist.'.format(node.capitalize()))
            return
        
        cls._logs[node.lower()].start_osc(locationId)

    @classmethod
    def extract_archives(cls):
        pattern = cls.settings._archive_regex
        archives = [ f for f in os.listdir() if pattern.match(f) ]
        threads = []

        if cls.settings.verbose_level > 0:
            print('Extracting archives...')

        for arch in archives:
            log = Log(arch)
            cls._logs[log.node_name.lower()] = log
            t = Thread(target=log.extract)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        if cls.settings.verbose_level > 0:
            print('Extraction complete.')

    @staticmethod
    def __is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    @classmethod
    def _get_next_free_port(cls):
        with cls.__lock:
            while cls.__is_port_in_use(cls._current_port):
                cls._current_port += 1
        return cls._current_port
    