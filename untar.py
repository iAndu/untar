import atexit
import argparse
import re
from threading import Thread
from app import App
import settings
from settings import Settings

def build_parser():
    parser = argparse.ArgumentParser(description='Unpack logs and open oscilloscope in browser for each IPS trace. Run in a directory with the packed logs and the oscilloscope executable.')
    parser.prog = "untar.exe"

    parser.add_argument('--browser', '-b',
                    default='chrome',
                    const='chrome',
                    nargs='?',
                    choices=['chrome', 'opera', 'firefox', 'edge'],
                    help='The browser used to open traces (default: %(default)s)')

    parser.add_argument('--no-open', '-n', action="store_false", help="Don't open in browser")
    parser.add_argument("--port", '-p', default=8080, type=int, help="First port to use")
    parser.add_argument("--keep", '-k', action="store_true", help="Keep .tgz files")

    return parser

# def close_procs():
#     for p, _ in processes.values():
#         p.kill()

def main():
    # App().start()
    app = App()
    app.extract_archives()

    op = input('CLI ready\n').strip().lower()

    while op == '' or not "exit".startswith(op):
        if op == '':
            op = input('').strip().lower()
            continue

        tokens = list(filter(None, op.split(' ')))
        cmd = tokens.pop(0)

        if "oscilloscope".startswith(cmd):
            pattern = re.compile(r'([\w\d]+)(?:\.(\d+))?')
            threads = []

            for token in tokens:
                match = pattern.match(token)
                if match:
                    node = match.group(1)
                    location_id = match.group(2) if match.group(2) is not None else '1'
                    t = Thread(target=app.start_osc, args=(node, location_id))
                    t.start()
                    threads.append(t)

            for t in threads:
                t.join()
        op = input('').strip().lower()
            
if __name__ == "__main__":
    # atexit.register(close_procs)

    args = build_parser().parse_args()

    settings.settings = Settings(browser=args.browser,
                                 keep_archives=args.keep,
                                 first_port=args.port)

    main()
