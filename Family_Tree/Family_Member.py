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

class Connection:
    LINKED_PERSON = 0
    VERTEX = 1

    def getID(self):
        raise NotImplementedError("Implemented in subclass")

    def getRelations(self):
        raise NotImplementedError("Implemented in subclass")

    def getName(self):
        raise NotImplementedError("Implemented in subclass")

class LinkedPerson(Connection):

    def __init__(self, person_id, person_info: PersonInfo):
        self.type = Connection.LINKED_PERSON
        self.person_id = person_id
        self.info = person_info
        self.parent_vertex: Vertex = None
        self.child_vertices: set = set()

    def getID(self):
        return self.person_id

    def addParentVertex(self, vertex):
        self.parent_vertex = vertex

    def addChildVertex(self, vertex):
        self.child_vertices.add(vertex)

    def getParent(self):
        return self.parent_vertex

    def getVertices(self):
        return self.child_vertices

    def getName(self):
        return f"{self.info.first_name} {self.info.last_name}"

    def getRelations(self):
        relations = {"type": self.type,
                     "child_vertices": [vertex.getID() for vertex in self.getVertices()],
                     "parent_vertex": self.getParent().getID() if self.parent_vertex is not None else None}
        return relations

    def __repr__(self):
        return str(self.info)

class Vertex(Connection):

    def __init__(self, vertex_id, members: set):
        self.type = Connection.VERTEX
        self.vertex_id = vertex_id
        self.children: set[LinkedPerson] = set()
        self.parents: set[LinkedPerson] = members
        assert len(members) == 1 or 2

    def addChild(self, child):
        self.children.add(child)

    def getID(self):
        return self.vertex_id

    def getParents(self):
        return self.parents

    def getChildren(self):
        return self.children

    def getName(self):
        members_list = list(self.getParents())
        if len(members_list) == 2:
            return f"Vertex: {members_list[0].getName()} and {members_list[1].getName()}"
        elif len(members_list) == 1:
            return f"Vertex: {members_list[0].getName()}"
        raise NotImplementedError("Vertex with more than 2 parents not implemented.")

    def getRelations(self):
        relations = {"type": self.type,
                     "children": [child.getID() for child in self.getChildren()],
                     "parents": [member.getID() for member in self.getParents()]}
        return relations

class FamilyManager:

    def __init__(self, import_filenames=None):
        self.id_system = ID_System()
        self.root = None
        self.connection_dict: dict[int, Connection] = {}
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
            if rels_values["type"] == Connection.LINKED_PERSON:
                person_info = info_dict[id_number]
                person = self.addFamilyMember(person_info)
                vertices = rels_values["child_vertices"]
                parent_unit_id = rels_values["parent_vertex"]
                if parent_unit_id is not None and parent_unit_id in self.connection_dict.keys():
                    parent_unit = self.getMember(parent_unit_id)
                    assert isinstance(parent_unit, Vertex)
                    self.addChild(parent_unit, person)
            elif rels_values["type"] == Connection.VERTEX:
                member_ids = rels_values['parents']
                members = set()
                for member_id in member_ids:
                    member = self.getMember(int(member_id))
                    assert isinstance(member, LinkedPerson)
                    members.add(member)
                vertex = self.addVertex(members, id_number)
                direct_children_ids = rels_values["children"]
                children = {self.getMember(id_num) for id_num in direct_children_ids if id_num in self.connection_dict.keys()}
                self.addChildren(vertex, children)
            else:
                raise ValueError(f"Invalid type of {rels_values['type']}. "
                                 f"Types must be {Connection.LINKED_PERSON} or {Connection.VERTEX}.")

    def createFamilyMember(self, first_name, last_name, birth, death):
        person_id = self.id_system.getPersonID()
        person_info = PersonInfo(person_id, first_name, last_name, birth, death)
        return self.addFamilyMember(person_info)

    def addFamilyMember(self, person_info):
        person_id = person_info.person_id
        person_connections = LinkedPerson(person_id, person_info)
        if self.root is None:
            self.root = person_connections
        self.connection_dict[person_id] = person_connections
        return person_connections

    def addVertex(self, members: set[LinkedPerson], vertex_id=None):
        if vertex_id is None:
            vertex_id = self.id_system.getVertexID()
        vertex = Vertex(vertex_id, members)
        self.connection_dict[vertex_id] = vertex
        for member in members:
            member.addChildVertex(vertex)
        return vertex

    @staticmethod
    def addChild(parent_vertex: Vertex, child: LinkedPerson):
        parent_vertex.addChild(child)
        child.addParentVertex(parent_vertex)

    @staticmethod
    def addChildren(parent_body: Vertex, children: set[LinkedPerson]):
        for child in children:
            FamilyManager.addChild(parent_body, child)

    def getMember(self, id_number):
        return self.connection_dict[id_number]

    def save(self, info_filepath, connections_filepath):
        self.write_family_info(info_filepath)
        self.writeFamilyConnections(connections_filepath)

    def write_family_info(self, filepath):
        info_list = []
        for key, person in self.connection_dict.items():
            if isinstance(person, LinkedPerson):
                logging.debug(f"{key=} {person=}")
                person_info_dict = asdict(person.info)
                info_list.append(person_info_dict)
        json_object = json.dumps(info_list, indent=4)
        with open(filepath, "w") as outfile:
            outfile.write(json_object)
            logging.info(f"Wrote family info to {filepath}")

    def writeFamilyConnections(self, filepath):
        output: dict[int, dict] = {}
        for key, connection in self.connection_dict.items():
            if isinstance(connection, LinkedPerson):
                output[key] = connection.getRelations()
        for key, connection in self.connection_dict.items():
            if isinstance(connection, Vertex):
                output[key] = connection.getRelations()

        json_object = json.dumps(output, indent=4)
        with open(filepath, "w") as outfile:
            outfile.write(json_object)
            logging.info(f"Wrote family relationships to {filepath}")

    def getBasicDict(self) -> dict[int, str]:
        output = {}
        for key, person in self.connection_dict.items():
            output[key] = person.getName()
        return output

def iterate_and_print(already_found, connection: Connection):
    already_found.add(connection.getID())
    if isinstance(connection, Vertex):
        for member in connection.getParents():
            if member.getID() not in already_found:
                iterate_and_print(already_found, member)
        for child in connection.getChildren():
            if child.getID() not in already_found:
                iterate_and_print(already_found, child)
    elif isinstance(connection, LinkedPerson):
        logging.info((connection, already_found))
        for vertex in connection.getVertices():
            if vertex.getID() not in already_found:
                iterate_and_print(already_found, vertex)
        parent = connection.getParent()
        if parent is not None and parent.getID() not in already_found:
            iterate_and_print(already_found, parent)

def stringToDate(input: str):
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

def addVertexWithInput(manager: FamilyManager):
    print(f"Current tree: {manager.getBasicDict()}")
    raw_head_ids = input("Select id(s) of head(s) of family unit. If 2 people, separate with a comma (ex. '3,7')")
    head_ids = raw_head_ids.split(',')
    heads = [manager.getMember(int(head_id)) for head_id in head_ids]
    for head in heads:
        assert isinstance(head, LinkedPerson)
    vertex = manager.addVertex(heads)

    is_children = input("Would you like to add children to this family unit? (Y/N)")
    if is_children.lower() not in ('y', 'yes'):
        return vertex
    

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
    return member

    # join_connection = input("Join as a child of an existing family unit? (Y/N)")
    # if join_connection.lower() not in ('y', 'yes'):
    #     return member
    #
    # print(f"Current tree: {manager.getBasicDict()}")
    # if member != manager.root:
    #     relation_id = int(input("What is the ID of the family member to relate to? "))
    #     related_member = manager.getMember(relation_id)
    #     relation_type = input(f"How is {member.getName()} related to {manager.connection_dict[relation_id].getName()}?\n"
    #                           f"Relationship options are child, spouse, and parent. ")
    #     match relation_type:
    #         case "child":
    #             manager.addChild(related_member, member)
    #         case "spouse":
    #             manager.addVertex(member, related_member)
    #         case "parent":
    #             manager.addChild(member, related_member)
    #         case _:
    #             raise ValueError(f"Input must be child, spouse, or parent. Input \"{relation_type}\" is not allowed")
    # logging.info(f"Family member {first} {last} successfully added to the tree.")

def test_manual_create():
    info_filename = os.path.join(os.getcwd(), "taraporevalas_info.json")
    connections_filename = os.path.join(os.getcwd(), "taraporevalas_connections.json")
    if not os.path.exists(info_filename):
        manager = FamilyManager()
    else:
        manager = FamilyManager((info_filename, connections_filename))

    while(True):
        todo = input(f"Type 's' to save tree, 'v' to view tree, 'a' to add to tree, or 'q' to quit ")
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

def test_write_to_file():
    info_filename = os.path.join(os.getcwd(), "test_info.json")
    connections_filename = os.path.join(os.getcwd(), "test_connections.json")
    manager = FamilyManager()
    tom = manager.createFamilyMember("Tom", "Jones", EventDate(1950, 4, 12), EventDate(2015, 3, 16))
    linda = manager.createFamilyMember("Linda", "Adams", EventDate(1950, 4, 12), None)
    suzan = manager.createFamilyMember("suzan", "Jones", EventDate(1980, 4, 12), None)
    gerald = manager.createFamilyMember("gerald", "Jones", EventDate(1983, 5, 12), None)

    tom_linda = manager.addVertex({tom, linda})
    manager.addChildren(tom_linda, {suzan, gerald})

    root: LinkedPerson = manager.root
    iterate_and_print(set(), suzan)

    manager.save(info_filename, connections_filename)

def test_read_from_file():
    info_filename = os.path.join(os.getcwd(), "test_info.json")
    connections_filename = os.path.join(os.getcwd(), "test_connections.json")
    manager = FamilyManager(import_filenames=(info_filename, connections_filename))
    logging.debug(manager.getBasicDict())
    info_filename = os.path.join(os.getcwd(), "test_info_1.json")
    connections_filename = os.path.join(os.getcwd(), "test_connections_1.json")
    manager.save(info_filename, connections_filename)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    #test_write_to_file()
    #test_read_from_file()
    test_manual_create()
