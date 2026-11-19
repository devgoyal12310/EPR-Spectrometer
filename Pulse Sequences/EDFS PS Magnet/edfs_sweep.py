from EDFSExp import EDFSExp
from EDFSParameters import EDFSParameters
from EPRHardware import EPRHardware
from HardwareFiles.PS10360 import PS10360

from Sweep import Sweep
import numpy as np

parameters = EDFSParameters()
magnet= PS10360()

# Initialization of instruments
parameters.pulse_freq = 100e6
parameters.mw_freq = 9.6932

hardware = EPRHardware(parameters) # Should be kept after frequencies
hardware.set_iq_offset(0.01628,-0.03015)

# Pulse sequence
parameters.envelope="gaussian"
parameters.seq_offset_ns = 400
parameters.pi_by_two_pulse_ns = 32
parameters.gap_len1_ns = 250
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_offset_ns = 00
parameters.switch_pulse_ns = 600


# Acquisition
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 2048


# MW amplitudes
parameters.pi_by_two_amplitude =0 # 0.175
parameters.pi_amplitude = 0 #0.35

sweep_value_min = 100 #Gauss
sweep_value_max = 500 #Gauss
sweep_value_step = 100 #Gauss


parameters.filename ="Ni_bpyBr_" +\
                      "{:.4f}".format(parameters.mw_freq).replace('.', 'p') + "GHz_" + \
                      "field_from" + "{:.2f}".format(sweep_value_min).replace('.', 'p') + "G_to" + \
                      "{:.2f}".format(sweep_value_max ).replace('.', 'p') + "G"

parameters.filename=f"Test_Dev_"

sweep = Sweep(
    experiment_class=EDFSExp,
    parameters=parameters,
    hardware=hardware,
    parameter_name="B_field",
    sweep_values=np.concatenate([np.arange(sweep_value_min, sweep_value_max + sweep_value_step, sweep_value_step)]),
    magnet = magnet
)

try:

    results = sweep.run()

except KeyboardInterrupt:

    print("\nExperiment interrupted by user.")

finally:

    print("Disposing hardware...")
    hardware.dispose()
    magnet.close()
    print("Hardware disposed.")