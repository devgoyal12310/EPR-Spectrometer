"""Pulse Sequences/EDFS PS Magnet/EDFSExp.py, with the settings from edfs_sweep.py."""
import pyvisa

from support import (PS10360_ADDRESS, FakePS, FakeResourceManager, assert_programs_built,
                     assert_saved, fixed_by, run_experiment)

FOLDER = "Pulse Sequences/EDFS PS Magnet/"


def make_magnet(monkeypatch):
    from HardwareFiles.PS10360 import PS10360
    fake = FakePS()
    monkeypatch.setattr(pyvisa, "ResourceManager", FakeResourceManager({PS10360_ADDRESS: fake}))
    return PS10360(), fake


def run(monkeypatch, save_dir, field, save=False):
    magnet, fake = make_magnet(monkeypatch)
    result, hardware = run_experiment(FOLDER + "EDFSExp.py", "EDFSExp", FOLDER + "EDFSParameters.py",
                                      "EDFSParameters", FOLDER + "edfs_sweep.py", save_dir,
                                      save=save, ctor_args=(magnet,), B_field=field)
    return result, hardware, fake


def test_sets_the_field_then_builds_the_programs(monkeypatch, save_dir):
    _, hardware, magnet = run(monkeypatch, save_dir, 3400)
    assert "SOUR:CURR 11.1156 A" in magnet.writes()
    assert_programs_built(hardware)


def test_saves_data_and_the_field(monkeypatch, save_dir):
    result, _, _ = run(monkeypatch, save_dir, 3400, save=True)
    _, parameters = assert_saved(result, save_dir)
    assert parameters["B_field"] == 3400


def test_zero_field(monkeypatch, save_dir):
    _, _, magnet = run(monkeypatch, save_dir, 0)
    assert "SOUR:CURR 0.0000 A" in magnet.writes()


@fixed_by(10, "fields between 0 and ~38.8 G raise ZeroDivisionError")
def test_field_below_the_calibration_offset(monkeypatch, save_dir):
    _, _, magnet = run(monkeypatch, save_dir, 20)
    assert "SOUR:CURR 0.0000 A" in magnet.writes()
