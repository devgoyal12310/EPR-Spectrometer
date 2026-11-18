print("Start")

from InversionRecoveryExp import InversionRecoveryExp
from InversionRecoveryParameters import InversionRecoveryParameters
from HahnEchoHardware import HahnEchoHardware


parameters = InversionRecoveryParameters()

# Initialization of instruments
parameters.pulse_freq = 10e6
parameters.mw_freq = 9.7059  # actual is 9.569394

hardware = HahnEchoHardware(parameters) # Should be kept after frequencies
experiment = InversionRecoveryExp(parameters,hardware)

# Pulse sequence
parameters.envelope ="gaussian" #square or gaussian
parameters.seq_offset_ns = 300
parameters.pi_by_two_pulse_ns = 32
parameters.gap_len1_ns = 268
parameters.pi_pulse_ns = 32
parameters.trigger_offset_ns = 100
parameters.switch_pulse_ns = 1000

# Acquisition
parameters.shot_repetition_time_ns = 5e6
parameters.shots_number = 2048
parameters.data_start = 1
parameters.data_stop = 5000

# MW amplitudes
parameters.pi_by_two_amplitude = 0.016
parameters.pi_amplitude = 2*parameters.pi_by_two_amplitude

#Inversion Pulse Parameters

parameters.inversion_pulse_ns = 400
parameters.inversion_pulse_amplitude = 0.15
parameters.inversion_recovery_time_ns = 300

parameters.filename = f"inversion_Recovery"


# Run Experiment
result = experiment.run(True)
hardware.dispose()

print("End")