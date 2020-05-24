global settings
settings = None

class Settings(object):
    __instance = None

    def __init__(self, 
                browser='chrome',
                keep_archives=False, 
                first_port=8080,
                start_all=False,
                folder_format='node%s',
                verbose_level=1,
                osc_path='oscilloscope.exe'):
        if Settings.__instance is not None:
            raise Exception('Settings is a singleton class!')

        self.browser = browser

        self._browser_start_string = 'start '
        if self.browser == "edge":
            self._browser_start_string += "microsoft-edge:"
        else:
            self._browser_start_string += self.browser + " "

        if '%s' not in folder_format:
            print('Folder format invalid. Defaulting to "%s".')
        else:
            self.folder_format = folder_format

        self.keep_archives = keep_archives
        self.first_port = first_port
        self.start_all = start_all
        self.verbose_level = verbose_level
        self.osc_path = osc_path
    
    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls()
        return cls.__instance