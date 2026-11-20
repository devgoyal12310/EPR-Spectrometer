import numpy as np

print("Start")

from CPMGExp import CPMGExp
from CPMGParameters import CPMGParameters
from EPRHardware import EPRHardware

parameters = CPMGParameters()

# Keep hardware declaration and experiment after mw_freq is defined
parameters.pulse_freq = 20e6 #
parameters.mw_freq = 9.6847
parameters.B0_field = 3381.0  #Gauss. Set Nothing.

#Magnetic field should be set in Ox_PS_field_setter.py

hardware = EPRHardware(parameters)
experiment = CPMGExp(parameters,hardware)

hardware.set_iq_offset(0.01628,-0.03015)


#print(f"Running experiment {i*16}/1024")

# Pulse sequence
parameters.envelope = "square"
parameters.seq_offset_ns = 800
parameters.pi_by_two_pulse_ns = 100
parameters.gap_len1_ns = 500
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_offset_ns = 100
parameters.switch_pulse_ns = 500
parameters.pi_by_two_axis = "+X"
parameters.pi_axis = "+X"


# Acquisition
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 256

# MW amplitudes
parameters.pi_by_two_amplitude = 0.1#0.016
parameters.pi_amplitude = 0.1 #0.032

parameters.cpmg_pulse_ns = parameters.pi_by_two_pulse_ns #same as pi amplitude
parameters.cpmg_count = 6  # Should be a mulitple of the number of axes put - if two axes are defined, they will be repeated
parameters.cpmg_gap_len_ns = 2*parameters.gap_len1_ns
parameters.cpmg_detection_bool = True  #True = intermediate gates open over multipulse / Flase - closed.

parameters.cpmg_pulse_axes = ["+X","+Y"]     # The sign should be mentioned
parameters.cpmg_pulse_amplitudes = [0.5,0.5]
parameters.cpmg_pulse_phase_offsets = [0.0,270]  # Should be positive

# RF Section:
parameters.rf_amp = 0.0
parameters.rf_phase= 0 # \+phi, deg. sin (x+phi)
parameters.rf_freq_fac = 1.0

parameters.rf_frequency =  parameters.rf_freq_fac*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns)) *1e9

parameters.filename = f"N14C60_mianB_xmy_mymy_" + \
                      "{:.1f}".format(parameters.B0_field).replace('.', 'p') + "_G" + \
                      "_tau_" + "{:.1f}".format(parameters.gap_len1_ns*1e-3).replace('.', 'p') +"_us"+ \
                      "_cpmg_" + "{:.0f}".format(parameters.cpmg_count ).replace('.', 'p') + "_"+ \
                      "rf_800mV_amp_" + "{:.2f}".format(parameters.rf_amp).replace('.', 'p')
parameters.filename=f"Test_"


print("HI")
result = experiment.run(True)
hardware.dispose()

print("End")