import time

from EDFSExp import EDFSExp
from EDFSParameters import EDFSParameters
from EPRHardware import EPRHardware
from HardwareFiles.PS10360 import PS10360

parameters = EDFSParameters()
magnet= PS10360()

# Initialization of instruments
parameters.pulse_freq = 100e6
parameters.mw_freq = 9.6923  # actual frequency = 9.569394
parameters.B0_field = 3400  # Will actually change the field

hardware = EPRHardware(parameters) # Should be kept after frequencies and field
experiment = EDFSExp(parameters,hardware,magnet)

# Pulse sequence
parameters.envelope = "gaussian"  # square or gaussian - case insensitive
parameters.seq_offset_ns = 500
parameters.pi_by_two_pulse_ns = 32
parameters.gap_len1_ns = 250
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_offset_ns = 00
parameters.switch_pulse_ns = 600 # window width, centered 2 tau position

# Acquisition
parameters.shot_repetition_time_ns = 5e6
parameters.shots_number = 2048

# MW amplitudes
parameters.pi_by_two_amplitude = 0.175
parameters.pi_amplitude = 0.35 #2 * parameters.pi_by_two_amplitude
parameters.filename =f"N15C60_D25_{parameters.pulse_freq}_gaussian_test_"

# Run Experiment
result = experiment.run(True)
hardware.dispose()
print("End")