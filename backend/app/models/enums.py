from enum import Enum

class RelationshipType(str, Enum):
    son = "son"
    daughter = "daughter"
    mother = "mother"
    father = "father"
    spouse = "spouse"
    partner = "partner"
    brother = "brother"
    sister = "sister"


class ThemeType(str, Enum):
    light = "light"
    dark = "dark"

class Gender(str, Enum):
    male = "male"
    female = "female"

class InvitationStatus(str, Enum):
    invited = "invited"
    accepted = "accepted"
    declined = "declined"

class InvitationType(str, Enum):
    claim_member = "claim_member"
    new_member = "new_member"

class AlbumVisibility(str, Enum):
    private = "private"
    event = "event"
    family = "family"
