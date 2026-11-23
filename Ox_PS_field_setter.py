import time
from HardwareFiles.PS10360 import PS10360

magnet = PS10360()
field = 50 #3390.4
# Minimum: 38.8 Gauss
# Maximum: 8,829 Gauss

magnet.set_centerfield(field)
time.sleep(3)

# Below ~38.8 G set_centerfield commands zero current and the resistance is undefined
if magnet.get_current_in_A() > 0:
     magnet_resistance_check_value = magnet.get_resistance_in_Ohm()
    #magnet.check_resistance(field) # Magent safety - resistance check during field =/=0

