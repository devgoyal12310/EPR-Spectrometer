"""Fake-hardware behaviour harness for the EPR spectrometer code.

Runs every scenario against one checkout of the repository and writes what it
observed to a JSON file:

  * programs: every lab script, end-to-end on the virtual rig (virtual_rig.py), with
    every command sent to every instrument, the SeqC programs and command tables
    uploaded to the HDAWG, saved data, printed output and how the run ended;
  * faults: some of those programs again, with an instrument misbehaving;
  * driver checks: targeted cases for individual drivers and validation checks.

check_pr.py runs this on a PR's base and on the merge result and reports every
difference. Nothing here talks to real hardware or the network, and nothing outside
this folder imports it.

Usage:
    python debug/fake_hardware_harness.py [REPO_ROOT] [OUT_JSON]

REPO_ROOT defaults to the checkout containing this file; OUT_JSON defaults to
harness_results.json in the current directory.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import types
import warnings
from unittest import mock

sys.dont_write_bytecode = True  # do not leave __pycache__ folders in the checkout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)
OUT = sys.argv[2] if len(sys.argv) > 2 else "harness_results.json"

os.environ["MPLBACKEND"] = "Agg"  # live plots render off-screen
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "HardwareFiles"))

# The Zurich Instruments toolkit is only needed to talk to the HDAWG; stub it.
_zh = types.ModuleType("zhinst")
_zt = types.ModuleType("zhinst.toolkit")
_zt.Session = mock.MagicMock()
_zt.CommandTable = mock.MagicMock()
_zh.toolkit = _zt
sys.modules["zhinst"] = _zh
sys.modules["zhinst.toolkit"] = _zt

import time as _time  # noqa: E402

import numpy as np  # noqa: E402
import pyvisa  # noqa: E402

_time.sleep = lambda *_a, **_k: None  # no real waiting (instrument settling, polling)

TMP = tempfile.mkdtemp(prefix="epr_harness_")
results = {}


# ----------------------------------------------------------------------------- helpers
def h(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def clean(text, limit):
    """Drop the checkout's own path so results from two checkouts compare equal."""
    for root in {ROOT, ROOT.replace("\\", "/"), ROOT.replace("/", "\\")}:
        text = text.replace(root, "<repo>")
    return text[:limit]


def scenario(name):
    """Run fn now and record its output, warnings, or exception under `name`."""
    def deco(fn):
        try:
            with warnings.catch_warnings(record=True) as caught, \
                    contextlib.redirect_stdout(io.StringIO()):
                warnings.simplefilter("always")
                out = fn()
            results[name] = {"ok": True, "out": out,
                             "warnings": [clean(str(w.message), 120) for w in caught]}
        except BaseException as error:  # noqa: B902 - KeyboardInterrupt etc. are scenarios too
            results[name] = {"ok": False, "error": type(error).__name__,
                             "msg": clean(str(error), 200)}
        return fn
    return deco


_loaded = {}


def load(rel_path):
    """Import a repo file by path (several folders reuse module names like CPMGExp)."""
    if rel_path in _loaded:
        return _loaded[rel_path]
    full = os.path.join(ROOT, rel_path)
    name = "harness_" + h(rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(full))  # for sibling imports inside that folder
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    _loaded[rel_path] = module
    return module


class Rec:
    """Records attribute assignments such as ct.table[0].amplitude0.value = 0.5."""
    def __init__(self, path, log):
        object.__setattr__(self, "_p", path)
        object.__setattr__(self, "_l", log)

    def __getattr__(self, name):
        return Rec(f"{self._p}.{name}", self._l)

    def __getitem__(self, index):
        return Rec(f"{self._p}[{index}]", self._l)

    def __setattr__(self, name, value):
        self._l.append(f"{self._p}.{name}={value!r}")


def fake_result(machine="Oxford", temp=4.2):
    t = np.arange(8) * 1e-9
    pos = {"ch1": np.linspace(0, 1, 8), "ch2": np.linspace(1, 0, 8)}
    neg = {"ch1": -pos["ch1"], "ch2": -pos["ch2"]}
    return {"temperature": temp, "time": t, "oscilloscope_time_step": 1e-9,
            "positive_channel_data": pos, "negative_channel_data": neg,
            "field_before": 3400.0, "field_after": 3401.0, "Machine": machine}


def make_osc(resource=None):
    from OscilloscopeTektronix import OscilloscopeTektronix
    osc = OscilloscopeTektronix.__new__(OscilloscopeTektronix)
    osc.oscilloscope = resource
    osc.nframes_offset = 1
    return osc


class FakeHW:
    """Stands in for EPRHardware inside Exp.run(): captures programs and command tables."""
    def __init__(self):
        self.Osc = make_osc()  # real save_data_to_matlab, no instrument
        self.calls = []

    def run(self, parameters, pos, neg, p1, mw, rf, phase_cycle=True):
        log_mw, log_rf = [], []
        mw(Rec("ct", log_mw))
        rf(Rec("ct", log_rf))
        self.calls.append({"pos": h(pos), "neg": h(neg), "p1": h(p1),
                           "ct_mw": log_mw, "ct_rf": log_rf, "phase_cycle": bool(phase_cycle)})
        return fake_result()


def saved_summary(path):
    import scipy.io
    mat = scipy.io.loadmat(path, simplify_cells=True)
    return {"keys": sorted(mat["esr_experiment_data"].keys()),
            "params": sorted(mat["esr_experiment_parameters"].keys())}


# ----------------------------------------------------------------------------- Sweep
class SweepParams:
    def __init__(self):
        self.gap_len1_ns = 300
        self.filename = "sweep_"
        self.save_directory = TMP


def sweep_run(fail_at=None, exc=RuntimeError):
    from Sweep import Sweep
    saves = []

    class Osc:
        def save_data_to_matlab(self, **kw):
            sd = kw["sweep_data"]
            saves.append({"file_name": kw["file_name"], "completed": int(sd["completed_points"]),
                          "n_temps": len(kw["exp_data"]["temperature"]),
                          "pos_shape": list(kw["exp_data"]["positive_channel_data"]["ch1"].shape),
                          "integrated": [round(float(x), 6) for x in sd["integrated_values"]]})
            return "saved"

    count = {"i": 0}

    class Exp:
        def __init__(self, parameters, hardware):
            pass

        def run(self, save=False):
            count["i"] += 1
            if fail_at is not None and count["i"] == fail_at:
                raise exc("boom")
            return fake_result()

    sweep = Sweep(Exp, SweepParams(), types.SimpleNamespace(Osc=Osc()), "gap_len1_ns",
                  [100, 200, 300, 400, 500])
    try:
        out = sweep.run()
        return {"saves": saves, "returned_saved_path": out["saved_path"]}
    except BaseException as error:  # noqa: B902
        return {"saves": saves, "raised": type(error).__name__}


scenario("sweep_normal")(lambda: sweep_run())
scenario("sweep_ctrl_c_at_3")(lambda: sweep_run(3, KeyboardInterrupt))
scenario("sweep_error_at_3")(lambda: sweep_run(3, RuntimeError))
scenario("sweep_error_at_1")(lambda: sweep_run(1, RuntimeError))


# ----------------------------------------------------------------------------- Oscilloscope
class FakeScope:
    def __init__(self, maxframes=100000, states=("1", "1", "0")):
        self.log = []
        self.maxframes = maxframes
        self.states = list(states)
        self.timeout = None

    def write(self, s):
        self.log.append("W " + s)

    def query(self, s):
        self.log.append("Q " + s)
        if s == "ACQUIRE:STATE?":
            return self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return {"HORizontal:FASTframe:MAXFRames?": str(self.maxframes),
                "HORizontal:ACQLENGTH?": "8", "WFMOutpre:BYT_Nr?": "1",
                "WFMOutpre:BN_Fmt?": "RI\n", "wfmoutpre:ymult?": "0.5",
                "wfmoutpre:yzero?": "0", "wfmoutpre:yoff?": "0",
                "wfmoutpre:xincr?": "1e-9"}[s]

    def query_binary_values(self, s, **kw):
        self.log.append("B " + s)
        return np.arange(8)


def scope_case(nframes, maxframes):
    scope = FakeScope(maxframes)
    osc = make_osc(scope)
    osc.oscilloscope_init(nframes)
    res = osc.scope_run([1, 2], types.SimpleNamespace(shots_number=nframes))
    return {"log": scope.log, "ch1": res["channel_data"]["ch1"].tolist()}


scenario("scope_normal_50000")(lambda: scope_case(50000, 100000))
scenario("scope_clamped_50000_max_1000")(lambda: scope_case(50000, 1000))
scenario("scope_single_shot")(lambda: scope_case(1, 100000))
scenario("scope_zero_frames")(lambda: scope_case(0, 100000))


def acq_wait():
    scope = FakeScope(states=("1", "1", "1", "0"))
    make_osc(scope).check_acquisition_status()
    return {"log": scope.log}


class FakeClock:
    """Replaces the scope module's `time`: sleep() advances a fake clock, so long waits
    run instantly and the same number of polls happens on every run."""
    def __init__(self):
        self.t = 0.0

    def sleep(self, seconds):
        self.t += seconds

    def perf_counter(self):
        return self.t


def acq_wait_with_timeout(busy_polls, timeout_s, abort_on_timeout):
    """Scope reports 'acquiring' for busy_polls polls (0.05 s each), then 'done'.

    The scope always finishes eventually, so this terminates whatever the code under
    test does when the timeout passes (warn and keep waiting, or abort).
    """
    import OscilloscopeTektronix as scope_module
    scope = FakeScope(states=("1",) * busy_polls + ("0",))
    real_time = scope_module.time
    scope_module.time = FakeClock()
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            make_osc(scope).check_acquisition_status(timeout_s=timeout_s,
                                                     abort_on_timeout=abort_on_timeout)
    finally:
        scope_module.time = real_time
    return {"polls": len(scope.log) - 1, "printed": printed.getvalue().strip()}


scenario("acq_wait_default")(acq_wait)
# 30 polls = 1.5 s of acquisition, timeout 0.5 s:
#   abort_on_timeout=False -> one warning, keeps waiting to the end
#   abort_on_timeout=True  -> TimeoutError at 0.5 s
scenario("acq_wait_slow_warns_and_keeps_waiting")(lambda: acq_wait_with_timeout(30, 0.5, False))
scenario("acq_wait_slow_aborts")(lambda: acq_wait_with_timeout(30, 0.5, True))
# finishes before the timeout -> no warning, no error
scenario("acq_wait_on_time_no_warning")(lambda: acq_wait_with_timeout(3, 10.0, False))


# ----------------------------------------------------------------------------- EPRHardware.run
class FakeOscForHW:
    def __init__(self):
        self.calls = []

    def oscilloscope_init(self, n):
        self.calls.append(f"init({n})")

    def check_acquisition_status(self, *args):
        self.calls.append(f"check{args}")

    def scope_run(self, channels, parameters):
        self.calls.append(f"scope_run({channels})")
        return {"time": np.arange(4), "channel_data": {"ch1": np.ones(4)}, "time_step": 1e-9}


def make_hw(machine=0, field_fail=False, temp_fail=False):
    import EPRHardware
    hw = EPRHardware.EPRHardware.__new__(EPRHardware.EPRHardware)  # skip connecting
    hw.Machine = machine
    hw.time_checks = 0
    hw.Machine_Name = "Oxford" if machine == 0 else "QMUL"
    hw.device = mock.MagicMock()
    hw.session = mock.MagicMock()
    hw.Osc = FakeOscForHW()
    hw.acquisition_timeout_factor = 2.0  # only read by versions that have the acquisition timeout
    hw.acquisition_timeout_margin_s = 120.0
    hw.MWSource = mock.MagicMock()
    hw.SR830 = mock.MagicMock()

    def field():
        if field_fail:
            raise OSError("field sensor offline")
        return 3400.5

    def temperature():
        if temp_fail:
            raise OSError("ITC not responding")
        return 4.2

    hw.read_magnetic_field = field
    hw.ITC = types.SimpleNamespace(get_temperature=temperature)
    return hw


def hw_run(abort_on_acquisition_timeout=None, **kw):
    hw = make_hw(**kw)
    params = types.SimpleNamespace(shots_number=1000, oscilloscope_wait_time=0.5,
                                   mw_freq=9.7, pulse_freq=100e6)
    if abort_on_acquisition_timeout is not None:
        params.abort_on_acquisition_timeout = abort_on_acquisition_timeout
    result = hw.run(params, "pos", "neg", "p1", lambda ct: None, lambda ct: None, True)
    calls = ["check" if c.startswith("check") else c for c in hw.Osc.calls]
    check_args = sorted({c for c in hw.Osc.calls if c.startswith("check")})
    out = {}
    for key, value in result.items():
        if isinstance(value, float) and value != value:
            out[key] = "nan"
        elif isinstance(value, (str, float, int, type(None))):
            out[key] = value
        else:
            out[key] = "array"
    return {"osc_calls": calls, "check_args": check_args, "result": out,
            "device_calls": h(re.sub(r"id='\d+'", "id", str(hw.device.mock_calls)))}


def qmul_run_and_save():
    hw = make_hw(machine=1)
    hw.initialize(9.7, 100e6)
    params = types.SimpleNamespace(shots_number=10, oscilloscope_wait_time=0.5)
    result = hw.run(params, "pos", "neg", "p1", lambda ct: None, lambda ct: None, True)
    path = make_osc().save_data_to_matlab(exp_data=result, exp_parameters={"a": 1},
                                          save_directory=TMP, file_name="qmul")
    return saved_summary(path)


scenario("hw_run_normal")(lambda: hw_run())
scenario("hw_run_abort_on_timeout_set")(lambda: hw_run(abort_on_acquisition_timeout=True))
scenario("hw_run_field_sensor_down")(lambda: hw_run(field_fail=True))
scenario("hw_run_itc_down")(lambda: hw_run(temp_fail=True))
scenario("hw_qmul_run_and_save")(qmul_run_and_save)


# ----------------------------------------------------------------------------- Oxford ITC
class FakeITC:
    def __init__(self, replies):
        self.replies = list(replies)
        self.log = []

    def write(self, s):
        self.log.append("W " + s)

    def read(self):
        reply = self.replies.pop(0) if self.replies else "TIMEOUT"
        self.log.append("R " + reply)
        if reply == "TIMEOUT":
            raise pyvisa.errors.VisaIOError(-1073807339)
        return reply


def itc(method, replies):
    from Oxford_ITC import Oxford_ITC
    driver = Oxford_ITC.__new__(Oxford_ITC)
    driver.thisOxfordITC = FakeITC(replies)
    value = getattr(driver, method)()
    return {"value": value, "log": driver.thisOxfordITC.log}


scenario("itc_temp_normal")(lambda: itc("get_temperature", ["R4.215"]))
scenario("itc_heater_pct_normal")(lambda: itc("get_heater_percent", ["R12.5"]))
scenario("itc_heater_volt_normal")(lambda: itc("get_heater_voltage", ["R3.1"]))
scenario("itc_temp_garbled_once")(lambda: itc("get_temperature", ["?", "TIMEOUT", "R4.215"]))
scenario("itc_heater_pct_garbled_once")(lambda: itc("get_heater_percent", ["?", "TIMEOUT", "R12.5"]))
scenario("itc_temp_always_garbled")(lambda: itc("get_temperature", ["?", "TIMEOUT"] * 2000))


# ----------------------------------------------------------------------------- PS10360 magnet + EDFS
class FakePS:
    def __init__(self):
        self.log = []
        self.current = 0.0

    def write(self, s):
        self.log.append("W " + s)
        if s.startswith("SOUR:CURR"):
            self.current = float(s.split()[1])

    def query(self, s):
        self.log.append("Q " + s)
        if s == "MEAS:CURR:DC?":
            return f"{self.current:.4f} A"
        if s == "MEAS:VOLT:DC?":
            return f"{self.current * 2.6:.4f} V"
        return "0"


def fake_magnet():
    from PS10360 import PS10360
    magnet = PS10360.__new__(PS10360)  # skip opening the TCP socket
    magnet.PS10360 = FakePS()
    return magnet


EDFS = "Pulse Sequences/EDFS PS Magnet/"


def edfs_init(field):
    magnet = fake_magnet()
    params = load(EDFS + "EDFSParameters.py").EDFSParameters()
    params.B_field = field
    load(EDFS + "EDFSExp.py").EDFSExp(params, FakeHW(), magnet)
    return {"magnet_log": magnet.PS10360.log}


def edfs_run():
    params = load(EDFS + "EDFSParameters.py").EDFSParameters()
    params.B_field = 3400
    params.save_directory = TMP
    hw = FakeHW()
    load(EDFS + "EDFSExp.py").EDFSExp(params, hw, fake_magnet()).run(save=False)
    return hw.calls


for _field in (0, 20, 50, 3400):
    scenario(f"edfs_init_field_{_field}G")(lambda f=_field: edfs_init(f))
scenario("edfs_run_programs")(edfs_run)


# ----------------------------------------------------------------------------- CPMG trigger validation
CPMG = "Pulse Sequences/CPMG Sequence/"


def cpmg_case(trigger_offset_ns, gap_len1_ns):
    params = load(CPMG + "CPMGParameters.py").CPMGParameters()
    params.seq_offset_ns = 800  # above the 500 ns amplifier margin, as in the lab scripts
    params.trigger_offset_ns = trigger_offset_ns
    params.gap_len1_ns = gap_len1_ns
    hw = FakeHW()
    load(CPMG + "CPMGExp.py").CPMGExp(params, hw).run(save=False)
    return hw.calls[0]


def cpmg_validation_grid():
    grid = {}
    for trigger in (0, 100, 300, 500, 800, 1500):
        for gap in (200, 300, 800, 2000):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    cpmg_case(trigger, gap)
                grid[f"trigger={trigger},gap={gap}"] = "ok"
            except Exception as error:
                grid[f"trigger={trigger},gap={gap}"] = f"{type(error).__name__}: {str(error)[:60]}"
    return grid


scenario("cpmg_defaults")(lambda: cpmg_case(500, 800))
scenario("cpmg_validation_grid")(cpmg_validation_grid)


# ----------------------------------------------------------------------------- run + save paths
def cpmg_double_peak_run_and_save():
    params = load(CPMG + "CPMGdoublePeakParameters.py").CPMGdoublePeakParameters()
    params.filename = "dp"
    hw = FakeHW()
    exp = load(CPMG + "CPMGdoublePeakExp.py").CPMGdoublePeakExp(params, hw, save_directory=TMP)
    result = exp.run(save=True)
    return {"saved": saved_summary(result["saved_path"]), "programs": hw.calls}


def service_run_and_save(folder):
    base = f"Service Scripts/{folder}/"
    params = load(base + "PulseOptimizationParameters.py").PulseOptimizationParameters()
    params.filename = "svc"
    hw = FakeHW()
    result = load(base + "HahnEchoExp.py").HahnEchoExp(params, hw, TMP).run(True)
    return {"saved": saved_summary(result["saved_path"]), "programs": hw.calls}


T1 = "Pulse Sequences/T1 sequence/"
HAHN = "Pulse Sequences/Hahn Echo/"


def t1_import_and_run():
    params = load(T1 + "InversionRecoveryParameters.py").InversionRecoveryParameters()
    hw = FakeHW()
    load(T1 + "InversionRecoveryExp.py").InversionRecoveryExp(params, hw).run(save=False)
    return hw.calls


def hahn_echo_programs():
    params = load(HAHN + "HahnEchoParameters.py").HahnEchoParameters()
    hw = FakeHW()
    load(HAHN + "HahnEchoExp.py").HahnEchoExp(params, hw).run(save=False)
    return hw.calls


scenario("cpmg_double_peak_run_and_save")(cpmg_double_peak_run_and_save)
scenario("service_pulse_opt_defaults_run_and_save")(lambda: service_run_and_save("Pulse Optimization"))
scenario("service_power_cal_defaults_run_and_save")(lambda: service_run_and_save("Power Calibration"))
scenario("t1_import_and_run")(t1_import_and_run)
scenario("hahn_echo_programs")(hahn_echo_programs)


# ----------------------------------------------------------------------------- lab scripts' own settings
ASSIGN = re.compile(r"^\s*(parameters\.\w+\s*=\s*[^#\n]+)")


def apply_script(params, script):
    """Apply every `parameters.x = ...` line of a lab script, in order, to params.

    Loop variables used in some scripts (i, q, k, j) are given fixed values.
    """
    applied = 0
    with open(os.path.join(ROOT, script), encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for line in lines:
        match = ASSIGN.match(line)
        if not match:
            continue
        try:
            exec(match.group(1), {"parameters": params, "np": np, "i": 0.0, "q": 4, "k": 1, "j": 1})
            applied += 1
        except Exception:
            pass
    return applied


def run_with_script(exp_file, exp_cls, par_file, par_cls, script, save=False, **ctor):
    params = getattr(load(par_file), par_cls)()
    applied = apply_script(params, script)
    params.save_directory = TMP
    params.filename = "s"
    hw = FakeHW()
    cls = getattr(load(exp_file), exp_cls)
    exp = cls(params, hw, **ctor) if ctor else cls(params, hw)
    result = exp.run(save=save)
    out = {"assignments_applied": applied, "programs": hw.calls}
    if save:
        out["saved"] = saved_summary(result["saved_path"])
    return out


for _s in ("cpmg.py", "cpmg_single_shot_independent.py", "cpmg_sweep_parameter_averages.py",
           "sweep_parameters.py"):
    scenario("script_cpmg_" + _s)(lambda s=_s: run_with_script(
        CPMG + "CPMGExp.py", "CPMGExp", CPMG + "CPMGParameters.py", "CPMGParameters", CPMG + s))
scenario("script_cpmg_double_peak_save")(lambda: run_with_script(
    CPMG + "CPMGdoublePeakExp.py", "CPMGdoublePeakExp",
    CPMG + "CPMGdoublePeakParameters.py", "CPMGdoublePeakParameters",
    CPMG + "cpmg_double_peak.py", save=True, save_directory=TMP))
for _s in ("inversionrrecovery.py", "sweep_parameters.py"):
    scenario("script_t1_" + _s)(lambda s=_s: run_with_script(
        T1 + "InversionRecoveryExp.py", "InversionRecoveryExp",
        T1 + "InversionRecoveryParameters.py", "InversionRecoveryParameters", T1 + s))
for _s in ("hahnecho.py", "sweep_parameters.py"):
    scenario("script_hahn_" + _s)(lambda s=_s: run_with_script(
        HAHN + "HahnEchoExp.py", "HahnEchoExp", HAHN + "HahnEchoParameters.py",
        "HahnEchoParameters", HAHN + s))
for _folder in ("Pulse Optimization", "Power Calibration"):
    _base = f"Service Scripts/{_folder}/"
    scenario("script_service_" + _folder.lower().replace(" ", "_") + "_single_check_save")(
        lambda b=_base: run_with_script(
            b + "HahnEchoExp.py", "HahnEchoExp", b + "PulseOptimizationParameters.py",
            "PulseOptimizationParameters", b + "single_check.py", save=True, save_directory=TMP))


# ----------------------------------------------------------------------------- programs on the virtual rig
# Every lab script in the checkout runs end-to-end, unchanged, on the virtual rig
# (virtual_rig.py): real drivers, EPRHardware, Sweep and experiment classes, with fake
# instruments underneath. Every command sent to every instrument is recorded.
_rig_spec = importlib.util.spec_from_file_location("virtual_rig", os.path.join(HERE, "virtual_rig.py"))
virtual_rig = importlib.util.module_from_spec(_rig_spec)
_rig_spec.loader.exec_module(virtual_rig)

SKIP_DIRS = {".git", ".idea", "__pycache__", "debug", "test", "tests", "venv", ".venv"}
BASE_SYS_PATH = [p for p in sys.path if not os.path.abspath(p or ".").startswith(ROOT)]


def discover_programs():
    """Lab scripts: files with top-level code and no classes, or with a __main__ block.

    GUI programs (tkinter) are listed but not run, because they wait for a user.
    """
    import ast
    programs, gui = [], []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for file in sorted(files):
            if not file.endswith(".py"):
                continue
            path = os.path.join(folder, file)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            with open(path, encoding="utf-8", errors="replace") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    programs.append(rel)  # running it records the SyntaxError
                    continue
            body = tree.body
            imports = {alias.name.split(".")[0] for node in ast.walk(tree)
                       if isinstance(node, (ast.Import, ast.ImportFrom))
                       for alias in (node.names if isinstance(node, ast.Import)
                                     else [types.SimpleNamespace(name=node.module or "")])}
            has_class = any(isinstance(n, ast.ClassDef) for n in body)
            has_main = any(isinstance(n, ast.If) and "__name__" in ast.dump(n.test) for n in body)
            runs_code = any(isinstance(n, (ast.Expr, ast.For, ast.While, ast.Try, ast.With))
                            and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
                            for n in body)
            if not (has_main or (runs_code and not has_class)):
                continue
            (gui if "tkinter" in imports else programs).append(rel)
    return programs, gui


def purge_repo_modules():
    """Forget every module imported from the checkout, so each program starts fresh
    (several folders reuse names such as CPMGExp and HahnEchoExp)."""
    for name, module in list(sys.modules.items()):
        locations = [getattr(module, "__file__", None) or ""]
        try:
            locations += list(getattr(module, "__path__", []) or [])
        except Exception:  # a namespace package whose parent was already removed
            locations.append(ROOT + os.sep)
        if any(loc and os.path.abspath(loc).startswith(ROOT + os.sep) for loc in locations):
            del sys.modules[name]


def last_repo_frame(error):
    import traceback
    tools = (HERE + os.sep, os.path.join(ROOT, "debug") + os.sep)
    frames = [f for f in traceback.extract_tb(error.__traceback__)
              if os.path.abspath(f.filename).startswith(ROOT + os.sep)
              and not os.path.abspath(f.filename).startswith(tools)]
    if not frames:
        return None, None
    frame = frames[-1]
    return f"{os.path.relpath(frame.filename, ROOT)} in {frame.name}", frame.lineno


def run_program(rel, faults=None):
    import runpy
    path = os.path.join(ROOT, rel)
    folder = os.path.dirname(path)
    purge_repo_modules()
    saved_path, saved_cwd = list(sys.path), os.getcwd()
    # As when run from PyCharm: the script's folder and the repo root are importable.
    sys.path[:] = [folder, ROOT] + BASE_SYS_PATH
    console = io.StringIO()
    rig = virtual_rig.Rig(faults=faults)
    status = {"ok": True}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            os.chdir(folder)
            with rig, contextlib.redirect_stdout(console), contextlib.redirect_stderr(console):
                runpy.run_path(path, run_name="__main__")
        except virtual_rig.RigLimit as limit:
            status = {"ok": True, "stopped_by_rig": str(limit)}
        except BaseException as error:  # noqa: B902 - Ctrl+C and SystemExit are outcomes too
            where, line = last_repo_frame(error)
            # "_line" is shown in reports but not compared: a PR that only moves code
            # around would otherwise look like it changed every error.
            status = {"ok": False, "error": type(error).__name__, "msg": clean(str(error), 300),
                      "where": where, "_line": line}
        finally:
            os.chdir(saved_cwd)
            sys.path[:] = saved_path
    lines = console.getvalue().splitlines()
    return {**status,
            "events": [clean(e, 2000) for e in virtual_rig.compress(rig.events)],
            "programs": rig.programs,
            "saves": json.loads(clean(json.dumps(rig.saves, default=str), 10 ** 9)),
            "console": [clean(line, 500) for line in virtual_rig.compress(lines)][:3000],
            "warnings": sorted({clean(f"{w.category.__name__}: {w.message}", 300) for w in caught})}


PROGRAMS, GUI_PROGRAMS = discover_programs()
for _program in PROGRAMS:
    results["program: " + _program] = run_program(_program)
for _program in GUI_PROGRAMS:
    results["program: " + _program] = {"ok": True, "skipped": "GUI program (tkinter), not run"}

# The same programs with an instrument misbehaving.
FAULT_RUNS = [
    ("Pulse Sequences/Hahn Echo/hahnecho.py", {"field_sensor": "offline"}),
    ("Pulse Sequences/Hahn Echo/hahnecho.py", {"itc": "garbled_once"}),
    ("Pulse Sequences/Hahn Echo/hahnecho.py", {"itc": "offline"}),
    ("Pulse Sequences/Hahn Echo/hahnecho.py", {"scope_slow_s": 1000}),
    ("Pulse Sequences/Hahn Echo/sweep_parameters.py", {"scope_interrupt_at": 5}),
    ("Pulse Sequences/Hahn Echo/sweep_parameters.py", {"scope_error_at": 5}),
    ("Pulse Sequences/EDFS PS Magnet/edfs_sweep.py", {"field_sensor": "offline"}),
]
for _program, _faults in FAULT_RUNS:
    if os.path.exists(os.path.join(ROOT, _program)):
        _label = ", ".join(f"{k}={v}" for k, v in _faults.items())
        results[f"fault: {_program} [{_label}]"] = run_program(_program, _faults)


# ----------------------------------------------------------------------------- write results
shutil.rmtree(TMP, ignore_errors=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1, sort_keys=True, default=str)
failed = sum(1 for r in results.values() if not r["ok"])
print(f"Wrote {OUT}: {len(results)} scenarios ({failed} raised an exception) for {ROOT}")
