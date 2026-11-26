"""Pulse Sequences/Hahn Echo/HahnEchoExp.py, with the settings from hahnecho.py."""
import pytest

from support import assert_programs_built, assert_saved, run_experiment

FOLDER = "Pulse Sequences/Hahn Echo/"


def run(save_dir, save=False, **overrides):
    return run_experiment(FOLDER + "HahnEchoExp.py", "HahnEchoExp",
                          FOLDER + "HahnEchoParameters.py", "HahnEchoParameters",
                          FOLDER + "hahnecho.py", save_dir, save=save, **overrides)


def test_builds_both_phase_cycles(save_dir):
    _, hardware = run(save_dir)
    assert_programs_built(hardware)


def test_saves_data_and_parameters(save_dir):
    result, _ = run(save_dir, save=True)
    _, parameters = assert_saved(result, save_dir)
    # Hahn Echo saves parameters.to_dict(), which uses its own names
    assert parameters["gap_len1"] == 300
    assert parameters["number_of_shots"] == 50000


def test_longer_tau_changes_the_program(save_dir):
    _, short = run(save_dir, gap_len1_ns=300)
    _, long = run(save_dir, gap_len1_ns=3000)
    assert short.runs[0]["pos"] != long.runs[0]["pos"]


def test_trigger_beyond_the_detection_window_is_rejected(save_dir):
    with pytest.raises(ValueError, match="Trigger offset"):
        run(save_dir, trigger_offset_ns=500)
