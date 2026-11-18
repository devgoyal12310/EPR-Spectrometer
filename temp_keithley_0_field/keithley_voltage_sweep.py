import time

import numpy as np
import pyvisa
from keithley_JB import Keithley2470

rm = pyvisa.ResourceManager()
res = rm.open_resource("GPIB1::18::INSTR")
res.read_termination = "\n"
res.write_termination = "\n"
res.timeout = 10_000

sm = Keithley2470(res)

try:
    print(sm.idn())
    sm.output_off()
    sm.set_source_current_mode()
    sm.set_voltage_limit(1.0)  # voltage compliance limit, in volts

    sm.set_source_voltage_mode()
    sm.set_current_limit(0.01)  # current compliance limit, in amps

    current_min_A = 0 #Amphere
    current_max_A = 2*1e-3 #amphere
    current_step_A = 0.1*1e-3 #1mA

    sweep_range = np.arange(current_min_A,current_max_A+current_step_A,current_max_A)
    for i in sweep_range:
        current_a = i  # 0 to 2 mA in 0.1 mA steps
        sm.set_current(current_a)
        print(f"Set current: {current_a * 1e3:.2f} mA")
        time.sleep(0.5)

finally:
    sm.output_off()
    res.close()
    rm.close()