"""Redirects filesystem-backed storage (storage.py, roster_storage.py,
lead_storage.py) at a throwaway temp directory for the whole test session,
before any app module is imported. Those modules compute their directory
paths from settings.data_dir once at import time, so this has to happen
here — in a conftest.py, which pytest loads before collecting test modules
— not in a fixture, which would run too late to matter.

Without this, tests that exercise the real routers (creating agents,
leads, calls) write real files into server/data/, permanently polluting
whatever a developer has stored there.
"""

import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="callevals-test-data-")
