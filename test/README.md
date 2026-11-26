# test/

Automated tests for the spectrometer code. They need no hardware: every instrument is
faked, and a test that tries to open a real VISA connection fails.

The folders mirror the repo, so the tests for `HardwareFiles/Oxford_ITC.py` are in
`test/HardwareFiles/test_Oxford_ITC.py`, and those for
`Pulse Sequences/CPMG Sequence/CPMGExp.py` are in `test/Pulse Sequences/CPMG Sequence/test_CPMGExp.py`.

## Running them

From the repo root:

```powershell
python -m pytest test
```

You need `pytest` as well as the program's own packages (`numpy`, `scipy`, `matplotlib`,
`pyvisa`, `requests`). `zhinst` isn't needed.

Each test is reported as one of:

| Result | Meaning |
|---|---|
| `passed` | Works as it should. |
| `xfail` | A known bug that an open PR fixes; the reason names the PR. Expected until that PR is merged. |
| `XPASS` | A known bug that's now fixed. Once its PR is merged, remove the `@fixed_by(...)` marker so the test guards against the bug coming back. |
| `failed` | Something is broken. |

## What's tested

- **Drivers** (`HardwareFiles/`): the commands each driver sends and how it reads replies. This covers the oscilloscope (FastFrame, waveform read-back, waiting, saving), ITC, PS10360 magnet supply, MW source and SR830.
- **`EPRHardware`**: a measurement with both phase cycles, sensor readings, and what happens when a sensor fails.
- **`Sweep`**: one save per completed sweep, and a partial save when the sweep stops early.
- **Each experiment** (`Pulse Sequences/`, `Service Scripts/`): built with the settings from its lab script, for example `hahnecho.py` and `cpmg.py`. The tests check:
  - that SeqC programs and command tables are produced for both phase cycles;
  - that saving works;
  - the experiment's own checks, such as trigger placement.

The experiment tests read the settings straight from the lab scripts (`apply_lab_settings` in `support.py`), so they follow the scripts when those change.

## Writing tests

- Put the test in the folder that mirrors the file it tests, named `test_<file>.py`.
- `support.py` has the shared fakes and helpers:
  - `FakeInstrument` and `FakeResourceManager` for VISA instruments, and `FakeScope` and `FakePS` for the scope and magnet supply;
  - `RecordingHardware`, which stands in for `EPRHardware` in an experiment;
  - `run_experiment(...)`;
  - `load(path)`, for importing a repo file whose name is shared with files in other folders.
- To fake an instrument, replace `pyvisa.ResourceManager` with `monkeypatch`, as in `test_MWSource.py`.
- A test for a bug that an open PR fixes gets `@fixed_by(<PR number>, "<what's wrong>")`.

`debug/check_pr.py` (added in #12) works differently. It runs whole lab scripts on a virtual spectrometer and reports every difference a PR makes. These tests instead state what the correct behaviour is.
