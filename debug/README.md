# debug/

Tools for checking what a code change does to the spectrometer, **without the hardware**.
Nothing in the experiment code imports this folder, and these scripts never talk to a real
instrument, so they don't affect anyone using the program.

## Check a pull request

```powershell
python debug/check_pr.py 8
```

1. **Finds the PR and the branch it merges into.** This uses the GitHub CLI (`gh`). Without it, pass `--base`.
2. **Builds the merge result** (base + PR) in a temporary folder. That's the code that would be on the base branch after merging. Your checkout and branches aren't touched.
3. **Runs every lab script on a virtual spectrometer**, once for the base and once for the merge result. All commands sent to every instrument are recorded.
4. **Reports every difference**, per scenario and per instrument, as a diff.

The report can't tell an intended change from a regression; the reviewer decides. A PR is fine if every difference is something it's meant to change. Any other difference is a problem. With no differences, the PR doesn't change anything the program does.

Other forms:

```powershell
python debug/check_pr.py pr/05-sensor-read-nan              # a branch (base taken from its PR)
python debug/check_pr.py pr/05-sensor-read-nan --base version-1
python debug/check_pr.py . --base version-1                 # your uncommitted working tree
python debug/check_pr.py 8 --report check_pr_8.md           # also write Markdown for the PR
```

- `--no-merge` compares the PR branch as it is, instead of the merge result.
- `--full` shows long diffs in full.

The run takes about a minute. Exit code 0 means no differences, 1 means differences were found, and 2 means the check couldn't run (unknown ref, merge conflict, ...).

## What runs

`fake_hardware_harness.py` runs three kinds of scenario against one checkout:

- **Programs.** Every lab script in the repo runs end-to-end and unchanged, for example `Pulse Sequences/Hahn Echo/hahnecho.py` and every `sweep_parameters.py`. Scripts are found automatically, so a new script is included without any change here.
  - GUI programs (tkinter) are listed but not run.
  - A script that keeps creating new hardware set-ups in a loop is stopped after 3.
- **Faults.** Some programs are run again with an instrument misbehaving:
  - the field sensor offline;
  - an ITC reply garbled, or no reply at all;
  - a very slow scope acquisition;
  - Ctrl+C, or a VISA timeout, part-way through a sweep.
- **Driver checks.** Targeted cases for individual drivers and checks, such as FastFrame limits, magnet set-up at 0–50 G, and the CPMG trigger validation grid.

For programs, it records:

- every command to every instrument, in order;
- each SeqC program uploaded to the HDAWG (in full) and each command-table entry;
- what was saved, and where: `.mat` contents, with array shapes and hashes;
- printed output and warnings;
- how the run ended (finished, or the exception and the line that raised it).

## The virtual spectrometer (`virtual_rig.py`)

The fakes sit where the program meets the hardware, so the real drivers in `HardwareFiles/`, `EPRHardware`, `Sweep` and the experiment classes all run unchanged.

| Real | Virtual |
|---|---|
| `pyvisa.ResourceManager` | Instruments chosen by VISA address: Tektronix scope (`GPIB1::1`), MW source (`GPIB1::19`), SR830 (`GPIB1::8`), Oxford ITC (`GPIB1::15`), PS10360 (`TCPIP0::100.100.100.4::5025::SOCKET`), Keithley (`GPIB1::18`). Any other address gets a generic instrument that answers `0`. |
| `zhinst.toolkit` (HDAWG) | Records every node call, SeqC program and command table |
| `requests` (field sensor) | Returns the field, which follows the magnet current |
| `time`, `datetime` | A virtual clock: sleeps are instant, and timestamps are the same on every run |
| `scipy.io.savemat`, `os.makedirs` | Saving is recorded; nothing is written to disk |
| `matplotlib` `show` / `pause` | Do nothing (plots render off-screen) |

The instruments behave enough like the real ones for the code to run:

- The scope finishes acquiring after 0.2 virtual seconds and returns a different waveform for each channel, frame and acquisition.
- The ITC answers each command once.
- The magnet supply's voltage matches the calibrated magnet resistance.

When a new instrument is added to the program, add a class for it in `virtual_rig.py` and an entry in `ADDRESSES`.

## Requirements and limits

- **Packages:** the same as the program (`numpy`, `scipy`, `matplotlib`, `pyvisa`, `requests`), plus `git`. `zhinst` isn't needed. `gh` is optional.
- **It's a model, not the rig:**
  - The instruments don't model real timing, real VISA replies, or the HDAWG compiling the SeqC.
  - Instrument responses are simplified, so a change that only matters with real signals won't show.
  - A clean report is evidence, not a replacement for a test on the rig.
- **Harness version:** the harness from the folder you run `check_pr.py` from is used on both sides. If a PR changes the harness itself, run it from that PR's checkout.
