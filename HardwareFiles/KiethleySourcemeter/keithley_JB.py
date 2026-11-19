"""Keithley 2470 SourceMeter commands (the instrument must use the SCPI command set)."""

try:
    from .base_JB import Instrument

except ImportError:  # Ox_Kiethley_field_setter.py and base.py copied to a folder outside this package
    from base_JB import Instrument


class Keithley2470(Instrument):
    """Keithley 2470 sourcing either current or voltage.

    Wraps a PyVISA resource that is already open, with "\\n" read and write terminations.
    Values are sent as given: the driver does not check them against any safe limit.
    """

    def idn(self):
        return self.query("*IDN?")

    def reset_instrument(self):
        return self.write("*RST")

    def read(self):
        """Take one reading of the selected measure function, returned as text."""
        return self.query(":READ?")

    def output_on(self):
        return self.write(":OUTP ON")

    def output_off(self):
        return self.write(":OUTP OFF")

    # -------- Source current --------

    def set_source_current_mode(self):
        return self.write(":SOUR:FUNC CURR")

    def set_current(self, amps):
        return self.write(f":SOUR:CURR:LEV {amps}")

    def set_voltage_limit(self, volts):
        """Set the compliance voltage used while sourcing current."""
        return self.write(f":SOUR:CURR:VLIM {volts}")

    def enable_autorange_current(self):
        """Autorange the sourced current."""
        return self.write(":SOUR:CURR:RANG:AUTO ON")

    # -------- Source voltage --------

    def set_source_voltage_mode(self):
        return self.write(":SOUR:FUNC VOLT")

    def set_voltage(self, volts):
        return self.write(f":SOUR:VOLT:LEV {volts}")

    def get_voltage(self):
        """Read the programmed source voltage, without changing output state."""
        return self.query(":SOUR:VOLT:LEV?")

    def set_voltage_range(self, volts):
        """Set the range of the sourced voltage."""
        return self.write(f":SOUR:VOLT:RANG {volts}")

    def enable_autorange_source_voltage(self):
        return self.write(":SOUR:VOLT:RANG:AUTO ON")

    def set_current_limit(self, curr):
        """Set the compliance current used while sourcing voltage."""
        return self.write(f":SOUR:VOLT:ILIM {curr}")

    def set_source_voltage_delay_auto(self, enabled):
        return self.write(f":SOUR:VOLT:DEL:AUTO {'ON' if enabled else 'OFF'}")

    def set_source_voltage_delay(self, seconds):
        return self.write(f":SOUR:VOLT:DEL {seconds}")

    # -------- Measure voltage --------

    def measure_voltage(self):
        """Select voltage as the measure function; read() takes the reading."""
        return self.write(':SENS:FUNC "VOLT"')

    def set_measure_voltage_range(self, volts):
        return self.write(f":SENS:VOLT:RANG {volts}")

    def enable_autorange_measure_voltage(self):
        return self.write(":SENS:VOLT:RANG:AUTO ON")

    # -------- Measure current --------

    def measure_current(self):
        """Select current as the measure function; read() takes the reading."""
        return self.write(':SENS:FUNC "CURR"')

    def enable_autorange_measure_current(self):
        return self.write(":SENS:CURR:RANG:AUTO ON")

    def disable_autorange_measure_current(self):
        return self.write(":SENS:CURR:RANG:AUTO OFF")

    def set_measure_current_range(self, amps):
        return self.write(f":SENS:CURR:RANG {amps}")

    def set_measure_current_nplc(self, nplc):
        return self.write(f":SENS:CURR:NPLC {nplc}")

    def set_measure_current_autozero(self, enabled):
        return self.write(f":SENS:CURR:AZER {'ON' if enabled else 'OFF'}")

    # -------- Sweep --------

    def _configure_sweep(
        self, function, start, stop, points, delay, count, range_type, fail_abort, dual, buffer_name
    ):
        cmd = (
            f":SOUR:SWE:{function}:LIN {start},{stop},{int(points)},{delay},"
            f"{int(count)},{str(range_type).upper()},{str(fail_abort).upper()},{str(dual).upper()}"
        )
        if buffer_name:
            cmd += f',"{buffer_name}"'
        return self.write(cmd)

    def configure_voltage_sweep(
        self,
        start,
        stop,
        points,
        delay,
        count=0,
        range_type="BEST",
        fail_abort="OFF",
        dual="OFF",
        buffer_name=None,
    ):
        """Program a linear voltage sweep. The default count=0 repeats until abort_sweep().

        Set the current limit first. delay is the time at each point in seconds,
        fail_abort="ON" stops at a compliance limit, and dual="ON" also sweeps back.
        """
        return self._configure_sweep(
            "VOLT", start, stop, points, delay, count, range_type, fail_abort, dual, buffer_name
        )

    def configure_current_sweep(
        self,
        start,
        stop,
        points,
        delay,
        count=0,
        range_type="BEST",
        fail_abort="OFF",
        dual="OFF",
        buffer_name=None,
    ):
        """Program a linear current sweep; arguments match configure_voltage_sweep."""
        return self._configure_sweep(
            "CURR", start, stop, points, delay, count, range_type, fail_abort, dual, buffer_name
        )

    def start_sweep(self):
        return self.write(":INIT")

    def trigger(self):
        """Same command as start_sweep; kept for the archived scripts."""
        return self.start_sweep()

    def wait_for_sweep(self):
        """Hold later commands until the sweep ends; the next query waits for its reply."""
        return self.write("*WAI")

    def abort_sweep(self):
        return self.write(":ABOR")

    def read_sweep_data(self, start_pt, end_pt, buffer="defbuffer1"):
        """Return "source,reading,source,reading,..." text for points numbered from 1."""
        return self.query(f'TRAC:DATA? {start_pt},{end_pt},"{buffer}",SOUR,READ')
