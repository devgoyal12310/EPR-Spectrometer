"""A virtual spectrometer: fake instruments at the transport layer.

Everything the program uses to reach hardware is replaced while a Rig is active:

  * pyvisa.ResourceManager  -> fake instruments chosen by VISA address
                               (Tektronix scope, MW source, SR830, Oxford ITC,
                               PS10360 magnet supply, Keithley; anything else is
                               a generic instrument that answers "0")
  * zhinst.toolkit          -> a fake HDAWG session that records every node call,
                               every SeqC program and every command table uploaded
  * requests.Session        -> the field sensor's HTTP interface
  * time / datetime         -> a virtual clock: sleeps take no real time, and every
                               run sees the same times and timestamps
  * scipy.io.savemat,       -> saving is recorded, nothing is written to disk
    os.makedirs
  * matplotlib show/pause   -> no-ops (plots render off-screen)

The real driver code (HardwareFiles/), EPRHardware, Sweep and the lab scripts run
unchanged on top. Every command they send is appended to Rig.events as
"<instrument>: <command>", so two versions of the code can be compared command by command.

Faults can be injected per run, for example Rig(faults={"field_sensor": "offline"}).
See FAULTS below.
"""
import datetime as _datetime
import hashlib
import os
import sys
import time as _time
import types

import numpy as np
import pyvisa
import requests

# Faults a scenario can ask for:  Rig(faults={name: value, ...})
FAULTS = {
    "field_sensor": "'offline': every HTTP read raises requests.ConnectionError",
    "itc": "'garbled_once': first temperature reply is '?'; 'offline': no replies at all",
    "scope_slow_s": "seconds every acquisition takes (default 0.2)",
    "scope_interrupt_at": "n: Ctrl+C (KeyboardInterrupt) while waiting for the n-th acquisition",
    "scope_error_at": "n: VISA timeout (VisaIOError) while waiting for the n-th acquisition",
}


class RigLimit(BaseException):
    """Raised to stop a script that runs far longer than any real measurement."""


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ----------------------------------------------------------------------------- clock
class VirtualClock:
    EPOCH = 946684800.0  # 2000-01-01 00:00:00 UTC

    def __init__(self, rig):
        self.rig = rig
        self.t = 0.0

    def sleep(self, seconds):
        self.t += float(seconds)
        self.rig.log("host", f"sleep {float(seconds):g}")
        if self.t > self.rig.max_virtual_s:
            raise RigLimit(f"virtual time passed {self.rig.max_virtual_s:.0f} s")

    def perf_counter(self):
        return self.t

    def time(self):
        return self.EPOCH + self.t


def _fake_datetime_class(clock):
    real = _datetime.datetime

    class FakeDatetime(real):
        @classmethod
        def now(cls, tz=None):
            return real(2000, 1, 1) + _datetime.timedelta(seconds=clock.t)

        @classmethod
        def today(cls):
            return cls.now()

    return FakeDatetime


# ----------------------------------------------------------------------------- VISA instruments
class FakeInstrument:
    """Generic VISA instrument: records everything, answers queries with '0'."""
    name = None

    def __init__(self, rig, address):
        object.__setattr__(self, "_rig", rig)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "_replies", [])
        if self.name is None:
            object.__setattr__(self, "name", address)

    def __setattr__(self, key, value):
        self._rig.log(self.name, f"set {key}={value!r}")
        object.__setattr__(self, key, value)

    # --- what the drivers call
    def write(self, command, *args, **kwargs):
        self._rig.log(self.name, f"W {command}")
        self.on_write(command)
        return len(command)

    def query(self, command, *args, **kwargs):
        self._rig.log(self.name, f"Q {command}")
        reply = self.on_query(command)
        self._rig.log(self.name, f"  -> {str(reply).strip()}")
        return reply

    def read(self, *args, **kwargs):
        reply = self.on_read()
        self._rig.log(self.name, f"R -> {str(reply).strip()}")
        return reply

    def query_binary_values(self, command, *args, **kwargs):
        self._rig.log(self.name, f"B {command}")
        values = self.on_binary(command)
        self._rig.log(self.name, f"  -> {len(values)} values, sha {sha(repr(list(values)))}")
        return np.asarray(values)

    def set_visa_attribute(self, attribute, value):
        self._rig.log(self.name, f"set_visa_attribute {getattr(attribute, 'name', attribute)}={value!r}")

    def clear(self):
        self._rig.log(self.name, "clear")

    def close(self):
        self._rig.log(self.name, "close")

    # --- behaviour, overridden per instrument
    def on_write(self, command):
        pass

    def on_query(self, command):
        if command.strip() == "*IDN?":
            return f"FAKE,{self.name},0,0"
        return "0"

    def on_read(self):
        if self._replies:
            return self._replies.pop(0)
        raise pyvisa.errors.VisaIOError(pyvisa.constants.StatusCode.error_timeout)

    def on_binary(self, command):
        return []


class TektronixScope(FakeInstrument):
    name = "scope"
    POINTS = 256

    def __init__(self, rig, address):
        super().__init__(rig, address)
        for key, value in (("acquisitions", 0), ("busy_until", 0.0), ("channel", 1),
                           ("frame", 1), ("interrupt_pending", False), ("error_pending", False)):
            object.__setattr__(self, key, value)

    def on_write(self, command):
        cmd = command.strip().lower()
        if cmd == "acquire:state on":
            n = self.acquisitions + 1
            object.__setattr__(self, "acquisitions", n)
            duration = float(self._rig.faults.get("scope_slow_s", 0.2))
            object.__setattr__(self, "busy_until", self._rig.clock.t + duration)
            object.__setattr__(self, "interrupt_pending", self._rig.faults.get("scope_interrupt_at") == n)
            object.__setattr__(self, "error_pending", self._rig.faults.get("scope_error_at") == n)
        elif cmd == "acquire:state off":
            object.__setattr__(self, "busy_until", 0.0)
        elif cmd.startswith("data:source ch"):
            object.__setattr__(self, "channel", int(cmd.rsplit("ch", 1)[1]))
        elif cmd.startswith(":data:framestart"):
            object.__setattr__(self, "frame", int(cmd.split()[1]))

    def on_query(self, command):
        cmd = command.strip()
        if cmd.upper() == "ACQUIRE:STATE?":
            if self.interrupt_pending:
                object.__setattr__(self, "interrupt_pending", False)
                self._rig.log(self.name, "  !! fault: Ctrl+C while waiting for the acquisition")
                raise KeyboardInterrupt
            if self.error_pending:
                object.__setattr__(self, "error_pending", False)
                self._rig.log(self.name, "  !! fault: VISA timeout")
                raise pyvisa.errors.VisaIOError(pyvisa.constants.StatusCode.error_timeout)
            return "1\n" if self._rig.clock.t < self.busy_until else "0\n"
        replies = {
            "HORizontal:FASTframe:MAXFRames?": "100000", "HORizontal:ACQLENGTH?": str(self.POINTS),
            "WFMOutpre:BYT_Nr?": "1", "WFMOutpre:BN_Fmt?": "RI", "wfmoutpre:ymult?": "0.004",
            "wfmoutpre:yzero?": "0", "wfmoutpre:yoff?": "0", "wfmoutpre:xincr?": "4e-10",
            "*OPC?": "1", "*IDN?": "TEKTRONIX,FAKE,0,0",
        }
        return replies.get(cmd, "0") + "\n"

    def on_binary(self, command):
        # Deterministic, different for each channel, frame and acquisition.
        i = np.arange(self.POINTS)
        return ((i * self.channel + 7 * self.acquisitions + self.frame) % 200 - 100).astype(np.int8)


class MWSource(FakeInstrument):
    name = "mw_source"

    def __init__(self, rig, address):
        super().__init__(rig, address)
        object.__setattr__(self, "state", {"FREQ:CW": "9.7E9", "POW:AMPL": "-10"})

    def on_write(self, command):
        key, _, value = command.strip().partition(" ")
        if key in self.state:
            self.state[key] = value

    def on_query(self, command):
        key = command.strip().rstrip("?")
        return self.state.get(key, super().on_query(command))


class OxfordITC(FakeInstrument):
    """Answers each write with one reply, as the ITC503 does (R1 = temperature etc.)."""
    name = "itc"
    REPLIES = {"R0": "R4.2000", "R1": "R4.2150", "R5": "R12.5", "R6": "R3.1"}

    def __init__(self, rig, address):
        super().__init__(rig, address)
        object.__setattr__(self, "temperature_reads", 0)

    def on_write(self, command):
        fault = self._rig.faults.get("itc")
        if fault == "offline":
            return
        cmd = command.strip()
        reply = self.REPLIES.get(cmd, cmd[:1])
        if cmd == "R1":
            object.__setattr__(self, "temperature_reads", self.temperature_reads + 1)
            if fault == "garbled_once" and self.temperature_reads == 1:
                reply = "?"
        self._replies.append(reply)


class PS10360(FakeInstrument):
    """Magnet supply. Voltage follows the calibrated magnet resistance, so checks pass."""
    name = "magnet_ps10360"

    def __init__(self, rig, address):
        super().__init__(rig, address)
        object.__setattr__(self, "current", 0.0)

    def on_write(self, command):
        cmd = command.strip()
        if cmd.startswith("SOUR:CURR "):
            object.__setattr__(self, "current", float(cmd.split()[1]))
            if self.current > 0:
                self._rig.field_gauss = 10 * (self.current + 0.1282) / 0.03307

    def on_query(self, command):
        cmd = command.strip()
        if cmd == "MEAS:CURR:DC?":
            return f"{self.current:.4f} A"
        if cmd == "MEAS:VOLT:DC?":
            field = 10 * (self.current + 0.1282) / 0.03307 if self.current > 0 else 0.0
            return f"{self.current * (2.580871 + field * 1.765071e-05):.4f} V"
        return super().on_query(command)


class SR830(FakeInstrument):
    name = "lockin_sr830"


class Keithley(FakeInstrument):
    name = "keithley"

    def on_read(self):
        return "+1.000000E-03"


ADDRESSES = {
    "GPIB1::1": TektronixScope,
    "TCPIP0::192.168.3.30::inst0::INSTR": TektronixScope,
    "GPIB1::19": MWSource,
    "GPIB1::8": SR830,
    "GPIB1::15": OxfordITC,
    "TCPIP0::100.100.100.4::5025::SOCKET": PS10360,
    "GPIB1::18::INSTR": Keithley,
    "GPIB1::18": Keithley,
}


def _resource_manager_class(rig):
    class FakeResourceManager:
        def __init__(self, *args, **kwargs):
            rig.log("visa", "ResourceManager()")

        def list_resources(self, *args, **kwargs):
            return tuple(sorted(ADDRESSES))

        def open_resource(self, address, *args, **kwargs):
            cls = ADDRESSES.get(str(address), FakeInstrument)
            instrument = cls(rig, str(address))
            rig.log("visa", f"open_resource({address!r}) -> {instrument.name}")
            return instrument

        def close(self):
            rig.log("visa", "ResourceManager.close()")

    return FakeResourceManager


# ----------------------------------------------------------------------------- HDAWG (zhinst.toolkit)
class FakeNode:
    """Any node of the fake HDAWG: attribute and index access build a path, calls are logged."""

    def __init__(self, rig, path):
        object.__setattr__(self, "_rig", rig)
        object.__setattr__(self, "_path", path)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return FakeNode(self._rig, f"{self._path}.{name}")

    def __getitem__(self, index):
        return FakeNode(self._rig, f"{self._path}[{index}]")

    def __setattr__(self, name, value):
        self._rig.log("hdawg", f"{self._path}.{name} = {value!r}")

    def __call__(self, *args, **kwargs):
        rig, leaf = self._rig, self._path.rsplit(".", 1)[-1]
        if leaf == "load_sequencer_program":
            program = str(args[0]) if args else str(kwargs.get("sequencer_program", ""))
            key = sha(program)
            rig.programs[key] = program
            rig.log("hdawg", f"{self._path}(seqc:{key}, {program.count(chr(10)) + 1} lines)")
            return None
        if leaf == "load_validation_schema":
            rig.log("hdawg", f"{self._path}()")
            return {"fake": "command table schema"}
        if leaf == "upload_to_device":
            table = args[0] if args else kwargs.get("ct")
            entries = table.entries() if isinstance(table, FakeCommandTable) else [repr(table)]
            rig.log("hdawg", f"{self._path}({len(entries)} command-table entries)")
            for entry in entries:
                rig.log("hdawg", f"    {entry}")
            return None
        rendered = ", ".join([repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()])
        rig.log("hdawg", f"{self._path}({rendered})")
        return 0 if not args and not kwargs else None


class FakeSession(FakeNode):
    def __init__(self, host="localhost", *args, **kwargs):
        rig = Rig.current()
        super().__init__(rig, "session")
        rig.log("hdawg", f"Session({host!r})")

    def connect_device(self, serial, *args, **kwargs):
        rig = self._rig
        rig.connections += 1
        rig.log("hdawg", f"connect_device({serial!r})")
        if rig.connections > rig.max_connections:
            raise RigLimit(f"stopped at experiment set-up {rig.connections} "
                           f"(the rig runs at most {rig.max_connections} per script)")
        return FakeNode(rig, "device")


class _TableRecorder:
    def __init__(self, path, log):
        object.__setattr__(self, "_p", path)
        object.__setattr__(self, "_l", log)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _TableRecorder(f"{self._p}.{name}", self._l)

    def __getitem__(self, index):
        return _TableRecorder(f"{self._p}[{index}]", self._l)

    def __setattr__(self, name, value):
        self._l.append(f"{self._p}.{name} = {value!r}")


class FakeCommandTable:
    def __init__(self, schema=None, *args, **kwargs):
        object.__setattr__(self, "_log", [])

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _TableRecorder(f"ct.{name}", self._log)

    def __setattr__(self, name, value):
        self._log.append(f"ct.{name} = {value!r}")

    def entries(self):
        return list(self._log)

    def as_dict(self):
        return {"entries": list(self._log)}


def install_zhinst_stub():
    """Make `from zhinst.toolkit import Session, CommandTable` load the fakes."""
    zh = types.ModuleType("zhinst")
    zt = types.ModuleType("zhinst.toolkit")
    zt.Session = FakeSession
    zt.CommandTable = FakeCommandTable
    zh.toolkit = zt
    sys.modules["zhinst"] = zh
    sys.modules["zhinst.toolkit"] = zt


# ----------------------------------------------------------------------------- field sensor (HTTP)
def _http_session_class(rig):
    class Response:
        def __init__(self, value):
            self.value = value
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return self.value

    class FakeHTTPSession:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url, *args, **kwargs):
            rig.log("field_sensor", f"GET {url}")
            if rig.faults.get("field_sensor") == "offline":
                rig.log("field_sensor", "  !! fault: no response")
                raise requests.ConnectionError("field sensor offline (virtual rig fault)")
            value = round(rig.field_gauss, 3)
            rig.log("field_sensor", f"  -> {value}")
            return Response(value)

        def close(self):
            pass

    return FakeHTTPSession


# ----------------------------------------------------------------------------- saving
def summarise(value):
    """A short, stable description of saved data: shape and a hash for arrays."""
    if isinstance(value, dict):
        return {str(k): summarise(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, np.ndarray) and value.size > 8:
        rounded = np.round(value.astype(float), 9) if value.dtype.kind in "fiub" else value
        return f"array{list(value.shape)} {value.dtype} sha {sha(repr(rounded.tolist()))}"
    if isinstance(value, (list, tuple)) and len(value) > 8:
        return summarise(np.asarray(value))
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, float)):
        return float(np.round(float(value), 9)) if value == value else "nan"
    if isinstance(value, (np.integer,)):
        return int(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return repr(value)


def compress(events):
    """Collapse runs of a repeated block of 1-3 events (polling loops) into one line."""
    out, i, n_events = [], 0, len(events)
    while i < n_events:
        best = None
        for size in (1, 2, 3):
            block = events[i:i + size]
            if len(block) < size:
                break
            repeats = 1
            while events[i + repeats * size:i + (repeats + 1) * size] == block:
                repeats += 1
            if repeats >= 3 and (best is None or repeats * size > best[0] * best[1]):
                best = (repeats, size)
        if best:
            repeats, size = best
            out.append(f"[x{repeats}] " + "  |  ".join(events[i:i + size]))
            i += repeats * size
        else:
            out.append(events[i])
            i += 1
    return out


# ----------------------------------------------------------------------------- the rig
class Rig:
    _current = None

    def __init__(self, faults=None, max_events=300_000, max_virtual_s=7 * 24 * 3600, max_connections=3):
        self.faults = dict(faults or {})
        self.max_events = max_events
        self.max_virtual_s = max_virtual_s
        self.max_connections = max_connections
        self.events = []
        self.programs = {}
        self.saves = []
        self.connections = 0
        self.field_gauss = 3400.0
        self.clock = VirtualClock(self)
        self._saved = []

    @classmethod
    def current(cls):
        if cls._current is None:
            raise RuntimeError("virtual rig used outside `with Rig(...)`")
        return cls._current

    def log(self, instrument, text):
        self.events.append(f"{instrument}: {text}")
        if len(self.events) > self.max_events:
            raise RigLimit(f"more than {self.max_events} instrument commands")

    # --- patching
    def _patch(self, obj, name, value):
        self._saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def __enter__(self):
        import matplotlib.pyplot as plt
        import scipy.io

        Rig._current = self
        install_zhinst_stub()
        self._patch(pyvisa, "ResourceManager", _resource_manager_class(self))
        self._patch(requests, "Session", _http_session_class(self))
        self._patch(_time, "sleep", self.clock.sleep)
        self._patch(_time, "perf_counter", self.clock.perf_counter)
        self._patch(_time, "monotonic", self.clock.perf_counter)
        self._patch(_time, "time", self.clock.time)
        self._patch(_datetime, "datetime", _fake_datetime_class(self.clock))
        self._patch(scipy.io, "savemat", self._savemat)
        self._patch(os, "makedirs", self._makedirs)
        self._patch(plt, "show", lambda *a, **k: None)
        self._patch(plt, "pause", lambda *a, **k: None)
        return self

    def __exit__(self, *exc):
        import matplotlib.pyplot as plt
        for obj, name, value in reversed(self._saved):
            setattr(obj, name, value)
        self._saved.clear()
        plt.close("all")
        Rig._current = None
        return False

    def _makedirs(self, path, *args, **kwargs):
        self.log("disk", f"makedirs {path}")

    def _savemat(self, path, data, *args, **kwargs):
        self.log("disk", f"savemat {path}")
        self.saves.append({"path": str(path), "content": summarise(data)})
