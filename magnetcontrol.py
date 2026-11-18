import time
from PS10360 import PS10360

magnet = PS10360()
field = 0 # gauss; use 0 for zero field
# Min = 38.8 Gauss
# Max = 8820 Gauss

magnet.set_centerfield(field)
time.sleep(3)

if magnet.get_current_in_A() > 0:
    magnet_resistance_check_value = magnet.get_resistance_in_Ohm()
    #magnet.check_resistance(field)  # magnet safety check at nonzero field # Make it comment for 0 field
else:
    print('Zero field: current and voltage set to zero; resistance is undefined.')

