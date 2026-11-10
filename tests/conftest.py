"""Keep the test suite on the mock client. Never load a live workspace token."""
import os

os.environ["OTARI_MODE"] = "mock"
os.environ.pop("OTARI_API_KEY", None)
os.environ.pop("OTARI_API_KEY_WEST", None)
