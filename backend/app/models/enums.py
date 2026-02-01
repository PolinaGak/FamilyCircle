from enum import Enum

class RelationshipType(str, Enum):
    son = "son"
    daughter = "daughter"
    mother = "mother"
    father = "father"
    spouse = "spouse"
    partner = "partner"


class ThemeType(str, Enum):
    light = "light"
    dark = "dark"

class InvintationStatus(str, Enum):
    invited = "invited"
    accepted = "accepted"
    declined = "declined"
