import time
import requests

t = time.perf_counter()
from zhinst.toolkit import Session, CommandTable
print(f"[IMPORT] zhinst.toolkit: {time.perf_counter() - t:.6f} s")

t = time.perf_counter()
from HardwareFiles.OscilloscopeTektronix import OscilloscopeTektronix
print(f"[IMPORT] OscilloscopeTektronix: {time.perf_counter() - t:.6f} s")

from HardwareFiles.MWSource import MWSource
from HardwareFiles.SR830 import SR830
from HardwareFiles.Oxford_ITC import Oxford_ITC


class EPRHardware:

    def __init__(self,parameters):

        self.Machine = 0  # 0 for OXFORD , 1 for QMUL

        self.time_checks = 0

        if self.Machine == 0:

            self.MWSource = MWSource()
            self.SR830 = SR830(8)
            self.deviceID = "dev8606"
            self.OscID= "GPIB1::1"
            self.ITC = Oxford_ITC(15)
            self.field_sensor_ip = "100.100.100.7"
            self.field_sensor_session = requests.Session()
            self.Machine_Name = "Oxford"
            #self.set_iq_offset(0.01628,-0.03015)

        else:
            self.deviceID= "dev9182"
            self.OscID = "TCPIP0::192.168.3.30::inst0::INSTR"
            self.Machine_Name = "QMUL"

        self.Osc = OscilloscopeTektronix(self.Machine,self.OscID)

        print("Connecting to HDAWG...")
        t = time.perf_counter()

        self.session = Session("localhost")
        self.device = self.session.connect_device(self.deviceID)

        if(self.time_checks == 1):
            print(f"[Session Connect HDAWG]: {time.perf_counter() - t:.6f} s")
            t = time.perf_counter()

        self.initialize(parameters.mw_freq,parameters.pulse_freq)
        if (self.time_checks == 1):
            print(f"[Intializing HDAWG]: {time.perf_counter() - t:.6f} s")

    def read_temp(self):
        temp = self.ITC.get_temperature()
        return temp
    def read_magnetic_field(self):
        url = (f"http://{self.field_sensor_ip}/io/t1/probe/average_field/value.json")
        response = self.field_sensor_session.get(url,timeout=2)
        response.raise_for_status()
        field_gauss = float(response.json())
        return field_gauss

    def initialize(self,mw_freq,pulse_freq):

        self.device.system.awg.channelgrouping(0)

        self.temp = None
        self.field_before = None
        self.field_after = None

        self.device.awgs[0].enable(0)
        self.device.awgs[1].enable(0)

        self.session.sync()

        self.device.awgs[0].commandtable.clear(1)
        self.device.awgs[1].commandtable.clear(1)

        self.device.awgs[0].reset(1)
        self.device.awgs[1].reset(1)

        self.device.oscs[1].freq(float(0))
        self.device.system.awg.oscillatorcontrol(0)
        self.device.awgs[0].outputs[0].modulation.mode(0)
        self.device.awgs[0].outputs[1].modulation.mode(0)

        self.device.sigouts[0].direct(1)
        self.device.sigouts[1].direct(1)

        #self.device.sigouts[0].range(0.5)
        #self.device.sigouts[1].range(0.5)

        # Marker Routings
        self.device.triggers.out[0].source(4)
        self.device.triggers.out[1].source(5)
        self.device.triggers.out[2].source(6)
        self.device.triggers.out[3].source(7)

        self.device.sigouts[0].offset(float(0.0))
        self.device.sigouts[1].offset(float(0.0))

        self.device.sigouts[0].on(1)
        self.device.sigouts[1].on(1)

        self.device.system.synchronization.source(0)
        self.device.awgs[0].synchronization.enable(1)
        self.device.awgs[1].synchronization.enable(1)


        self.session.sync()
        time.sleep(0.1)

        if self.Machine == 0:
            self.MWSource.set_freq_Ghz(mw_freq,pulse_freq)
            self.MWSource.switch_on()
            self.SR830.set_aux_vol(4, 4.5)


    def dispose(self):
        self.device.awgs[0].enable(0)
        self.device.awgs[1].enable(0)
        if self.Machine == 0:
            self.MWSource.switch_off()
            self.SR830.set_aux_vol(4, 0)

    def set_iq_offset(self,i_offset,q_offset):
        self.device.sigouts[0].offset(float(i_offset))
        self.device.sigouts[1].offset(float(q_offset))

    def run(self,parameters,seq_prog_pos,seq_prog_neg,seq_prog_1,mw_hahn_echo,rf_hahn_echo,phase_cycle=True):

        # Change for different Channel Acquisition
        channels = [1, 2,3,4]

        self.Osc.oscilloscope_init(parameters.shots_number)

        time.sleep(1)  # Important to keep

        if self.Machine==0:
            self.field_before = self.read_magnetic_field()

        # definition
        device = self.device

        # Time Calculator
        t0 = time.perf_counter()

        #Positive Phase Cycle

        device.awgs[0].load_sequencer_program(seq_prog_pos)
        device.awgs[1].load_sequencer_program(seq_prog_1)

        ## Initialize command table

        ct_schema = device.awgs[0].commandtable.load_validation_schema()
        ct_mw = CommandTable(ct_schema)
        ct_rf = CommandTable(ct_schema)


        mw_hahn_echo(ct_mw)
        rf_hahn_echo(ct_rf)

        print(ct_mw.as_dict())

        ## Upload command table

        device.awgs[0].commandtable.upload_to_device(ct_mw)
        device.awgs[1].commandtable.upload_to_device(ct_rf)
        self.session.sync()


        # Start both cores together so the two output pairs stay aligned.

        device.awgs[0].enable_sequencer(single=True)
        device.awgs[1].enable_sequencer(single=True)

        if (self.time_checks == 1):
            print((time.perf_counter() - t0), " Total Time to load Positive Cycle")
            print("AWG started")
            t0=time.perf_counter()

        self.Osc.check_acquisition_status()

        if (self.time_checks == 1):
            print((time.perf_counter() - t0), " Time to average for the Oscilloscope Positive Cycle")
            t0=time.perf_counter()

        positive_result = self.Osc.scope_run(channels, parameters)

        if (self.time_checks == 1):
            print((time.perf_counter() - t0), " Time to save data Positive Cycle")
            t0=time.perf_counter()

        self.Osc.check_acquisition_status()


        ## Second Negative Phase Cycle
        if(phase_cycle):

            self.Osc.oscilloscope_init(parameters.shots_number)
            time.sleep(1)

            t0 = time.perf_counter()

            device.awgs[0].load_sequencer_program(seq_prog_neg)
            #device.awgs[1].load_sequencer_program(seq_prog_1)  #also incldue timeout

            device.awgs[0].commandtable.upload_to_device(ct_mw)
            #device.awgs[1].commandtable.upload_to_device(ct_rf)

            device.awgs[0].synchronization.enable(1)
            device.awgs[1].synchronization.enable(1)

            device.awgs[0].enable_sequencer(single=True)
            device.awgs[1].enable_sequencer(single=True)

            if (self.time_checks == 1):
                print((time.perf_counter() - t0), " Time to enable Sequencer Neagative Phase Cycle")
                t0=time.perf_counter()

            self.Osc.check_acquisition_status()

            if (self.time_checks == 1):
                print((time.perf_counter() - t0), " Time to average for the Oscilloscope Negative Cycle")
                t0=time.perf_counter()


            negative_result =self.Osc.scope_run(channels,parameters)

            if (self.time_checks == 1):
                print((time.perf_counter() - t0), " Time to Save Data")


        else:
            negative_result = positive_result

        if self.Machine == 0:
            self.field_after = self.read_magnetic_field()
            self.temp = self.read_temp()

        return {
            "temperature":self.temp,
            "time": positive_result["time"],
            "oscilloscope_time_step":positive_result["time_step"],
            "positive_channel_data": positive_result["channel_data"],
            "negative_channel_data": negative_result["channel_data"],
            "field_before":self.field_before,
            "field_after":self.field_after,
            "Machine":self.Machine_Name,
        }
