import pyvisa as visa

rm = visa.ResourceManager()
scope = rm.open_resource("GPIB::1")

try:
    scope.write("ACQUIRE:STATE OFF")
except:
    pass

try:
    scope.clear()
except:
    pass

scope.close()

print("Scope cleared.")