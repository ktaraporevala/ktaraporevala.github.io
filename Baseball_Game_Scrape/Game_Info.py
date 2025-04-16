import logging
from Player import Player

class Game_Info:

    def __init__(self, full_text):
        full_text = full_text.split("\n")

        self.away_team = None
        self.home_team = None
        self.date = None
        self.game_type = None
        self.first_up = None  # 0 or 1 for home or away (usually 0 but not always)

        self.plays = [[],[]]
        self.total_innings = -1

        self.lineups = [[None] * 9, [None] * 9]

        self.away_score_dict = {}
        self.home_score_dict = {}

        self.read_info(full_text)
        self.read_lineup(full_text)
        self.section_innings(full_text)

    # Get home team, away team, date, game type
    def read_info(self, full_text: [str]):
        info_list = [text.split(",")[1:] for text in full_text if text.startswith("info,")]
        info_dict = {row[0]: row[1] for row in info_list}

        self.away_team = info_dict["visteam"]
        self.home_team = info_dict["hometeam"]
        self.game_type = info_dict["gametype"]
        self.date = info_dict["date"]
        if info_dict["number"] != 0:
            self.date += f"_{info_dict['number']}"

        logging.debug(f"Away team is {self.away_team}. Home team is {self.home_team}")

    def read_lineup(self, full_text: str):  # TODO make compatible with multi-word names
        player_list = [text.split(",")[1:] for text in full_text if text.startswith("start,")]

        for player_info in player_list:
            id = player_info[0]
            name = player_info[1]
            team = int(player_info[2])
            order_spot = int(player_info[3])
            position = int(player_info[4])     #TODO make work with shohei (2 pos listed)
            if order_spot > 0:  # ignore pitcher if there is a DH
                player = Player(id, name, position)
                self.lineups[team][order_spot - 1] = player

        logging.debug(f"Away lineup is {self.lineups[0]}")
        logging.debug(f"Home lineup is {self.lineups[1]}")

    def section_innings(self, full_text):
        play_list = [text for text in full_text if text.startswith("play,") or text.startswith("sub,")]

        current_inning = 0
        current_team = -1
        play_ball = True  # first pitch
        for play_or_sub in play_list:
            if play_or_sub.startswith("play,"):
                play = play_or_sub.split(",")
                inning = int(play[1])
                team = int(play[2])
                if play_ball:
                    self.first_up = team
                    play_ball = False
                if current_team != team or current_inning != inning:
                    self.plays[team].append([])
                    assert current_inning == inning or current_inning == inning-1
                current_inning = inning
                current_team = team
            else:
                pass  # TODO parse for team, adjust inning if start of next
            logging.info(play_or_sub)
            self.plays[current_team][current_inning-1] += [play_or_sub]
            pass

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
