import logging


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
