import pyvisa as visa
import numpy as np
import os
import time
import datetime
import scipy.io
import warnings
import matplotlib.pyplot as plt




class OscilloscopeTektronix:

    def __init__(self,Machine,ID):
        self.rm = visa.ResourceManager()
        #self.oscilloscope = self.rm.open_resource("TCPIP0::192.168.3.30::inst0::INSTR")  For QMUL
        self.oscilloscope = self.rm.open_resource(ID)# For Oxford
        if Machine==0:
            self.nframes_offset = 1
        else:
            self.nframes_offset = 1

    def oscilloscope_init(self, nframes):

        self.oscilloscope.write('*CLS')
        self.oscilloscope.write('header off')
        self.oscilloscope.write('*CLS')
        self.oscilloscope.write('acquire:state off')
        self.oscilloscope.write('horizontal:fastframe:state off')
        self.oscilloscope.timeout = 120000
        if (nframes > 1):
            self.oscilloscope.write('horizontal:fastframe:state on')
            self.oscilloscope.write('HORizontal:FASTframe:SUMFrame:STATE on')
            ff_count = int(self.oscilloscope.query('HORizontal:FASTframe:MAXFRames?'))

            if (ff_count < nframes):
                warnings.warn(f"Invalid FastFrame Numbers: {nframes} \n "
                              f"Using Maximum FastFrames Possible: {ff_count}.",
                              UserWarning,
                              stacklevel=2)
                nframes = ff_count

            self.oscilloscope.write(f'horizontal:fastframe:count {nframes}')
            self.oscilloscope.write("HORizontal:FASTframe:SUMFrame AVErage")
            self.oscilloscope.write(':horizontal:fastframe:selected:ch1 ' + str(nframes + self.nframes_offset))
        if (nframes<1):
            raise ValueError(" FastFrame Number cannot be 0 or negative")

        self.oscilloscope.write('acquire:stopafter sequence')
        # Trigger Settings
        self.oscilloscope.write('trigger:a:type edge')
        self.oscilloscope.write('trigger:a:edge:source aux')
        self.oscilloscope.write('trigger:a:mode normal')
        self.oscilloscope.write('trigger:level:aux 1.2')

        self.oscilloscope.write('acquire:state on')

        # oscilloscope.timeout=12000

    def obtain_waveform_from_frame_binary(self,channel_id, frame_number ):
        self.oscilloscope.write('header off')

        self.oscilloscope.write('data:source ch' + str(channel_id))
        self.oscilloscope.write('data:encdg fastest')

        self.oscilloscope.write(':data:framestart ' + str(frame_number))
        self.oscilloscope.write(':data:framestop ' + str(frame_number))

        total_number_of_points_in_waveform = int(self.oscilloscope.query('HORizontal:ACQLENGTH?'))

        data_start = 1
        data_stop = total_number_of_points_in_waveform

        byte_number = int(self.oscilloscope.query('WFMOutpre:BYT_Nr?'))

        binary_format = str(self.oscilloscope.query('WFMOutpre:BN_Fmt?'))

        self.oscilloscope.write('data:start ' + str(data_start))
        self.oscilloscope.write('data:stop ' + str(data_stop))

        datatype = ""

        if binary_format == "RI\n":
            if byte_number == 1:
                datatype = 'b'
            elif byte_number == 2:
                datatype = 'h'

        elif binary_format == "RP\n":
            if byte_number == 1:
                datatype = 'B'
            elif byte_number == 2:
                datatype = 'H'

        if datatype == "":
            raise ValueError(
                f"Unsupported waveform format: "
                f"BN_Fmt={binary_format.strip()}, BYT_Nr={byte_number}"
            )

        volts_per_digitised_level = float(self.oscilloscope.query('wfmoutpre:ymult?'))
        offset_in_volts = float(self.oscilloscope.query('wfmoutpre:yzero?'))
        offset_in_digitised_levels = float(self.oscilloscope.query('wfmoutpre:yoff?'))
        time_between_two_points = float(self.oscilloscope.query('wfmoutpre:xincr?'))
        samples_in_digitised_levels = self.oscilloscope.query_binary_values('CURV?', datatype=datatype, container=np.array,
                                                                       expect_termination=False)
        samples_in_volts = (
                                       samples_in_digitised_levels - offset_in_digitised_levels) * volts_per_digitised_level + offset_in_volts
        time_in_s = (np.arange(len(samples_in_digitised_levels)) * time_between_two_points)
        self.oscilloscope.write('header on')

        return time_in_s, samples_in_volts, time_between_two_points

    def acquire_channels(self,channels, frame_number):

        channel_data = {}
        time_in_s = None
        time_step = None

        for channel_id in channels:

            print(f"Reading CH{channel_id}...")
            x, y, dt = self.obtain_waveform_from_frame_binary(channel_id=channel_id, frame_number=frame_number)
            channel_data[f"ch{channel_id}"] = y
            if time_in_s is None:
                time_in_s = x
                time_step = dt

        return time_in_s, channel_data, time_step

    def save_data_to_matlab(self,exp_data,exp_parameters, save_directory, file_name="hahn_echo",sweep_data=None):

        os.makedirs(save_directory, exist_ok=True)
        esr_experiment_data = exp_data.copy()

        if sweep_data is not None:
            esr_experiment_data["sweep_data"] = sweep_data

        esr_experiment_parameters = exp_parameters
        matlab_data = {"esr_experiment_data": esr_experiment_data,"esr_experiment_parameters": esr_experiment_parameters}
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        full_file_name = (f"{file_name}_{timestamp}.mat")
        full_path = os.path.join(save_directory, full_file_name)
        scipy.io.savemat(full_path, matlab_data)
        print("\nData saved to:")
        print(full_path)
        return full_path

    def scope_run(self,channels,parameters):

        # Acquisition part
        time_in_s, channel_data, time_step = self.acquire_channels(channels=channels, frame_number=parameters.shots_number+self.nframes_offset)
        return{ "time":time_in_s,"channel_data":channel_data,"time_step":time_step}

    def check_acquisition_status(self):
        self.oscilloscope.write('header off')
        time.sleep(0.5)
        while True:
            state = int(self.oscilloscope.query("ACQUIRE:STATE?"))

            if state == 0:
                break

            time.sleep(0.05)

    def check_acquisition_status_old(self):
        print(self.oscilloscope.query('*OPC?'))  # if program is interrupted during this command - the osc stops responding