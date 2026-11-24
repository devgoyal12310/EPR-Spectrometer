class PulseOptimizationParameters():
    def __init__(self):
        self.seq_offset_ns = 200
        self.pi_by_two_pulse_ns = 50
        self.gap_len1_ns = 800
        self.pi_pulse_ns = 50
        self.data_start = 1
        self.data_stop = 5000
        self.trigger_pulse_ns = 500
        self.switch_pulse_ns = 1000
        self.filename= "test_"

        self.i_phase_offset = 0
        self.q_phase_offset = 0
        self.pulse_freq = 100e6
        self.i_offset= 0.0
        self.q_offset = 0.0

        self.shot_repetition_time_ns = 1e6
        self.shots_number = 32

        # Oscilloscope wait: if an acquisition takes longer than expected
        # (2 x oscilloscope_wait_time + 120 s): False = print a warning and keep waiting,
        # True = stop the run with a TimeoutError.
        self.abort_on_acquisition_timeout = False
        self.q_scaling_fac = 1


        self.pi_by_two_amplitude = 0.5
        self.pi_amplitude = 1.0
        self.oscilloscope_wait_time = ((self.seq_offset_ns +self.pi_by_two_pulse_ns + self.gap_len1_ns
                                       + self.pi_pulse_ns+self.switch_pulse_ns + 1000 + self.shot_repetition_time_ns) * self.shots_number) /1e9

    def to_dict(self):
        return {
            "pi_pulse_duration": self.pi_pulse_ns,
            "pi_by_two_pulse_duration": self.pi_by_two_pulse_ns,
            "sequence_offset": self.seq_offset_ns,
            "gap_len1": self.gap_len1_ns,
            "data_start": self.data_start,
            "data_stop": self.data_stop,
            "trigger_pulse_duration": self.trigger_pulse_ns,
            "switch_pulse_duration": self.switch_pulse_ns,
            "shot_repetition_time": self.shot_repetition_time_ns,
            "number_of_shots": self.shots_number,
            "pi_by_two_amplitude": self.pi_by_two_amplitude,
            "pi_amplitude": self.pi_amplitude,
            "oscilloscope_wait_time": self.oscilloscope_wait_time,
            "i_phase_offset":self.i_phase_offset,
            "q_phase_offset": self.q_phase_offset,
            "i_offset":self.i_offset,
            "q_offset": self.q_offset,
            "pulse_freq":self.pulse_freq,
            "q_scaling_factor":self.q_scaling_fac

        }
