from EDFSExp import EDFSExp
from EDFSParameters import EDFSParameters
from EPRHardware import EPRHardware
from HardwareFiles.kiethleymagnet import kiethleymagnet

from Sweep import Sweep
import numpy as np

parameters = EDFSParameters()
magnet= kiethleymagnet()

# Initialization of instruments
parameters.pulse_freq = 100e6
parameters.mw_freq = 9.6990

hardware = EPRHardware(parameters) # Should be kept after frequencies
hardware.set_iq_offset(0.01628,-0.03015)

# Pulse sequence
parameters.envelope="gaussian"
parameters.seq_offset_ns = 400
parameters.pi_by_two_pulse_ns = 20
parameters.gap_len1_ns = 320
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_offset_ns = 50
parameters.switch_pulse_ns = 300


# Acquisition
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 2048


# MW amplitudes
parameters.pi_by_two_amplitude = 0.3#0.75*0.5 #0.175#0.175
parameters.pi_amplitude = 0.6#0.75 #0.35#0.35

sweep_value_min = -0.1 #amps
sweep_value_max = +0.1 #amps
sweep_value_step = 0.025 #amps

sweep_list = np.concatenate([np.arange(-0.8,-0.4,0.05),np.arange(-0.4,-0.2,0.025),np.arange(-0.2,0.2,0.025),np.arange(0.2,0.4,0.025),np.arange(0.4,0.8,0.05)])
#sweep_list = np.array([-0.1,-0.05,0,0.05,0.1])

parameters.filename ="Ni_bpyBr_C15_5K_" +\
                      "{:.4f}".format(parameters.mw_freq).replace('.', 'p') + "GHz_" + \
                      "current_from" + "{:.4f}".format(-0.8).replace('.', 'p') + "A_to" + \
                      "{:.4f}".format(0.8 ).replace('.', 'p') + "A"

parameters.filename=f"Dev_test"

sweep = Sweep(
    experiment_class=EDFSExp,
    parameters=parameters,
    hardware=hardware,
    parameter_name="B_field",
    sweep_values=sweep_list,
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