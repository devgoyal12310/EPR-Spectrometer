"""HardwareFiles/MWSource.py: microwave source frequency and output."""
import pyvisa

from support import FakeInstrument, FakeResourceManager


def make_source(monkeypatch):
    from HardwareFiles.MWSource import MWSource
    fake = FakeInstrument({"FREQ:CW?": "9.7E9", "POW:AMPL?": "-10"})
    monkeypatch.setattr(pyvisa, "ResourceManager", FakeResourceManager({"GPIB1::19": fake}))
    return MWSource(), fake


def test_frequency_is_the_mw_frequency_plus_the_pulse_frequency(monkeypatch):
    source, fake = make_source(monkeypatch)
    source.set_freq_Ghz(9.701, 100e6)
    assert fake.writes() == ["FREQ:CW 9801000000.0"]


def test_switch_on_disables_modulation_first(monkeypatch):
    source, fake = make_source(monkeypatch)
    source.switch_on()
    assert fake.writes() == ["OUTP:MOD 0", "OUTP ON"]


def test_switch_off(monkeypatch):
    source, fake = make_source(monkeypatch)
    source.switch_off()
    assert fake.writes() == ["OUTP OFF"]


def test_set_power(monkeypatch):
    source, fake = make_source(monkeypatch)
    source.set_power_dBm(-3)
    assert fake.writes() == ["POW:AMPL -3"]
