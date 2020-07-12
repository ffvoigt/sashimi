from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar
)
import pyqtgraph as pg
from lightparam.gui import ParameterGui
from lightparam.param_qt import ParametrizedQt
from lightparam import Param
from lightsheet.state import convert_camera_params, GlobalState

from time import time_ns
import napari
import  numpy as np

pg.setConfigOptions(imageAxisOrder="row-major")


class DisplaySettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "display_settings"
        self.display_framerate = Param(16, (1, 100))


class ViewingWidget(QWidget):
    def __init__(self, state, timer):
        super().__init__()
        self.state = state
        self.timer = timer
        self.refresh_timer = QTimer()
        self.main_layout = QVBoxLayout()

        self.display_settings = DisplaySettings()
        self.wid_display_settings = ParameterGui(self.display_settings)

        self.viewer = napari.Viewer(show=False)
        self.frame_layer = self.viewer.add_image(np.zeros([1000, 1000]))
        self.roi = self.viewer.add_shapes([np.array([[0, 0], [500, 500]])], opacity=0.1)

        self.experiment_progress = QProgressBar()
        self.experiment_progress.setFormat("Volume %v of %m")
        self.lbl_experiment_progress = QLabel()

        self.btn_autoadjust = QPushButton("Autoadjust LUT")

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addWidget(self.wid_display_settings)
        self.bottom_layout.addWidget(self.btn_autoadjust)
        self.bottom_layout.addStretch()

        self.main_layout.addWidget(self.viewer.window.qt_viewer)
        self.main_layout.addLayout(self.bottom_layout)
        self.main_layout.addWidget(self.experiment_progress)
        self.main_layout.addWidget(self.lbl_experiment_progress)

        self.experiment_progress.hide()
        self.lbl_experiment_progress.hide()

        self.is_first_image = True
        self.refresh_display = True

        self.last_time_updated = 0

        self.setLayout(self.main_layout)

        self.timer.timeout.connect(self.refresh)
        self.btn_autoadjust.clicked.connect(self.autoadjust_lut)

    def refresh(self) -> None:
        current_image = self.state.get_image()
        if current_image is None:
            return
        if self.is_first_image:
            self.viewer.layers.remove_selected()
            self.frame_layer = self.viewer.add_image(current_image)
            self.is_first_image = False

        current_time = time_ns()
        delta_t = (current_time - self.last_time_updated) / 1e9
        # TODO: Auto-adjust for fist image after binning change (right now one has to click autoadjust_lut)
        if delta_t > 1 / self.display_settings.display_framerate:
            self.frame_layer.data = current_image
            self.last_time_updated = time_ns()

        sstatus = self.state.get_save_status()
        if sstatus is not None:
            self.experiment_progress.show()
            self.lbl_experiment_progress.show()
            self.experiment_progress.setMaximum(sstatus.target_params.n_volumes)
            self.experiment_progress.setValue(sstatus.i_volume)
            self.lbl_experiment_progress.setText("Saved chunks: {}".format(sstatus.i_chunk))

    def autoadjust_lut(self):
        self.is_first_image = True


class CameraSettingsContainerWidget(QWidget):
    def __init__(self, state, roi, timer):
        super().__init__()
        self.roi = roi
        self.state = state
        self.full_size = True
        self.camera_info_timer = timer
        self.setLayout(QVBoxLayout())

        self.wid_camera_settings = ParameterGui(self.state.camera_settings)

        self.lbl_camera_info = QLabel()
        self.lbl_roi = QLabel()

        self.set_roi_button = QPushButton("set ROI")
        self.set_full_size_frame_button = QPushButton("set full size frame")

        self.layout().addWidget(self.wid_camera_settings)
        self.layout().addWidget(self.lbl_camera_info)
        self.layout().addWidget(self.set_roi_button)
        self.layout().addWidget(self.set_full_size_frame_button)
        self.layout().addWidget(self.lbl_roi)

        self.update_camera_info()
        self.camera_info_timer.start()

        self.set_roi_button.clicked.connect(self.set_roi)
        self.set_full_size_frame_button.clicked.connect(self.set_full_size_frame)
        self.camera_info_timer.timeout.connect(self.update_camera_info)

    def set_roi(self):
        roi_pos = self.roi.pos()
        roi_size = self.roi.size()
        self.state.camera_settings.subarray = tuple([roi_pos.x(), roi_pos.y(), roi_size.x(), roi_size.y()])
        self.update_roi_info(width=roi_size.x(), height=roi_size.y())
        self.roi.hide()

    def set_full_size_frame(self):
        self.state.camera_settings.subarray = [
            0,
            0,
            self.state.current_camera_status.image_width,
            self.state.current_camera_status.image_height
        ]
        camera_params = convert_camera_params(self.state.camera_settings)
        self.update_roi_info(
            width=self.state.current_camera_status.image_width / camera_params.binning,
            height=self.state.current_camera_status.image_height / camera_params.binning
        )
        self.roi.show()

    def update_roi_info(self, width, height):
        self.lbl_roi.setText(
            "Current frame dimensions are:\nHeight: {}\nWidth: {}".format(int(height), int(width)))

    def update_camera_info(self):
        triggered_frame_rate = self.state.get_triggered_frame_rate()
        if triggered_frame_rate is not None:
            if self.state.global_state == GlobalState.PAUSED:
                self.lbl_camera_info.hide()
            else:
                self.lbl_camera_info.setStyleSheet("color: white")
                expected_frame_rate = None
                if self.state.global_state == GlobalState.PREVIEW:
                    frame_rate = self.state.current_camera_status.internal_frame_rate
                    self.lbl_camera_info.setText("Internal frame rate: {} Hz".format(round(frame_rate, 2)))
                if self.state.global_state == GlobalState.VOLUME_PREVIEW:
                    planes = self.state.volume_setting.n_planes - \
                             self.state.volume_setting.n_skip_start - self.state.volume_setting.n_skip_end
                    expected_frame_rate = self.state.volume_setting.frequency * planes
                if self.state.global_state == GlobalState.PLANAR_PREVIEW:
                    expected_frame_rate = self.state.single_plane_settings.frequency
                if self.state.volume_setting.i_freeze > 0:
                    expected_frame_rate = 1
                if expected_frame_rate:
                    self.lbl_camera_info.setText(
                        "\n".join(
                            [
                                "Camera frame rate: {} Hz".format(round(triggered_frame_rate, 2))
                            ]
                            + (
                                ["Camera is lagging behind. Decrease exposure, number of planes or frequency"]
                                if expected_frame_rate > (triggered_frame_rate * 1.1)
                                else [
                                    "Seems to follow well current speed"
                                ]
                            )
                        )
                    )

                    if expected_frame_rate > (triggered_frame_rate * 1.1):
                        self.lbl_camera_info.setStyleSheet("color: red")
                    else:
                        self.lbl_camera_info.setStyleSheet("color: green")

                self.lbl_camera_info.show()
