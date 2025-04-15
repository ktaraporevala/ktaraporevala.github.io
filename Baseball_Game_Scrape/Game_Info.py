import logging
from Player import Player

class Game_Info:
    MAX_INNINGS = 30

    def __init__(self, pbp_full_text):
        self.box = None
        self.pbp: list = pbp_full_text.split('\n\n')

        self.away_team = None
        self.home_team = None
        self.home_inning_indices = [None] * Game_Info.MAX_INNINGS
        self.away_inning_indices = [None] * Game_Info.MAX_INNINGS
        self.total_innings = -1

        self.away_lineup = [None] * 9
        self.home_lineup = [None] * 9

        self.away_score_dict = {}
        self.home_score_dict = {}

        self.read_basic_info()

    def read_basic_info(self):
        lineup_index = None
        for i in range(len(self.pbp)):
            item = self.pbp[i]
            rows = item.split("\n")
            if "Starting Lineup" in item:
                lineup_index = i + 1
            elif lineup_index == i:
                teams_raw = rows[0].split("  ")
                self.parse_teams(teams_raw)
                self.parse_lineup(rows)
            else:
                first_row = rows[0].split(" ")
                if len(first_row) > 1:
                    try_inning_num = first_row[1]
                    inning_str = try_inning_num[0]
                    if inning_str.isnumeric():
                        inning: int = int(inning_str)
                        team = first_row[0].lower()
                        if team in self.home_team.lower():
                            self.home_inning_indices[inning - 1] = i
                        elif team in self.away_team.lower():
                            self.away_inning_indices[inning - 1] = i
                        self.total_innings = max(self.total_innings, inning)

    def parse_teams(self, teams_text: str):
        teams = [team.strip() for team in teams_text if team.strip() != ""]
        self.away_team = teams[0]
        self.home_team = teams[1]
        logging.debug(f"Away team is {self.away_team}. Home team is {self.home_team}")

    def parse_lineup(self, lineup_text: list):  # TODO make compatible with multi-word names
        for i in range(len(lineup_text)):
            row_raw: str = lineup_text[i].split(" ")
            row = [row.strip() for row in row_raw if row.strip() != ""]
            if row[0][0].isnumeric():
                spot = int(row[0][0])
                self.away_lineup[spot - 1] = Player.format_player_name(row[1])
                self.home_lineup[spot - 1] = Player.format_player_name(row[3])
        logging.debug(f"Away lineup is {self.away_lineup}")
        logging.debug(f"Home lineup is {self.home_lineup}")

    def replace_player(self, old_player: str, new_player: str, is_home: bool):
        lineup = self.home_lineup if is_home else self.away_lineup
        lineup_spot = lineup.index(old_player)
        logging.debug(f"Player {old_player} replaced by {new_player} in batting order spot {lineup_spot+1}")
        lineup[lineup_spot] = new_player
        return

    def player_scored_fn(self, credit_dict: dict, is_home: bool):
        score_dict = self.home_score_dict if is_home else self.away_score_dict
        for player in credit_dict.keys():
            if player not in score_dict.keys():
                score_dict[player] = 0
            score_dict[player] += credit_dict[player] / 4
            logging.info(f"Player {player} gets credit for {credit_dict[player] / 4} runs")
            assert sum(credit_dict.values()) == 4
