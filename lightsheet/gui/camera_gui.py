from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QDockWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar
)
import pyqtgraph as pg
from lightparam.gui import ParameterGui
from lightparam.param_qt import ParametrizedQt
from lightparam import Param
from pyqtgraph.graphicsItems.ROI import ROI
from lightsheet.state import CameraSettings


class DisplaySettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "display_settings"
        self.replay_rate = Param(5, (1, 10))


class ViewingWidget(QWidget):
    def __init__(self, state, timer):
        super().__init__()
        self.state = state
        self.timer = timer
        self.refresh_timer = QTimer()
        self.setLayout(QVBoxLayout())

        self.display_settings = DisplaySettings()
        self.wid_display_settings = ParameterGui(self.display_settings)

        self.image_viewer = pg.ImageView()
        self.roi = ROI(pos=[100, 100], size=500)
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.image_viewer.view.addItem(self.roi)

        self.image_viewer.ui.roiBtn.hide()
        self.image_viewer.ui.menuBtn.hide()

        self.stack_progress = QProgressBar()
        self.chunk_progress = QProgressBar()
        self.chunk_progress.setFormat("Chunk %v of %m")
        self.stack_progress.setFormat("Frame in chunk %v of %m")

        self.layout().addWidget(self.image_viewer)
        self.layout().addWidget(self.wid_display_settings)
        self.layout().addWidget(self.chunk_progress)
        self.layout().addWidget(self.stack_progress)

        self.chunk_progress.hide()
        self.stack_progress.hide()

        self.is_first_image = True
        self.refresh_display = True

        # ms for display clock. Currently 5 fps replay
        self.refresh_timer.start(int(1000 / self.display_settings.replay_rate))

        self.timer.timeout.connect(self.refresh)
        self.refresh_timer.timeout.connect(self.display_new_image)
        self.display_settings.sig_param_changed.connect(self.update_replay_rate)

    def update_replay_rate(self):
        self.refresh_timer.setInterval(int(1000 / self.display_settings.replay_rate))

    def refresh(self) -> None:
        current_image = self.state.get_image()
        if current_image is None:
            return

        if self.refresh_display:
            self.image_viewer.setImage(
                current_image,
                autoLevels=self.is_first_image,
                autoRange=self.is_first_image,
                autoHistogramRange=self.is_first_image,
            )
            self.is_first_image = False
            self.refresh_display = False

        sstatus = self.state.get_save_status()
        if sstatus is not None:
            self.chunk_progress.show()
            self.stack_progress.show()
            num_chunks = int(sstatus.target_params.n_t / sstatus.target_params.chunk_size)
            self.chunk_progress.setMaximum(num_chunks)
            self.chunk_progress.setValue(sstatus.i_chunk)
            self.stack_progress.setMaximum(int(sstatus.target_params.n_t / num_chunks))
            self.stack_progress.setValue(sstatus.i_t)

    def display_new_image(self):
        self.refresh_display = True


class CameraSettingsContainerWidget(QWidget):
    def __init__(self, state, roi):
        super().__init__()
        self.roi = roi
        self.state = state
        self.camera_info_timer = QTimer()
        self.camera_info_timer.setInterval(500)
        self.setLayout(QVBoxLayout())

        self.wid_camera_settings = ParameterGui(self.state.camera_settings)

        self.lbl_camera_info = QLabel()

        self.set_roi_button = QPushButton("set ROI")
        self.set_full_size_frame_button = QPushButton("set full size frame")

        self.layout().addWidget(self.wid_camera_settings)
        self.layout().addWidget(self.lbl_camera_info)
        self.layout().addWidget(self.set_roi_button)
        self.layout().addWidget(self.set_full_size_frame_button)

        self.update_camera_info()
        self.camera_info_timer.start()

        self.set_roi_button.clicked.connect(self.set_roi)
        self.set_full_size_frame_button.clicked.connect(self.set_full_size_frame)
        self.camera_info_timer.timeout.connect(self.update_camera_info)

    def set_roi(self):
        roi_pos = self.roi.pos()
        roi_size = self.roi.size()
        self.state.camera_settings.subarray = [roi_pos.x(), roi_pos.y(), roi_size.x(), roi_size.y()]

    def set_full_size_frame(self):
        self.state.camera_settings.subarray = [
            0,
            0,
            self.state.current_camera_status.image_width,
            self.state.current_camera_status.image_height
        ]

    def update_camera_info(self):
        triggered_frame_rate = self.state.get_triggered_frame_rate()
        if triggered_frame_rate is not None:
            if self.state.status.scanning_state == "Paused":
                self.lbl_camera_info.hide()
            else:
                if self.state.status.scanning_state == "Calibration":
                    frame_rate = self.state.current_camera_status.internal_frame_rate
                else:
                    frame_rate = triggered_frame_rate
                self.lbl_camera_info.setText("Internal frame rate: " + str(round(frame_rate, 2)))
                self.lbl_camera_info.show()
