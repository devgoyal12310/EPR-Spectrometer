import numpy as np

print("Start")

from CPMGdoublePeakExp import CPMGdoublePeakExp
from CPMGdoublePeakParameters import CPMGdoublePeakParameters
from EPRHardware import EPRHardware

num_shot = np.arange(1, 65+1, 1)
for i in num_shot:

    parameters = CPMGdoublePeakParameters()

    # Keep hardware declaration and experiment after mw_freq is defined
    parameters.pulse_freq = 20e6 #
    parameters.mw_freq = 9.6847
    parameters.B0_field = 3381.0  #Gauss. Set Nothing.
    #Magnetic field should be set in Ox_PS_field_setter.py

    hardware = EPRHardware(parameters)
    experiment = CPMGdoublePeakExp(parameters,hardware)

    hardware.set_iq_offset(0.01628,-0.03015)


    print(f"Running experiment {i*16}/1024")
    # Pulse sequence
    parameters.envelope = "gaussian"
    parameters.seq_offset_ns = 800
    parameters.pi_by_two_pulse_ns = 500
    parameters.gap_len1_ns = 5000
    parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
    parameters.trigger_offset_ns = 100
    parameters.switch_pulse_ns = 8000


    # Acquisition
    parameters.shot_repetition_time_ns = 5e6
    parameters.shots_number = 16

    # MW amplitudes
    parameters.pi_by_two_amplitude = 0.016
    parameters.pi_amplitude = 0.032

    parameters.cpmg_pulse_ns = parameters.pi_by_two_pulse_ns
    parameters.cpmg_pulse_amplitude = parameters.pi_amplitude #same as pi amplitude
    parameters.cpmg_gap_len_ns = 2*parameters.gap_len1_ns
    parameters.cpmg_count = 4

    parameters.cpmg_detection_bool = True  #True = intermediate gates open over multipulse / Flase - closed.


    # RF Section:
    parameters.rf_amp = 0.0
    parameters.rf_phase= 0 # \+phi, deg. sin (x+phi)
    parameters.rf_freq_fac = 1.0

    parameters.rf_frequency =  parameters.rf_freq_fac*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns)) *1e9

    parameters.filename = f"N14C60_mianB_CPMG_xmx_mxmx_" + \
                          "16_shots_ " + "{:.0f}".format(i).replace('.', 'p') +"_" + \
                          "{:.1f}".format(parameters.B0_field).replace('.', 'p') + "_G" + \
                            "rf_800mV_amp_" + "{:.1f}".format(parameters.rf_amp).replace('.', 'p')



    print("HI")
    result = experiment.run(True)
    hardware.dispose()

    print("End")