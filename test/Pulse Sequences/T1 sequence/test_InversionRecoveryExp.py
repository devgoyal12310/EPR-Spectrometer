"""Pulse Sequences/T1 sequence/InversionRecoveryExp.py, with the settings from sweep_parameters.py."""
from support import assert_programs_built, assert_saved, fixed_by, load, run_experiment

FOLDER = "Pulse Sequences/T1 sequence/"


def run(save_dir, save=False):
    return run_experiment(FOLDER + "InversionRecoveryExp.py", "InversionRecoveryExp",
                          FOLDER + "InversionRecoveryParameters.py", "InversionRecoveryParameters",
                          FOLDER + "sweep_parameters.py", save_dir, save=save)


@fixed_by(2, "imports HahnEchoHardware, which no longer exists")
def test_can_be_imported():
    load(FOLDER + "InversionRecoveryExp.py")


@fixed_by(2, "imports HahnEchoHardware, which no longer exists")
def test_builds_both_phase_cycles(save_dir):
    _, hardware = run(save_dir)
    assert_programs_built(hardware)


@fixed_by(2, "imports HahnEchoHardware, which no longer exists")
def test_saves_data_and_parameters(save_dir):
    result, _ = run(save_dir, save=True)
    assert_saved(result, save_dir)
