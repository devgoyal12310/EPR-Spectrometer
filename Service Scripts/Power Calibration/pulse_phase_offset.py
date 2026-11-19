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

# ============================================================
# Sweep folder

sweep_name = "IQ_Phase_Offset"

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

sweep_directory = Path(
    fr"H:\Data\NewCodeData\Pulse Optimization\{sweep_name}_{timestamp}"
)

sweep_directory.mkdir(parents=True, exist_ok=True)

print(f"Sweep data will be saved to:")
print(sweep_directory)

# ============================================================



# operation

print(f"Importing hardware and parameters {(time.perf_counter() - t0):.6f} s")
t0 = time.perf_counter()

parameters = PulseOptimizationParameters()
hardware = HahnEchoHardware()

# Pulse sequence
parameters.seq_offset_ns = 300
parameters.pi_by_two_pulse_ns = 300
parameters.gap_len1_ns = 500
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_pulse_ns = 700
parameters.switch_pulse_ns = 1000
parameters.pulse_freq = 15e6

# Acquisition
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 4

# MW amplitudes
parameters.pi_by_two_amplitude = 0.3
parameters.pi_amplitude = 2*parameters.pi_by_two_amplitude


experiment = HahnEchoExp(parameters,hardware,sweep_directory)


i_phase_sweep= np.linspace(-10,10,10)
q_phase_sweep = np.linspace(-10,10,10)


for i in i_phase_sweep:
    for q in q_phase_sweep:


        parameters.i_phase_offset = round(float(i),2)
        parameters.q_phase_offset = round(float(q),2)
        parameters.filename = f"Pulse_Phase_optimization_i_phase_offset_{parameters.i_phase_offset}_q_phase_offset_{parameters.q_phase_offset}_"
        result = experiment.run(True)
        print(f"Saved Data for i_phase_offset= {i} and q_phase_offset = {q}")


hardware.dispose()
print("End")