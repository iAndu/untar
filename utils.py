import socket
from threading import Lock

lock = Lock()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_next_free_port(start_port):
    while is_port_in_use(start_port):
        start_port += 1
    return start_port