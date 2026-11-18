"""Simple Tk panel for manual constant-current/constant-voltage control.

Run with the Python installation that has PyVISA and the lab VISA backend.
The output starts off, and configuring a setpoint never enables it.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import pyvisa

from keithley_JB import Keithley2470


DEFAULT_RESOURCE = "GPIB1::18::INSTR"


class KeithleyPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Keithley 2470 control")
        self.root.resizable(False, False)
        self.rm = None
        self.resource = None
        self.instrument = None
        self.output_enabled = False
        self.setpoint_applied = False

        self.resource_name = tk.StringVar(value=DEFAULT_RESOURCE)
        self.mode = tk.StringVar(value="current")
        self.setpoint = tk.StringVar(value="0.002")
        self.compliance = tk.StringVar(value="1.0")
        self.status = tk.StringVar(value="Disconnected; output state not checked")

        frame = ttk.Frame(root, padding=12)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="VISA resource").grid(row=0, column=0, sticky="w")
        self.resource_box = ttk.Combobox(frame, textvariable=self.resource_name, width=25)
        self.resource_box.grid(row=0, column=1, padx=6, sticky="ew")
        ttk.Button(frame, text="Scan", command=self.scan).grid(row=0, column=2)
        self.connect_button = ttk.Button(frame, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=3, padx=(6, 0))

        ttk.Label(frame, text="Source mode").grid(row=1, column=0, sticky="w", pady=(12, 0))
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=1, column=1, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Radiobutton(mode_frame, text="Constant current", variable=self.mode,
                        value="current", command=self._update_labels).grid(row=0, column=0)
        ttk.Radiobutton(mode_frame, text="Constant voltage", variable=self.mode,
                        value="voltage", command=self._update_labels).grid(row=0, column=1, padx=12)

        self.setpoint_label = ttk.Label(frame)
        self.setpoint_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.setpoint, width=16).grid(row=2, column=1, sticky="w", pady=(10, 0))
        self.compliance_label = ttk.Label(frame)
        self.compliance_label.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.compliance, width=16).grid(row=3, column=1, sticky="w", pady=(8, 0))

        self.apply_button = ttk.Button(frame, text="Apply setpoint (output off)",
                                       command=self.apply_setpoint, state="disabled")
        self.apply_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self.output_button = ttk.Button(frame, text="Enable output…", command=self.toggle_output,
                                        state="disabled")
        self.output_button.grid(row=4, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(14, 0))
        ttk.Label(frame, textvariable=self.status, wraplength=490).grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(12, 0)
        )

        self._update_labels()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.scan()

    def _update_labels(self):
        if self.mode.get() == "current":
            self.setpoint_label.configure(text="Current setpoint (A)")
            self.compliance_label.configure(text="Voltage limit (V)")
        else:
            self.setpoint_label.configure(text="Voltage setpoint (V)")
            self.compliance_label.configure(text="Current limit (A)")

    def scan(self):
        try:
            manager = pyvisa.ResourceManager()
            try:
                resources = tuple(manager.list_resources())
            finally:
                manager.close()
            self.resource_box["values"] = resources
            if self.resource_name.get() not in resources and DEFAULT_RESOURCE in resources:
                self.resource_name.set(DEFAULT_RESOURCE)
            self.status.set("Found: " + (", ".join(resources) if resources else "no VISA resources"))
        except Exception as error:
            self.status.set(f"VISA scan failed: {error}")

    def connect(self):
        if self.instrument is not None:
            return
        try:
            self.rm = pyvisa.ResourceManager()
            self.resource = self.rm.open_resource(self.resource_name.get().strip())
            self.resource.read_termination = "\n"
            self.resource.write_termination = "\n"
            self.resource.timeout = 60_000
            self.instrument = Keithley2470(self.resource, name="Keithley 2470")
            identity = self.instrument.idn()
            output_state = self.instrument.query(":OUTP?").strip().upper()
            self.output_enabled = output_state in ("1", "ON")
            output_text = "on" if self.output_enabled else "off"
            self.status.set(f"Connected: {identity}. Instrument output is {output_text}.")
            self.connect_button.configure(text="Connected", state="disabled")
            self.apply_button.configure(state="normal")
            self.output_button.configure(
                state="normal" if self.setpoint_applied or self.output_enabled else "disabled",
                text="Turn output off" if self.output_enabled else "Enable output…",
            )
        except Exception as error:
            self._release_connection()
            messagebox.showerror("Connection failed", str(error), parent=self.root)
            self.status.set(f"Connection failed: {error}")

    def apply_setpoint(self):
        try:
            value = float(self.setpoint.get())
            limit = float(self.compliance.get())
            if limit <= 0:
                raise ValueError("The compliance limit must be greater than zero.")
            self.instrument.output_off()
            self.output_enabled = False
            if self.mode.get() == "current":
                self.instrument.set_source_current_mode()
                self.instrument.set_voltage_limit(limit)
                self.instrument.set_current(value)
                summary = f"Configured {value:g} A, voltage limit {limit:g} V. Output is off."
            else:
                self.instrument.set_source_voltage_mode()
                self.instrument.set_current_limit(limit)
                self.instrument.set_voltage(value)
                summary = f"Configured {value:g} V, current limit {limit:g} A. Output is off."
            self.setpoint_applied = True
            self.output_button.configure(text="Enable output…")
            self.output_button.configure(state="normal")
            self.status.set(summary)
        except Exception as error:
            messagebox.showerror("Could not apply setpoint", str(error), parent=self.root)
            self.status.set(f"Setpoint not confirmed: {error}")

    def toggle_output(self):
        if not self.output_enabled:
            if not messagebox.askyesno(
                "Enable Keithley output?",
                "Enable the output using the setpoint and compliance shown above? Check the wiring and load first.",
                parent=self.root,
            ):
                return
            try:
                self.instrument.output_on()
                self.output_enabled = True
                self.output_button.configure(text="Turn output off")
                self.status.set("Output is on. Use the button to turn it off.")
            except Exception as error:
                messagebox.showerror("Could not enable output", str(error), parent=self.root)
        else:
            self._turn_output_off()

    def _turn_output_off(self):
        if self.instrument is not None:
            try:
                self.instrument.output_off()
                self.status.set("Output is off.")
            except Exception as error:
                self.status.set(f"Output-off command failed: {error}")
                messagebox.showerror("Output-off command failed", str(error), parent=self.root)
        self.output_enabled = False
        self.output_button.configure(text="Enable output…")

    def _release_connection(self):
        if self.resource is not None:
            try:
                self.resource.close()
            except Exception:
                pass
        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
        self.resource = self.rm = self.instrument = None

    def close(self):
        if self.instrument is not None:
            self._turn_output_off()
        self._release_connection()
        self.root.destroy()


def main():
    root = tk.Tk()
    KeithleyPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
