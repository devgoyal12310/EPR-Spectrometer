import numpy as np




class HahnEchoExp:

    def __init__(self, parameters,hardware,save_directory = None):
        self.parameters = parameters
        self.hardware = hardware

        #Sequence margins
        self.amp_left_margin_ns = 200
        self.amp_right_margin_ns = 100
        self.switch_right_margin_ns = 500
        self.foldername = "Pulse Optimization"
        self.exp_type = "pulse_optimization_"
        self.save_directory = save_directory

    def ns_to_samples(self, ns: float, fs_hz: float = 2.4e9, multiple: int = 16) -> int:
        raw = int(round(ns * 1e-9 * fs_hz))

        if raw <= 0:
            raw = 1

        return int(np.ceil(raw / multiple) * multiple)

    def mw_pulse(self, left_zeros: int, pulse: int, right_zeros: int):
        return f"join(zeros({left_zeros}),rect({pulse},1.0),zeros({right_zeros}));"

    def marker_pulse(self, left_zeros: int, pulse: int, right_zeros: int, id: int):
        return f"join(marker({left_zeros},0),marker({pulse},{id}),marker({right_zeros},0));"

    def blank_pulse(self, pulse: int):
        return f"zeros({pulse});"

    def seq_program_0(self,pi_by_two_pulse,amp_1,pi_pulse,amp_2,detection_pulse,amp_3,trigger,shots,repetition_time,pi_by_two_pulse_ct_index):
        seqc_program = f"""\
        // Section 1
        wave mw_sec_1 = {pi_by_two_pulse}
        wave m_amp_1 = {amp_1}
        mw_sec_1 = mw_sec_1 + m_amp_1;

        // Section 2
        wave mw_sec_2 = {pi_pulse}
        wave m_amp_2 = {amp_2}
        mw_sec_2 = mw_sec_2 + m_amp_2;

        // Section 3
        wave mw_sec_3 = {detection_pulse}
        wave m_amp = {amp_3}
        wave osc_trig = {trigger}
        mw_sec_3 = mw_sec_3 + m_amp + osc_trig;

        // Assigning Indices
        assignWaveIndex(mw_sec_1,mw_sec_1,0);
        assignWaveIndex(mw_sec_2,mw_sec_2,1);
        assignWaveIndex(mw_sec_3,mw_sec_3,2);

        repeat({shots}){{
            resetOscPhase();
            executeTableEntry({pi_by_two_pulse_ct_index});
            resetOscPhase();
            executeTableEntry(1);
            executeTableEntry(2);
            playZero({repetition_time});
        }}
        """

        return seqc_program

    def seq_program_1(self,mw_sec_1,mw_sec_2,mw_sec_3,switch,shots,repetition_time):
        seqc_program = f"""\

        wave mw_sec_1 = zeros({mw_sec_1});
        wave mw_sec_2 = zeros({mw_sec_2});
        wave mw_sec_3 = zeros({mw_sec_3});
        wave m_prot = {switch}

        mw_sec_3 = mw_sec_3 + m_prot;

        assignWaveIndex(mw_sec_1,mw_sec_1,0);
        assignWaveIndex(mw_sec_2,mw_sec_2,1);
        assignWaveIndex(mw_sec_3,mw_sec_3,2);

        repeat({shots}){{
            resetOscPhase();
            executeTableEntry(0);
            resetOscPhase();
            executeTableEntry(1);
            executeTableEntry(2);
            playZero({repetition_time});
        }}
        
        """

        return seqc_program

    def pi_pulse_pos(self, ct, amp, phase1, phase2, wave_index, TABLE_INDEX):
        ct.table[TABLE_INDEX].waveform.index = wave_index

        ct.table[TABLE_INDEX].amplitude0.value = amp
        ct.table[TABLE_INDEX].amplitude1.value = amp*self.parameters.q_scaling_fac

        ct.table[TABLE_INDEX].phase0.value = phase1
        ct.table[TABLE_INDEX].phase0.increment = False

        ct.table[TABLE_INDEX].phase1.value = phase2
        ct.table[TABLE_INDEX].phase1.increment = False

    def mw_hahn_echo(self, ct):
        self.pi_pulse_pos(ct, self.parameters.pi_by_two_amplitude, (0+self.parameters.i_phase_offset), (90+self.parameters.q_phase_offset), 0, 0)
        self.pi_pulse_pos(ct, self.parameters.pi_amplitude, (0+self.parameters.i_phase_offset), (90+self.parameters.q_phase_offset), 1, 1)
        self.pi_pulse_pos(ct, 0.0, 0, 0, 2, 2)
        self.pi_pulse_pos(ct,-self.parameters.pi_by_two_amplitude, (0+self.parameters.i_phase_offset), (90+self.parameters.q_phase_offset), 0, 3)

    def rf_hahn_echo(self, ct):
        self.pi_pulse_pos(ct, 0, 0, 90, 0, 0)
        self.pi_pulse_pos(ct, 0, 0, 90, 1, 1)
        self.pi_pulse_pos(ct, 0, 0, 0, 2, 2)

    def run(self,save=False):
        parameters = self.parameters


        # Oscilloscope Wait time
        parameters.oscilloscope_wait_time = ((parameters.seq_offset_ns + parameters.pi_by_two_pulse_ns + parameters.gap_len1_ns
                                        + parameters.pi_pulse_ns + parameters.switch_pulse_ns + 1000 + parameters.shot_repetition_time_ns) * parameters.shots_number) / 1e9
        print("Wait time=",parameters.oscilloscope_wait_time)


        # Creation of parameters for file
        exp_parameters = parameters.to_dict()

        # Convert into samples
        seq_offset_samples = self.ns_to_samples(parameters.seq_offset_ns)
        pi_by_two_pulse_samples = self.ns_to_samples(parameters.pi_by_two_pulse_ns)
        gap_len1_samples = self.ns_to_samples(parameters.gap_len1_ns)
        pi_pulse_samples = self.ns_to_samples(parameters.pi_pulse_ns)
        trigger_pulse_samples = self.ns_to_samples(parameters.trigger_pulse_ns)
        amp_left_margin_samples = self.ns_to_samples(self.amp_left_margin_ns)
        amp_right_margin_samples = self.ns_to_samples(self.amp_right_margin_ns)
        switch_right_margin_samples = self.ns_to_samples(self.switch_right_margin_ns)
        switch_pulse_samples = self.ns_to_samples(parameters.switch_pulse_ns)
        shot_repetition_time_cycle = self.ns_to_samples(parameters.shot_repetition_time_ns)


        # Calculations of durations
        mw_section_1_samples = (seq_offset_samples + pi_by_two_pulse_samples)
        amp_1_left_zeros_samples = (seq_offset_samples-amp_left_margin_samples)
        mw_section_2_samples = (gap_len1_samples + pi_pulse_samples)
        mw_section_3_samples = (switch_right_margin_samples + switch_pulse_samples)
        amp_3_right_zeros_samples = (mw_section_3_samples - amp_right_margin_samples)

        osc_trig_right_zeros_samples = max(0,(mw_section_3_samples - trigger_pulse_samples - 480))

        # Strings for sequence
        pi_by_two_pulse = self.mw_pulse(seq_offset_samples,pi_by_two_pulse_samples,0)
        amp_1 = self.marker_pulse(amp_1_left_zeros_samples,amp_left_margin_samples+pi_by_two_pulse_samples,0,2)
        pi_pulse = self.mw_pulse(gap_len1_samples,pi_pulse_samples,0)
        amp_2 = self.marker_pulse(0,mw_section_2_samples,0,2)
        detection_pulse = self.blank_pulse(mw_section_3_samples)
        amp_3 = self.marker_pulse(0,amp_right_margin_samples,amp_3_right_zeros_samples,2)
        switch = self.marker_pulse(switch_right_margin_samples,switch_pulse_samples,0,1)
        osc_trig = self.marker_pulse(trigger_pulse_samples,240,osc_trig_right_zeros_samples,1)

        # Validation of Durations
        trigger_min =(self.switch_right_margin_ns+parameters.switch_pulse_ns) - parameters.trigger_pulse_ns - 100
        if(trigger_min <= 0 ):
            raise ValueError(" Oscilloscope Trigger is outside range of detection: Increase Detection Pulse Width by atlease ",(- trigger_min+1), " ns.")


        if(amp_1_left_zeros_samples<=0):
            raise ValueError("Increase Sequence Offset by minimum of: ",(-parameters.seq_offset_ns+self.amp_left_margin_ns+1)," ns")

        if(self.parameters.pi_amplitude>1.0 or self.parameters.pi_by_two_amplitude>1.0):
            raise ValueError("Pulse Amplitudes are larger than 1.0!")

        if((self.parameters.pi_amplitude*self.parameters.q_scaling_fac)>1.0 or (self.parameters.pi_by_two_amplitude*self.parameters.q_scaling_fac)>1.0):
            raise ValueError("Amplitude Ratio / Scaling Factor too high!")

        # Build programs

        seq_prog_pos = self.seq_program_0(
            pi_by_two_pulse,
            amp_1,
            pi_pulse,
            amp_2,
            detection_pulse,
            amp_3,
            osc_trig,
            parameters.shots_number,
            shot_repetition_time_cycle,0
        )
        seq_prog_neg = self.seq_program_0(
            pi_by_two_pulse,
            amp_1,
            pi_pulse,
            amp_2,
            detection_pulse,
            amp_3,
            osc_trig,
            parameters.shots_number,
            shot_repetition_time_cycle,3
        )

        seq_prog_1 = self.seq_program_1(
            mw_section_1_samples,
            mw_section_2_samples,
            mw_section_3_samples,
            switch,
            parameters.shots_number,
            shot_repetition_time_cycle
        )

        result = self.hardware.run(parameters,seq_prog_pos,seq_prog_neg,seq_prog_1,self.mw_hahn_echo,self.rf_hahn_echo,False)

        if save:

            if self.save_directory is None:
                save_directory = fr"Y:\DAQ\CondensedMatterGroups\Rest-Of-CM-DAQ-Groups\ArdavanGroup\Measurements\New_Code\{self.foldername}"
            else:
                save_directory = self.save_directory



            #save_directory = fr"H:\Data\NewCodeData\{self.foldername}"

            file_name = f"{parameters.filename}_{self.exp_type}"

            saved_path = self.hardware.Osc.save_data_to_matlab(
                positive_channel_data=result["positive_channel_data"],
                negative_channel_data=result["negative_channel_data"],
                oscilloscope_time_step=result["oscilloscope_time_step"],
                exp_parameters=exp_parameters,
                save_directory=save_directory,
                file_name=file_name
            )

            result["saved_path"] = saved_path

        return result

        #self.save_data_to_file()