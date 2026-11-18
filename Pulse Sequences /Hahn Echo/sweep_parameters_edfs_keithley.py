import time

from HahnEchoExp import HahnEchoExp
from HahnEchoParameters import HahnEchoParameters
from EPRHardware import EPRHardware
from Sweep import Sweep
import numpy as np
from HardwareFiles.kiethleymagnet import kiethleymagnet
from time import time

parameters = HahnEchoParameters()
magnet = kiethleymagnet()

# Initialization of instruments
parameters.pulse_freq = 100e6
parameters.mw_freq = 9.701 #9.6895
#parameters.B0_field = 0 #Setting nothing. Just to record the parameter.

hardware = EPRHardware(parameters) # Should be kept after frequencies
hardware.set_iq_offset(0.01628,-0.03015)

# Pulse sequence
parameters.envelope="gaussian"
parameters.seq_offset_ns = 400
parameters.pi_by_two_pulse_ns = 20
parameters.gap_len1_ns = 300
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_offset_ns = 100
parameters.switch_pulse_ns = 300


# Acquisition
parameters.shot_repetition_time_ns = 0.3e6
parameters.shots_number = 10000

# MW amplitudes
parameters.pi_amplitude = 0.6
parameters.pi_by_two_amplitude = 0.6*0.5


sweep_value_min = 270
sweep_value_max = 500
sweep_value_step = 19

#current_range = np.concatenate([np.array([-0.0142]), np.arange(-0.35, -0.04, 0.05), np.arange(-0.041, 0.031, 0.02),np.arange(0.03,0.35+0.05,0.05)])
current_range = np.concatenate([np.array([-0.0154])])

#Amphere

try:
    for current in current_range:

        magnet.set_current(current) # Set current + wait 6 seconds

        parameters.B0_field= current

        parameters.filename = f"Ni_bpyBr_C45_3p4K_T2_" + \
                              "keitheley_current_" + "{:.4f}".format(parameters.B0_field).replace('.', 'p') + "_A_" + \
                              "tau_from_" + "{:.3f}".format(sweep_value_min).replace('.', 'p') + "_to_" + \
                              "{:.2f}".format(3000).replace('.', 'p') + "_ns_"


        sweep = Sweep(
            experiment_class=HahnEchoExp,
            parameters=parameters,
            hardware=hardware,
            parameter_name="gap_len1_ns",
            sweep_values=np.concatenate([
                np.arange(sweep_value_min, sweep_value_max, sweep_value_step),
                np.arange(500, 1000, 53),
                np.arange(1000, 1500, 101),
                np.arange(1500, 3000 + 250, 251)

            ])
        )



        results = sweep.run()

except KeyboardInterrupt:

            print("\nExperiment interrupted by user.")

finally:

    print("Disposing hardware...")
    hardware.dispose()
    magnet.close()
    print("Hardware and magnet connections closed.")