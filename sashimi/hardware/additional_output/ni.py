from sashimi.hardware.additional_output.interface import AbstractAdditionalOutput

import nidaqmx
from nidaqmx.constants import LineGrouping

from warnings import warn

class NIAdditionalOutput(AbstractAdditionalOutput):
    def __init__(self, ao_channels=None, do_channels=None):
        super().__init__(ao_channels, do_channels)

    def set_analog_out(self, channel, value):
        try:
            with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan(channel)
                task.write(value)
                print("Voltage written")
        except:
            print("NI additional analog output write failed")

    def set_digital_out(self, channel, value):
        """Sets shutter"""
        try:
            with nidaqmx.Task() as task:
                task.do_channels.add_do_chan(channel, line_grouping=LineGrouping.CHAN_PER_LINE)
                task.write([value], auto_start=True)
        except:
            print("NI additional digital output write failed")

    def close(self):
        pass
