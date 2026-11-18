"""Set a Keithley 2470 output from the values below; no GUI is used.

Set MODE to "current" or "voltage" to configure and enable the source. The
output remains enabled after this script exits. Set MODE to "off" and run the
script to disable the output.
"""

import pyvisa
from keithley_JB import Keithley2470


RESOURCE = "GPIB1::18::INSTR"

# Choose "current", "voltage", or "off".
MODE = "current"

# Current mode: SETPOINT is amperes; COMPLIANCE is the voltage limit in volts.
# Voltage mode: SETPOINT is volts; COMPLIANCE is the current limit in amperes.
SETPOINT = -0.0154  # Amphere or Voltage
COMPLIANCE = 4.8

#0.001 A = 0.3 Gauss
#0.01 A = 3 Gauss
#0.1 A = 30 Gauss


rm = pyvisa.ResourceManager()
res = None
sm = None

try:
    print("VISA resources:", rm.list_resources())
    res = rm.open_resource(RESOURCE)
    res.read_termination = "\n"
    res.write_termination = "\n"
    res.timeout = 60_000
    sm = Keithley2470(res)
    print("Connected:", sm.idn())

    mode = MODE.strip().lower()
    if mode == "off":
        sm.output_off()
        print("Keithley output is off.")
    elif mode == "current":
        sm.output_off()
        sm.set_source_current_mode()
        sm.set_voltage_limit(COMPLIANCE)
        sm.set_current(SETPOINT)
        sm.measure_voltage()
        sm.output_on()
        print(f"Output enabled: {SETPOINT:g} A, voltage limit {COMPLIANCE:g} V")
        print("Voltage reading:", sm.read())
    elif mode == "voltage":
        sm.output_off()
        sm.set_source_voltage_mode()
        sm.set_current_limit(COMPLIANCE)
        sm.set_voltage(SETPOINT)
        sm.measure_voltage()
        sm.output_on()
        print(f"Output enabled: {SETPOINT:g} V, current limit {COMPLIANCE:g} A")
        print("Voltage reading:", sm.read())
    else:
        raise ValueError('MODE must be "current", "voltage", or "off"')
finally:
    if res is not None:
        res.close()
    rm.close()


