# Driver for the Magnet Power Supply PS10360
# Author: Niccolo Fontana
# Year: 2023
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

##### Parameters #####
par = {
    "Nominal_Current_in_A": 30.6,  # from specs
    "Nominal_Voltage_in_V": 300,  # from specs
    "Nominal_Power_in_W": 3000,  # from specs
    "Maximum_B_field_in_mT": 900  # from calibration 6 Dec. 2023
}

import pyvisa as pv
import warnings
import numpy as np
from scipy import stats


class PS10360:
    resistance_margin_max = 0.1  # Ohm

    ###### Connection to the interface ######
    def __init__(self):
        rm = pv.ResourceManager()
        #self.PS10360 = rm.open_resource('ASRL3::INSTR')
        self.PS10360 = rm.open_resource('TCPIP0::100.100.100.4::5025::SOCKET') # This part was used to be # commented.
        self.PS10360.set_visa_attribute(pv.constants.ResourceAttribute.tcpip_keepalive, True)
        self.PS10360.read_termination = '\n'
        self.PS10360.write_termination = '\n'
        self.PS10360.write('SYST:LOCK: ON')
        self.PS10360.write('OUT ON')
        self.set_mode('CC')

    ###### Ordinary commands ######
    def start_remote_control(self):
        self.PS10360.write('SYST:LOCK: ON')

    def switch_on_input(self):
        self.PS10360.write('INP ON')

    def switch_on_output(self):
        self.PS10360.write('OUT ON')

    def end_remote_control(self):
        self.PS10360.write('SYST:LOCK: OFF')

    def switch_off_input(self):
        self.PS10360.write('INP OFF')

    def switch_off_output(self):
        self.PS10360.write('OUT OFF')

    def clear_queue(self):
        self.PS10360.write('*CLS')

    def reset(self):
        self.PS10360.write('*RST')
        print("You reset the power supply. You need to turn it on manually from the front panel!")

    # Remote: power supply is connected remotely
    # Local: denial/interruption of remote control
    # None: power supply is NOT connected remotely
    def print_connection_status(self):
        string = 'SYST:LOCK:OWN?'
        print(self.PS10360.query(string))

    def print_status(self):
        print(self.PS10360.query("*STB?"))

    ###### Basic control commands ######
    def set_mode(self, mode):
        if mode == 'CC':
            string = 'SOURCE:VOLTAGE: MAX'
            self.PS10360.write(string)
        elif mode == 'CV':
            string = 'SOURCE:CURRENT: MAX'
            self.PS10360.write(string)
        else:
            warnings.warn('The mode can be either constant-current (input: "CC") or constant-voltage (input: "CV")')

    def set_centerfield(self, B_field_in_G):
        B_field_in_mT = B_field_in_G / 10.0
        # Getting the voltage and the current (from calibration done on 6 Dec. 2023)
        Curr = 0.03307 * B_field_in_mT - 0.1282  # in A

        if Curr >= 0.95 * par["Nominal_Current_in_A"] or B_field_in_mT >= par["Maximum_B_field_in_mT"]:
            raise ValueError(
                'The voltage and/or the current value exceed the maximum. The max field achievable is 900mT!')
        elif Curr <= 0 or B_field_in_mT < 0:
            Curr = 0
            string = 'SOUR:CURR %s A' % Curr
            self.PS10360.write(string)
        else:
            string = 'SOUR:CURR %s A' % Curr
            self.PS10360.write(string)

    def get_resistance_in_Ohm(self):
        voltage = self.get_voltage_in_V()
        current = self.get_current_in_A()
        resistance = voltage / current

        return resistance

    ## Orifianlly, :
    #def get_resistance_in_Ohm(self):
        #voltage = self.get_voltage_in_V()
        #current = self.get_current_in_A()
        #resistance = voltage / current

        #return resistance

    def check_resistance(self, field_in_G):
        # field_values = np.arange(1000.0, 9000.0, 1000.0)
        # resistance_values = np.array([2.61006, 2.61941, 2.63265, 2.64122, 2.65692, 2.67748, 2.70634, 2.73832])
        # p = np.polynomial.polynomial.Polynomial.fit(field_values, resistance_values, 1)
        # pnormal = p.convert(domain=(-1, 1))
        # expected_resistance = pnormal.coef[0] + 1000 * pnormal.coef[1]
        expected_resistance = 2.580871 + field_in_G * 1.765071e-05

        actual_resistance = self.get_resistance_in_Ohm()
        if abs(actual_resistance - expected_resistance) > self.resistance_margin_max:
            self.set_centerfield(0)
            raise Exception(
                f"PS10360: Resistance of the magnet ({actual_resistance} Ohm) excided the expected value ({expected_resistance} Ohm) by more than the threshold ({self.resistance_margin_max} Ohm)")

    def set_current_in_A(self, Curr):
        string = 'SOUR:CURR %.4f A' % Curr
        self.PS10360.write(string)

    def set_voltage_in_V(self, Volt):
        string = 'SOUR:VOLTAGE %.4f V' % Volt
        self.PS10360.write(string)

    ###### Protective feature commands ######
    def print_prot_overvoltage(self):
        try:
            print(self.PS10360.query("SOUR:VOLT:PROT:LEV?"))
        except:
            print("An error has occurred! Check the protection settings in the power supply!")

    def print_prot_overcurrent(self):
        try:
            print(self.PS10360.query("SOUR:CURR:PROT:LEV?"))
        except:
            print("An error has occurred! Check the protection settings in the power supply!")

    def print_prot_overpower(self):
        try:
            print(self.PS10360.query("SOUR:POW:PROT:LEV?"))
        except:
            print("An error has occurred! Check the protection settings in the power supply!")

    ###### Reading values commands ######
    def print_voltage(self):
        try:
            print(self.PS10360.query("MEAS:VOLT:DC?"))
        except:
            print("An error has occurred! Check the power supply is on and connected!")

    def get_voltage_in_V(self):
        voltage_string = self.PS10360.query("MEAS:VOLT:DC?")
        voltage = float(voltage_string[0:voltage_string.find('V') - 1])
        return voltage

    def print_current(self):
        try:
            print(self.PS10360.query("MEAS:CURR:DC?"))
        except:
            print("An error has occurred! Check the power supply is on and connected!")

    def get_current_in_A(self):
        current_string = self.PS10360.query("MEAS:CURR:DC?")
        current = float(current_string[0:current_string.find('A') - 1])
        return current

    def print_power(self):
        try:
            print(self.PS10360.query("MEAS:POW:DC?"))
        except:
            print("An error has occurred! Check the power supply is on and connected!")

    def print_all_par(self):
        try:
            array = np.array(self.PS10360.query("MEAS:ARR?"))
            print(array)
        except:
            print("An error has occurred! Check the power supply is on and connected!")

    def close(self):
        self.PS10360.close()
