from HahnEchoExp import HahnEchoExp
from HahnEchoParameters import HahnEchoParameters
from EPRHardware import EPRHardware

parameters = HahnEchoParameters()

# Initialization of instruments
parameters.pulse_freq = 100e6
parameters.mw_freq = 9.701 #9.6932

hardware = EPRHardware(parameters) # Should be kept after frequencies
experiment = HahnEchoExp(parameters,hardware)


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
parameters.shot_repetition_time_ns = 0.2e6
parameters.shots_number = 20000

# MW amplitudes

parameters.pi_amplitude = 0.6 #0.75
parameters.pi_by_two_amplitude =0.5*parameters.pi_amplitude


parameters.filename ="Ni_bpyBr_C45_7p0K_test_" +\
                      "{:.4f}".format(parameters.mw_freq).replace('.', 'p') + "GHz_"


print("HI")
result = experiment.run(True)
hardware.dispose()

print("End")