"""pytest set-up: make the repo importable, and keep every test away from real hardware."""
import os
import sys
import types
from unittest import mock

import pytest

sys.dont_write_bytecode = True  # leave no __pycache__ folders in the repo

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TEST_DIR)
for path in (TEST_DIR, ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("MPLBACKEND", "Agg")  # plots render off-screen

# The Zurich Instruments toolkit is only needed to talk to the HDAWG.
if "zhinst.toolkit" not in sys.modules:
    _zh, _zt = types.ModuleType("zhinst"), types.ModuleType("zhinst.toolkit")
    _zt.Session, _zt.CommandTable = mock.MagicMock(), mock.MagicMock()
    _zh.toolkit = _zt
    sys.modules["zhinst"], sys.modules["zhinst.toolkit"] = _zh, _zt


@pytest.fixture(autouse=True)
def no_real_waiting(monkeypatch):
    """Instrument settling and polling sleeps take no time."""
    import time
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)


@pytest.fixture(autouse=True)
def no_real_instruments(monkeypatch):
    """Opening a VISA resource that a test didn't fake is an error, never a real connection."""
    import pyvisa

    def refuse(*args, **kwargs):
        raise AssertionError("test tried to open a real VISA ResourceManager; fake it")

    monkeypatch.setattr(pyvisa, "ResourceManager", refuse)


@pytest.fixture
def save_dir():
    """An empty folder for saved data, deleted afterwards."""
    import pathlib
    import shutil
    import tempfile
    folder = tempfile.mkdtemp(prefix="epr_test_")
    yield pathlib.Path(folder)
    shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    import matplotlib.pyplot as plt
    plt.close("all")
