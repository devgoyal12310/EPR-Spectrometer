import numpy as np
import datetime as datetime
from pathlib import Path

print("Start")
import time
t0 = time.perf_counter()


program_start = time.perf_counter()

t = time.perf_counter()
from HahnEchoExp import HahnEchoExp
print(f"Import HahnEchoExp:        {time.perf_counter() - t:.6f} s")

t = time.perf_counter()
from PulseOptimizationParameters import PulseOptimizationParameters
print(f"Import HahnEchoParameters: {time.perf_counter() - t:.6f} s")

t = time.perf_counter()
from EPRHardware import HahnEchoHardware
print(f"Import HahnEchoHardware:   {time.perf_counter() - t:.6f} s")

# operation

print(f"Importing hardware and parameters {(time.perf_counter() - t0):.6f} s")
t0 = time.perf_counter()











parameters = PulseOptimizationParameters()
hardware = HahnEchoHardware()

# Pulse sequence
parameters.seq_offset_ns = 400
parameters.pi_by_two_pulse_ns = 1000
parameters.gap_len1_ns = 300
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_pulse_ns = 600
parameters.switch_pulse_ns = 1000


# Acquisition
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 4

# MW amplitudes
parameters.pi_by_two_amplitude = 0.5
parameters.pi_amplitude = parameters.pi_by_two_amplitude



i_offset_sweep = np.linspace(-40,40,20)*1e-3
q_offset_sweep = np.linspace(-60,0,20)*1e-3

pulse_freq_sweep = [0,1e6,2e6,50e6,88e6,100e6,110e6,90e6,112e6,200e6]

#pulse_freq_sweep = [10e6,20e6]

for k in pulse_freq_sweep:
    # ============================================================
    # Sweep folder

    sweep_name = f"PulseFreq {k}"


    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    sweep_directory = Path(
        fr"Y:\DAQ\CondensedMatterGroups\Rest-Of-CM-DAQ-Groups\ArdavanGroup\Measurements\New_Code\Pulse Optimization\{sweep_name}_{timestamp}"
    )

    sweep_directory.mkdir(parents=True, exist_ok=True)

    print(f"Sweep data will be saved to:")
    print(sweep_directory)

    # ============================================================
    parameters.pulse_freq = k
    experiment = HahnEchoExp(parameters, hardware, sweep_directory)







    for i in i_offset_sweep:
        for q in q_offset_sweep:


            parameters.i_offset = round(float(i),5)
            parameters.q_offset = round(float(q),5)

            hardware.set_iq_offset(parameters.i_offset,parameters.q_offset)

            parameters.filename = f"Pulse_iq_offset_optimization_i_offset_{parameters.i_offset*1e3}mV_q_offset_{parameters.q_offset*1e3}mV_"
            result = experiment.run(True)
            print(f"Saved Data for i_phase_offset= {i} and q_phase_offset = {q}")


hardware.dispose()
print("End")