"""Service Scripts/Power Calibration/HahnEchoExp.py, with the settings from single_check.py."""
from support import assert_programs_built, assert_saved, fixed_by, run_experiment

FOLDER = "Service Scripts/Power Calibration/"


def run(save_dir, save=False):
    return run_experiment(FOLDER + "HahnEchoExp.py", "HahnEchoExp",
                          FOLDER + "PulseOptimizationParameters.py", "PulseOptimizationParameters",
                          FOLDER + "single_check.py", save_dir, save=save)


def test_builds_both_phase_cycles(save_dir):
    _, hardware = run(save_dir)
    assert_programs_built(hardware)


@fixed_by(4, "the save call passes arguments save_data_to_matlab doesn't take")
def test_saves_data_and_parameters(save_dir):
    result, _ = run(save_dir, save=True)
    assert_saved(result, save_dir)
