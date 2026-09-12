import fcntl
import tempfile
from contextlib import contextmanager
from pathlib import Path


class AlreadyRunningError(RuntimeError):
    """Raised when another process owns the project lock."""


@contextmanager
def single_instance_lock(lock_name="autoposter-template.lock"):
    """Prevent two local publishers from running concurrently."""

    lock_path = Path(tempfile.gettempdir()) / lock_name
    lock_file = lock_path.open("a+", encoding="utf-8")

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        lock_file.close()
        raise AlreadyRunningError from error

    try:
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

