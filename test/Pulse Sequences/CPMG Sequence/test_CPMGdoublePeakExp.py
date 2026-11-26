"""Pulse Sequences/CPMG Sequence/CPMGdoublePeakExp.py, with the settings from cpmg_double_peak.py."""
from support import assert_programs_built, assert_saved, fixed_by, load, run_experiment

FOLDER = "Pulse Sequences/CPMG Sequence/"


def run(save_dir, save=False):
    return run_experiment(FOLDER + "CPMGdoublePeakExp.py", "CPMGdoublePeakExp",
                          FOLDER + "CPMGdoublePeakParameters.py", "CPMGdoublePeakParameters",
                          FOLDER + "cpmg_double_peak.py", save_dir, save=save)


@fixed_by(3, "CPMGdoublePeakParameters() raises NameError (cpmg_pulse_axis = X)")
def test_parameters_can_be_created():
    parameters = load(FOLDER + "CPMGdoublePeakParameters.py").CPMGdoublePeakParameters()
    assert parameters.cpmg_pulse_axis == "+X"


@fixed_by(3, "CPMGdoublePeakParameters() raises NameError (cpmg_pulse_axis = X)")
def test_builds_both_phase_cycles(save_dir):
    _, hardware = run(save_dir)
    assert_programs_built(hardware)


@fixed_by(4, "the save call passes arguments save_data_to_matlab doesn't take (also needs #3)")
def test_saves_data_and_parameters(save_dir):
    result, _ = run(save_dir, save=True)
    assert_saved(result, save_dir)
