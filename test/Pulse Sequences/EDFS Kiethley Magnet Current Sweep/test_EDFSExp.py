"""Pulse Sequences/EDFS Kiethley Magnet Current Sweep/EDFSExp.py, with the settings from
edfs_sweep_keithley.py. Here B_field is the Keithley current in amps."""
import pyvisa

from support import FakeInstrument, FakeResourceManager, assert_programs_built, assert_saved, run_experiment

FOLDER = "Pulse Sequences/EDFS Kiethley Magnet Current Sweep/"


def run(monkeypatch, save_dir, current, save=False):
    from HardwareFiles.kiethleymagnet import kiethleymagnet
    fake = FakeInstrument({"*IDN?": "KEITHLEY,2470", ":READ?": "1.0E-01"})
    monkeypatch.setattr(pyvisa, "ResourceManager", FakeResourceManager({"GPIB1::18::INSTR": fake}))
    result, hardware = run_experiment(FOLDER + "EDFSExp.py", "EDFSExp", FOLDER + "EDFSParameters.py",
                                      "EDFSParameters", FOLDER + "edfs_sweep_keithley.py", save_dir,
                                      save=save, ctor_args=(kiethleymagnet(),), B_field=current)
    return result, hardware, fake


def test_sets_the_current_then_builds_the_programs(monkeypatch, save_dir):
    _, hardware, keithley = run(monkeypatch, save_dir, -0.4)
    assert ":SOUR:CURR:LEV -0.4" in keithley.writes()
    assert_programs_built(hardware)


def test_saves_data_and_parameters(monkeypatch, save_dir):
    result, _, _ = run(monkeypatch, save_dir, -0.4, save=True)
    assert_saved(result, save_dir)
