"""Sweep.py: runs an experiment once per sweep value and saves all points to one file."""
import types

import pytest

from support import fake_result, fixed_by

VALUES = [100, 200, 300, 400, 500]


class SaveRecorder:
    def __init__(self, fail=False):
        self.saves = []
        self.fail = fail

    def save_data_to_matlab(self, **kwargs):
        if self.fail:
            raise OSError("network drive not available")
        self.saves.append(kwargs)
        return "saved.mat"


def make_sweep(fail_at=None, error=RuntimeError, save_fails=False):
    """A Sweep over gap_len1_ns whose experiment raises `error` at point `fail_at` (1-based)."""
    from Sweep import Sweep
    seen = []

    class Experiment:
        def __init__(self, parameters, hardware):
            self.parameters = parameters

        def run(self, save=False):
            seen.append(self.parameters.gap_len1_ns)
            if len(seen) == fail_at:
                raise error("instrument problem")
            return fake_result()

    parameters = types.SimpleNamespace(gap_len1_ns=0, filename="sweep_", save_directory="unused")
    osc = SaveRecorder(fail=save_fails)
    sweep = Sweep(Experiment, parameters, types.SimpleNamespace(Osc=osc), "gap_len1_ns", VALUES)
    return sweep, osc, seen


def test_sets_the_parameter_before_each_point():
    sweep, _, seen = make_sweep()
    sweep.run()
    assert seen == VALUES


def test_completed_sweep_saves_all_points_once():
    sweep, osc, _ = make_sweep()
    result = sweep.run()
    assert len(osc.saves) == 1
    save = osc.saves[0]
    assert save["file_name"] == "sweep_"
    assert save["sweep_data"]["completed_points"] == len(VALUES)
    assert save["exp_data"]["positive_channel_data"]["ch1"].shape == (8, len(VALUES))
    assert len(save["exp_data"]["temperature"]) == len(VALUES)
    assert result["saved_path"] == "saved.mat"


def test_ctrl_c_saves_completed_points_then_stops():
    sweep, osc, _ = make_sweep(fail_at=3, error=KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        sweep.run()
    assert len(osc.saves) == 1
    assert osc.saves[0]["file_name"] == "sweep__INTERRUPTED"
    assert osc.saves[0]["sweep_data"]["completed_points"] == 2


@fixed_by(5, "an error part-way through a sweep loses every completed point")
def test_error_saves_completed_points_then_raises():
    sweep, osc, _ = make_sweep(fail_at=3, error=RuntimeError)
    with pytest.raises(RuntimeError):
        sweep.run()
    assert len(osc.saves) == 1
    assert osc.saves[0]["file_name"] == "sweep__INTERRUPTED"
    assert osc.saves[0]["sweep_data"]["completed_points"] == 2


@fixed_by(5, "a failed partial save hides the error that stopped the sweep")
def test_failed_partial_save_does_not_hide_the_original_error():
    sweep, _, _ = make_sweep(fail_at=3, error=KeyboardInterrupt, save_fails=True)
    with pytest.raises(KeyboardInterrupt):
        sweep.run()


def test_error_at_the_first_point_saves_nothing():
    sweep, osc, _ = make_sweep(fail_at=1, error=RuntimeError)
    with pytest.raises(RuntimeError):
        sweep.run()
    assert osc.saves == []
