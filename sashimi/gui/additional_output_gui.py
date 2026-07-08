from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
)
from lightparam.gui import ParameterGui


class AdditionalOutputWidget(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.setLayout(QVBoxLayout())
        self.wid_additional_output = ParameterGui(state.additional_output_settings)
        self.layout().addWidget(self.wid_additional_output)
        self._channel_map = state.additional_output_settings._channel_map

        state.additional_output_settings.sig_param_changed.connect(self.param_changed)

    def param_changed(self, change_dict):
        (param_name,) = change_dict.keys()
        (new_value,) = change_dict.values()

        mapping = self._channel_map.get(param_name)
        if mapping is None:
            return

        if mapping["type"] == "digital":
            self.state.additional_output.set_digital_out(mapping["channel"], new_value)
        else:
            self.state.additional_output.set_analog_out(
                mapping["channel"], new_value * mapping["conversion_factor"]
            )
