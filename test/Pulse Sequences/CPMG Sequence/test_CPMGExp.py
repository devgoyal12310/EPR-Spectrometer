"""Pulse Sequences/CPMG Sequence/CPMGExp.py, with the settings from cpmg.py."""
import pytest

from support import assert_programs_built, assert_saved, fixed_by, run_experiment

FOLDER = "Pulse Sequences/CPMG Sequence/"


def run(save_dir, save=False, **overrides):
    return run_experiment(FOLDER + "CPMGExp.py", "CPMGExp", FOLDER + "CPMGParameters.py",
                          "CPMGParameters", FOLDER + "cpmg.py", save_dir, save=save, **overrides)


def test_builds_both_phase_cycles(save_dir):
    _, hardware = run(save_dir)
    assert_programs_built(hardware)


def test_saves_data_and_parameters(save_dir):
    result, _ = run(save_dir, save=True)
    _, parameters = assert_saved(result, save_dir)
    assert "cpmg_count" in parameters


def test_more_refocusing_pulses_change_the_program(save_dir):
    _, few = run(save_dir, cpmg_count=4)
    _, many = run(save_dir, cpmg_count=8)
    assert few.runs[0]["pos"] != many.runs[0]["pos"]


# The trigger pulse is played in section 4 (detection), so it must fit in section 4.
@fixed_by(11, "the trigger is checked against section 3 instead of the detection section")
def test_long_tau_is_accepted(save_dir):
    run(save_dir, seq_offset_ns=800, trigger_offset_ns=100, gap_len1_ns=2000, switch_pulse_ns=1000,
        cpmg_gap_len_ns=1600)


@fixed_by(11, "the trigger is checked against section 3 instead of the detection section")
def test_trigger_past_the_detection_section_is_rejected(save_dir):
    with pytest.raises(ValueError, match="Trigger offset"):
        run(save_dir, seq_offset_ns=800, trigger_offset_ns=500, gap_len1_ns=800, switch_pulse_ns=1000,
            cpmg_gap_len_ns=1600)
