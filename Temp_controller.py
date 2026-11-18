import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import csv
import os

from Oxford_ITC import Oxford_ITC


ITC_ADDRESS = 15
UPDATE_INTERVAL_MS = 2000

MIN_ALLOWED_TEMPERATURE = 1.5
MAX_ALLOWED_TEMPERATURE = 320.0

MIN_ALLOWED_HEATER_PERCENT = 0.0
MAX_ALLOWED_HEATER_PERCENT = 99.1

LOG_FILE = "itc_front_panel_log.csv"


class ITCFrontPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Oxford ITC Front Panel")

        self.itc = Oxford_ITC(ITC_ADDRESS)

        try:
            self.itc.clear_queue()
        except Exception:
            pass

        self.temperature_var = tk.StringVar(value="-- K")
        self.heater_voltage_var = tk.StringVar(value="-- V")
        self.heater_percent_var = tk.StringVar(value="-- %")
        self.status_var = tk.StringVar(value="Connected")
        self.mode_var = tk.StringVar(value="Unknown")

        self.target_temperature_var = tk.StringVar(value="100.0")
        self.manual_heater_percent_var = tk.StringVar(value="0.0")

        self.create_widgets()
        self.create_log_file_if_needed()
        self.update_readings()

    def create_widgets(self):
        title = tk.Label(
            self.root,
            text="Oxford ITC Temperature Control",
            font=("Arial", 16, "bold")
        )
        title.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        tk.Label(self.root, text="Current temperature:").grid(
            row=1, column=0, sticky="e", padx=10, pady=5
        )
        tk.Label(self.root, textvariable=self.temperature_var, font=("Arial", 14)).grid(
            row=1, column=1, sticky="w", padx=10, pady=5
        )

        tk.Label(self.root, text="Heater voltage readback:").grid(
            row=2, column=0, sticky="e", padx=10, pady=5
        )
        tk.Label(self.root, textvariable=self.heater_voltage_var, font=("Arial", 14)).grid(
            row=2, column=1, sticky="w", padx=10, pady=5
        )

        tk.Label(self.root, text="Heater percent readback:").grid(
            row=3, column=0, sticky="e", padx=10, pady=5
        )
        tk.Label(self.root, textvariable=self.heater_percent_var, font=("Arial", 14)).grid(
            row=3, column=1, sticky="w", padx=10, pady=5
        )

        tk.Label(self.root, text="Control mode:").grid(
            row=4, column=0, sticky="e", padx=10, pady=5
        )
        tk.Label(self.root, textvariable=self.mode_var, font=("Arial", 12, "bold")).grid(
            row=4, column=1, sticky="w", padx=10, pady=5
        )

        auto_frame = tk.LabelFrame(self.root, text="Automatic temperature control")
        auto_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        tk.Label(auto_frame, text="Target temperature / K:").grid(
            row=0, column=0, sticky="e", padx=10, pady=5
        )
        tk.Entry(auto_frame, textvariable=self.target_temperature_var, width=12).grid(
            row=0, column=1, sticky="w", padx=10, pady=5
        )

        tk.Button(
            auto_frame,
            text="Switch to AUTO mode",
            command=self.switch_to_auto_mode,
            width=22
        ).grid(row=1, column=0, padx=10, pady=5)

        tk.Button(
            auto_frame,
            text="Set Temperature",
            command=self.set_temperature,
            width=22
        ).grid(row=1, column=1, padx=10, pady=5)

        manual_frame = tk.LabelFrame(self.root, text="Manual heater control")
        manual_frame.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        tk.Label(manual_frame, text="Manual heater percent / %:").grid(
            row=0, column=0, sticky="e", padx=10, pady=5
        )
        tk.Entry(manual_frame, textvariable=self.manual_heater_percent_var, width=12).grid(
            row=0, column=1, sticky="w", padx=10, pady=5
        )

        tk.Button(
            manual_frame,
            text="Switch to MANUAL mode",
            command=self.switch_to_manual_mode,
            width=22
        ).grid(row=1, column=0, padx=10, pady=5)

        tk.Button(
            manual_frame,
            text="Set Manual Heater",
            command=self.set_manual_heater_percent,
            width=22
        ).grid(row=1, column=1, padx=10, pady=5)

        tk.Button(
            self.root,
            text="Read Now",
            command=self.update_readings_once,
            width=22
        ).grid(row=7, column=0, columnspan=3, padx=10, pady=5)

        tk.Label(self.root, textvariable=self.status_var, fg="blue").grid(
            row=8, column=0, columnspan=3, padx=10, pady=10
        )

    def create_log_file_if_needed(self):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "temperature_K",
                        "heater_voltage_V",
                        "heater_percent",
                        "mode",
                    ]
                )

    def log_reading(self, temperature, heater_voltage, heater_percent):
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now().isoformat(),
                    temperature,
                    heater_voltage,
                    heater_percent,
                    self.mode_var.get(),
                ]
            )

    def update_readings_once(self):
        try:
            temperature = self.itc.get_temperature()
            heater_voltage = self.itc.get_heater_voltage()
            heater_percent = self.itc.get_heater_percent()

            self.temperature_var.set(f"{temperature:.4f} K")
            self.heater_voltage_var.set(f"{heater_voltage:.4f} V")
            self.heater_percent_var.set(f"{heater_percent:.2f} %")
            self.status_var.set("Read successful")

            self.log_reading(temperature, heater_voltage, heater_percent)

        except Exception as exc:
            self.status_var.set(f"Read error: {exc}")

    def update_readings(self):
        self.update_readings_once()
        self.root.after(UPDATE_INTERVAL_MS, self.update_readings)

    def switch_to_auto_mode(self):
        confirm = messagebox.askyesno(
            "Confirm AUTO mode",
            "Switch ITC heater control to AUTO mode?\n\n"
            "This lets the controller regulate heater output to reach the set temperature."
        )
        if not confirm:
            return

        try:
            self.itc.clear_queue()
        except Exception:
            pass

        try:
            self.itc.set_autoHeater(1)
            self.mode_var.set("AUTO")
            self.status_var.set("Switched to AUTO mode")
            self.update_readings_once()
        except Exception as exc:
            messagebox.showerror("ITC auto-mode error", str(exc))
            self.status_var.set(f"Auto-mode error: {exc}")

    def set_temperature(self):
        try:
            target = float(self.target_temperature_var.get())

            if target < MIN_ALLOWED_TEMPERATURE or target > MAX_ALLOWED_TEMPERATURE:
                messagebox.showerror(
                    "Temperature out of range",
                    f"Allowed range is {MIN_ALLOWED_TEMPERATURE} K to {MAX_ALLOWED_TEMPERATURE} K."
                )
                return

            confirm = messagebox.askyesno(
                "Confirm temperature setpoint",
                f"Set ITC temperature to {target} K?"
            )
            if not confirm:
                return

            try:
                self.itc.clear_queue()
            except Exception:
                pass

            self.itc.set_autoHeater(1)
            self.mode_var.set("AUTO")
            self.itc.set_temperature(target)

            self.status_var.set(f"Setpoint sent: {target} K")
            self.update_readings_once()

        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid temperature.")
        except Exception as exc:
            messagebox.showerror("ITC error", str(exc))
            self.status_var.set(f"Set error: {exc}")

    def switch_to_manual_mode(self):
        confirm = messagebox.askyesno(
            "Confirm MANUAL mode",
            "Switch ITC heater control to MANUAL mode?\n\n"
            "In manual mode, the heater output is fixed and the controller will not "
            "automatically regulate to a temperature setpoint."
        )
        if not confirm:
            return

        try:
            self.itc.clear_queue()
        except Exception:
            pass

        try:
            self.itc.set_autoHeater(0)
            self.mode_var.set("MANUAL")
            self.status_var.set("Switched to MANUAL mode")
            self.update_readings_once()
        except Exception as exc:
            messagebox.showerror("ITC manual-mode error", str(exc))
            self.status_var.set(f"Manual-mode error: {exc}")

    def set_manual_heater_percent(self):
        try:
            percent = float(self.manual_heater_percent_var.get())

            if percent < MIN_ALLOWED_HEATER_PERCENT or percent > MAX_ALLOWED_HEATER_PERCENT:
                messagebox.showerror(
                    "Heater percent out of range",
                    f"Allowed range is {MIN_ALLOWED_HEATER_PERCENT} % to {MAX_ALLOWED_HEATER_PERCENT} %."
                )
                return

            confirm = messagebox.askyesno(
                "Confirm manual heater output",
                f"Set heater to {percent} % in manual mode?"
            )
            if not confirm:
                return

            try:
                self.itc.clear_queue()
            except Exception:
                pass

            self.itc.set_autoHeater(0)
            self.mode_var.set("MANUAL")


            self.itc.set_heater(percent)

            self.status_var.set(f"Manual heater set to {percent} %")
            self.update_readings_once()

        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid heater percent.")
        except Exception as exc:
            messagebox.showerror("ITC heater error", str(exc))
            self.status_var.set(f"Heater error: {exc}")


def main():
    root = tk.Tk()
    app = ITCFrontPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()