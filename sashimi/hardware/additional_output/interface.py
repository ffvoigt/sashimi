from abc import ABC, abstractmethod

class AbstractAdditionalOutput(ABC):
    def __init__(self, ao_channels, do_channels):
        self.ao_channels = ao_channels
        self.do_channels = do_channels
        self._ao_status = []
        self._do_status = []

    @abstractmethod
    def set_analog_out(self, channel, value):
        """Sets analog out voltage"""
        pass

    @abstractmethod
    def set_digital_out(self, channel, value):
        """Sets digital out channel"""
        pass

    @abstractmethod
    def close(self):
        pass
