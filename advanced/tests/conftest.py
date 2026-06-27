"""pytest session setup — isolate the demo store's persistence file so test
runs don't leak enrolled users into each other or into the repo."""
import os
import tempfile

os.environ["MEDITECH_DEMO"] = "1"
_TEST_USERS = os.path.join(tempfile.gettempdir(), "meditech_test_users.json")
os.environ["MEDITECH_USERS_FILE"] = _TEST_USERS
if os.path.exists(_TEST_USERS):
    os.remove(_TEST_USERS)
