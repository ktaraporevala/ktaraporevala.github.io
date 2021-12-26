import datetime
from dataclasses import dataclass, field

@dataclass
class EventDate:
    year: int = None
    month: int = None
    day: int = None

    def getDate(self):
        return f"{self.year}-{self.month}-{self.day}"

    def __repr__(self):
        return f"{self.year}-{self.month}-{self.day}"

class ID_System:

    def __init__(self):
        self._last_person_id = None
        self._last_couple_id = None
        self.couples = {}

    def getPersonID(self):
        if self._last_person_id is None:
            person_id = 1
        else:
            person_id = self._last_person_id + 2
        self._last_person_id = person_id
        return person_id

    def getCoupleID(self, id_1, id_2):
        if self._last_couple_id is None:
            couple_id = 2
        else:
            couple_id = self._last_couple_id + 2
        self._last_couple_id = couple_id
        self.couples[couple_id] = (id_1, id_2)
        return couple_id

    @staticmethod
    def isCouple(id_num):
        return id_num % 2 == 0
