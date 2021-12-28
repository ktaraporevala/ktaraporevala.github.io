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
        self._last_vertex_id = None

    def getPersonID(self):
        if self._last_person_id is None:
            person_id = 1
        else:
            person_id = self._last_person_id + 2
        self._last_person_id = person_id
        return person_id

    def getVertexID(self):
        if self._last_vertex_id is None:
            vertex_id = 2
        else:
            vertex_id = self._last_vertex_id + 2
        self._last_vertex_id = vertex_id
        return vertex_id

    @staticmethod
    def isVertex(id_num):
        return id_num % 2 == 0
