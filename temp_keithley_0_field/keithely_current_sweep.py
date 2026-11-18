import time

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
    sm.set_voltage_limit(4.0)  # voltage compliance limit, in volts

    sm.set_current(0.0)
    sm.output_on()

    current_min_A = -200*1e-3
    current_max_A = 200*1e-3
    current_step_A = 10e-3
    delay_s = 5.0

    number_of_steps = round((current_max_A - current_min_A) / current_step_A)
    for i in range(number_of_steps + 1):
        current_a = current_min_A + i * current_step_A
        sm.set_current(current_a)
        print(f"Set current: {current_a * 1e3:.2f} mA")
        time.sleep(delay_s)

finally:
    sm.output_off()
    res.close()
    rm.close()
