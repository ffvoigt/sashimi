from sashimi.hardware.additional_output.interface import AbstractAdditionalOutput

import nidaqmx
from nidaqmx.constants import LineGrouping

from warnings import warn

class NIAdditionalOutput(AbstractAdditionalOutput):
    def __init__(self, ao_channels=None, do_channels=None):
        super().__init__(ao_channels, do_channels)

    def set_analog_out(self, channel, value):
        """Sets analog out"""
        pass

    def set_digital_out(self, channel, value):
        """Sets shutter"""
        try:
            with nidaqmx.Task() as task:
                task.do_channels.add_do_chan(channel, line_grouping=LineGrouping.CHAN_PER_LINE)
                task.write([value], auto_start=True)
        except:
            warn("NI additional output didn't work", ShutterWarning)

    def close(self):
        pass
