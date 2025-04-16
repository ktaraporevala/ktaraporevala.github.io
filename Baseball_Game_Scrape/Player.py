import logging

BASE_DICT = {0: "nowhere", 1: "first", 2: "second", 3: "third", 4: "home"}
POSITIONS = {}

class Player:

    def __init__(self, player_id: str, player_name: str, position: int):
        self.id = player_id
        self.name = player_name
        self.position = position
        self.base_dict = {}
        self.current_base = None
        logging.debug(f"Player {player_name} created")

    def player_out(self):
        self.base_dict = {}
        self.current_base = None

    def batter_event(self, bases, bases_credit_max):
        self.current_base = bases
        bases_credit = min(bases, bases_credit_max)
        self.base_dict[self.name] = bases_credit
        logging.debug(f"Player {self.name} batted and is now on {BASE_DICT[bases]} with {bases_credit} bases of credit")

    # TODO rework this function
    def player_replaced(self, new_name):
        self.name = new_name
        self.base_dict[new_name] = 0

    def runner_event(self, end_base, hitter_name, hitter_credit_max, is_hit, is_error):
        bases_advanced = end_base - self.current_base
        if is_error:
            hitter_credit = 0
            runner_credit = 0
            error_credit = bases_advanced
        else:
            if bases_advanced <= hitter_credit_max:
                hitter_credit = bases_advanced
            elif is_hit:
                hitter_credit = hitter_credit_max + 0.5
            else:
                hitter_credit = hitter_credit_max
            runner_credit = bases_advanced - hitter_credit
            error_credit = None

            assert runner_credit >= 0

        if hitter_credit > 0:
            self.base_dict[hitter_name] = hitter_credit
        self.base_dict[self.name] += runner_credit
        if error_credit is not None:
            if None not in self.base_dict.keys():
                self.base_dict[None] = 0
            self.base_dict[None] += error_credit

        self.current_base = end_base
        logging.debug(f"Runner {self.name} advanced to {BASE_DICT[end_base]} with {runner_credit} of credit for himself and {hitter_credit} of credit for {hitter_name}")