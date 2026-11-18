import zhinst.toolkit

zt= zhinst.toolkit.session

session = zt.Session("localhost")
# self.device = self.session.connect_device("dev9182")  # For QMUL
device = session.connect_device("dev8606")

print(zt.Devices(session).connected())
print(zt.Devices(session).created_devices())

device.oscs[0].freq(float(1e6))
device.oscs[1].freq(float(15e6))
device.system.awg.oscillatorcontrol(0)

device.sigouts[0].on(0)
device.sigouts[1].on(0)
device.sigouts[2].on(0)
device.sigouts[3].on(0)

device.sigouts[0].direct(0)
device.sigouts[1].direct(0)

device.sigouts[0].range(0.6)
device.sigouts[1].range(0.6)

# Marker Routings
device.triggers.out[0].source(4)
device.triggers.out[1].source(5)
device.triggers.out[2].source(6)
device.triggers.out[3].source(7)

device.sigouts[0].offset(float(0.0))
device.sigouts[1].offset(float(0.0))

device.sigouts[0].on(1)
device.sigouts[1].on(1)

session.sync()


print("Connected to:", device)
print("Core 0 object:", device.awgs[0])
print("Core 1 object:", device.awgs[1])

#daq.setInt("/dev8606/sigouts/0/on", 1)