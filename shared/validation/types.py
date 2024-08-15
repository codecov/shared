from enum import Enum
from typing import List, Literal, NamedTuple


class BundleThreshold(NamedTuple):
    type: Literal["absolute"] | Literal["percentage"]
    threshold: int | float


class CoverageCommentRequiredChanges(Enum):
    """Concrete choices of requirements to post the coverage PR comment
    See shared.validation.user_schema.py for description
    """

    no_requirements = 0b000
    any_change = 0b001
    coverage_drop = 0b010
    uncovered_patch = 0b100


ValidRawRequiredChange = (
    Literal["any_change"] | Literal["coverage_drop"] | Literal["uncovered_patch"]
)
CoverageCommentRequiredChangesORGroup = (
    # This represents a grouping of CoverageCommentRequiredChanges through OR operations (bitwise).
    # For the group to be satisfied ANY of the conditions should be satisfied
    # To know if a CoverageCommentRequiredChanges you do a bitwise AND:
    # Example:
    #   0b110 & CoverageCommentRequiredChanges.uncovered_patch == True (so 'uncovered_patch' is a member of this OR group)
    Literal[0b000]
    | Literal[0b001]
    | Literal[0b010]
    | Literal[0b011]
    | Literal[0b100]
    | Literal[0b101]
    | Literal[0b110]
    | Literal[0b111]
)

# For the AND group to be satisfied ALL of the individual OR groups need to be satisfied
# Example:
#   [0b001, 0b100] - There has to be any change in coverage AND the patch can't be 100% covered
CoverageCommentRequiredChangesANDGroup = List[CoverageCommentRequiredChangesORGroup]
