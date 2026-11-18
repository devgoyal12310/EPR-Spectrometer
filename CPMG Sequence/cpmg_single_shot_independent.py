import numpy as np

print("Start")

from CPMGExp import CPMGExp
from CPMGParameters import CPMGParameters
from HahnEchoHardware import HahnEchoHardware


num_shot = np.arange(1, 65, 1)
cpmg_num_count = np.arange(6, 27, 3)
for q in cpmg_num_count:
    for i in num_shot:
        print(f"Running experiment {i}/1024")

        parameters = CPMGParameters()

        # Keep hardware declaration and experiment after mw_freq is defined
        parameters.pulse_freq = 20e6 #
        parameters.mw_freq = 9.6847
        parameters.B0_field = 3381.0 #Gauss. Set Nothing. Just for the record
        #Magnetic field should be set in magnetcontrol.py

        hardware = HahnEchoHardware(parameters)
        experiment = CPMGExp(parameters,hardware)

        hardware.set_iq_offset(0.01628,-0.03015)

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
        parameters.cpmg_count = q
        parameters.cpmg_gap_len_ns = 2*parameters.gap_len1_ns
        parameters.cpmg_detection_bool = True  #True = intermediate gates open over multipulse / Flase - closed.

        # RF Section:
        parameters.rf_amp = 0.15
        parameters.rf_phase= 0 # \+phi, deg. sin (x+phi)
        parameters.rf_freq_fac = 1.0

        parameters.rf_frequency =  parameters.rf_freq_fac*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns)) *1e9

        parameters.filename = f"N14C60_mainB_cpmg_rf_200mV_" +  "{:.2f}".format(parameters.rf_amp).replace('.', 'p') +"_tau_"+ \
                              "{:.3f}".format(parameters.gap_len1_ns*1e-3).replace('.', 'p') + "us_cpmg_" + \
                              "{:.0f}".format(parameters.cpmg_count).replace('.', 'p') + "_" + \
                               "num_" + "{:.0f}".format(i)



        print("HI")
        result = experiment.run(True)
        hardware.dispose()

        print("End")