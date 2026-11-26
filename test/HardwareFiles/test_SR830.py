"""HardwareFiles/SR830.py: lock-in amplifier (its AUX output drives the MW switch)."""
import pyvisa

from support import FakeInstrument, FakeResourceManager


def make_lockin(monkeypatch, replies=None):
    from HardwareFiles.SR830 import SR830
    fake = FakeInstrument(replies)
    monkeypatch.setattr(pyvisa, "ResourceManager", FakeResourceManager({"GPIB1::8": fake}))
    return SR830(8), fake


def test_aux_output_command(monkeypatch):
    lockin, fake = make_lockin(monkeypatch)
    lockin.set_aux_vol(4, 4.5)
    assert fake.writes() == ["AUXV4{,4.500000}"]


def test_reads_x_and_y(monkeypatch):
    lockin, _ = make_lockin(monkeypatch, {"OUTP?1": "1.5e-3", "OUTP?2": "-2e-4"})
    assert lockin.get_X() == 1.5e-3
    assert lockin.get_Y() == -2e-4
