class HahnEchoParameters():
    def __init__(self):

        #self.save_directory = fr"D:\Data\NewCodeData\Spin Echo" # for QMUL
        self.save_directory = fr"Y:\DAQ\CondensedMatterGroups\Rest-Of-CM-DAQ-Groups\ArdavanGroup\Measurements\New_Code\Spin_echo"    #"H:\Data\NewCodeData\Spin Echo"

        self.envelope="Gaussian"
        self.seq_offset_ns = 200
        self.pi_by_two_pulse_ns = 50
        self.gap_len1_ns = 800
        self.pi_pulse_ns = 50
        self.data_start = 1
        self.data_stop = 5000
        self.trigger_offset_ns = 500
        self.switch_pulse_ns = 1000
        self.filename= "test_"
        self.mw_freq = 9.7 #GHz
        self.B0_field = 3400 #Gauss
        self.shot_repetition_time_ns = 1e6
        self.shots_number = 32
        self.pulse_freq = 0

        self.pi_by_two_amplitude = 0.5
        self.pi_amplitude = 1.0
        self.oscilloscope_wait_time = ((self.seq_offset_ns +self.pi_by_two_pulse_ns + self.gap_len1_ns
                                       + self.pi_pulse_ns+self.switch_pulse_ns + 1000 + self.shot_repetition_time_ns) * self.shots_number) /1e9

    def to_dict(self):
        return {
            "mw_source_freq": self.mw_freq,
            "B0_field": self.B0_field,
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
            "oscilloscope_wait_time": self.oscilloscope_wait_time
                    }
