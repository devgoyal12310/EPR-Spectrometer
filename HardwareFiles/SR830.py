# -*- coding: utf-8 -*-
"""
Created on Wed Jan 04 13:48:57 2017

@author: ardavanlab
"""

import sys, time
import pyvisa as visa


class SR830:
    def __init__(self, address):
        rm = visa.ResourceManager()
        self.address = address
        # rm.open_resource('GPIB0::12::INSTR')
        self.thisSR830 = rm.open_resource('GPIB1::' + str(address))
        #print('Lock-in initialised')

    def get_X(self):
        text = self.thisSR830.query('OUTP?1')
        return float(text)

    def get_Y(self):
        text = self.thisSR830.query('OUTP?2')
        return float(text)

    def get_R(self):
        text = self.thisSR830.query('OUTP?3')
        return float(text)

    def get_T(self):
        text = self.thisSR830.query('OUTP?4')
        return float(text)

    def set_sensitivity(self, sen):
        string = 'SENS%s' % sen
        self.thisSR830.write(string)

    def set_phase(self, phase):
        string = 'PHAS%s' % phase
        self.thisSR830.write(string)

    def set_freq(self, frequency):
        string = 'FREQ%s' % frequency
        self.thisSR830.write(string)

    def set_time_const(self, time_constant):
        index = self._get_time_constant_index(time_constant)
        string = 'OFLT%s' % index
        self.thisSR830.write(string)

    def get_phase(self):
        text = self.thisSR830.query('PHAS?')
        return float(text)

    def get_aux_vol(self, aux_channel):
        string = 'OAUX? %s' % (aux_channel)
        text = self.thisSR830.query(string)
        return float(text)

    def auto_phase(self):
        self.thisSR830.write('APHS')
        text = self.thisSR830.query('PHAS?')
        return float(text)

    def auto_offset_X(self):
        self.thisSR830.write('AOFF 1')

    def auto_offset_Y(self):
        self.thisSR830.write('AOFF 2')

    def auto_gain(self):
        self.thisSR830.write('AGAN')

    def auto_gain_plus_one(self):
        self.thisSR830.write('AGAN')
        time.sleep(10)
        sen = float(self.thisSR830.query('SENS?'))
        if sen < 26:
            string = 'SENS%s' % (sen + 1)
            self.thisSR830.write(string)

    def get_input_overload(self):
        self.thisSR830.query('LIAS? 0')
        text = self.thisSR830.query('LIAS? 0')
        return float(text)

    def set_aux_vol(self, aux_channel, aux_vol):
        string = 'AUXV%s{,%f}' % (aux_channel, aux_vol)
        self.thisSR830.write(string)

    def set_amplitude(self, amplitude):
        string = 'SLVL%s' % (amplitude)
        self.thisSR830.write(string)

    def get_harmonic(self):
        text = self.thisSR830.query('HARM?')
        return float(text)

    def set_harmonic(self, harmonic):
        string = 'HARM%s' % (harmonic)
        self.thisSR830.write(string)

    def close(self):
        self.thisSR830.close()

    def read(self):
        return self.thisSR830.read()

    def clear_queue(self):
        while (True):
            try:
                self.thisSR830.read()
            except visa.VisaIOError:
                break;

    def _get_time_constant_index(self, time_constant):
        index = 0

        if time_constant <= 20e-6:
            index = 0
        elif time_constant <=60e-6:
            index = 1
        elif time_constant<=200e-6:
            index = 2
        elif time_constant<=600e-6:
            index = 3
        elif time_constant<=2e-3:
            index = 4
        elif time_constant<=6e-3:
            index = 5
        elif time_constant <=20e-3:
            index=6
        elif time_constant <=60e-3:
            index = 7
        elif time_constant <=200e-3:
            index = 8
        elif time_constant <=600e-3:
            index = 9
        elif time_constant <=2:
            index = 10
        elif time_constant <=6:
            index = 11
        elif time_constant <=20:
            index=12
        elif time_constant <= 60:
            index = 13
        elif time_constant <=200:
            index = 14
        elif time_constant <=600:
            index = 15
        elif time_constant <=2e3:
            index = 16
        elif time_constant <=6e3:
            index = 17
        elif time_constant <= 20e3:
            index = 18
        else:
            index = 19
        return  index