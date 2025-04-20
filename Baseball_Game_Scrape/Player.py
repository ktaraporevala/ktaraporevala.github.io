import logging

BASE_DICT = {0: "nowhere", 1: "first", 2: "second", 3: "third", 4: "home"}
POSITIONS = {}

class Player:

    def __init__(self, player_id: str, player_name: str, position: int, team: int, order_spot: int):
        self.id = player_id
        self.name = player_name
        self.position = position
        self.team = team
        self.order_spot = order_spot
        self.base_dict = {}
        self.current_base = 0
        logging.debug(f"Player {player_name} created (id: {self.id})")

    def clear_player(self):
        self.base_dict = {}
        self.current_base = 0

    def batter_event(self, bases, bases_credit_max):
        assert self.current_base == 0
        self.current_base = bases
        bases_credit = min(bases, bases_credit_max)
        self.base_dict[self.id] = bases_credit
        if bases_credit < bases:
            self.base_dict[None] = bases - bases_credit
        logging.debug(f"Player {self.name} batted and is now on {BASE_DICT[bases]} with {bases_credit} bases of credit")

    # TODO rework this function
    def get_base_dict(self) -> {}:
        return self.base_dict

    def runner_event(self, end_base, hitter_id, hitter_credit_max, is_error):
        bases_advanced = end_base - self.current_base
        if is_error:
            hitter_credit = 0
            runner_credit = 0  # TODO decide if this is max(0, bases_advanced - num_errors)
            error_credit = bases_advanced
        else:
            if bases_advanced <= hitter_credit_max:
                hitter_credit = bases_advanced
            else:
                hitter_credit = hitter_credit_max
            runner_credit = bases_advanced - hitter_credit
            error_credit = None

            assert runner_credit >= 0

        for credit_pair in ((hitter_id, hitter_credit), (self.id, runner_credit), (None, error_credit)):
            id, credit = credit_pair
            if credit is None:
                continue
            if id not in self.base_dict.keys():
                self.base_dict[id] = 0
            self.base_dict[id] += credit

        self.current_base = end_base
        logging.debug(f"Runner {self.name} advanced to {BASE_DICT[end_base]} with {runner_credit} of credit for himself and {hitter_credit} of credit for {hitter_id}")