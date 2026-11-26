"""Pulse Sequences/CPMG Sequence High Control/CPMGExp.py, with the settings from cpmg.py."""
from support import assert_programs_built, assert_saved, run_experiment

FOLDER = "Pulse Sequences/CPMG Sequence High Control/"


def run(save_dir, save=False, **overrides):
    return run_experiment(FOLDER + "CPMGExp.py", "CPMGExp", FOLDER + "CPMGParameters.py",
                          "CPMGParameters", FOLDER + "cpmg.py", save_dir, save=save, **overrides)


def test_builds_both_phase_cycles(save_dir):
    _, hardware = run(save_dir)
    assert_programs_built(hardware)


def test_saves_data_and_parameters(save_dir):
    result, _ = run(save_dir, save=True)
    assert_saved(result, save_dir)


def test_pulse_axis_changes_the_program(save_dir):
    _, x = run(save_dir, pi_by_two_axis="+X")
    _, y = run(save_dir, pi_by_two_axis="+Y")
    assert x.runs[0]["pos"] != y.runs[0]["pos"]
