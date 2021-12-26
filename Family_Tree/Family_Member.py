import os.path
import sys
from dataclasses import dataclass, asdict
from lib import EventDate, ID_System
import json
import logging

@dataclass
class PersonInfo:
    person_id: int
    first_name: str
    last_name: str
    birth: EventDate
    death: EventDate

    @staticmethod
    def infoFromDict(info_dict):
        person_id = info_dict['person_id']
        first_name = info_dict['first_name']
        last_name = info_dict['last_name']
        birth_info = info_dict['birth']
        birth = EventDate(**birth_info) if birth_info is not None else None
        death_info = info_dict['death']
        death = EventDate(**death_info) if death_info is not None else None
        return PersonInfo(person_id, first_name, last_name, birth, death)

class LinkedPerson:

    def __init__(self, person_id, person_info: PersonInfo):
        self.person_id = person_id
        self.info = person_info
        self.parent = None
        self.couples = set()
        self.children = set()

    def getID(self):
        return self.person_id

    def addChild(self, child):
        self.children.add(child)

    def addParent(self, person_or_couple):
        self.parent = person_or_couple

    def joinCouple(self, couple):
        self.couples.add(couple)

    def getChildren(self):
        return self.children

    def getParent(self):
        return self.parent

    def getCouples(self):
        return self.couples

    def getName(self):
        return f"{self.info.first_name}_{self.info.last_name}"

    def getRelations(self):
        relations = {}
        relations["direct_children"] = [child.getID() for child in self.getChildren()]
        relations["couples"] = [couple.getID() for couple in self.getCouples()]
        relations["parent_unit"] = self.getParent().getID() if self.parent is not None else None
        return relations

    def __repr__(self):
        return str(self.info)

class Couple(LinkedPerson):

    def __init__(self, couple_id, members: set):
        super().__init__(couple_id, None)
        self.couples = None
        self.parent = None
        self.members: set[LinkedPerson] = members
        assert len(members) == 2

    def getMembers(self):
        return self.members

    def getName(self):
        members_list = list(self.getMembers())
        return f"{members_list[0].getName()} and {members_list[1].getName()}"

    def getRelations(self):
        relations = {}
        relations["direct_children"] = [child.getID() for child in self.getChildren()]
        relations["members"] = [member.getID() for member in self.getMembers()]
        return relations

class FamilyManager:

    def __init__(self, import_filenames=None):
        self.id_system = ID_System()
        self.root = None
        self.linked_person_dict: dict[int, LinkedPerson] = {}
        if import_filenames is not None:
            info_file = import_filenames[0]
            relationships_file = import_filenames[1]
            self.import_from_jsons(info_file, relationships_file)


    def import_from_jsons(self, info_filename, relationships_filename):
        with open(info_filename, "r") as infile:
            raw_info_dict = json.load(infile)
            logging.info(f"Read family info from {info_filename}")
        with open(relationships_filename, "r") as infile:
            rels_dict = json.load(infile)
            logging.info(f"Read family info from {relationships_filename}")
        info_dict = {}
        for info_values in raw_info_dict:
            info_object = PersonInfo.infoFromDict(info_values)
            info_dict[info_object.person_id] = info_object
        for key, rels_values in rels_dict.items():
            id_number = int(key)
            if ID_System.isCouple(id_number):
                member_id0, member_id1 = rels_values['members']
                member_0, member_1 = self.getMember(int(member_id0)), self.getMember(int(member_id1))
                couple = self.addCouple(member_0, member_1, id_number)
                direct_children_ids = rels_values["direct_children"]
                children = {self.getMember(id_num) for id_num in direct_children_ids if id_num in self.linked_person_dict.keys()}
                self.addChildren(couple, children)
            else:
                person_info = info_dict[id_number]
                person = self.addFamilyMember(person_info)
                direct_children_ids = rels_values["direct_children"]
                children = {self.getMember(id_num) for id_num in direct_children_ids if id_num in self.linked_person_dict.keys()}
                self.addChildren(person, children)
                couples = rels_values["couples"]
                parent_unit_id = rels_values["parent_unit"]
                if parent_unit_id is not None and parent_unit_id in self.linked_person_dict.keys():
                    parent_unit = self.getMember(parent_unit_id)
                    self.addChild(parent_unit, person)


    def createFamilyMember(self, first_name, last_name, birth, death):
        person_id = self.id_system.getPersonID()
        person_info = PersonInfo(person_id, first_name, last_name, birth, death)
        return self.addFamilyMember(person_info)

    def addFamilyMember(self, person_info):
        person_id = person_info.person_id
        person_connections = LinkedPerson(person_id, person_info)
        if self.root is None:
            self.root = person_connections
        self.linked_person_dict[person_id] = person_connections
        return person_connections

    def addCouple(self, lperson_1: LinkedPerson, lperson_2: LinkedPerson, couple_id=None):
        if couple_id is None:
            couple_id = self.id_system.getCoupleID(lperson_1.person_id, lperson_2.person_id)
        couple = Couple(couple_id, {lperson_1, lperson_2})
        self.linked_person_dict[couple_id] = couple
        lperson_1.joinCouple(couple)
        lperson_2.joinCouple(couple)
        return couple

    @staticmethod
    def addChild(parent_body: LinkedPerson, child: LinkedPerson):
        parent_body.addChild(child)
        child.addParent(parent_body)

    @staticmethod
    def addChildren(parent_body: LinkedPerson, children: set):
        for child in children:
            FamilyManager.addChild(parent_body, child)

    def getMember(self, id_number):
        return self.linked_person_dict[id_number]

    def save(self, info_filepath, connections_filepath):
        self.write_family_info(info_filepath)
        self.writeFamilyConnections(connections_filepath)

    def write_family_info(self, filepath):
        info_list = []
        for key, person in self.linked_person_dict.items():
            if not isinstance(person, Couple):
                logging.debug(f"{key=} {person=}")
                person_info_dict = asdict(person.info)
                info_list.append(person_info_dict)
        json_object = json.dumps(info_list, indent=4)
        with open(filepath, "w") as outfile:
            outfile.write(json_object)
            logging.info(f"Wrote family info to {filepath}")

    def writeFamilyConnections(self, filepath):
        output: dict[int, LinkedPerson] = {}
        for key, person in self.linked_person_dict.items():
            output[key] = person.getRelations()
        json_object = json.dumps(output, indent=4)
        with open(filepath, "w") as outfile:
            outfile.write(json_object)
            logging.info(f"Wrote family relationships to {filepath}")

    def getBasicDict(self) -> dict[int, str]:
        output = {}
        for key, person in self.linked_person_dict.items():
            output[key] = person.getName()
        return output

def iterate_and_print(already_found, root: LinkedPerson):
    already_found.add(root.getID())
    for child in root.getChildren():
        if child.getID() not in already_found:
            iterate_and_print(already_found, child)
    if isinstance(root, Couple):
        for member in root.getMembers():
            if member.getID() not in already_found:
                iterate_and_print(already_found, member)
        return

    logging.info(root, already_found)
    for couple in root.getCouples():
        if couple.getID() not in already_found:
            iterate_and_print(already_found, couple)
    parent = root.getParent()
    if parent is not None and parent.getID() not in already_found:
        iterate_and_print(already_found, parent)

def stringToDate(input):
    match len(input.split('-')):
        case 3:
            pass
        case _:
            raise RuntimeError("Incorrect number of inputs")
    year, month, day = input.split('-')
    event_components: list[str] = [year, month, day]
    for i, item in enumerate(event_components):
        if item.isnumeric():
            event_components[i] = int(event_components[i])
            match i:
                case 0:
                    assert(len(item) == 4)
                case 1 | 2:
                    assert(len(item) == 2)
        else:
            event_components[i] = None
    year, month, day = event_components
    date_time = EventDate(year, month, day)
    return date_time

def addMemberWithInput(manager: FamilyManager):
    first = input("What is this person's first name? ")
    last = input("What is this person's last name? ")
    dob_raw = input("What is this person's DOB? Please write in format YYYY-MM-DD (replace digits with Ns if unknown) ")
    dob = stringToDate(dob_raw)
    dod_raw = input("What is this person's DOD? Please write 'Alive' if alive and "
                    "in format YYYY-MM-DD if deceased(replace digits with Ns if unknown) ")
    if dod_raw.lower() == 'alive':
        dod = None
    else:
        dod = stringToDate(dod_raw)

    member = manager.createFamilyMember(first, last, dob, dod)
    print(f"Current tree: {manager.getBasicDict()}")
    if member != manager.root:
        relation_id = int(input("What is the ID of the family member to relate to? "))
        related_member = manager.getMember(relation_id)
        relation_type = input(f"How is {first} {last} related to {manager.linked_person_dict[relation_id].getName()}?\n"
                              f"Relationship options are child, spouse, and parent. ")
        match relation_type:
            case "child":
                manager.addChild(related_member, member)
            case "spouse":
                manager.addCouple(member, related_member)
            case "parent":
                manager.addChild(member, related_member)
            case _:
                raise ValueError(f"Input must be child, spouse, or parent. Input \"{relation_type}\" is not allowed")
    logging.info(f"Family member {first} {last} successfully added to the tree.")

def test_manual_create():
    info_filename = os.path.join(os.getcwd(), "taraporevalas_info.json")
    connections_filename = os.path.join(os.getcwd(), "taraporevalas_connections.json")
    if not os.path.exists(info_filename):
        manager = FamilyManager()
    else:
        manager = FamilyManager((info_filename, connections_filename))

    while(True):
        todo = input(f"Type 's' to save tree, 'v' to view tree, 'a' to add to tree, or 'q' to quit")
        match todo:
            case 's':
                manager.save(info_filename, connections_filename)
            case 'v':
                logging.info(manager.getBasicDict())
            case 'a':
                addMemberWithInput(manager)
            case 'q':
                really_quit = input("Are you sure you want to quit? (Y/N)")
                if really_quit.lower() in ('y', 'yes'):
                    return
            case _:
                logging.warning("Incorrect input. Please input either 's', 'v', 'a', or 'q'.")

def test():
    info_filename = os.path.join(os.getcwd(), "sample.json")
    connections_filename = os.path.join(os.getcwd(), "test.json")
    manager = FamilyManager()
    tom = manager.createFamilyMember("Tom", "Jones", EventDate(1950, 4, 12), None)
    linda = manager.createFamilyMember("Linda", "Adams", EventDate(1950, 4, 12), None)
    suzan = manager.createFamilyMember("suzan", "Jones", EventDate(1980, 4, 12), None)
    gerald = manager.createFamilyMember("gerald", "Jones", EventDate(1983, 5, 12), None)

    tom_linda = manager.addCouple(tom, linda)
    manager.addChildren(tom_linda, {suzan, gerald})

    root: LinkedPerson = manager.root
    iterate_and_print(set(), suzan)

    manager.write_family_info(info_filename)
    manager.writeFamilyConnections(connections_filename)

def test_read_from_file():
    info_filename = os.path.join(os.getcwd(), "sample.json")
    connections_filename = os.path.join(os.getcwd(), "test.json")
    manager = FamilyManager(import_filenames=(info_filename, connections_filename))
    logging.debug(manager.getBasicDict())
    manager.write_family_info(os.path.join(os.getcwd(), "sample_1.json"))
    manager.writeFamilyConnections(os.path.join(os.getcwd(), "test_1.json"))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    #test()
    #test_read_from_file()
    test_manual_create()
