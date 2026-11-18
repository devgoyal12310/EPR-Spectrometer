import time
t0 = time.perf_counter()
import requests

print("Time to import=",time.perf_counter()-t0)
t0 = time.perf_counter()

ip = "100.100.100.7"

url = f"http://{ip}/io/t1/probe/average_field/value.json"




while(True):

    time.sleep(0.5)

    response = requests.get(url, timeout=2)
    response.raise_for_status()
    field_gauss = float(response.json())

    print(f"Magnetic field: {field_gauss:.3f} G")
    print(f"Magnetic field: {field_gauss / 10000:.6f} T")

    print("Time to get value=",time.perf_counter()-t0-0.5)
    t0 = time.perf_counter()