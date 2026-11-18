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




# ============================================================
# Sweep folder

sweep_name = "Single_Test"

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

sweep_directory = Path(
    fr"H:\Data\NewCodeData\Pulse Optimization\{sweep_name}_{timestamp}"
)

sweep_directory.mkdir(parents=True, exist_ok=True)

print(f"Sweep data will be saved to:")
print(sweep_directory)

# ============================================================

parameters = PulseOptimizationParameters()
hardware = HahnEchoHardware()

# Pulse sequence
parameters.seq_offset_ns = 400
parameters.pi_by_two_pulse_ns = 1000
parameters.gap_len1_ns = 300
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_pulse_ns = 800
parameters.switch_pulse_ns = 1000
parameters.pulse_freq = 100e6

# Acquisition
parameters.shot_repetition_time_ns = 100e6
parameters.shots_number = 4

# MW amplitudes
parameters.pi_by_two_amplitude = 0.4
parameters.pi_amplitude = parameters.pi_by_two_amplitude

experiment = HahnEchoExp(parameters,hardware,sweep_directory)


# Pulse Optimization:
parameters.i_offset = 0.00632#0.01128 #-0.03
parameters.q_offset = -0.03158 #-0.0331 # 0.02
parameters.i_phase_offset = 0
parameters.q_phase_offset = 0
parameters.q_scaling_fac = 1.0


parameters.filename = f"Single_test_scaling_fac_{parameters.q_scaling_fac}_"
hardware.set_iq_offset(parameters.i_offset,parameters.q_offset)

result = experiment.run(True)

hardware.dispose()
print("End")