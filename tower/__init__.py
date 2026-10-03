"""Tower system: bell simulator, strike analyser and information board."""

import os as _os
import sys as _sys

__version__ = "0.3.0"

# Production runs from /opt/tower/current, a symlink that an update repoints.
# Pin this process to the release it started from, so a lazy import after a
# swap can never load code from a different release.
__path__[:] = [_os.path.realpath(p) for p in __path__]
_sys.path[:] = [_os.path.realpath(p) if p else p for p in _sys.path]
