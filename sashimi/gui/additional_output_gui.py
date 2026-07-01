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

        self.state.additional_output_settings.sig_param_changed.connect(self.param_changed)

    def param_changed(self, value):
        print("something changed: ", str(value))
