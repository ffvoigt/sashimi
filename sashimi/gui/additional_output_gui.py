from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
)
from lightparam.gui import ParameterGui

import numpy as np

class AdditionalOutputWidget(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.setLayout(QVBoxLayout())
        self.wid_additional_output = ParameterGui(state.additional_output_settings)
        self.layout().addWidget(self.wid_additional_output)
        self.ao_channels = self.state.additional_output.ao_channels
        self.do_channels = self.state.additional_output.do_channels

        self.state.additional_output_settings.sig_param_changed.connect(self.param_changed)

    def param_changed(self, change_dict):
        '''
        Not ideal as the channel assignment is hard-coded
        ... and as a UI Widget contains that kind of information which is not exactly
        separation of responsibilities
        However, it seems to be Sashimi standard to have Widgets directly interact with the state
        object.

        Note that also the conversion of 100% laser intensity to 5V is hardcoded
        '''

        # print("something changed: ", str(change_dict))
        (ui_key,) = change_dict.keys()
        (new_value,) = change_dict.values()

        if isinstance(new_value,bool):
            ''' Digital output tree '''
            # print("digital output of ", ui_key , " changed to: ", new_value)
            if ui_key == "Laser_405nm_enable":
                self.state.additional_output.set_digital_out(self.do_channels + "0", new_value)
            elif ui_key == "Laser_488nm_enable":
                self.state.additional_output.set_digital_out(self.do_channels + "1", new_value)
            elif ui_key == "Laser_561nm_enable":
                self.state.additional_output.set_digital_out(self.do_channels + "2", new_value)
            elif ui_key == "Laser_640nm_enable":
                self.state.additional_output.set_digital_out(self.do_channels + "3", new_value)
        else:
            ''' Analog output tree '''
            if ui_key == "Intensity_405nm":
                new_value = new_value/20 # 100% equals 5V
                self.state.additional_output.set_analog_out(self.ao_channels + "0", new_value)
            elif ui_key == "Intensity_488nm":
                #print("setting 488 intensity")
                #print(self.ao_channels + "1")
                new_value = new_value/20 # 100% equals 5V
                self.state.additional_output.set_analog_out(self.ao_channels + "1", new_value)
            elif ui_key == "Intensity_561nm":
                new_value = new_value/20 # 100% equals 5V
                self.state.additional_output.set_analog_out(self.ao_channels + "2", new_value)
            elif ui_key == "Intensity_640nm":
                new_value = new_value/20 # 100% equals 5V
                self.state.additional_output.set_analog_out(self.ao_channels + "3", new_value)
            elif ui_key == "ETL_output":
                self.state.additional_output.set_analog_out(self.ao_channels + "4", new_value)
            elif ui_key == "Resonant_output":
                self.state.additional_output.set_analog_out(self.ao_channels + "5", new_value)
