import numpy as np
import matplotlib.pyplot as plt




phase_cycle_option = 1


data_trim = 0 # select 1 if you want to trim

#Trim range if data_trim = 1
data_start = 1
data_end = 1000


class SweepPlotter:

    def __init__(
        self,
        sweep_values,
        parameter_name
    ):

        self.sweep_values = np.asarray(sweep_values)
        self.parameter_name = parameter_name

        # Future sweep points remain zero
        self.y_values = np.zeros(
            len(self.sweep_values)
        )

        # Interactive plotting
        plt.ion()

        self.fig, self.ax = plt.subplots()

        self.line, = self.ax.plot(
            self.sweep_values,
            self.y_values,
            marker="o"
        )

        self.ax.set_xlabel(
            self.parameter_name
        )

        self.ax.set_ylabel(
            "Integrated signal"
        )

        self.ax.set_title(
            "Live Sweep"
        )

        self.ax.grid(True)

        plt.show(block=False)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()



    # DATA TRIMMING

    def trim_data(self, data):

        if data_trim == 0:

            return data

        elif data_trim == 1:

            n_points = len(data)

            if data_start < 1:
                raise ValueError(
                    "data_start must be >= 1"
                )

            if data_end > n_points:
                raise ValueError(
                    f"data_end = {data_end} exceeds "
                    f"waveform length = {n_points}"
                )

            if data_end < data_start:
                raise ValueError(
                    "data_end must be >= data_start"
                )

            # Convert 1-based inclusive point numbers
            # into Python slicing
            start_index = data_start - 1
            end_index = data_end

            return data[
                start_index:end_index
            ]

        else:

            raise ValueError(
                "data_trim must be 0 or 1"
            )


    # ======================================================
    # CALCULATE Y VALUE
    # ======================================================

    def calculate_integrated_value(
        self,
        positive_channel_data,
        negative_channel_data
    ):

        # --------------------------------------------------
        # No phase cycling
        # --------------------------------------------------

        if phase_cycle_option == 0:

            ch1 = (
                    positive_channel_data["ch1"]
            )

            ch2 = (
                    positive_channel_data["ch2"]
            )


        # --------------------------------------------------
        # Phase cycled
        # --------------------------------------------------

        elif phase_cycle_option == 1:

            ch1 = (
                positive_channel_data["ch1"]
                - negative_channel_data["ch1"]
            )

            ch2 = (
                positive_channel_data["ch2"]
                - negative_channel_data["ch2"]
            )




        else:

            raise ValueError(
                "phase_cycle_option must be 0 or 1"
            )


        # Apply optional trimming
        ch1 = self.trim_data(
            ch1
        )

        ch2 = self.trim_data(
            ch2
        )

        # Integrated sum
        integrated_value = np.sum(np.sqrt(ch1**2 + ch2**2))


        return integrated_value


    # ======================================================
    # UPDATE PLOT
    # ======================================================

    def update(
        self,
        index,
        positive_channel_data,
        negative_channel_data
    ):

        integrated_value = (
            self.calculate_integrated_value(
                positive_channel_data,
                negative_channel_data
            )
        )

        self.y_values[index] = (
            integrated_value
        )


        # Update plot
        self.line.set_ydata(
            self.y_values
        )

        # Keep full X range
        # but automatically rescale Y
        self.ax.relim()

        self.ax.autoscale_view(
            scalex=False,
            scaley=True
        )

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        plt.pause(0.01)

        return integrated_value

    def print_maximum(self, completed_points=None):

        if completed_points is None:
            completed_points = len(self.y_values)

        y_completed = self.y_values[:completed_points]
        x_completed = self.sweep_values[:completed_points]

        max_index = np.argmax(y_completed)

        max_x = x_completed[max_index]
        max_y = y_completed[max_index]

        print("\nMaximum Integrated Signal")
        print(f"{self.parameter_name} = {max_x}")
        print(f"Integrated signal = {max_y}")

        return max_x, max_y