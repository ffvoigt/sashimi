from sashimi.hardware.additional_output.interface import AbstractAdditionalOutput

class MockAdditionalOutput(AbstractAdditionalOutput):
    def __init__(self, ao_channels=None, do_channels=None):
        super().__init__(ao_channels, do_channels)
        self.ao_channels = ao_channels
        self.do_channels = do_channels

    def set_analog_out(self, channel, value):
        """Sets analog out"""
        pass

    def set_digital_out(self, channel, value):
        """Sets digital out"""
        pass

    def close(self):
        pass
