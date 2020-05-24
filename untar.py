import atexit
import argparse
from app import App
import settings
from settings import Settings
import utils

def build_parser():
    parser = argparse.ArgumentParser(description='Unpack logs and open oscilloscope in browser for each IPS trace. Run in a directory with the packed logs and the oscilloscope executable.')
    parser.prog = "untar.exe"

    parser.add_argument('--browser', '-b',
                    default='chrome',
                    const='chrome',
                    nargs='?',
                    choices=['chrome', 'opera', 'firefox', 'edge'],
                    help='The browser used to open traces (default: %(default)s)')

    parser.add_argument('--start-all', '-s', action="store_true", help="Start oscilloscope on all nodes right away")
    parser.add_argument("--port", '-p', default=8080, type=int, help="First port to use")
    parser.add_argument("--keep", '-k', action="store_true", help="Keep .tgz files")

    return parser

def main():
    utils.init()
    App().cmdloop()
            
if __name__ == "__main__":
    args = build_parser().parse_args()
    settings.settings = Settings(browser=args.browser,
                                 keep_archives=args.keep,
                                 first_port=args.port,
                                 start_all=args.start_all)
    main()
