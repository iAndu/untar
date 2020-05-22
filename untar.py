import atexit
import argparse
import re
from threading import Thread
from app import App

parser = None

def build_parser():
    global parser
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

# def close_procs():
#     for p, _ in processes.values():
#         p.kill()

def main():
    App.extract_archives()

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
                    location = match.group(2) if match.group(2) is not None else '1'
                    t = Thread(target=App.start_osc, args=(node, location))
                    t.start()
                    threads.append(t)

            for t in threads:
                t.join()
        op = input('').strip().lower()
            
if __name__ == "__main__":
    # atexit.register(close_procs)

    build_parser()

    args = parser.parse_args()

    PORT = args.port
    browser = args.browser
    # if browser == "edge":
    #     browser_start_string += "microsoft-edge:"
    # else:
    #     browser_start_string += browser + " "
    start_browser = args.no_open
    keep_files = args.keep

    main()
