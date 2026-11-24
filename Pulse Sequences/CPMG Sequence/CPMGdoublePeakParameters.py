class CPMGdoublePeakParameters:
    def __init__(self):

        self.save_directory = fr"Y:\DAQ\CondensedMatterGroups\Rest-Of-CM-DAQ-Groups\ArdavanGroup\Measurements\New_Code\CPMG"
        self.envelope ="square"
        self.seq_offset_ns = 200
        self.pi_by_two_pulse_ns = 50
        self.gap_len1_ns = 800
        self.pi_pulse_ns = 50
        self.data_start = 1
        self.data_stop = 1000
        self.trigger_offset_ns = 500
        self.switch_pulse_ns = 1000
        self.filename ="test"
        self.pulse_freq = 100e6

        self.mw_freq= 9.7
        self.cpmg_gap_len_ns = 1600
        self.cpmg_detection_bool = False
        self.rf_tau_ns = 111.0

        self.cpmg_pulse_ns = 50
        self.cpmg_pulse_amplitude = 1.0
        self.cpmg_count = 1
        self.cpmg_pulse_axis = +X

        self.rf_amp = 1.0
        self.rf_phase = 0.0
        self.rf_freq_frac = 1.0
        self.rf_frequency = 10e6


        self.shot_repetition_time_ns = 1e6
        self.shots_number = 32

        # Oscilloscope wait: if an acquisition takes longer than expected
        # (2 x oscilloscope_wait_time + 120 s): False = print a warning and keep waiting,
        # True = stop the run with a TimeoutError.
        self.abort_on_acquisition_timeout = False

        self.pi_by_two_amplitude = 0.5
        self.pi_amplitude = 1.0
        self.oscilloscope_wait_time = (((self.seq_offset_ns +self.pi_by_two_pulse_ns + self.gap_len1_ns +self.pi_pulse_ns)+ (self.cpmg_pulse_ns+self.gap_len1_ns)* self.cpmg_count
                                       + self.switch_pulse_ns + 1000 + self.shot_repetition_time_ns) * self.shots_number) /1e9

    def to_dict(self):
        return {
            "mw_freq":self.mw_freq,
            "pi_pulse_duration": self.pi_pulse_ns,
            "pi_by_two_pulse_duration": self.pi_by_two_pulse_ns,
            "sequence_offset": self.seq_offset_ns,
            "gap_len1": self.gap_len1_ns,
            "data_start": self.data_start,
            "data_stop": self.data_stop,
            "trigger_offset_ns": self.trigger_offset_ns,
            "switch_pulse_duration": self.switch_pulse_ns,
            "shot_repetition_time": self.shot_repetition_time_ns,
            "number_of_shots": self.shots_number,
            "pi_by_two_amplitude": self.pi_by_two_amplitude,
            "pi_amplitude": self.pi_amplitude,
            "cpmg_pulse_amp": self.cpmg_pulse_amplitude,
            "cpmg_pulse_ns": self.cpmg_pulse_ns,
            "cpmg_count": self.cpmg_count,
            "cpmg_gap_len_ns": self.cpmg_gap_len_ns,
            "oscilloscope_wait_time": self.oscilloscope_wait_time,
            "rf_amp":self.rf_amp,
            "rf_phase":self.rf_phase,
            "rf_frequency":self.rf_frequency,
            "rf_freq_frac":self.rf_freq_frac,
             "rf_tau_ns_tau_sweep":self.rf_tau_ns
        }
