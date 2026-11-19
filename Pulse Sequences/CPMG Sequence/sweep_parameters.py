print("Start")

from CPMGExp import CPMGExp
from CPMGParameters import CPMGParameters
from EPRHardware import EPRHardware
from Sweep import Sweep
import numpy as np

parameters = CPMGParameters()

for i in np.arange(0,0.1,0.02):
    # Keep hardware declaration and experiment after mw_freq is defined
    parameters.pulse_freq = 20e6
    parameters.mw_freq = 9.6847
    parameters.B0_field = 3381.0 #Setting nothing. Just to record the parameter.
    # Control it in magnetcontrol

    hardware = EPRHardware(parameters)
    experiment = CPMGExp(parameters,hardware)
    hardware.set_iq_offset(0.01628,-0.03015)

    # Pulse sequence
    parameters.envelope = "gaussian"
    parameters.seq_offset_ns = 800
    parameters.pi_by_two_pulse_ns = 500
    parameters.gap_len1_ns = 6000
    parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
    parameters.trigger_offset_ns = 00
    parameters.switch_pulse_ns = 6000


    # Acquisition
    parameters.shot_repetition_time_ns = 5e6
    parameters.shots_number = 1024

    # MW amplitudes
    parameters.pi_by_two_amplitude = 0.016
    parameters.pi_amplitude = 0.032

    parameters.cpmg_pulse_ns = parameters.pi_by_two_pulse_ns
    parameters.cpmg_pulse_amplitude = parameters.pi_amplitude
    parameters.cpmg_count = 7
    parameters.cpmg_gap_len_ns = 2*parameters.gap_len1_ns
    parameters.cpmg_detection_bool = True #True = intermediate gates open over multipulse / Flase - closed.

    # RF Section:
    parameters.rf_amp = i
    parameters.rf_phase= 0 # \+phi, deg. sin (x+phi)
    parameters.rf_freq_fac = 1
    parameters.rf_frequency = parameters.rf_freq_fac*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns))*1e9 #Hz

    #sweep_value_min = 3500
    #sweep_value_max = 11000
    #sweep_value_step = 100 #100ns = 5 MHz
    sweep_value_min = 0*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns))*1e9
    sweep_value_max = 2.0*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns))*1e9
    sweep_value_step = 0.02*(1/(4*parameters.gap_len1_ns+2*parameters.cpmg_pulse_ns))*1e9

    parameters.filename = f"N14C60_mainB_cpmg_rf_200mV_tau_" +"{:.2f}".format(parameters.gap_len1_ns*1e-3).replace('.', 'p') + \
                          "{:.3f}".format(parameters.gap_len1_ns*1e-3).replace('.', 'p') + "us_cpmg_" + \
                          "{:.0f}".format(parameters.cpmg_count).replace('.', 'p') + "_" + \
                          "rf_freq_sweep_from_" + "{:.2f}".format(sweep_value_min*1e-3).replace('.', 'p') + "_to_" + \
                          "{:.2f}".format(sweep_value_max*1e-3).replace('.', 'p')+ "us"

    sweep = Sweep(
        experiment_class=CPMGExp,
        parameters=parameters,
        hardware=hardware,
        parameter_name="rf_frequency",
        sweep_values=np.concatenate([
                        np.arange(sweep_value_min, sweep_value_max + sweep_value_step, sweep_value_step)
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

