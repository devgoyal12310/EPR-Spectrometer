"""HardwareFiles/Oxford_ITC.py: temperature controller readings over GPIB."""
import pytest

import pyvisa

from support import FakeInstrument, FakeResourceManager, fixed_by


class FakeITC(FakeInstrument):
    """Answers each command once, like the ITC503. `replies` lists the answers to give,
    in order, per command; when a list runs out the last answer repeats."""

    def __init__(self, **replies):
        super().__init__()
        self.answers = {cmd: list(answers) for cmd, answers in replies.items()}

    def on_write(self, command):
        answers = self.answers.get(command, [command[:1]])
        self.read_queue.append(answers.pop(0) if len(answers) > 1 else answers[0])


def make_itc(monkeypatch, **replies):
    from HardwareFiles.Oxford_ITC import Oxford_ITC
    fake = FakeITC(**replies)
    monkeypatch.setattr(pyvisa, "ResourceManager", FakeResourceManager({"GPIB1::15": fake}))
    return Oxford_ITC(15), fake


def test_connects_in_remote_mode(monkeypatch):
    _, fake = make_itc(monkeypatch)
    assert fake.writes() == ["C3"]


def test_reads_temperature(monkeypatch):
    itc, _ = make_itc(monkeypatch, R1=["R4.215"])
    assert itc.get_temperature() == 4.215


def test_reads_heater_percent_and_voltage(monkeypatch):
    itc, _ = make_itc(monkeypatch, R5=["R12.5"], R6=["R3.1"])
    assert itc.get_heater_percent() == 12.5
    assert itc.get_heater_voltage() == 3.1


def test_garbled_temperature_reply_is_retried(monkeypatch):
    itc, fake = make_itc(monkeypatch, R1=["?", "R4.215"])
    assert itc.get_temperature() == 4.215
    assert fake.writes().count("R1") == 2


@fixed_by(9, "a garbled heater reply returns the temperature instead")
def test_garbled_heater_reply_is_retried_as_a_heater_reading(monkeypatch):
    itc, _ = make_itc(monkeypatch, R5=["?", "R12.5"], R1=["R4.215"])
    assert itc.get_heater_percent() == 12.5


@fixed_by(9, "an ITC that never answers properly recurses until RecursionError")
def test_gives_up_after_three_garbled_replies(monkeypatch):
    itc, fake = make_itc(monkeypatch, R1=["?"])
    with pytest.raises(ValueError, match="no valid reply"):
        itc.get_temperature()
    assert fake.writes().count("R1") == 3


def test_set_temperature_command(monkeypatch):
    itc, fake = make_itc(monkeypatch)
    itc.set_temperature(4.2)
    assert fake.writes()[-1] == "T4.2000"


def test_manual_heater_switches_to_manual_first(monkeypatch):
    itc, fake = make_itc(monkeypatch)
    itc.set_heater(25)
    assert fake.writes()[-2:] == ["A0", "O25.0"]
