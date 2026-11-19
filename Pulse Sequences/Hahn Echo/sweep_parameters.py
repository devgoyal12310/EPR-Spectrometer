import time

from HahnEchoExp import HahnEchoExp
from HahnEchoParameters import HahnEchoParameters
from EPRHardware import EPRHardware
from Sweep import Sweep
import numpy as np


parameters = HahnEchoParameters()


# Initialization of instruments
parameters.pulse_freq = 100e6
parameters.mw_freq = 9.701 #GHz
parameters.B0_field = 0 #Setting nothing. Just to record the parameter.

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
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 10000

# MW amplitudes
parameters.pi_amplitude = 0.6 #0.35
parameters.pi_by_two_amplitude = 0.6*0.5 #0.5*parameters.pi_amplitude



sweep_value_min = 270
sweep_value_max = 477
sweep_value_step = 23


parameters.filename =f"Ni_bpyBr_C45_7p0K_" + \
                     "B0_" + "{:.2f}".format(parameters.B0_field).replace('.', 'p') +"_G_"+ \
                     "tau_from_" + "{:.4f}".format(sweep_value_min).replace('.', 'p') + "_to_" + \
                     "{:.4f}".format(3000).replace('.', 'p') + "_ns_"


sweep = Sweep(
    experiment_class=HahnEchoExp,
    parameters=parameters,
    hardware=hardware,
    parameter_name="gap_len1_ns",
    sweep_values = np.concatenate([
        np.arange(sweep_value_min, sweep_value_max, sweep_value_step),
        np.arange(500, 736+59, 59),
        np.arange(800, 1562+127, 127),
        np.arange(1700, 2453 + 251, 251),
        np.array([3000, 3500, 4000, 5000])

    ])
)

try:

    results = sweep.run()

except KeyboardInterrupt:

    print("\nExperiment interrupted by user.")

finally:

    print("Disposing hardware...")
    hardware.dispose()
    print("Hardware disposed.")