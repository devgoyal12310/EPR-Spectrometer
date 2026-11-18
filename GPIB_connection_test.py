import pyvisa as visa

rm = visa.ResourceManager()
print(rm.list_resources())


try:
    for address in rm.list_resources():
        try:
            device = rm.open_resource(address)
            device.read_termination = "\n"
            device.write_termination = "\n"
            device.timeout = 3000
            print(address, "->", device.query("*IDN?").strip())
            device.close()
        except Exception as error:
            print(address, "-> no ID response:", error)
finally:
    rm.close()