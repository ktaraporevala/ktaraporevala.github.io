import logging


class Player:
    BASE_DICT = {0: "batting", 1: "first", 2: "second", 3: "third", 4: "home"}

    def __init__(self, player_id: str, player_name: str, position: int, team: int, order_spot: int):
        self.id = player_id
        self.name = player_name.strip("\"")
        self.position = position
        self.team = team
        self.order_spot = order_spot
        self.base_dict = {}
        self.current_base = 0
        logging.debug(f"Player {self.name} created (id: {self.id})")

    def __str__(self):
        return f"{self.name} - team: {self.team}, id: {self.id}"

    def clear_player(self):
        self.base_dict = {}
        self.current_base = 0

    # TODO rework this function
    def get_base_dict(self) -> {}:
        return self.base_dict

    def get_current_base(self):
        return self.current_base

    def advance(self, num_bases):
        logging.debug(f"Player {self.name} is now on {Player.BASE_DICT[self.current_base + num_bases]} "
                      f"from {Player.BASE_DICT[self.current_base]}")
        self.current_base += num_bases

    def credit_player(self, player_id: str, credit):
        if credit != 0:
            if player_id not in self.base_dict.keys():
                self.base_dict[player_id] = 0
            self.base_dict[player_id] += credit
            logging.debug(f"For {self.name}'s advancement, {player_id} gets {credit} bases of credit")
