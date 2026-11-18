import numpy as np

from HahnEchoHardware import HahnEchoHardware


class InversionRecoveryExp:

    def __init__(self, parameters,hardware):
        self.parameters = parameters
        self.hardware = hardware

        #Sequence margins
        self.amp_left_margin_ns = 500
        self.amp_right_margin_ns = 50 #100

        self.source_switch_left_margin_ns = 300
        self.source_switch_right_margin_ns = 50 #200

        self.switch_right_margin_ns = 100 #500
        self.foldername = "InversionRecovery"
        self.exp_type=  "inversion_recovery_"


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

    def mw_iq_pulse(self,left_zeros: int,pulse: int,right_zeros: int,frequency_hz: float,axis: str = "+X",iq_phase_offset_deg: float = 0.0,envelope: str = "square",):
        fs = 2.4e9

        envelope = envelope.strip().lower()
        axis=axis.strip().lower()

        # Envelope Definition
        if envelope == "gaussian":
            position = pulse / 2
            width = pulse / 6
            env = f"gauss({pulse}, 1.0,{position}, {width})"

        elif envelope == "square":
            env = f"rect({pulse}, 1.0)"

        else:
            raise ValueError("Pulse envelope must be 'gaussian' or 'square'.")

        # Pulse Definition
        if (frequency_hz == 0 ):  # For DC

            axis_amplitudes = {"+x": (1.0, 0.0),"-x": (-1.0, 0.0),"+y": (0.0, 1.0),"-y": (0.0, -1.0)}

            if axis not in axis_amplitudes:
                raise ValueError(f"Invalid pulse axis '{axis}': Use +X, -X, +Y or -Y.")

            i_amp, q_amp = axis_amplitudes[axis]

            i_pulse = f"({i_amp} * {env})"
            q_pulse = f"({q_amp} * {env})"

        else:  # For AC

            axis_phases = {"+x": 0.0,"-x": 180.0,"+y": 90.0,"-y": -90.0}

            if axis not in axis_phases:
                raise ValueError(f"Invalid pulse axis '{axis}': Use +X, -X, +Y or -Y.")

            # Convert Axis to main phase
            axis_phase_deg = axis_phases[axis]
            periods = pulse * frequency_hz / fs

            # Convert phase
            i_phase_rad = np.deg2rad(axis_phase_deg)
            q_phase_rad = np.deg2rad(axis_phase_deg + 90.0 + iq_phase_offset_deg)

            # Sine Pulses
            i_sine = f"sine({pulse}, 1.0,{i_phase_rad}, {periods})"
            q_sine = f"sine({pulse}, 1.0,{q_phase_rad}, {periods})"

            i_pulse = f"({i_sine} * {env})"
            q_pulse = f"({q_sine} * {env})"

        i_wave = f"join(zeros({left_zeros}),{i_pulse},zeros({right_zeros}));"
        q_wave = f"join(zeros({left_zeros}),{q_pulse},zeros({right_zeros}));"

        return i_wave, q_wave

    def play_zero_repeated(self, samples: int) :
        max_chunk = 500_000_000

        n_chunks = samples // max_chunk
        remainder = samples % max_chunk

        seq = ""

        if n_chunks > 0:
            seq += (
                f"repeat({n_chunks}) {{\n"
                f"    playZero({max_chunk});\n"
                f"}}\n"
            )

        if remainder > 0:
            seq += f"playZero({remainder});\n"

        return seq

    def seq_program_0(self,inversion_pulse_i,inversion_pulse_q,amp_0,pi_by_two_pulse_i,pi_by_two_pulse_q,amp_1,pi_pulse_i,pi_pulse_q,amp_2,detection_pulse,amp_3,trigger,shots,inversion_gap,shot_repetition,pi_by_two_pulse_ct_index):
        seqc_program = f"""\
        // Section 0
        wave mw_sec_i_0 = {inversion_pulse_i}
        wave mw_sec_q_0 = {inversion_pulse_q}
        wave m_amp_0 = {amp_0}
        mw_sec_i_0 = mw_sec_i_0 + m_amp_0;
        mw_sec_q_0 = mw_sec_q_0 + m_amp_0;
        
        // Section 1
        wave mw_sec_i_1 = {pi_by_two_pulse_i}
        wave mw_sec_q_1 = {pi_by_two_pulse_q}
        wave m_amp_1 = {amp_1}
        mw_sec_i_1 = mw_sec_i_1 + m_amp_1;
        mw_sec_q_1 = mw_sec_q_1 + m_amp_1;

        // Section 2
        wave mw_sec_i_2 = {pi_pulse_i}
        wave mw_sec_q_2 = {pi_pulse_q}
        wave m_amp_2 = {amp_2}
        mw_sec_i_2 = mw_sec_i_2 + m_amp_2;
        mw_sec_q_2 = mw_sec_q_2 + m_amp_2;

        // Section 3
        wave mw_sec_3 = {detection_pulse}
        wave m_amp = {amp_3}
        wave osc_trig = {trigger}
        mw_sec_3 = mw_sec_3 + m_amp + osc_trig;

        // Assigning Indices
        assignWaveIndex(mw_sec_i_0,mw_sec_q_0,0);
        assignWaveIndex(mw_sec_i_1,mw_sec_q_1,1);
        assignWaveIndex(mw_sec_i_2,mw_sec_q_2,2);
        assignWaveIndex(mw_sec_3,mw_sec_3,3);

        repeat({shots}){{
            executeTableEntry(0);
            {inversion_gap}
            executeTableEntry({pi_by_two_pulse_ct_index});
            executeTableEntry(2);
            executeTableEntry(3);
            {shot_repetition}
        }}
        """

        return seqc_program

    def seq_program_1(self,mw_sec_0,mw_sec_1,mw_sec_2,mw_sec_3,switch,source_switch_0,source_switch_1,source_switch_2,source_switch_gen_left,shots,inversion_gap,shot_repetition):
        seqc_program = f"""\
        
        wave mw_sec_0 = zeros({mw_sec_0});
        wave mw_sec_1 = zeros({mw_sec_1});
        wave mw_sec_2 = zeros({mw_sec_2});
        wave mw_sec_3 = zeros({mw_sec_3});
        
        wave s_switch_0 = {source_switch_0}
        wave s_switch_1 = {source_switch_1}
        wave s_switch_2 = {source_switch_2}
        wave s_gen = {source_switch_gen_left}
        
        wave m_prot = {switch}
        
        mw_sec_0 = mw_sec_0 + s_switch_0;
        mw_sec_1 = mw_sec_1 + s_switch_1 + s_gen;
        mw_sec_2 = mw_sec_2 + s_switch_2 + s_gen;
        mw_sec_3 = mw_sec_3 + m_prot+ s_gen;
        
        assignWaveIndex(mw_sec_0,mw_sec_0,0);
        assignWaveIndex(mw_sec_1,mw_sec_1,1);
        assignWaveIndex(mw_sec_2,mw_sec_2,2);
        assignWaveIndex(mw_sec_3,mw_sec_3,3);

        repeat({shots}){{
            executeTableEntry(0);
            {inversion_gap}
            executeTableEntry(1);
            executeTableEntry(2);
            executeTableEntry(3);
            {shot_repetition}
        }}
        
        """

        return seqc_program

    def pi_pulse_pos(self, ct, amp, wave_index, TABLE_INDEX):
        ct.table[TABLE_INDEX].waveform.index = wave_index

        ct.table[TABLE_INDEX].amplitude0.value = amp
        ct.table[TABLE_INDEX].amplitude1.value = amp


    def mw_hahn_echo(self, ct):
        self.pi_pulse_pos(ct,self.parameters.inversion_pulse_amplitude,0,0)  # (3,4)
        self.pi_pulse_pos(ct, self.parameters.pi_by_two_amplitude, 1, 1)
        self.pi_pulse_pos(ct, self.parameters.pi_amplitude, 2, 2)
        self.pi_pulse_pos(ct, 0.0, 3, 3)
        self.pi_pulse_pos(ct,-self.parameters.pi_by_two_amplitude, 1, 4)

    def rf_hahn_echo(self, ct):
        self.pi_pulse_pos(ct, 0, 0, 0)
        self.pi_pulse_pos(ct, 0, 1, 1)
        self.pi_pulse_pos(ct, 0, 2, 2)
        self.pi_pulse_pos(ct,0,3,3)

    def run(self,save= True):
        parameters = self.parameters

        # Oscilloscope Wait time
        parameters.oscilloscope_wait_time = ((parameters.seq_offset_ns + parameters.pi_by_two_pulse_ns + parameters.gap_len1_ns +parameters.inversion_pulse_ns +parameters.inversion_recovery_time_ns
                                        + parameters.pi_pulse_ns + parameters.switch_pulse_ns + 1000 + parameters.shot_repetition_time_ns) * parameters.shots_number) / 1e9
        print("Wait time=",parameters.oscilloscope_wait_time)

        # Creation of parameters for file
        exp_parameters = parameters.to_dict()

        #Inversion parameters calculation
        inversion_recovery_time_samples = self.ns_to_samples(parameters.inversion_recovery_time_ns)
        print("Inversion recovery time samples=",inversion_recovery_time_samples)
        inversion_pulse_samples = self.ns_to_samples(parameters.inversion_pulse_ns)


        # Convert into samples
        seq_offset_samples = self.ns_to_samples(parameters.seq_offset_ns)
        pi_by_two_pulse_samples = self.ns_to_samples(parameters.pi_by_two_pulse_ns)
        gap_len1_samples = self.ns_to_samples(parameters.gap_len1_ns)
        pi_pulse_samples = self.ns_to_samples(parameters.pi_pulse_ns)

        trigger_pulse_samples = self.ns_to_samples(parameters.trigger_offset_ns+parameters.gap_len1_ns)

        amp_left_margin_samples = self.ns_to_samples(self.amp_left_margin_ns)
        amp_right_margin_samples = self.ns_to_samples(self.amp_right_margin_ns)
        switch_right_margin_samples = self.ns_to_samples(self.switch_right_margin_ns)
        detection_switch_half_width_samples = self.ns_to_samples(parameters.switch_pulse_ns/2)
        shot_repetition_time_samples = self.ns_to_samples(parameters.shot_repetition_time_ns)

        source_switch_left_margin_samples = self.ns_to_samples(self.source_switch_left_margin_ns)
        source_switch_right_margin_samples = self.ns_to_samples(self.source_switch_right_margin_ns)


        # The amp gate duration that is required during inversion recovery time
        inversion_margin_gates_samples_1 = max(source_switch_right_margin_samples,amp_right_margin_samples)
        inversion_margin_gates_samples_2 = max(source_switch_left_margin_samples,amp_left_margin_samples)

        # Calculations of durations

        #Section 0
        mw_section_0_samples =(seq_offset_samples + inversion_pulse_samples+inversion_margin_gates_samples_1)
        amp_0_left_zeros_samples = (seq_offset_samples - amp_left_margin_samples)
        mw_section_0_right_zeros_samples = inversion_margin_gates_samples_1

        #Section 1
        mw_section_1_samples = (pi_by_two_pulse_samples + inversion_margin_gates_samples_2)
        amp_1_duration_samples = pi_by_two_pulse_samples + amp_left_margin_samples
        mw_section_1_left_zeros_samples = inversion_margin_gates_samples_2

        #Section 2
        mw_section_2_samples = (gap_len1_samples + pi_pulse_samples)

        #Section 3
        mw_section_3_samples = (gap_len1_samples + detection_switch_half_width_samples)
        amp_3_right_zeros_samples = (mw_section_3_samples - amp_right_margin_samples)


        # Source Switch Durations
        # Source switch will be an envelope over the pulse

        source_switch_0_left_zeros_samples = seq_offset_samples - source_switch_left_margin_samples
        source_switch_0_duration_samples = mw_section_0_samples -source_switch_0_left_zeros_samples
        source_switch_1_left_zeros_samples = inversion_margin_gates_samples_2 - source_switch_left_margin_samples
        source_switch_1_duration_samples = source_switch_left_margin_samples + pi_by_two_pulse_samples
        source_switch_2_left_zeros_samples = gap_len1_samples - source_switch_left_margin_samples
        source_switch_2_duration_samples = mw_section_2_samples - source_switch_2_left_zeros_samples
        source_switch_general_left_zeros = source_switch_right_margin_samples

        # Detection Switch Durations
        mw_section_3_samples = (gap_len1_samples + detection_switch_half_width_samples)
        echo_center_samples = gap_len1_samples
        earliest_detection_samples = switch_right_margin_samples
        desired_detection_start = (echo_center_samples - detection_switch_half_width_samples)
        detection_left_zeros_samples = max(earliest_detection_samples,
                                           desired_detection_start)  # Clipping to ensure it doesn't open before the switch margin
        detection_end_samples = (
                    echo_center_samples + detection_switch_half_width_samples)  # Right side always extends with half width
        detection_duration_samples = (
                    detection_end_samples - detection_left_zeros_samples)  # Actual switch-open duration

        # Oscilloscope Trigger Durations
        osc_trig_left_zeros_samples = trigger_pulse_samples - 120
        osc_trig_right_zeros_samples = max(0, (mw_section_3_samples - osc_trig_left_zeros_samples - 240))

        # Strings for sequence
        inversion_pulse_i,inversion_pulse_q = self.mw_iq_pulse(seq_offset_samples,inversion_pulse_samples,mw_section_0_right_zeros_samples,parameters.pulse_freq, "+X", 0,parameters.envelope)
        pi_by_two_pulse_i,pi_by_two_pulse_q = self.mw_iq_pulse(mw_section_1_left_zeros_samples, pi_by_two_pulse_samples, 0,parameters.pulse_freq, "+X", 0,parameters.envelope)
        pi_pulse_i,pi_pulse_q = self.mw_iq_pulse(gap_len1_samples, pi_pulse_samples, 0,parameters.pulse_freq, "+X", 0,parameters.envelope)

        amp_0 =self.marker_pulse(amp_0_left_zeros_samples,(amp_left_margin_samples+inversion_pulse_samples+amp_right_margin_samples),mw_section_0_right_zeros_samples-amp_right_margin_samples,2)
        amp_1 = self.marker_pulse(inversion_margin_gates_samples_2-amp_left_margin_samples,amp_1_duration_samples,0,2)
        amp_2 = self.marker_pulse(0,mw_section_2_samples,0,2)
        detection_pulse = self.blank_pulse(mw_section_3_samples)
        amp_3 = self.marker_pulse(0,amp_right_margin_samples,amp_3_right_zeros_samples,2)
        switch = self.marker_pulse(detection_left_zeros_samples, detection_duration_samples, 0, 1)
        osc_trig = self.marker_pulse(osc_trig_left_zeros_samples, 240, osc_trig_right_zeros_samples, 1)
        inversion_gap = self.play_zero_repeated(inversion_recovery_time_samples-inversion_margin_gates_samples_1-inversion_margin_gates_samples_2)
        shot_repetition = self.play_zero_repeated(shot_repetition_time_samples)

        # Strings for source switch
        source_switch_0 = self.marker_pulse(source_switch_0_left_zeros_samples, source_switch_0_duration_samples, 0, 2)
        source_switch_1 = self.marker_pulse(source_switch_1_left_zeros_samples, source_switch_1_duration_samples, 0, 2)
        source_switch_2 = self.marker_pulse(source_switch_2_left_zeros_samples, source_switch_2_duration_samples, 0, 2)
        source_gen_left = self.marker_pulse(0, source_switch_general_left_zeros, 0, 2)


        # Validation of Durations
        if(inversion_recovery_time_samples-inversion_margin_gates_samples_1-inversion_margin_gates_samples_2<0):
            raise ValueError(f"Minimum recovery time samples should be {round((inversion_margin_gates_samples_1+inversion_margin_gates_samples_2)/2.4,3)+1}")


        if parameters.switch_pulse_ns < 200:
            raise ValueError(f"Switch Pulse should be atleast 200 ns")

        if detection_end_samples < earliest_detection_samples:
            raise ValueError(f"Detection opens before the right margin. Increase Tau or gap_len1_ns ")

        if osc_trig_left_zeros_samples + 240 > mw_section_3_samples:
            raise ValueError(
                f"Trigger offset {parameters.trigger_offset_ns} ns places trigger beyond detection section.")

        if(amp_0_left_zeros_samples<=0):
            raise ValueError("Increase Sequence Offset by minimum of: ",(-parameters.seq_offset_ns+self.amp_left_margin_ns+1)," ns")

        if (source_switch_0_left_zeros_samples < 0):
            raise ValueError(
                f"Sequence Offset : {parameters.seq_offset_ns} ns must be at least equal to the source-switch left margin :{self.source_switch_left_margin_ns} ns ")

        # Build programs

        seq_prog_pos = self.seq_program_0(
            inversion_pulse_i,inversion_pulse_q,
            amp_0,
            pi_by_two_pulse_i,pi_by_two_pulse_q,
            amp_1,
            pi_pulse_i,pi_pulse_q,
            amp_2,
            detection_pulse,
            amp_3,
            osc_trig,
            parameters.shots_number,inversion_gap,
            shot_repetition,1
        )
        seq_prog_neg = self.seq_program_0(
            inversion_pulse_i,inversion_pulse_q,
            amp_0,
            pi_by_two_pulse_i,pi_by_two_pulse_q,
            amp_1,
            pi_pulse_i,pi_pulse_q,
            amp_2,
            detection_pulse,
            amp_3,
            osc_trig,
            parameters.shots_number,inversion_gap,
            shot_repetition,4
        )

        seq_prog_1 = self.seq_program_1(mw_section_0_samples,
            mw_section_1_samples,
            mw_section_2_samples,
            mw_section_3_samples,
            switch,
            source_switch_0,
            source_switch_1,
            source_switch_2,
            source_gen_left,
            parameters.shots_number,inversion_gap,
            shot_repetition
        )

        result = self.hardware.run(parameters,seq_prog_pos,seq_prog_neg,seq_prog_1,self.mw_hahn_echo,self.rf_hahn_echo)

        if save:
            save_directory = parameters.save_directory
            file_name = f"{parameters.filename}_{self.exp_type}"

            saved_path = self.hardware.Osc.save_data_to_matlab(
                exp_data=result,
                exp_parameters=exp_parameters,
                save_directory=save_directory,
                file_name=file_name
            )

            result["saved_path"] = saved_path

        return result

        #self.save_data_to_file()