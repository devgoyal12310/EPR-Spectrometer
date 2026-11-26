"""HardwareFiles/OscilloscopeTektronix.py: FastFrame set-up, waveform read-back, waiting, saving."""
import numpy as np
import pytest

from support import FakeClock, FakeScope, fixed_by, loadmat, make_scope


def init_and_read(nframes, maxframes=100000):
    scope = FakeScope(maxframes=maxframes)
    osc = make_scope(scope)
    osc.oscilloscope_init(nframes)
    result = osc.scope_run([1, 2], type("P", (), {"shots_number": nframes})())
    return scope, result


def test_fastframe_is_set_to_the_shot_count():
    scope = FakeScope()
    make_scope(scope).oscilloscope_init(50000)
    writes = scope.writes()
    assert "horizontal:fastframe:state on" in writes
    assert "horizontal:fastframe:count 50000" in writes
    assert ":horizontal:fastframe:selected:ch1 50001" in writes
    assert writes[-1] == "acquire:state on"


def test_trigger_is_set_to_the_aux_input():
    scope, _ = init_and_read(10)
    assert {"trigger:a:edge:source aux", "trigger:level:aux 1.2"} <= set(scope.writes())


def test_too_many_frames_are_clamped_with_a_warning():
    with pytest.warns(UserWarning, match="Maximum FastFrames Possible: 1000"):
        scope, _ = init_and_read(50000, maxframes=1000)
    assert "horizontal:fastframe:count 1000" in scope.writes()


def test_reads_the_summary_frame_after_the_last_shot():
    scope, _ = init_and_read(50000)
    assert set(scope.frames_read()) == {50001}


@fixed_by(7, "the summary frame read back ignores clamping")
def test_reads_the_summary_frame_of_the_clamped_count():
    with pytest.warns(UserWarning):
        scope, _ = init_and_read(50000, maxframes=1000)
    assert set(scope.frames_read()) == {1001}


@fixed_by(7, "a single shot reads frame 2, which doesn't exist without FastFrame")
def test_single_shot_reads_frame_1():
    scope, _ = init_and_read(1)
    assert "horizontal:fastframe:state on" not in scope.writes()
    assert set(scope.frames_read()) == {1}


def test_zero_frames_is_rejected():
    with pytest.raises(ValueError, match="cannot be 0"):
        make_scope(FakeScope()).oscilloscope_init(0)


@fixed_by(7, "an invalid frame count is only rejected after the scope has been reconfigured")
def test_zero_frames_is_rejected_before_anything_is_sent():
    scope = FakeScope()
    with pytest.raises(ValueError):
        make_scope(scope).oscilloscope_init(0)
    assert scope.log == []


def test_waveform_is_converted_to_volts_and_seconds():
    _, result = init_and_read(10)
    # raw levels 0..7, yoff 2, ymult 0.5, yzero 0.1
    np.testing.assert_allclose(result["channel_data"]["ch1"], (np.arange(8) - 2) * 0.5 + 0.1)
    np.testing.assert_allclose(result["time"], np.arange(8) * 1e-9)
    assert set(result["channel_data"]) == {"ch1", "ch2"}


def test_unsupported_waveform_format_is_an_error():
    scope = FakeScope()
    scope.replies["WFMOutpre:BN_Fmt?"] = "FP\n"
    with pytest.raises(ValueError, match="Unsupported waveform format"):
        make_scope(scope).obtain_waveform_from_frame_binary(1, 1)


def test_waits_until_the_acquisition_stops():
    scope = FakeScope(busy_polls=3)
    make_scope(scope).check_acquisition_status()
    assert scope.log.count("Q ACQUIRE:STATE?") == 4


def wait_with_fake_clock(monkeypatch, busy_polls, **kwargs):
    import HardwareFiles.OscilloscopeTektronix as module
    monkeypatch.setattr(module, "time", FakeClock())
    scope = FakeScope(busy_polls=busy_polls)
    make_scope(scope).check_acquisition_status(**kwargs)
    return scope


@fixed_by(8, "a scope that never finishes acquiring hangs the program silently")
def test_slow_acquisition_warns_and_keeps_waiting(monkeypatch):
    # 30 polls x 0.05 s = 1.5 s, against a 0.5 s limit
    with pytest.warns(RuntimeWarning, match="still running"):
        scope = wait_with_fake_clock(monkeypatch, 30, timeout_s=0.5, abort_on_timeout=False)
    assert scope.log.count("Q ACQUIRE:STATE?") == 31


@fixed_by(8, "a scope that never finishes acquiring hangs the program silently")
def test_slow_acquisition_can_abort(monkeypatch):
    with pytest.raises(TimeoutError):
        wait_with_fake_clock(monkeypatch, 30, timeout_s=0.5, abort_on_timeout=True)


def test_save_writes_data_and_parameters(save_dir):
    path = make_scope().save_data_to_matlab(
        exp_data={"ch1": np.arange(3.0)}, exp_parameters={"gap_len1_ns": 300},
        save_directory=str(save_dir / "new folder"), file_name="echo", sweep_data={"values": [1, 2]})
    saved = loadmat(path)
    assert path.endswith(".mat") and "echo_" in path
    np.testing.assert_array_equal(saved["esr_experiment_data"]["ch1"], [0, 1, 2])
    assert saved["esr_experiment_parameters"]["gap_len1_ns"] == 300
    np.testing.assert_array_equal(saved["esr_experiment_data"]["sweep_data"]["values"], [1, 2])
