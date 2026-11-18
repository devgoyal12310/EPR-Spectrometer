import pyvisa as visa
import time as time


class MWSource:

    def __init__(self):
        self.rm = visa.ResourceManager()
        self.MW = self.rm.open_resource("GPIB1::19")


    def set_freq_Ghz(self,MW_freq,Pulse_freq):
        print("Original Frequency = ", (float(self.MW.query('FREQ:CW?'))/1e9)," GHz")

        Final_freq = MW_freq*1e9+Pulse_freq
        self.MW.write(f"FREQ:CW {Final_freq}")

        print("Final Frequency = ", (float(self.MW.query('FREQ:CW?'))/1e9)," GHz")

    def set_power_dBm(self,Power):
        print("Original Power = ", float(self.MW.query('POW:AMPL?')), " dBm")


        self.MW.write(f"POW:AMPL {Power}")

        print("Final Power = ", float(self.MW.query('POW:AMPL?')), " dBm")

    def switch_on(self):
        self.MW.write("OUTP:MOD 0")
        self.MW.write("OUTP ON")
        print("OUTPUT ON")

    def switch_off(self):
        self.MW.write("OUTP OFF")
        print("Output OFF")


    def __main__(self):
        self.switch_off()
