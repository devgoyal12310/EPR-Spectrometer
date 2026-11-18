import time

from InversionRecoveryExp import InversionRecoveryExp
from InversionRecoveryParameters import InversionRecoveryParameters
from HahnEchoHardware import HahnEchoHardware
from Sweep import Sweep
import numpy as np

parameters = InversionRecoveryParameters()



# Initialization of instruments
parameters.mw_freq = 9.701 #9.68956
parameters.B0_field = 0 #Setting nothing. Just to record the parameter.
parameters.pulse_freq = 100e6


hardware = HahnEchoHardware(parameters) # Should be kept after frequencies
hardware.set_iq_offset(0.01628,-0.03015)
experiment = InversionRecoveryExp(parameters,hardware)

# Pulse sequence
parameters.envelope = 'gaussian'
parameters.seq_offset_ns = 800
parameters.pi_by_two_pulse_ns = 20
parameters.gap_len1_ns = 300
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_offset_ns = 100
parameters.switch_pulse_ns = 300

# Acquisition
parameters.shot_repetition_time_ns = 0.2e6
parameters.shots_number = 16000
parameters.data_start = 1
parameters.data_stop = 2500

# MW amplitudes
parameters.pi_amplitude = 0.6
parameters.pi_by_two_amplitude = 0.6*0.5


#Inversion Pulse Parameters

parameters.inversion_pulse_ns = parameters.pi_pulse_ns
parameters.inversion_pulse_amplitude = parameters.pi_amplitude
parameters.inversion_recovery_time_ns = 1500


sweep_value_min = 1000
sweep_value_max = 4000
sweep_value_step = 500

parameters.filename = f"Ni_bpyBr_C45_3p9K_T1_B0_" + \
                      "{:.1f}".format(parameters.B0_field).replace('.', 'p') + "_G" + \
                      "_Tdelay_from_" + "{:.3f}".format(sweep_value_min).replace('.', 'p') + "ns_to" + \
                      "{:.3f}".format(150).replace('.', 'p')+ "us_"

sweep = Sweep(
    experiment_class=InversionRecoveryExp,
    parameters=parameters,
    hardware=hardware,
    parameter_name="inversion_recovery_time_ns",
    #sweep_values=np.concatenate([np.linspace(0, 0.2, 80)])
    sweep_values=np.concatenate([
        np.arange(1000, 3000, 500),
        np.arange(3000, 8000, 2500),
        np.arange(8000, 15000, 5000),
        np.arange(15000, 20000, 10000),
        np.arange(20000, 60001, 20000),
        np.array([75000, 100000, 125000, 150000, 200000, 250000])

    ])

)

#np.concatenate([np.linspace(0, 0.5, 50),np.linspace(10e4, 10e5, 5),np.linspace(10e5, 10e6, 5),np.linspace(10e6, 10e7, 5)])
try:

    results = sweep.run()

except KeyboardInterrupt:

    print("\nExperiment interrupted by user.")

finally:

    print("Disposing hardware...")
    hardware.dispose()
    print("Hardware disposed.")