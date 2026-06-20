import numpy as np
from warnings import warn

from sashimi.hardware.cameras.interface import (
    AbstractCamera,
    TriggerMode,
    CameraException,
    CameraWarning,
)
from sashimi.config import read_config

conf = read_config()


class PhotometricsCamera(AbstractCamera):
    def __init__(self, camera_id, max_sensor_resolution):
        super().__init__(camera_id, max_sensor_resolution)

        from pyvcam import pvc
        from pyvcam import constants as const
        from pyvcam.camera import Camera

        self._pvc = pvc
        self._const = const

        pvc.init_pvcam()

        cameras = list(Camera.detect_camera())
        if not cameras:
            raise CameraException("No Photometrics camera detected")

        if camera_id < len(cameras):
            self._cam = cameras[camera_id]
        else:
            self._cam = cameras[0]
            warn(
                f"Camera ID {camera_id} out of range, using first camera",
                CameraWarning,
            )

        self._cam.open()

        photometrics_conf = conf["camera"].get("photometrics", {})

        self._cam.exp_res = 0

        self._exposure_time_ms = conf["camera"]["default_exposure"]
        self._binning = conf["camera"]["default_binning"]
        self._trigger_mode = TriggerMode.FREE
        self._roi = (0, 0) + tuple(max_sensor_resolution)
        self._is_acquiring = False

        self._cam.exp_time = int(self._exposure_time_ms)

        if "readout_port" in photometrics_conf:
            self._cam.set_param(
                param_id=const.PARAM_READOUT_PORT,
                value=photometrics_conf["readout_port"],
            )

        if "speed_table_index" in photometrics_conf:
            self._cam.speed_table_index = photometrics_conf["speed_table_index"]

        if "gain_index" in photometrics_conf:
            self._cam.set_param(
                const.PARAM_GAIN_INDEX,
                photometrics_conf["gain_index"],
            )
        if "exp_out_mode" in photometrics_conf:
            self._cam.exp_out_mode = photometrics_conf["exp_out_mode"]

        if "scan_mode" in photometrics_conf:
            self._cam.set_param(
                param_id=const.PARAM_SCAN_MODE,
                value=photometrics_conf["scan_mode"],
            )
        if "scan_direction" in photometrics_conf:
            self._cam.set_param(
                param_id=const.PARAM_SCAN_DIRECTION,
                value=photometrics_conf["scan_direction"],
            )
        if "scan_line_delay" in photometrics_conf:
            self._cam.set_param(
                param_id=const.PARAM_SCAN_LINE_DELAY,
                value=photometrics_conf["scan_line_delay"],
            )



    @property
    def exposure_time(self):
        return self._exposure_time_ms

    @exposure_time.setter
    def exposure_time(self, exp_val):
        self._exposure_time_ms = exp_val
        self._cam.exp_time = int(exp_val)

    @property
    def binning(self):
        return self._binning

    @binning.setter
    def binning(self, n_bin):
        self._binning = int(n_bin)
        self._cam.binning = (self._binning, self._binning)

    @property
    def roi(self):
        return self._roi

    @roi.setter
    def roi(self, exp_val: tuple):
        self._roi = exp_val
        vpos, hpos, vsize, hsize = exp_val
        self._cam.reset_rois()
        self._cam.set_roi(int(hpos), int(vpos), int(hsize), int(vsize))

    @property
    def trigger_mode(self):
        return self._trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, exp_val: TriggerMode):
        if str(exp_val) == str(TriggerMode.FREE):
            self._cam.exp_mode = "Internal Trigger"
        elif str(exp_val) == str(TriggerMode.EXTERNAL_TRIGGER):
              self._cam.exp_mode = "Edge Trigger"
        self._trigger_mode = exp_val

    @property
    def frame_rate(self):
        if self._exposure_time_ms > 0:
            return 1000.0 / self._exposure_time_ms
        return 0.0

    def start_acquisition(self):
        self._cam.exp_time = int(self._exposure_time_ms)
        self._cam.start_live()
        self._is_acquiring = True

    def stop_acquisition(self):
        if self._is_acquiring:
            self._cam.finish()
            self._is_acquiring = False

    def get_frames(self):
        frames = []
        if not self._is_acquiring:
            return frames
        try:
            result = self._cam.poll_frame()
            if result is not None:
                frame_dict, fps, frame_count = result
                if frame_dict is not None and "pixel_data" in frame_dict:
                    frames.append(frame_dict["pixel_data"].copy())
        except Exception:
            pass
        return frames

    def shutdown(self):
        super().shutdown()
        try:
            self._cam.close()
        except Exception:
            pass
        try:
            self._pvc.uninit_pvcam()
        except Exception:
            pass
