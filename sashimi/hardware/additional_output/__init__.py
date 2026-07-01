from sashimi.hardware.additional_output.mock import MockAdditionalOutput
from sashimi.hardware.additional_output.ni import NIAdditionalOutput

# Update this dictionary and add the import above when adding a new laser
additional_output_class_dict = dict(
    ni=NIAdditionalOutput,
    mock=MockAdditionalOutput,
)
