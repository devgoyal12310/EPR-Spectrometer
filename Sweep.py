import numpy as np
from SweepPlotter import SweepPlotter
from datetime import datetime

class Sweep:

    def __init__(
        self,
        experiment_class,
        parameters,
        hardware,
        parameter_name,
        sweep_values, magnet = None
    ):
        self.experiment_class = experiment_class
        self.parameters = parameters
        self.hardware = hardware
        self.magnet = magnet

        self.parameter_name = parameter_name
        self.sweep_values = np.asarray(sweep_values)
        self.plotter = SweepPlotter(
            sweep_values=self.sweep_values,
            parameter_name=self.parameter_name
        )



    def run(self):

        positive_data = None
        negative_data = None
        oscilloscope_time_step = None
        temperatures = []
        field_befores=[]
        field_afters=[]
        timestamps=[]
        completed_points = 0

        n_sweep =len(self.sweep_values)

        try:
            for i,value in enumerate(self.sweep_values):

                print(f"{self.parameter_name} = {value}")

                # Change selected parameter
                setattr(
                    self.parameters,
                    self.parameter_name,
                    value
                )

                if self.magnet is not None:
                    # Run exp using updated parameters
                    experiment = self.experiment_class(
                        self.parameters,
                        self.hardware,self.magnet
                    )
                else:
                    experiment = self.experiment_class(
                        self.parameters,
                        self.hardware
                    )


                # Record timestamp immediately before measurement
                timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")

                # Run experiment
                result = experiment.run(save=False)

                # Store timestamp for this sweep point
                temperatures.append(result["temperature"])
                field_befores.append(result["field_before"])
                field_afters.append(result["field_after"])
                timestamps.append(timestamp)


                # First initialization

                if positive_data is None:
                    positive_data ={}
                    negative_data ={}

                    for channel,trace in result["positive_channel_data"].items():
                        n_samples = len(trace)

                        #Future points initialized to 0
                        positive_data[channel] = np.zeros((n_samples,n_sweep))
                        negative_data[channel] = np.zeros((n_samples,n_sweep))

                    oscilloscope_time_step = result["oscilloscope_time_step"]

                for channel in positive_data:
                    positive_data[channel][:, i] = (result["positive_channel_data"][channel])

                    negative_data[channel][:, i] = (result["negative_channel_data"][channel])

                # Update live plot
                self.plotter.update(
                    i,
                    result["positive_channel_data"],
                    result["negative_channel_data"]
                )

                completed_points = i + 1

        except BaseException as error:
            # Save completed points on Ctrl+C and on any other failure
            # (instrument timeout, validation error at a later point, ...)
            if isinstance(error, KeyboardInterrupt):
                print(" Sweep Interrupted")
            else:
                print(f" Sweep stopped by error: {error!r}")

            if completed_points > 0:
                try:
                    self.save(
                        positive_data,
                        negative_data,
                        oscilloscope_time_step,
                        temperatures,
                        field_befores,
                        field_afters,
                        completed_points,
                        timestamps,
                        interrupted=True
                    )
                except Exception as save_error:
                    # Do not hide the original error behind a save error
                    print(f" Could not save partial sweep data: {save_error!r}")

            raise

        # Print maximum ONCE after completed sweep
        max_x, max_y = self.plotter.print_maximum(
            completed_points
        )
        print(rf"Max Value {max_y} at the parameter value of {max_x}")

        # Normal save
        saved_path = self.save(
            positive_data,
            negative_data,
            oscilloscope_time_step,
            temperatures,
            field_befores,
            field_afters,
            completed_points,
            timestamps,
            interrupted=False
        )

        return {
            "positive_channel_data": positive_data,
            "negative_channel_data": negative_data,
            "oscilloscope_time_step": oscilloscope_time_step,
            "temperatures": temperatures,
            "field_before": field_befores,
            "field_after": field_afters,
            "integrated_values": self.plotter.y_values,
            "saved_path": saved_path
        }

    def save(
            self,
            positive_data,
            negative_data,
            oscilloscope_time_step,
            temperatures,
            field_befores,
            field_afters,
            completed_points,
            timestamps=None,
            interrupted=False
    ):

        sweep_data = {
            "parameter_name": self.parameter_name,
            "values": self.sweep_values,
            "integrated_values": self.plotter.y_values,
            "timestamps": np.asarray(timestamps, dtype=str),
            "completed_points": completed_points
        }

        exp_parameters = vars(self.parameters).copy()

        file_name = self.parameters.filename

        if interrupted:
            file_name += "_INTERRUPTED"

        experiment_data = {
            "positive_channel_data": positive_data,
            "negative_channel_data": negative_data,
            "oscilloscope_time_step": oscilloscope_time_step,
            "temperature": np.asarray(temperatures),
            "field_before": np.asarray(field_befores),
            "field_after": np.asarray(field_afters)
        }
        return self.hardware.Osc.save_data_to_matlab(
            exp_data=experiment_data,
            exp_parameters=exp_parameters,
            save_directory=self.parameters.save_directory,
            file_name=file_name,
            sweep_data=sweep_data
        )
