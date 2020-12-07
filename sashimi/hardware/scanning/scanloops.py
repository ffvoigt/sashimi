from copy import deepcopy
from dataclasses import dataclass, asdict
from enum import Enum
from multiprocessing.queues import Queue
from typing import Tuple, Union
from arrayqueues.shared_arrays import ArrayQueue

import numpy as np

from scopecuisine.rolling_buffer import FillingRollingBuffer, RollingBuffer

from sashimi.config import read_config
from sashimi.processes.logging import ConcurrenceLogger
from sashimi.utilities import lcm, get_last_parameters
from sashimi.waveforms import TriangleWaveform, SawtoothWaveform, NegativeStepWaveform, \
    CameraRollingBuffer
from sashimi.hardware.scanning.__init__ import AbstractScanInterface

conf = read_config()


class ScanningState(Enum):
    PAUSED = 1
    PLANAR = 2
    VOLUMETRIC = 3


class ExperimentPrepareState(Enum):
    PREVIEW = 1
    NO_TRIGGER = 2
    EXPERIMENT_STARTED = 3
    ABORT = 4


@dataclass
class XYScanning:
    vmin: float = 1
    vmax: float = 0
    frequency: float = 800


@dataclass
class PowerCntrScanning:
    vmin: float = 1
    vmax: float = 0
    frequency: float = 800
    threshold: float = 0.9


@dataclass
class PlanarScanning:
    lateral: XYScanning = XYScanning()
    power: PowerCntrScanning = PowerCntrScanning()


@dataclass
class ZManual:
    piezo: float = 0
    lateral: float = 0
    frontal: float = 0


@dataclass
class ZSynced:
    piezo: float = 0
    lateral_sync: Tuple[float, float] = (0.0, 0.0)
    frontal_sync: Tuple[float, float] = (0.0, 0.0)


@dataclass
class ZScanning:
    piezo_min: float = 0
    piezo_max: float = 0
    frequency: float = 1
    lateral_sync: Tuple[float, float] = (0.0, 0.0)
    frontal_sync: Tuple[float, float] = (0.0, 0.0)


@dataclass
class TriggeringParameters:
    n_planes: int = 0
    n_skip_start: int = 0
    n_skip_end: int = 0
    frequency: Union[None, float] = None


@dataclass
class ScanParameters:
    state: ScanningState = ScanningState.PAUSED
    experiment_state: ExperimentPrepareState = ExperimentPrepareState.PREVIEW
    z: Union[ZScanning, ZManual, ZSynced] = ZManual()
    offset: float = 0
    amplitude: float = -0.015
    xy: PlanarScanning = PlanarScanning()
    triggering: TriggeringParameters = TriggeringParameters()


class ScanLoop:
    """General class for the control of the event loop of the scanning, taking
    care of the synchronization between the galvo and piezo scanning and the camera triggering.
    It has a loop method which is defined only here and not overwritten in sublasses, which controls
    the main order of events. In this class we handle only the lateral scanning, which is common to calibration,
    planar, and volumetric acquisitions.

    The class does not implement a Process by itself; instead, the suitable child of this class (depending on
    the scanning mode) is "mounted" by the ScannerProcess process, and the ScanLoop.loop method is executed.

    """

    def __init__(
            self,
            board: AbstractScanInterface,
            stop_event,
            restart_event,
            initial_parameters: ScanParameters,
            parameter_queue: Queue,
            n_samples,
            sample_rate,
            waveform_queue: ArrayQueue,
            wait_signal,
            logger: ConcurrenceLogger,
            trigger_exp_from_scanner,
    ):

        self.sample_rate = sample_rate
        self.n_samples = n_samples

        self.board = board

        self.stop_event = stop_event
        self.restart_event = restart_event
        self.logger = logger

        self.parameter_queue = parameter_queue
        self.waveform_queue = waveform_queue

        self.parameters = initial_parameters
        self.old_parameters = initial_parameters

        self.trigger_exp_from_scanner = trigger_exp_from_scanner

        self.started = False
        self.n_acquired = 0
        self.first_update = True
        self.i_sample = 0
        self.n_samples_read = 0

        self.lateral_waveform = TriangleWaveform(**asdict(self.parameters.xy.lateral))
        self.frontal_waveform = NegativeStepWaveform(**asdict(self.parameters.xy.power))

        self.time = np.arange(self.n_samples) / self.sample_rate
        self.shifted_time = self.time.copy()

        self.wait_signal = wait_signal

    def _n_samples_period(self):
        ns_lateral = int(round(self.sample_rate / self.lateral_waveform.frequency))
        ns_frontal = int(round(self.sample_rate / self.frontal_waveform.frequency))
        return lcm(ns_lateral, ns_frontal)

    def _loop_condition(self):
        """Returns False if main event loop has to be interrupted. this happens both when we want
        to restart the scanning loop (if restart_event is set), or we want to interrupt scanning
        (stop_event is set).

        """
        if self.restart_event.is_set():
            self.restart_event.clear()
            return False
        return not self.stop_event.is_set()

    def _check_start(self):
        if not self.started:
            self.board.start()
            self.started = True

    def _fill_arrays(self):
        self.shifted_time[:] = self.time + self.i_sample / self.sample_rate
        self.board.xy_lateral = self.lateral_waveform.values(self.shifted_time)
        self.board.xy_frontal = self.frontal_waveform.values(self.shifted_time)

    def _write(self):
        self.board.write()
        self.logger.log_message("write")

    def _read(self):
        self.board.read()
        self.logger.log_message("read")
        self.n_samples_read += self.board.n_samples

    def initialize(self):
        self.n_acquired = 0
        self.first_update = True
        self.i_sample = 0
        self.n_samples_read = 0

    def _update_settings(self):
        """Update parameters and return True only if got new parameters.
        """
        new_params = get_last_parameters(self.parameter_queue)
        if new_params is None:
            return False

        self.parameters = new_params
        self.lateral_waveform = TriangleWaveform(**asdict(self.parameters.xy.lateral))
        self.frontal_waveform = NegativeStepWaveform(**asdict(self.parameters.xy.power))
        self.first_update = False  # To avoid multiple updates
        return True

    def loop(self, first_run=False):
        """Main loop that gets executed in the run of the ScannerProcess class.
        The stop_event regulates breaking out of this loop and
        returns to the execution of the run of ScannerProcess.
        """
        while True:
            self._update_settings()
            self.old_parameters = deepcopy(self.parameters)
            if not self._loop_condition():
                break
            self._fill_arrays()
            self._write()
            self._check_start()
            self._read()
            self.i_sample = (self.i_sample + self.n_samples) % self._n_samples_period()
            self.n_acquired += 1
            if first_run:
                break


class PlanarScanLoop(ScanLoop):
    """Class for controlling the planar scanning mode, where we image only one plane and
    do not control the piezo and vertical galvo."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.camera_pulses = RollingBuffer(self._n_samples_period())

    def _n_samples_period(self):
        # If we are not using camera trigger, the period is dictated by lateral scanning:
        if (
                self.parameters.triggering.frequency is None
                or self.parameters.triggering.frequency == 0
        ):
            return super()._n_samples_period()
        # Else, find least common multiple between timepoints required for trigger and for the lateral scanning:
        else:
            n_samples_trigger = int(
                round(self.sample_rate / self.parameters.triggering.frequency)
            )
            return lcm(n_samples_trigger, super()._n_samples_period())

    def _loop_condition(self):
        return (
                super()._loop_condition() and self.parameters.state == ScanningState.PLANAR
        )

    def _fill_arrays(self):
        # Drive the piezo z to specified position:
        self.board.z_piezo = self.parameters.z.piezo

        # If we are in calibration mode and galvos are not synched, use interface value to set them:
        if isinstance(self.parameters.z, ZManual):
            self.board.z_lateral = self.parameters.z.lateral
            self.board.z_frontal = self.parameters.z.frontal

        # Else, calculate the galvo z from the calibration:
        elif isinstance(self.parameters.z, ZSynced):
            self.board.z_lateral = calc_sync(
                self.parameters.z.piezo, self.parameters.z.lateral_sync
            )
            self.board.z_frontal = calc_sync(
                self.parameters.z.piezo, self.parameters.z.frontal_sync
            )
        super()._fill_arrays()


class VolumetricScanLoop(ScanLoop):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.z_waveform = SawtoothWaveform()
        buffer_len = int(round(self.sample_rate / self.parameters.z.frequency))
        self.recorded_signal = FillingRollingBuffer(buffer_len)
        self.camera_pulses_buffer = CameraRollingBuffer(buffer_len)
        self.current_frequency = self.parameters.z.frequency
        self.camera_on = False
        self.trigger_exp_start = False
        self.camera_was_off = True
        self.wait_signal.set()

    def _n_samples_period(self):
        n_samples_trigger = int(round(self.sample_rate / self.parameters.z.frequency))
        return max(n_samples_trigger, super()._n_samples_period())

    def _loop_condition(self):
        return (
                super()._loop_condition()
                and self.parameters.state == ScanningState.VOLUMETRIC
        )

    def _check_start(self):
        super()._check_start()
        # Toggle the experiment state after starting the new acquisition:
        if (
                self.parameters.experiment_state
                == ExperimentPrepareState.EXPERIMENT_STARTED
        ):
            self.parameters.experiment_state = ExperimentPrepareState.PREVIEW

    def _update_settings(self):
        updated = super()._update_settings()
        if not updated and not self.first_update:
            return False

        if self.parameters.state != ScanningState.VOLUMETRIC:
            return True

        if self.parameters != self.old_parameters:
            if self.parameters.z.frequency > 0.1:
                full_period = int(round(self.sample_rate / self.parameters.z.frequency))
                self.recorded_signal = FillingRollingBuffer(full_period)
                self.camera_pulses_buffer = CameraRollingBuffer(full_period)
                self.initialize()

        self.camera_pulses_buffer.set_impulses(
            self.parameters.triggering.n_planes,
            n_skip_start=self.parameters.triggering.n_skip_start,
            n_skip_end=self.parameters.triggering.n_skip_end,
        )

        self.z_waveform = SawtoothWaveform(
            frequency=self.parameters.z.frequency,
            vmin=self.parameters.z.piezo_min,
            vmax=self.parameters.z.piezo_max,
        )

        if not self.camera_on and self.n_samples_read > self._n_samples_period():
            self.camera_on = True
            self.trigger_exp_start = True
        elif not self.camera_on:
            self.wait_signal.set()
        return True

    def _fill_arrays(self):
        super()._fill_arrays()
        self.board.z_piezo = self.z_waveform.values(self.shifted_time)
        i_sample = self.i_sample % len(self.recorded_signal.buffer)

        # if self.recorded_signal.is_complete():
        #     wave_part = self.recorded_signal.read(i_sample, self.n_samples)  # piezo Z AI
        #     piezo_maxmin_voltage = 5  # Max (and -min) voltage
        #     for board, parameters in ((self.board.z_lateral, self.parameters.z.lateral_sync),
        #                               (self.board.z_frontal, self.parameters.z.frontal_sync)):
        #         wave_out = np.clip(calc_sync(wave_part, parameters), -piezo_maxmin_voltage, piezo_maxmin_voltage)
        #         board = wave_out

            # max_wave, min_wave = (np.max(wave_part), np.min(wave_part))
            # print(calc_sync(min_wave, (self.parameters.offset,
            #                            self.parameters.amplitude)),
            #       calc_sync(max_wave, (self.parameters.offset,
            #                            self.parameters.amplitude))
            #       )
            # SAFE_COEF = 5  # clipping for safety, in Volts
            # if (
            #         -SAFE_COEF < calc_sync(min_wave, (self.parameters.offset,
            #                                           self.parameters.amplitude)) < SAFE_COEF
            #         and -SAFE_COEF < calc_sync(max_wave, (self.parameters.offset,
            #                                               self.parameters.amplitude)) < SAFE_COEF
            # ):
            #     self.board.z_lateral = calc_sync(
            #         wave_part, (self.parameters.offset,
            #                     self.parameters.amplitude)
            #     )
            #
            # # Frontal beam
            # if (
            #         -2 < calc_sync(min_wave, self.parameters.z.frontal_sync) < 2
            #         and -2 < calc_sync(max_wave, self.parameters.z.frontal_sync) < 2
            # ):
            #     self.board.z_frontal = calc_sync(
            #         wave_part, self.parameters.z.frontal_sync
            #     )

        camera_pulses = 0
        if self.camera_on:
            if self.camera_was_off:
                self.logger.log_message("Camera was off")
                # calculate how many samples are remaining until we are in a new period
                if i_sample == 0:
                    camera_pulses = self.camera_pulses_buffer.read(i_sample, self.n_samples)
                    self.camera_was_off = False
                    self.wait_signal.clear()
                else:
                    n_to_next_start = self._n_samples_period() - i_sample
                    if n_to_next_start < self.n_samples:
                        camera_pulses = self.camera_pulses_buffer.read(
                            i_sample, self.n_samples
                        ).copy()
                        camera_pulses[:n_to_next_start] = 0
                        self.camera_was_off = False
                        self.wait_signal.clear()
            else:
                camera_pulses = self.camera_pulses_buffer.read(i_sample, self.n_samples)

        self.board.camera_trigger = camera_pulses

    def _read(self):
        super()._read()
        i_insert = (self.i_sample - self.n_samples) % len(self.recorded_signal.buffer)
        self.recorded_signal.write(
            self.board.z_piezo[
            : min(len(self.recorded_signal.buffer), len(self.board.z_piezo))
            ],
            i_insert,
        )
        self.waveform_queue.put(self.recorded_signal.buffer)

    def initialize(self):
        super().initialize()
        self.camera_on = False
        self.wait_signal.set()


def calc_sync(z, sync_coef):
    """sync_coef is slope and intercept"""
    return sync_coef[0] + sync_coef[1] * z
