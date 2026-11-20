import numpy as np

class CPMGExp:

    def __init__(self, parameters,hardware,save_directory = None):
        self.parameters = parameters
        self.hardware= hardware

        #Sequence margins
        self.amp_left_margin_ns = 500 # Before start of pi/2 pulse
        self.amp_right_margin_ns = 100  # After end of last pi pulse

        self.source_switch_left_margin_ns = 50 #Ignore not implemented yet
        self.source_switch_right_margin_ns = 50 #Ignore not implemented yet

        self.switch_right_margin_ns = 500 # Detection Pulse Gate Opening after end of last pi pulse

        self.cpmg_det_left_margin_ns = 100 # After end of last pi pulse
        self.cpmg_det_right_margin_ns = 100 # Before start of next pi pulse

        self.save_directory = save_directory
        self.foldername = "CPMG"
        self.exp_type=  "cpmg_"



    def validate_double_peak(self,displacement_samples,seq_offset_samples,gap_len1_samples,cpmg_gap_len_samples,source_switch_left_margin_samples,source_switch_right_margin_samples,cpmg_detection_pulse_samples,) :
        d = displacement_samples

        if d<0:
            raise ValueError("Double Peak Gap cannot be negative.")
        if d> seq_offset_samples:
            raise ValueError("Double Peak Gap is greater than Sequence Offset. Increase Sequence Offset.")
        if d>gap_len1_samples:
            raise ValueError("Double Peak Gap is greater than Tau. Increase Gap_len1 ")
        if d>cpmg_gap_len_samples:
            raise ValueError("Double Peak Gap is greater than CPMG Gap. Increase CPMG_Gap_len ")
        if d > seq_offset_samples - source_switch_left_margin_samples:
            raise ValueError("Source-switch gate starts before Section 1. Increase seq_offset_ns or reduce Double Peak Gap.")
        if d>gap_len1_samples-source_switch_left_margin_samples:
            raise ValueError("Source-switch gate starts before Section 2. Increase gap_len1_ns or reduce Double Peak Gap.")

        # 6. Inverted CPMG gate LOW region must remain valid
        cpmg_low = (cpmg_gap_len_samples- source_switch_left_margin_samples - source_switch_right_margin_samples)

        if d > cpmg_low:
            raise ValueError("Double Peak Gap exceeds the CPMG source-switch LOW interval. Increase cpmg_gap_len_ns or reduce Double Peak Gap.")

        # 7. CPMG detection AND must retain an open window
        if self.parameters.cpmg_detection_bool:
            if d >= cpmg_detection_pulse_samples:
                raise ValueError(
                    "Double Peak displacement eliminates the CPMG detection window. Increase cpmg_gap_len_ns or reduce displacement or turn off cpmg_detection_bool.")



    def ns_to_samples(self, ns: float, fs_hz: float = 2.4e9, multiple: int = 16) -> int:
        raw = int(round(ns * 1e-9 * fs_hz))

        if raw <= 0:
            raw = 1

        return int(np.ceil(raw / multiple) * multiple)

    def mw_pulse(self, left_zeros: int, pulse: int, right_zeros: int):
        return f"join(zeros({left_zeros}),rect({pulse},1.0),zeros({right_zeros}));"

    def rf_pulse(self,samples,amplitude,phase,periods):
        return f"sine({samples},{amplitude},{phase},{periods});"

    def marker_pulse(self, left_zeros: int, pulse: int, right_zeros: int, id: int):
        return f"join(marker({left_zeros},0),marker({pulse},{id}),marker({right_zeros},0));"

    def double_marker_pulse(self,left_zeros,pulse,right_zeros,displacement_samples,marker_id,source_switch_general_left_zeros=0.0):
        if not 0 <= displacement_samples <= left_zeros:
            raise ValueError("Invalid marker displacement")

        # Union of the two overlapping HIGH windows
        return self.marker_pulse(
            left_zeros - displacement_samples,
            pulse + displacement_samples,
            right_zeros,
            marker_id,
        )


    def rep_marker_pulse(self,left_zeros: int, pulse: int, right_zeros: int, id: int,repeat:int,rf_left_zeros:int,rf_right_zeros:int):
        con_s = f"marker({rf_left_zeros},0),"

        for i in range(repeat):
            con_s= con_s+ f"marker({left_zeros},0),marker({pulse},{id}),"

            if i == (repeat-1):
                con_s = con_s + f"marker({right_zeros-rf_right_zeros},0),"
            else:
                con_s = con_s + f"marker({right_zeros},0),"


        con_s = con_s +f"marker({0},0)"
        return f"join({con_s});"

    def double_rep_marker_pulse_and(self,left_zeros,pulse,right_zeros,marker_id,repeat,displacement_samples,):
        if displacement_samples < 0:
            raise ValueError("Displacement must be non-negative")

        if displacement_samples >= pulse:
            # No overlap between detection windows
            total_samples = repeat * (
                    left_zeros + pulse + right_zeros
            )

            return f"marker({total_samples},0);"

        return self.rep_marker_pulse(
            left_zeros=left_zeros,
            pulse=pulse - displacement_samples,
            right_zeros=right_zeros + displacement_samples,
            id=marker_id,
            repeat=repeat,
            rf_left_zeros=0,
            rf_right_zeros=0,
        )

    def rep_marker_pulse_inv(self,left_zeros: int, pulse: int, right_zeros: int, id: int,repeat:int,rf_left_zeros:int,rf_right_zeros:int):
        con_s = f"marker({rf_left_zeros},{id}),"

        for i in range(repeat):
            con_s= con_s+ f"marker({left_zeros},{id}),marker({pulse},0),"

            if i == (repeat-1):
                con_s = con_s + f"marker({right_zeros-rf_right_zeros},{id}),"
            else:
                con_s = con_s + f"marker({right_zeros},{id}),"


        con_s = con_s +f"marker({0},{id})"
        return f"join({con_s});"

    def double_rep_marker_pulse_inv(self,left_zeros: int, pulse: int, right_zeros: int, id: int,repeat:int,rf_left_zeros:int,rf_right_zeros:int,displacement_samples=0):

        marker_1 = self.rep_marker_pulse_inv(left_zeros, pulse-displacement_samples,
                                                    right_zeros+displacement_samples, id, repeat, rf_left_zeros, rf_right_zeros)
        marker_2 = self.rep_marker_pulse_inv(left_zeros , pulse,
                                             right_zeros, id, repeat, rf_left_zeros,
                                             rf_right_zeros)

        return (
            f"({marker_1.rstrip(';')} + "
            f"{marker_2.rstrip(';')});"
        )

    def blank_pulse(self, pulse: int):
        return f"zeros({pulse});"

    def generate_cpmg_string(self, pattern_length, cpmg_count):

        repeats = cpmg_count // pattern_length  # Number of repetitions - removes the decimal
        pattern = ""

        for i in range(pattern_length):
            table_index= 5+i
            pattern+=f"executeTableEntry({table_index});\n"

        return f"""
        repeat({repeats}) {{
            {pattern}
        }}
        """

    def mw_iq_pulse(self,left_zeros: int,pulse: int,right_zeros: int,frequency_hz: float,axis: str = "+X",iq_phase_offset_deg: float = 0.0,envelope: str = "square",phase_offset=0.0,amplitude=1.0):
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

            i_amp, q_amp = axis_amplitudes[axis]   # Needs to be generalized to i = cos (phase) and q = sin (phase)

            i_pulse = f"({i_amp} * {env}*{amplitude})"
            q_pulse = f"({q_amp} * {env}*{amplitude})"

        else:  # For AC

            axis_phases = {"+x": 0.0,"-x": 180.0,"+y": 90.0,"-y": -90.0}

            if axis not in axis_phases:
                raise ValueError(f"Invalid pulse axis '{axis}': Use +X, -X, +Y or -Y.")

            # Convert Axis to main phase
            axis_phase_deg = axis_phases[axis] + phase_offset
            periods = pulse * frequency_hz / fs

            # Convert phase
            i_phase_rad = np.deg2rad(axis_phase_deg)
            q_phase_rad = np.deg2rad(axis_phase_deg + 90.0 + iq_phase_offset_deg)

            # Sine Pulses
            i_sine = f"sine({pulse}, {amplitude},{i_phase_rad}, {periods})"
            q_sine = f"sine({pulse}, {amplitude},{q_phase_rad}, {periods})"

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

    def generate_cpmg_waveforms(self,left_zeros,pulse_samples,right_zeros):
        configs = self.get_cpmg_config()

        waveforms = []

        for axis, amplitude, phase in configs:
            i_wave, q_wave = self.mw_iq_pulse(
                left_zeros=left_zeros,
                pulse=pulse_samples,
                right_zeros=right_zeros,
                frequency_hz=self.parameters.pulse_freq,
                axis=axis,
                iq_phase_offset_deg=4.25,
                envelope=self.parameters.envelope,
                phase_offset=phase
            )

            waveforms.append({
                "i": i_wave,
                "q": q_wave,
                "amplitude": amplitude
            })

        return waveforms

    def get_cpmg_config(self,index):

        if index == 1:
            axes = self.parameters.cpmg_pulse_axes_1
            amplitudes = self.parameters.cpmg_pulse_amplitudes_1
            phases = self.parameters.cpmg_pulse_phase_offsets_1
        if index == 2:
            axes = self.parameters.cpmg_pulse_axes_2
            amplitudes = self.parameters.cpmg_pulse_amplitudes_2
            phases = self.parameters.cpmg_pulse_phase_offsets_2

        if phases is None:
            phases = [0.0] * len(axes)

        if not (
                len(axes) == len(amplitudes) == len(phases)
        ):
            raise ValueError(
                "CPMG axes, amplitudes and phase offsets "
                "must have equal lengths."
            )

        if not axes:
            raise ValueError("CPMG pattern cannot be empty")

        if self.parameters.cpmg_count % len(axes) != 0:
            raise ValueError(
                "CPMG count must be divisible by pattern length"
            )

        if any(a < 0 or a > 1 for a in amplitudes):
            raise ValueError("CPMG amplitudes must be between 0 and 1")

        return list(zip(axes, amplitudes, phases))

    def generate_cpmg_wave_definitions(self, waveforms, amp_3):

        definitions = []

        for i, wave in enumerate(waveforms):
            wave_index = 2 + i

            definitions.append(f"""
            wave cpmg_i_{i} = {wave["i"]}
            wave cpmg_q_{i} = {wave["q"]}

            wave cpmg_amp_{i} = {amp_3}

            cpmg_i_{i} = cpmg_i_{i} + cpmg_amp_{i};
            cpmg_q_{i} = cpmg_q_{i} + cpmg_amp_{i};

            assignWaveIndex(
                cpmg_i_{i},
                cpmg_q_{i},
                {wave_index}
            );
            """)

        return "\n".join(definitions)

    def generate_double_cpmg_waveforms(
            self,
            left_zeros,
            pulse_samples,
            right_zeros,
            displacement_samples,
    ):
        configs_1 = self.get_cpmg_config(1)
        configs_2 = self.get_cpmg_config(2)

        if len(configs_1) != len(configs_2):
            raise ValueError(
                "Both CPMG patterns must have equal lengths"
            )

        if not 0 <= displacement_samples <= left_zeros:
            raise ValueError(
                "Double Peak displacement exceeds available left zeros"
            )

        waveforms = []

        for (axis_1, amp_1, phase_1), (axis_2, amp_2, phase_2) in zip(configs_1, configs_2):
            # Generate the first pulse
            i1, q1 = self.mw_iq_pulse(
                left_zeros=left_zeros - displacement_samples,
                pulse=pulse_samples,
                right_zeros=right_zeros+ displacement_samples,
                frequency_hz=self.parameters.pulse_freq_1,
                axis=axis_1,
                iq_phase_offset_deg=4.25,
                envelope=self.parameters.envelope,
                phase_offset=phase_1,
                amplitude=amp_1,
            )

            # Generate the second pulse, shifted left
            i2, q2 = self.mw_iq_pulse(
                left_zeros=left_zeros,
                pulse=pulse_samples,
                right_zeros=right_zeros ,
                frequency_hz=self.parameters.pulse_freq_2,
                axis=axis_2,
                iq_phase_offset_deg=4.25,
                envelope=self.parameters.envelope,
                phase_offset=phase_2,
                amplitude=amp_2,
            )

            waveforms.append({
                "i": f"({i1.rstrip(';')} + {i2.rstrip(';')});",
                "q": f"({q1.rstrip(';')} + {q2.rstrip(';')});",
            })

        return waveforms

    def mw_double_iq_pulse(
            self,
            left_zeros,
            pulse,
            right_zeros,
            frequency_hz_1,frequency_hz_2,
            axis="+X",
            iq_phase_offset_deg=0.0,
            envelope="square",
            phase_offset=0.0,
            displacement_samples=0.0,amplitude1=1.0,amplitude2=1.0
    ):
        if displacement_samples < 0:
            raise ValueError("Displacement must be non-negative")

        if displacement_samples > left_zeros:
            raise ValueError(
                "Displacement exceeds available left zeros"
            )

        # First pulse: original position
        i1, q1 = self.mw_iq_pulse(
            left_zeros- displacement_samples,
            pulse,
            right_zeros+ displacement_samples,
            frequency_hz_1,
            axis,
            iq_phase_offset_deg,
            envelope,
            phase_offset,amplitude1
        )

        # Second pulse: shifted LEFT
        i2, q2 = self.mw_iq_pulse(
            left_zeros,
            pulse,
            right_zeros,
            frequency_hz_2,
            axis,
            iq_phase_offset_deg,
            envelope,
            phase_offset,amplitude2
        )

        # Combine both I/Q waveforms
        combined_i = (
            f"({i1.rstrip(';')} + {i2.rstrip(';')});"
        )
        combined_q = (
            f"({q1.rstrip(';')} + {q2.rstrip(';')});"
        )

        return combined_i, combined_q

    def seq_program_0(self,cpmg_definitions,pi_by_two_pulse_i,pi_by_two_pulse_q,amp_1,pi_pulse_i,pi_pulse_q,amp_2,detection_pulse,amp_4,amp_gen,trigger,shots,shot_repetition,pi_by_two_pulse_ct_index,cpmg_count_string,detection_wave_index):
        seqc_program = f"""       
        // Section 1
        wave mw_sec_i_1 = {pi_by_two_pulse_i}
        wave mw_sec_q_1 = {pi_by_two_pulse_q}
        wave m_amp_1 = {amp_1}
        mw_sec_i_1 = mw_sec_i_1 + m_amp_1;
        mw_sec_q_1 = mw_sec_q_1 + m_amp_1;
        
        // Amp Gen
        wave m_amp_gen = {amp_gen}
        
        // Section 2
        wave mw_sec_i_2 = {pi_pulse_i}
        wave mw_sec_q_2 = {pi_pulse_q}
        wave m_amp_2 = {amp_2}
        mw_sec_i_2 = mw_sec_i_2 + m_amp_2 + m_amp_gen;
        mw_sec_q_2 = mw_sec_q_2 + m_amp_2 + m_amp_gen;
        
        //Section 3
        {cpmg_definitions}
        
        // Section 3
        wave mw_sec_4 = {detection_pulse}
        wave m_amp = {amp_4}
        wave osc_trig = {trigger}
        mw_sec_4 = mw_sec_4 + m_amp + osc_trig;
        
    
        // Assigning Indices
        assignWaveIndex(mw_sec_i_1,mw_sec_q_1,0);
        assignWaveIndex(mw_sec_i_2,mw_sec_q_2,1);
        assignWaveIndex(mw_sec_4,mw_sec_4,{detection_wave_index});

        repeat({shots}){{
            executeTableEntry({pi_by_two_pulse_ct_index});
            executeTableEntry(1);
            {cpmg_count_string}
            executeTableEntry(3);
            {shot_repetition}
        }}
        """

        return seqc_program

    def seq_program_1(self, mw_sec_1, mw_sec_2, mw_sec_3, mw_sec_4, switch_3, switch, source_switch_1, source_switch_2,
                      source_switch_3, source_switch_gen_left, shots, shot_repetition, cpmg_count_string, rf_seq):
        seqc_program = f"""

        wave mw_sec_1 = zeros({mw_sec_1});
        wave mw_sec_2 = zeros({mw_sec_2});
        wave mw_sec_3 = {rf_seq}
        wave mw_sec_4 = zeros({mw_sec_4});

        wave s_switch_1 = {source_switch_1}
        wave s_switch_2 = {source_switch_2}
        wave s_switch_3 = {source_switch_3}
        wave s_gen = {source_switch_gen_left}

        wave m_prot3 = {switch_3}
        wave m_prot = {switch}

        mw_sec_1 = mw_sec_1 + s_switch_1;
        mw_sec_2 = mw_sec_2 + s_switch_2 + s_gen;

        mw_sec_3 = mw_sec_3 + m_prot3 + s_switch_3;

        mw_sec_4 = mw_sec_4 + m_prot+ s_gen;

        assignWaveIndex(mw_sec_1,mw_sec_1,0);
        assignWaveIndex(mw_sec_2,mw_sec_2,1);
        assignWaveIndex(mw_sec_3,mw_sec_3,2);
        assignWaveIndex(mw_sec_4,mw_sec_4,3);

        repeat({shots}){{
            executeTableEntry(0);
            executeTableEntry(1);
            executeTableEntry(2);
            executeTableEntry(3);
            {shot_repetition}
        }}

        """

        return seqc_program

    def pi_pulse_pos(self, ct, amp, wave_index, TABLE_INDEX):
        #q_scaling_factor = 1.014
        q_scaling_factor = 1.0
        ct.table[TABLE_INDEX].waveform.index = wave_index

        ct.table[TABLE_INDEX].amplitude0.value = amp
        ct.table[TABLE_INDEX].amplitude1.value = amp*q_scaling_factor



    def mw_hahn_echo(self, ct):
        configs = self.get_cpmg_config(1)
        detection_wave_index = 2 + len(configs)

        self.pi_pulse_pos(ct, 1.0, 0, 0)
        self.pi_pulse_pos(ct, 1.0, 1, 1)
        self.pi_pulse_pos(ct, 0.0, detection_wave_index, 3)
        self.pi_pulse_pos(ct,-1.0, 0, 4)  # Negative Phase Cycle

        for i in range(len(self.parameters.cpmg_pulse_amplitudes_1)):
            wave_index = 2 + i
            table_index = 5+ i

            self.pi_pulse_pos(ct, 1.0, wave_index, table_index)


    def rf_hahn_echo(self, ct):
        self.pi_pulse_pos(ct, 1.0, 0, 0)
        self.pi_pulse_pos(ct, 1.0, 1, 1)
        self.pi_pulse_pos(ct, 1.0, 2, 2)
        self.pi_pulse_pos(ct,0,3,3)
        self.pi_pulse_pos(ct,1.0,0,4)


    def run(self,save=True):
        parameters = self.parameters

        parameters.cpmg_count= int(parameters.cpmg_count)

        eff_detection = parameters.cpmg_gap_len_ns - (self.cpmg_det_left_margin_ns+ self.cpmg_det_right_margin_ns)

        parameters.oscilloscope_wait_time = (((parameters.seq_offset_ns + parameters.pi_by_two_pulse_ns + parameters.gap_len1_ns +parameters.pi_pulse_ns) + (parameters.cpmg_pulse_ns+parameters.cpmg_gap_len_ns) *parameters.cpmg_count
                                        + parameters.pi_pulse_ns + parameters.switch_pulse_ns + 1000 + parameters.shot_repetition_time_ns) * parameters.shots_number) / 1e9
        print("Wait time=",parameters.oscilloscope_wait_time)


        # Creation of parameters for file
        exp_parameters = parameters.to_dict()

        #CPMG parameters calculation

        cpmg_pulse_samples = self.ns_to_samples(parameters.cpmg_pulse_ns)
        cpmg_gap_len_samples = self.ns_to_samples(parameters.cpmg_gap_len_ns)

        # Convert into samples
        seq_offset_samples = self.ns_to_samples(parameters.seq_offset_ns)
        pi_by_two_pulse_samples = self.ns_to_samples(parameters.pi_by_two_pulse_ns)
        gap_len1_samples = self.ns_to_samples(parameters.gap_len1_ns)
        pi_pulse_samples = self.ns_to_samples(parameters.pi_pulse_ns)
        trigger_pulse_samples = self.ns_to_samples(parameters.trigger_offset_ns+parameters.gap_len1_ns)
        amp_left_margin_samples = self.ns_to_samples(self.amp_left_margin_ns)
        amp_right_margin_samples = self.ns_to_samples(self.amp_right_margin_ns)
        switch_right_margin_samples = self.ns_to_samples(self.switch_right_margin_ns)
        detection_switch_half_width_samples = self.ns_to_samples(parameters.switch_pulse_ns / 2)
        shot_repetition_time_samples = self.ns_to_samples(parameters.shot_repetition_time_ns)
        source_switch_left_margin_samples = self.ns_to_samples(self.source_switch_left_margin_ns)
        source_switch_right_margin_samples = self.ns_to_samples(self.source_switch_right_margin_ns)
        cpmg_double_peak_gap_samples = int(round(parameters.cpmg_double_peak_gap* 1e-9 * 2.4e9 / 16)) * 16

        # Calculations of durations

        #Section 1

        mw_section_1_samples = (seq_offset_samples + pi_by_two_pulse_samples)
        amp_1_left_zeros_samples = (seq_offset_samples - amp_left_margin_samples)

        #Section 2
        mw_section_2_samples = (gap_len1_samples + pi_pulse_samples)

        # Section 3 CPMG Section
        mw_section_3_samples =  (cpmg_gap_len_samples + cpmg_pulse_samples)
        cpmg_detection_pulse_samples = self.ns_to_samples(eff_detection)
        cpmg_detection_left_zeros_samples = self.ns_to_samples(self.cpmg_det_left_margin_ns)
        cpmg_detection_right_zeros_samples = self.ns_to_samples(self.cpmg_det_right_margin_ns)

        #Section 4
        mw_section_4_samples = (gap_len1_samples + detection_switch_half_width_samples)
        amp_4_right_zeros_samples = (mw_section_4_samples - amp_right_margin_samples)

        # Detection Switch Durations
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
        osc_trig_right_zeros_samples = max(0, (mw_section_4_samples - osc_trig_left_zeros_samples - 240))

        # Source Switch Durations
        # Source switch will be an envelope over the pulse

        source_switch_1_left_zeros_samples = seq_offset_samples - source_switch_left_margin_samples
        source_switch_1_duration_samples = mw_section_1_samples - source_switch_1_left_zeros_samples
        source_switch_2_left_zeros_samples = gap_len1_samples - source_switch_left_margin_samples
        source_switch_2_duration_samples = mw_section_2_samples - source_switch_2_left_zeros_samples
        source_switch_general_left_zeros = source_switch_right_margin_samples

        # Source Switch Over CPMG Pulses

        source_switch_3_left_samples = source_switch_right_margin_samples
        source_switch_3_zeros_samples = cpmg_gap_len_samples - source_switch_left_margin_samples - source_switch_right_margin_samples
        source_switch_3_right_samples = source_switch_left_margin_samples + cpmg_pulse_samples


        # Rf duration
        rf_samples = mw_section_3_samples * parameters.cpmg_count
        rf_frequency = parameters.rf_frequency
        rf_periods = round(rf_samples*(rf_frequency/1e9)/2.4,3)
        rf_phase = parameters.rf_phase
        rf_amp=parameters.rf_amp

        self.validate_double_peak(cpmg_double_peak_gap_samples, seq_offset_samples, gap_len1_samples, cpmg_gap_len_samples,
                             source_switch_left_margin_samples, source_switch_right_margin_samples,
                             cpmg_detection_pulse_samples )  # Special Validation for Double Peak


        #rf correction durations to align rf noise to start from middle of pi pulse to mid of cpmg pulse
        rf_left_zeros = int(pi_pulse_samples / 2)
        rf_right_zeros = int(cpmg_pulse_samples / 2)

        # Strings for source switch
        source_switch_1 = self.double_marker_pulse(source_switch_1_left_zeros_samples, source_switch_1_duration_samples, 0,cpmg_double_peak_gap_samples, 2,source_switch_general_left_zeros)
        source_switch_2 = self.double_marker_pulse(source_switch_2_left_zeros_samples, source_switch_2_duration_samples, 0,cpmg_double_peak_gap_samples, 2,source_switch_general_left_zeros)
        source_gen_left = self.marker_pulse(0, source_switch_general_left_zeros, 0,2)

        source_switch_3 = self.double_rep_marker_pulse_inv(source_switch_3_left_samples, source_switch_3_zeros_samples,
                                                    source_switch_3_right_samples, 2, parameters.cpmg_count, 0, 0,cpmg_double_peak_gap_samples)

        hpa_source_equal_switch = True  # put true if you want HPA to turn off between pulses with timings same as Source Switch

        if hpa_source_equal_switch == True:
            amp_1 = self.double_marker_pulse(source_switch_1_left_zeros_samples, source_switch_1_duration_samples, 0,
                                      cpmg_double_peak_gap_samples,2,source_switch_general_left_zeros)  # added
            amp_2 = self.double_marker_pulse(source_switch_2_left_zeros_samples, source_switch_2_duration_samples, 0,
                                      cpmg_double_peak_gap_samples,2,source_switch_general_left_zeros)  # added
            amp_3 = self.double_rep_marker_pulse_inv(source_switch_3_left_samples, source_switch_3_zeros_samples,
                                              source_switch_3_right_samples, 2, 1, 0, 0,cpmg_double_peak_gap_samples)  # added
            amp_4 = self.marker_pulse(0, amp_right_margin_samples, amp_4_right_zeros_samples, 2)  # added
            amp_gen = self.marker_pulse(0, source_switch_general_left_zeros, 0, 2)

        else:
            amp_1 = self.marker_pulse(amp_1_left_zeros_samples-cpmg_double_peak_gap_samples, amp_left_margin_samples + pi_by_two_pulse_samples+cpmg_double_peak_gap_samples, 0, 2)
            amp_2 = self.marker_pulse(0, mw_section_2_samples, 0, 2)  # commented
            amp_4 = self.marker_pulse(0, amp_right_margin_samples, amp_4_right_zeros_samples, 2)  # commentred
            amp_3 = self.marker_pulse(0, mw_section_3_samples, 0, 2)  # commented
            amp_gen = self.marker_pulse(0,0,0,0)



        # Strings for sequence

        pi_by_two_pulse_i, pi_by_two_pulse_q = self.mw_double_iq_pulse(seq_offset_samples, pi_by_two_pulse_samples, 0,
                                                                parameters.pulse_freq_1,parameters.pulse_freq_2, parameters.pi_by_two_axis, 4.25, parameters.envelope,0.0,cpmg_double_peak_gap_samples,self.parameters.pi_by_two_amplitude_1,self.parameters.pi_by_two_amplitude_2)
        pi_pulse_i, pi_pulse_q = self.mw_double_iq_pulse(gap_len1_samples, pi_pulse_samples, 0,
                                                                parameters.pulse_freq_1,parameters.pulse_freq_2, parameters.pi_axis, 4.25, parameters.envelope,0.0,cpmg_double_peak_gap_samples,self.parameters.pi_amplitude_1,self.parameters.pi_amplitude_2)

        cpmg_waveforms = self.generate_double_cpmg_waveforms(cpmg_gap_len_samples,cpmg_pulse_samples,0,cpmg_double_peak_gap_samples)
        cpmg_definitions = self.generate_cpmg_wave_definitions(cpmg_waveforms,amp_3)
        cpmg_count_string = self.generate_cpmg_string(len(cpmg_waveforms),parameters.cpmg_count)

        detection_wave_index = 2 +len(cpmg_waveforms)



        detection_pulse = self.blank_pulse(mw_section_4_samples)

        switch = self.marker_pulse(detection_left_zeros_samples,detection_duration_samples,0,1)
        osc_trig = self.marker_pulse(osc_trig_left_zeros_samples,240,osc_trig_right_zeros_samples,1)
        shot_repetition = self.play_zero_repeated(shot_repetition_time_samples)


        if(parameters.cpmg_detection_bool):
            switch_3 = self.double_rep_marker_pulse_and(cpmg_detection_left_zeros_samples,cpmg_detection_pulse_samples,cpmg_detection_right_zeros_samples+cpmg_pulse_samples,1,parameters.cpmg_count,cpmg_double_peak_gap_samples)

        else:
            switch_3 = self.rep_marker_pulse(cpmg_detection_left_zeros_samples, cpmg_detection_pulse_samples,
                                             cpmg_detection_right_zeros_samples + cpmg_pulse_samples, 0,
                                             parameters.cpmg_count, 0, 0)

        # rf_string sequence


        #rf_section_2_samples = mw_section_2_samples- rf_left_zeros
        #rf_section_3_samples= rf_samples+ rf_left_zeros - rf_right_zeros
        #rf_section_4_samples = mw_section_4_samples +  rf_right_zeros
        #rf_seq = self.rf_pulse(rf_section_3_samples,rf_amp,rf_phase,rf_periods)

        rf_section_2_samples = mw_section_2_samples
        rf_section_3_samples= rf_samples
        rf_section_4_samples = mw_section_4_samples
        rf_seq = self.rf_pulse(rf_section_3_samples,rf_amp,rf_phase,rf_periods)


        # Validation of Durations and amplitude
        self.validate_double_peak(cpmg_double_peak_gap_samples, seq_offset_samples, gap_len1_samples, cpmg_gap_len_samples,
                             source_switch_left_margin_samples, source_switch_right_margin_samples,
                             cpmg_detection_pulse_samples )  # Special Validation for Double Peak

        if(rf_amp>1.0):
            raise ValueError(" RF Amplitude is set to more than 1.0 : Wave will be trimmed")

        if(cpmg_detection_pulse_samples<=0):
            raise ValueError(" Extend CPMG Gap Len by atleast", eff_detection)

        # Validation of Durations
        if parameters.switch_pulse_ns < 200:
            raise ValueError(f"Switch Pulse should be atleast 200 ns")

        if detection_end_samples < earliest_detection_samples:
            raise ValueError(f"Detection opens before the right margin. Increase Tau or gap_len1_ns ")

        if osc_trig_left_zeros_samples+240 > mw_section_4_samples:
            raise ValueError(f"Trigger offset {parameters.trigger_offset_ns} ns places trigger beyond detection section.")

        if osc_trig_left_zeros_samples < 0:
            raise ValueError("Trigger starts before detection section")

        if (amp_1_left_zeros_samples <= 0):
            raise ValueError("Increase Sequence Offset by minimum of: ",
                             (-parameters.seq_offset_ns + self.amp_left_margin_ns + 1), " ns")

        if (source_switch_1_left_zeros_samples < 0):
            raise ValueError(
                f"Sequence Offset : {parameters.seq_offset_ns} ns must be at least equal to the source-switch left margin :{self.source_switch_left_margin_ns} ns ")

        # Build programs

        seq_prog_pos = self.seq_program_0(
            cpmg_definitions,
            pi_by_two_pulse_i,pi_by_two_pulse_q,
            amp_1,
            pi_pulse_i,pi_pulse_q,
            amp_2,
            detection_pulse,
            amp_4,amp_gen,
            osc_trig,
            parameters.shots_number,
            shot_repetition,0,cpmg_count_string,detection_wave_index
        )
        seq_prog_neg = self.seq_program_0(
            cpmg_definitions,
            pi_by_two_pulse_i,pi_by_two_pulse_q,
            amp_1,
            pi_pulse_i,pi_pulse_q,
            amp_2,
            detection_pulse,
            amp_4,amp_gen,
            osc_trig,
            parameters.shots_number,
            shot_repetition,4,cpmg_count_string,detection_wave_index
        )

        seq_prog_1 = self.seq_program_1(mw_section_1_samples,
            rf_section_2_samples,
            rf_section_3_samples,
            rf_section_4_samples,
            switch_3,
            switch,
            source_switch_1,
            source_switch_2,
            source_switch_3,
            source_gen_left,
            parameters.shots_number,
            shot_repetition,cpmg_count_string,rf_seq
        )

        #print(seq_prog_1)
        #print(seq_prog_pos)
        result = self.hardware.run(parameters, seq_prog_pos, seq_prog_neg, seq_prog_1, self.mw_hahn_echo,
                                   self.rf_hahn_echo)


        if save:#

            if self.save_directory is None:
                save_directory = fr"Y:\DAQ\CondensedMatterGroups\Rest-Of-CM-DAQ-Groups\ArdavanGroup\Measurements\New_Code\{self.foldername}"
            else:
                save_directory = self.save_directory

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