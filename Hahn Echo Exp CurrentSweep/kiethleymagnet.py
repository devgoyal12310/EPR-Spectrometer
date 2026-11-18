import time
import pyvisa


class kiethleymagnet:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.mag = self.rm.open_resource("GPIB1::18::INSTR")
        self.mag.read_termination = "\n"
        self.mag.write_termination = "\n"
        self.mag.timeout = 60_000

        self.mag.write(":SOUR:FUNC CURR")
        self.mag.write(":SOUR:CURR:VLIM 4.0")
        print("Connected to", self.mag.query("*IDN?").strip())

        self.mag.write(":OUTP ON")

    def set_current(self, amps):

        self.mag.write(f":SOUR:CURR:LEV {amps}")
        self.mag.write(':SENS:FUNC "VOLT"')
        self.mag.write(":OUTP ON")

        time.sleep(5) #sec. Delay time between eah sweep. each measurement
        print("Voltage reading:", self.mag.query(":READ?").strip())

    def close(self):
        #self.mag.write(":OUTP OFF")
        self.mag.close()
        self.rm.close()