import socket
import settings
from threading import Lock

__next_free_port = None
__lock = Lock()

def init():
    """Initialize module variables."""

    assert(settings.settings is not None)
    global __next_free_port

    __next_free_port = settings.settings.first_port

def is_port_in_use(port):
    """Check if the given port is being used.

    Arguments:
        port {int} -- Port to be tested.

    Returns:
        bool -- True if used, False otherwise.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_next_free_port():
    """Get the first available port.

    Returns:
        int -- The first port available
    """
    
    global __next_free_port

    with __lock:
        port = __next_free_port
        while is_port_in_use(port):
            port += 1
        __next_free_port = port + 1

    return port