import logging
from Player import Player


class LeagueInfo:
    AMERICAN = 'A'
    AMERICAN1 = 'AL'
    NATIONAL = 'N'
    NATIONAL1 = 'NL'
    FEDERAL = 'F'
    NEGRO = 'R'
    LEAGUES = (AMERICAN, AMERICAN1, NATIONAL, NATIONAL1, FEDERAL, NEGRO)


class TeamInfo:

    def __init__(self, id: str, league: str, city: str, name: str):
        assert league in LeagueInfo.LEAGUES
        self.id = id
        self.league = league
        self.city = city
        self.name = name

    @property
    def full_name(self):
        return f"{self.city} {self.name}"

    def __str__(self):
        return self.full_name


class SeasonInfo:
    MANFRED_ID = "manfredrob"

    def __init__(self):
        self.players: {str: str} = {}  # to give credit for ghost runner
        self.teams: {str: TeamInfo} = {}

    def lookup_name(self, id_str):  # Note: may be player, team, or Manfred. Returns is_player
        if id_str in self.players:
            return self.players[id_str], True
        elif id_str in self.teams:
            return self.teams[id_str].name, False
        elif id_str == SeasonInfo.MANFRED_ID:
            return "Rob Manfred", False
        else:
            raise RuntimeError(f"ID {id_str} is not recognized")

    def player_encountered(self, player_id, player_name):
        if player_id in self.players.keys():
            if player_name != self.players[player_id]:
                old_name = self.players[player_id]
                if len(player_name) > len(old_name):  # If conflict, go with longer name
                    self.players[player_id] = player_name
                logging.warning(f"For player id {player_id}, name {player_name} doesn't match existing name {old_name}."
                                f" Continuing forward with {self.players[player_id]}")
        else:
            self.players[player_id] = player_name

    def read_team_names(self, team_file_path: str):
        full_text = open(team_file_path, "r").read().strip()
        logging.debug("Reading teams info")
        for line in full_text.split('\n'):
            logging.debug(f"Team info: {line}")
            team_info = line.split(',')
            team_id = team_info[0]
            team_league = team_info[1]
            team_city = team_info[2]
            team_name = team_info[3]
            assert team_id not in self.teams.keys()
            self.teams[team_id] = TeamInfo(team_id, team_league, team_city, team_name)


class GameInfo:

    def __init__(self, full_text: str, season_info: SeasonInfo):
        full_text = full_text.split("\n")
        self.season_info = season_info

        self.teams = [None, None]
        self.date = None
        self.game_type = None
        self.first_up = None  # 0 or 1 for home or away (usually 0 but not always)

        self.play_list = []
        self.total_innings = -1

        self.lineups: [[Player]] = [[None] * 10, [None] * 10]
        self.player_dict = {}

        self.score_dicts = [{}, {}]

        self.read_info(full_text)
        self.read_lineup(full_text)
        self.section_innings(full_text)

    # Get home team, away team, date, game type
    def read_info(self, full_text: [str]):
        info_list = [text.split(",")[1:] for text in full_text if text.startswith("info,")]
        info_dict = {row[0]: row[1] for row in info_list}

        self.teams[0] = info_dict["visteam"]
        self.teams[1] = info_dict["hometeam"]
        if "gametype" in info_dict.keys():
            self.game_type = info_dict["gametype"]
        else:
            self.game_type = "regular"
        self.date = info_dict["date"]
        if info_dict["number"] != 0:
            self.date += f"_{info_dict['number']}"

        logging.debug(f"Away team is {self.teams[0]}. Home team is {self.teams[1]}")

    def read_player(self, player_info: [str]) -> Player:
        id = player_info[1]
        name = player_info[2].strip('\"')
        team = int(player_info[3])
        order_spot = int(player_info[4])
        position = int(player_info[5])  # TODO make work with shohei (2 pos listed)
        player = Player(id, name, position, team, order_spot)
        self.player_dict[id] = player
        self.season_info.player_encountered(player_id=id, player_name=name)
        return player

    def read_lineup(self, full_text: str):
        player_list = [text.split(",") for text in full_text if text.startswith("start,")]

        for player_info in player_list:
            player = self.read_player(player_info)
            self.lineups[player.team][player.order_spot] = player

        logging.debug(f"Away lineup is {self.lineups[0]}")
        logging.debug(f"Home lineup is {self.lineups[1]}")

    def section_innings(self, full_text):
        self.play_list = [text for text in full_text if text.startswith("play,")
                          or text.startswith("sub,")
                          or text.startswith("radj,")
                          or text.startswith("com,")]

    def get_player(self, player_id: str) -> Player:
        return self.player_dict[player_id]

    def replace_player(self, new_player: Player):
        team = new_player.team
        slot = new_player.order_spot
        old_player: Player = self.lineups[team][slot]
        self.lineups[team][slot] = new_player
        new_player.base_dict = old_player.get_base_dict()
        new_player.current_base = old_player.current_base

        logging.debug(f"Player {old_player.name} replaced by {new_player.name} in batting order spot {slot}")
        return old_player.id

    def player_scored(self, credit_dict: dict, team: int):
        assert sum(credit_dict.values()) == 4
        score_dict = self.score_dicts[team]
        for player in credit_dict.keys():
            if player not in score_dict.keys():
                score_dict[player] = 0
            score_dict[player] += credit_dict[player] / 4
            logging.debug(f"Player {player} gets credit for {credit_dict[player] / 4} runs")

    def in_lineup(self, player_id, team):
        for player in self.lineups[team]:
            if player is not None and player.id == player_id:
                return True
        return False

