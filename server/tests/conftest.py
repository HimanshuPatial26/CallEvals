"""Points DATA_DIR at a throwaway temp directory for the whole test session, before
anything imports app.config (which builds the Settings singleton — and therefore
resolves DATA_DIR — at import time). Without this, tests that write through the
storage module (e.g. PUT /api/settings) would land in the real ./data used by a
locally running dev server instead of an isolated sandbox.
"""

import os
import tempfile

_tmp_data_dir = tempfile.mkdtemp(prefix="callevals-test-data-")
os.environ["DATA_DIR"] = _tmp_data_dir
