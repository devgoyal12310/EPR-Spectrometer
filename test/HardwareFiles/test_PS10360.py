"""HardwareFiles/PS10360.py: magnet power supply, field set-up and the resistance check."""
import pytest

import pyvisa

from support import PS10360_ADDRESS as ADDRESS, FakePS, FakeResourceManager


def make_magnet(monkeypatch, **kwargs):
    from HardwareFiles.PS10360 import PS10360
    fake = FakePS(**kwargs)
    monkeypatch.setattr(pyvisa, "ResourceManager", FakeResourceManager({ADDRESS: fake}))
    return PS10360(), fake


def test_connects_with_output_on_in_constant_current_mode(monkeypatch):
    _, fake = make_magnet(monkeypatch)
    assert fake.writes() == ["SYST:LOCK: ON", "OUT ON", "SOURCE:VOLTAGE: MAX"]


def test_field_is_converted_with_the_calibration(monkeypatch):
    magnet, fake = make_magnet(monkeypatch)
    magnet.set_centerfield(3400)
    assert fake.writes()[-2:] == ["SOURCE:VOLTAGE: MAX", "SOUR:CURR 11.1156 A"]


def test_field_below_the_calibration_offset_sets_zero_current(monkeypatch):
    magnet, fake = make_magnet(monkeypatch)
    magnet.set_centerfield(20)
    assert fake.writes()[-2:] == ["SOUR:CURR 0.0000 A", "SOUR:VOLTAGE 0.0000 V"]


def test_field_above_the_maximum_is_refused(monkeypatch):
    magnet, fake = make_magnet(monkeypatch)
    sent = len(fake.writes())
    with pytest.raises(ValueError):
        magnet.set_centerfield(9500)
    assert len(fake.writes()) == sent


def test_resistance_at_zero_current_is_an_error(monkeypatch):
    magnet, _ = make_magnet(monkeypatch)
    with pytest.raises(ZeroDivisionError):
        magnet.get_resistance_in_Ohm()


def test_resistance_check_passes_for_the_calibrated_magnet(monkeypatch):
    magnet, _ = make_magnet(monkeypatch)
    magnet.set_centerfield(3400)
    magnet.check_resistance(3400)


def test_resistance_check_fails_safe(monkeypatch):
    magnet, fake = make_magnet(monkeypatch, resistance_offset=1.0)
    magnet.set_centerfield(3400)
    with pytest.raises(Exception, match="Resistance of the magnet"):
        magnet.check_resistance(3400)
    assert fake.writes()[-2:] == ["SOUR:CURR 0.0000 A", "SOUR:VOLTAGE 0.0000 V"]
