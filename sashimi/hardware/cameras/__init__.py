from sashimi.hardware.cameras.mock import MockCamera
from sashimi.config import read_config

conf = read_config()
camera_name = conf["camera"]["name"]

camera_class_dict = dict(mock=MockCamera)

if camera_name == "hamamatsu":
    from sashimi.hardware.cameras.hamamatsu import HamamatsuCamera
    camera_class_dict["hamamatsu"] = HamamatsuCamera
elif camera_name == "photometrics":
    from sashimi.hardware.cameras.photometrics import PhotometricsCamera
    camera_class_dict["photometrics"] = PhotometricsCamera
