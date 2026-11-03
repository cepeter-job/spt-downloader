"""Native trust defaults for a new owned driver, without changing TLS checks."""
import os
import sys
import threading


_ENTRY_LOCK = threading.RLock()
_SYSTEM_CA = 'NODE_USE_SYSTEM_CA'


class _SystemCAManager:
    def __init__(self, manager):
        self.manager = manager

    def __enter__(self):
        # Node reads this option at process startup. Serialize only that entry;
        # the driver keeps its inherited default after Python restores its env.
        with _ENTRY_LOCK:
            if sys.platform != 'win32' or _SYSTEM_CA in os.environ:
                return self.manager.__enter__()
            os.environ[_SYSTEM_CA] = '1'
            try:
                return self.manager.__enter__()
            finally:
                # Preserve a caller update instead of overwriting its choice.
                if os.environ.get(_SYSTEM_CA) == '1':
                    os.environ.pop(_SYSTEM_CA, None)

    def __exit__(self, *args):
        return self.manager.__exit__(*args)


def system_ca_manager(manager):
    """Preserve the manager protocol and local factory/cleanup patch points."""
    return _SystemCAManager(manager)
