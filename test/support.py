"""Fakes and helpers shared by the tests. No real instrument is ever opened."""
import importlib.util
import os
import re
import sys

import numpy as np
import pyvisa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PR_URL = "https://github.com/devgoyal12310/EPR-Spectrometer/pull/"


def fixed_by(pr, what):
    """Mark a test of a bug that an open PR fixes.

    Until the PR is merged the test is expected to fail (reported as `xfail`). Once it is
    merged the test passes (reported as `XPASS`), and the marker should then be removed so
    the test guards against the bug coming back.
    """
    import pytest
    return pytest.mark.xfail(reason=f"{what}: fixed by {PR_URL}{pr}, not merged yet", strict=False)


_loaded = {}


def load(rel_path):
    """Import a repo file by path. Several folders reuse module names (CPMGExp, HahnEchoExp),
    so each file gets its own module name."""
    if rel_path in _loaded:
        return _loaded[rel_path]
    full = os.path.join(ROOT, rel_path)
    name = "repo_" + re.sub(r"\W", "_", rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(full))  # sibling imports inside that folder
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    _loaded[rel_path] = module
    return module


ASSIGN = re.compile(r"^\s*(parameters\.\w+\s*=\s*[^#\n]+)")


def apply_lab_settings(parameters, rel_script):
    """Apply every `parameters.x = ...` line of a lab script, in order.

    The experiment tests use the same settings as the lab scripts, so they stay in step
    with them. Loop variables used in some scripts (i, q, k, j) get fixed values.
    """
    with open(os.path.join(ROOT, rel_script), encoding="utf-8", errors="replace") as f:
        for line in f:
            match = ASSIGN.match(line)
            if match:
                try:
                    exec(match.group(1), {"parameters": parameters, "np": np,
                                          "i": 0.0, "q": 4, "k": 1, "j": 1})
                except Exception:
                    pass
    return parameters


# ----------------------------------------------------------------------------- VISA
class FakeInstrument:
    """Records writes and queries. `replies` maps a query to its answer (default '0');
    `on_write(command)` can queue answers for read()."""

    def __init__(self, replies=None):
        self.log = []
        self.replies = dict(replies or {})
        self.read_queue = []

    def write(self, command):
        self.log.append("W " + command)
        self.on_write(command)

    def on_write(self, command):
        pass

    def query(self, command):
        self.log.append("Q " + command)
        reply = self.replies.get(command, "0")
        return reply() if callable(reply) else reply

    def read(self):
        if not self.read_queue:
            raise pyvisa.errors.VisaIOError(pyvisa.constants.StatusCode.error_timeout)
        reply = self.read_queue.pop(0)
        self.log.append("R " + reply)
        return reply

    def query_binary_values(self, command, **kwargs):
        self.log.append("B " + command)
        return np.arange(8)

    def set_visa_attribute(self, *args):
        pass

    def close(self):
        self.log.append("close")

    def writes(self):
        return [entry[2:] for entry in self.log if entry.startswith("W ")]


class FakeResourceManager:
    """Use with monkeypatch.setattr(pyvisa, "ResourceManager", rm) where rm = FakeResourceManager(...)."""

    def __init__(self, instruments):
        self.instruments = instruments  # address -> FakeInstrument

    def __call__(self, *args, **kwargs):
        return self

    def open_resource(self, address, *args, **kwargs):
        return self.instruments.setdefault(address, FakeInstrument())

    def list_resources(self):
        return tuple(self.instruments)


class FakeScope(FakeInstrument):
    def __init__(self, maxframes=100000, busy_polls=2):
        super().__init__({
            "HORizontal:FASTframe:MAXFRames?": str(maxframes), "HORizontal:ACQLENGTH?": "8",
            "WFMOutpre:BYT_Nr?": "1", "WFMOutpre:BN_Fmt?": "RI\n", "wfmoutpre:ymult?": "0.5",
            "wfmoutpre:yzero?": "0.1", "wfmoutpre:yoff?": "2", "wfmoutpre:xincr?": "1e-9",
        })
        self.busy_polls = busy_polls
        self.replies["ACQUIRE:STATE?"] = self._state

    def _state(self):
        if self.busy_polls > 0:
            self.busy_polls -= 1
            return "1"
        return "0"

    def frames_read(self):
        return [int(w.split()[1]) for w in self.writes() if w.startswith(":data:framestart")]


PS10360_ADDRESS = "TCPIP0::100.100.100.4::5025::SOCKET"


class FakePS(FakeInstrument):
    """Reports back the current it was set to; voltage follows the calibrated resistance."""

    def __init__(self, resistance_offset=0.0):
        super().__init__()
        self.current = 0.0
        self.resistance_offset = resistance_offset
        self.replies["MEAS:CURR:DC?"] = lambda: f"{self.current:.4f} A"
        self.replies["MEAS:VOLT:DC?"] = self.voltage

    def on_write(self, command):
        if command.startswith("SOUR:CURR "):
            self.current = float(command.split()[1])

    def voltage(self):
        field = 10 * (self.current + 0.1282) / 0.03307
        resistance = 2.580871 + field * 1.765071e-05 + self.resistance_offset
        return f"{self.current * resistance:.4f} V"


def make_scope(fake=None):
    """A real OscilloscopeTektronix driver talking to a fake scope."""
    from HardwareFiles.OscilloscopeTektronix import OscilloscopeTektronix
    osc = OscilloscopeTektronix.__new__(OscilloscopeTektronix)  # skip opening a VISA resource
    osc.oscilloscope = fake
    osc.nframes_offset = 1
    return osc


class FakeClock:
    """Stands in for a module's `time`: sleep() moves a fake clock instead of waiting."""

    def __init__(self):
        self.t = 0.0

    def sleep(self, seconds):
        self.t += seconds

    def perf_counter(self):
        return self.t


# ----------------------------------------------------------------------------- experiments
def fake_result(machine="Oxford"):
    """What EPRHardware.run returns, with small made-up traces."""
    pos = {"ch1": np.linspace(0, 1, 8), "ch2": np.linspace(1, 0, 8)}
    return {"temperature": 4.2, "time": np.arange(8) * 1e-9, "oscilloscope_time_step": 1e-9,
            "positive_channel_data": pos,
            "negative_channel_data": {k: -v for k, v in pos.items()},
            "field_before": 3400.0, "field_after": 3401.0, "Machine": machine}


class TableRecorder:
    """Records command-table assignments such as ct.table[0].amplitude0.value = 0.5."""

    def __init__(self, path="ct", log=None):
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "log", [] if log is None else log)

    def __getattr__(self, name):
        return TableRecorder(f"{self._path}.{name}", self.log)

    def __getitem__(self, index):
        return TableRecorder(f"{self._path}[{index}]", self.log)

    def __setattr__(self, name, value):
        self.log.append((f"{self._path}.{name}", value))


class RecordingHardware:
    """Stands in for EPRHardware in an experiment: keeps the SeqC programs and command
    tables it's given, returns fake_result(), and saves with the real driver code."""

    def __init__(self):
        self.Osc = make_scope()
        self.runs = []

    def run(self, parameters, seq_prog_pos, seq_prog_neg, seq_prog_1, mw_table, rf_table,
            phase_cycle=True):
        mw, rf = TableRecorder(), TableRecorder()
        mw_table(mw)
        rf_table(rf)
        self.runs.append({"pos": seq_prog_pos, "neg": seq_prog_neg, "p1": seq_prog_1,
                          "mw_table": mw.log, "rf_table": rf.log, "phase_cycle": phase_cycle})
        return fake_result()


def loadmat(path):
    import scipy.io
    return scipy.io.loadmat(path, simplify_cells=True)


def run_experiment(exp_file, exp_class, params_file, params_class, lab_script, save_dir,
                   save=False, ctor_args=(), **overrides):
    """Build an experiment with the settings from `lab_script`, run it on RecordingHardware,
    and return (result, hardware). Saved files go to save_dir."""
    import inspect
    parameters = getattr(load(params_file), params_class)()
    apply_lab_settings(parameters, lab_script)
    for name, value in overrides.items():
        setattr(parameters, name, value)
    parameters.save_directory = str(save_dir)
    parameters.filename = "test_"
    cls = getattr(load(exp_file), exp_class)
    hardware = RecordingHardware()
    kwargs = {}
    if "save_directory" in inspect.signature(cls.__init__).parameters:
        kwargs["save_directory"] = str(save_dir)
    experiment = cls(parameters, hardware, *ctor_args, **kwargs)
    return experiment.run(save=save), hardware


def assert_programs_built(hardware, phase_cycle=True):
    """One run, with SeqC programs for both AWG cores and a filled command table."""
    assert len(hardware.runs) == 1
    run = hardware.runs[0]
    for key in ("pos", "neg", "p1"):
        assert isinstance(run[key], str) and run[key].strip(), key
    if phase_cycle:
        assert run["pos"] != run["neg"], "the two phase cycles use the same program"
    assert run["mw_table"], "no command-table entries"


def assert_saved(result, save_dir):
    path = result["saved_path"]
    assert os.path.dirname(os.path.abspath(path)) == os.path.abspath(str(save_dir))
    saved = loadmat(path)
    data, parameters = saved["esr_experiment_data"], saved["esr_experiment_parameters"]
    assert {"positive_channel_data", "negative_channel_data", "time"} <= set(data)
    assert parameters, "no parameters saved"
    return data, parameters
