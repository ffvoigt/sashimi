from sashimi.hardware.lasers import AbstractLaser


class MockCoboltLaser(AbstractLaser):
    def __init__(self, port):
        super().__init__(port)
        self._drive_current = 0

    @property
    def drive_current(self):
        return self._drive_current

    @drive_current.setter
    def drive_current(self, exp_val):
        self._drive_current = exp_val

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, exp_val):
        pass
