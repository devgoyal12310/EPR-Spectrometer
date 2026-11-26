"""EPRHardware.py: runs one measurement (both phase cycles) and reads the field and temperature."""
import math
import types
from unittest import mock

import numpy as np
import pytest

from support import fixed_by, loadmat, make_scope


class FakeOsc:
    """The oscilloscope driver as EPRHardware.run uses it."""

    def __init__(self):
        self.calls = []

    def oscilloscope_init(self, nframes):
        self.calls.append(("init", nframes))

    def check_acquisition_status(self, *args, **kwargs):
        self.calls.append(("wait", args, kwargs))

    def scope_run(self, channels, parameters):
        self.calls.append(("read", tuple(channels)))
        n = len([c for c in self.calls if c[0] == "read"])
        return {"time": np.arange(4), "channel_data": {"ch1": np.full(4, float(n))}, "time_step": 1e-9}


def make_hardware(machine=0, field=lambda: 3400.5, temperature=lambda: 4.2):
    import EPRHardware
    hw = EPRHardware.EPRHardware.__new__(EPRHardware.EPRHardware)  # don't connect to anything
    hw.Machine, hw.time_checks = machine, 0
    hw.Machine_Name = "Oxford" if machine == 0 else "QMUL"
    hw.device, hw.session = mock.MagicMock(), mock.MagicMock()
    hw.MWSource, hw.SR830 = mock.MagicMock(), mock.MagicMock()
    hw.Osc = FakeOsc()
    hw.acquisition_timeout_factor, hw.acquisition_timeout_margin_s = 2.0, 120.0
    hw.read_magnetic_field = field
    hw.ITC = types.SimpleNamespace(get_temperature=temperature)
    hw.initialize(9.7, 100e6)
    return hw


def run(hw, phase_cycle=True, **parameters):
    params = types.SimpleNamespace(shots_number=1000, oscilloscope_wait_time=5.0, **parameters)
    return hw.run(params, "pos", "neg", "p1", lambda ct: None, lambda ct: None, phase_cycle)


def offline():
    raise OSError("not responding")


def test_run_records_field_and_temperature():
    result = run(make_hardware())
    assert result["field_before"] == 3400.5
    assert result["field_after"] == 3400.5
    assert result["temperature"] == 4.2
    assert result["Machine"] == "Oxford"


def test_phase_cycle_measures_positive_and_negative():
    hw = make_hardware()
    result = run(hw)
    assert [c[0] for c in hw.Osc.calls].count("read") == 2
    assert result["positive_channel_data"]["ch1"][0] == 1
    assert result["negative_channel_data"]["ch1"][0] == 2


def test_without_phase_cycle_negative_is_the_positive_data():
    hw = make_hardware()
    result = run(hw, phase_cycle=False)
    assert [c[0] for c in hw.Osc.calls].count("read") == 1
    assert result["negative_channel_data"] is result["positive_channel_data"]


def test_programs_are_loaded_on_both_awg_cores():
    hw = make_hardware()
    run(hw)
    loads = [c for c in hw.device.mock_calls if "load_sequencer_program" in str(c)]
    assert [c.args[0] for c in loads] == ["pos", "p1", "neg"]


@fixed_by(6, "a field-sensor failure discards the scope data from the run")
def test_field_sensor_failure_records_nan_and_keeps_the_data():
    with pytest.warns(RuntimeWarning, match="magnetic field"):
        result = run(make_hardware(field=offline))
    assert math.isnan(result["field_before"]) and math.isnan(result["field_after"])
    assert result["temperature"] == 4.2
    assert "ch1" in result["positive_channel_data"]


@fixed_by(6, "an ITC failure discards the scope data from the run")
def test_temperature_failure_records_nan_and_keeps_the_data():
    with pytest.warns(RuntimeWarning, match="temperature"):
        result = run(make_hardware(temperature=offline))
    assert math.isnan(result["temperature"])
    assert result["field_before"] == 3400.5


@fixed_by(6, "QMUL results hold None, which scipy.io.savemat can't write")
def test_qmul_result_can_be_saved(save_dir):
    result = run(make_hardware(machine=1))
    path = make_scope().save_data_to_matlab(exp_data=result, exp_parameters={"a": 1},
                                            save_directory=str(save_dir), file_name="qmul")
    assert loadmat(path)["esr_experiment_data"]["Machine"] == "QMUL"


@fixed_by(8, "the wait for the scope has no time limit")
def test_scope_wait_gets_a_time_limit_from_the_expected_duration():
    hw = make_hardware()
    run(hw)
    waits = [c for c in hw.Osc.calls if c[0] == "wait"]
    assert waits and all(c[1] == (2 * 5.0 + 120.0, False) for c in waits)


@fixed_by(8, "the wait for the scope has no time limit")
def test_abort_on_acquisition_timeout_is_passed_to_the_scope():
    hw = make_hardware()
    run(hw, abort_on_acquisition_timeout=True)
    assert all(c[1][1] is True for c in hw.Osc.calls if c[0] == "wait")


def test_read_magnetic_field_parses_the_sensor_reply():
    import EPRHardware
    hw = EPRHardware.EPRHardware.__new__(EPRHardware.EPRHardware)
    hw.field_sensor_ip = "sensor"
    reply = mock.Mock(json=lambda: "3381.25")
    hw.field_sensor_session = mock.Mock(get=mock.Mock(return_value=reply))
    assert hw.read_magnetic_field() == 3381.25
    url = hw.field_sensor_session.get.call_args.args[0]
    assert url == "http://sensor/io/t1/probe/average_field/value.json"
