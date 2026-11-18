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
from HahnEchoHardware import HahnEchoHardware
print(f"Import HahnEchoHardware:   {time.perf_counter() - t:.6f} s")

# operation

print(f"Importing hardware and parameters {(time.perf_counter() - t0):.6f} s")
t0 = time.perf_counter()




# ============================================================
# Sweep folder

sweep_name = "Q_Scaling_Fac"

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
parameters.seq_offset_ns = 300
parameters.pi_by_two_pulse_ns = 300
parameters.gap_len1_ns = 500
parameters.pi_pulse_ns = parameters.pi_by_two_pulse_ns
parameters.trigger_pulse_ns = 500
parameters.switch_pulse_ns = 1000
parameters.pulse_freq = 10e6

# Acquisition
parameters.shot_repetition_time_ns = 1e6
parameters.shots_number = 1

# MW amplitudes
parameters.pi_by_two_amplitude = 0.4
parameters.pi_amplitude = parameters.pi_by_two_amplitude

experiment = HahnEchoExp(parameters,hardware,sweep_directory)

q_scaling_fac_sweep = np.linspace(1.0,1.1,1)




for i in q_scaling_fac_sweep:

        parameters.q_scaling_fac = round(float(i),3)

        #hardware.set_iq_offset(0.00632,-0.03158)
        parameters.filename = f"Pulse_amplitude_ratio_{parameters.q_scaling_fac}_"
        result = experiment.run(True)
        print(f"Saved Data for scaling factor = {i}")


hardware.dispose()
print("End")