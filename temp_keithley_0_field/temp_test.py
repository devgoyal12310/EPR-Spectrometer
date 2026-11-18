import pyvisa
import time

rm = pyvisa.ResourceManager()

meter = rm.open_resource("GPIB1::15::INSTR")

meter.timeout = 5000
meter.write_termination = "\n"
meter.read_termination = "\n"

print("Testing Keithley 2001...")

try:
    meter.clear()
    time.sleep(0.5)

    print("IDN:", meter.query("*IDN?"))

except Exception as e:
    print("Error:", repr(e))

finally:
    meter.close()
    rm.close()