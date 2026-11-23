# -*- coding: utf-8 -*-
"""
Created on Fri Sep 28 15:51:09 2018

@author: localadmin
"""

import sys, time
import pyvisa as visa

class Oxford_ITC:
    def __init__(self, address):
        rm = visa.ResourceManager()
        self.address = address
        self.thisOxfordITC = rm.open_resource('GPIB1::'+str(address))
        self.thisOxfordITC.read_termination = '\r'
        self.thisOxfordITC.write_termination = '\r'
        #self.thisOxfordITC.clear_queue()
        self.set_remote()
        #print 'ITC initialsed'

    def ITCask(self,string_input):
        self.thisOxfordITC.write(string_input)
        time.sleep(50e-3)
        result = self.thisOxfordITC.read()[0:]
        return result


    def set_remote(self):
        string_text = 'C3'
        self.ITCask(string_text)

    def set_local(self):
        string_text = 'C2'
        self.ITCask(string_text)

    def read_value(self, string_text, retries=3):
        # Query an R<n> reading. On a garbled reply clear the queue and retry
        # the same query, giving up after `retries` attempts instead of recursing forever.
        for attempt in range(retries):
            text = self.ITCask(string_text)
            try:
                return float(text.replace('R',''))
            except ValueError:
                self.clear_queue()
        raise ValueError(f"ITC gave no valid reply to {string_text!r} after {retries} attempts (last reply: {text!r})")

    def get_temperature(self):
        return self.read_value('R1')

    def get_setpoint(self):
        string_text = 'R0'
        text = self.ITCask(string_text)
        return float(text.replace('R',''))

    def set_temperature(self,Temperature):
        string_text = 'T%0.4f' %Temperature
        self.ITCask(string_text)

    def set_autoHeater(self,status):
        if status == 0:
            string_text = 'A0'
            self.ITCask(string_text)
            print('HEATER MANUAL, GAS MANUAL')
        elif status ==1:
            string_text = 'A1'
            self.ITCask(string_text)
            print('HEATER AUTO, GAS MANUAL')
        else:
            print('NO GAS control, choose between 0 and 1.')

    def set_heater(self,heater_percent):
        self.set_autoHeater(0)
        if 0.0 <= heater_percent <= 99.1:
            string_text = 'O%0.1f' %heater_percent
            self.ITCask(string_text)
        else:
            print('Heater must between 00.0 and 99.9.')

    def get_heater_percent(self):
        return self.read_value('R5')

    def get_heater_voltage(self):
        return self.read_value('R6')


    def clear_queue(self):
        while (True):
            try:
                self.thisOxfordITC.read()
            except visa.VisaIOError:
                break;



    def close(self):
        self.thisOxfordITC.close()
