import time
import os
import pandas as pd

from Half_Inning import Half_Inning
from Info import GameInfo, TeamInfo, LeagueInfo, SeasonInfo
import logging

class Season:
    def __init__(self, folder_path: str, year: int):
        self.folder_path = folder_path
        self.year = year
        self.game_counts: {str: int} = {}
        self.info = SeasonInfo()
        self.read_team_names()
        self.credit_dicts: [dict] = {}
        for team_id in self.info.teams:
            self.credit_dicts[team_id] = {}

    def read_team_names(self):
        target_file = f"TEAM{self.year}"
        for root, dirs, files in os.walk(self.folder_path):
            for file in files:
                if file == target_file:
                    self.info.read_team_names(os.path.join(root, file))
                    return

    def run_season(self):
        for root, dirs, files in os.walk(self.folder_path):
            for file in files:
                extension = file[-4:].lower()
                year = file[:4]
                if extension in [f".ev{lg.lower()}" for lg in LeagueInfo.LEAGUES] and int(year) == self.year:
                    logging.info(f"Reading file {file}")
                    file_path = os.path.join(root, file)
                    self.run_team_season(file_path)


    def run_team_season(self, file_path, game_list: [int] = None):
        full_text = open(file_path, "r").read()
        full_text = full_text.strip("id,")
        game_texts: [str] = full_text.split("\nid,")
        if game_list is None: game_list = [i for i in range(len(game_texts))]
        for game_num in game_list:
            logging.info(f"Running game number {game_num}")
            self.run_game(game_texts[game_num])

    def run_game(self, game_text: str):
        game_info = GameInfo(game_text, self.info)

        cur_half_inning: Half_Inning = None
        cur_team = 0
        cur_inning = 1

        for play_or_sub in game_info.play_list:
            if play_or_sub.startswith("play,"):
                play = play_or_sub.split(",")
                inning = int(play[1])
                team = int(play[2])
                assert cur_team == team
                assert cur_inning == inning
                if cur_half_inning is None:
                    logging.debug(f"\nInning: {inning}, Team: {team}")
                    cur_inning = inning
                    cur_team = team
                    cur_half_inning = Half_Inning(game_info, inning, team)
            if play_or_sub.startswith("com,") and cur_half_inning is None:
                continue
            cur_half_inning.parse_event(play_or_sub)
            if cur_half_inning.get_outs() == 3:
                cur_half_inning.end_half_inning()
                cur_inning = cur_inning + cur_team
                cur_team = (cur_team + 1) % 2
                logging.debug(f"\nInning: {cur_inning}, Team: {cur_team}")
                cur_half_inning = Half_Inning(game_info, cur_inning, cur_team)
                # TODO fix assumption that home team always bats second

        logging.debug(f"Away team scored {sum(game_info.score_dicts[0].values())} runs. Credit summary: "
                      f"{game_info.score_dicts[0]}")
        logging.debug(f"Home team scored {sum(game_info.score_dicts[1].values())} runs. Credit summary: "
                      f"{game_info.score_dicts[1]}")
        self.assign_game_credit(game_info)

    def assign_game_credit(self, game_info: GameInfo):
        for i in range(2):
            team = game_info.teams[i]

            if team not in self.game_counts.keys():
                self.game_counts[team] = 0
            self.game_counts[team] += 1

            credit_dict = game_info.score_dicts[i]
            for player_id in credit_dict.keys():
                if player_id not in self.credit_dicts[team].keys():
                    self.credit_dicts[team][player_id] = 0
                self.credit_dicts[team][player_id] += credit_dict[player_id]

    def get_rg_csv(self, include_extras=False, delimeter=','):
        rg_csv = "Team,Player,Runs Generated\n"
        for team_id in self.credit_dicts.keys():
            credit_dict = self.credit_dicts[team_id]
            team_name = self.info.lookup_name(team_id)[0]
            team_credit = 0
            players = credit_dict.keys()
            players_sorted = sorted(players, key=lambda player_id: credit_dict[player_id], reverse=True)
            for player_id in players_sorted:
                credit = credit_dict[player_id]
                name, is_player = self.info.lookup_name(player_id)
                if include_extras or is_player:
                    team_credit += credit
                    rg_csv += f"{team_name},{name},{credit}\n"
            rg_csv += f",{team_name} total,{team_credit}\n"
        return rg_csv

    def get_rg_readable(self, include_extras=False):
        rg_readable = ""
        for team_id, credit_dict in self.credit_dicts.items():
            team_info: TeamInfo = self.info.teams[team_id]
            team_credit = 0
            credit_dict_str = ""
            players = credit_dict.keys()
            players_sorted = sorted(players, key=lambda player_id: credit_dict[player_id], reverse=True)
            for player_id in players_sorted:
                credit = credit_dict[player_id]
                name, is_player = self.info.lookup_name(player_id)
                if include_extras or is_player:
                    team_credit += credit
                    credit_dict_str += f"{name}: {credit},"
            rg_readable += f"For team {team_info.full_name}, there have been {self.game_counts[team_id]} games played.\n"
            rg_readable += f"    Total team runs generated: {team_credit}. By player - {credit_dict_str[:-1]}\n"
        return rg_readable

def run_season(folder, year):
    logging.basicConfig(level=logging.INFO)
    season = Season(folder, year)
    season.run_season()
    time.sleep(0.1)
    print(season.get_rg_readable())
    print()
    print(season.get_rg_csv(include_extras=True))

def run_game_debug(folder, year, file_name, game_num):
    logging.basicConfig(level=logging.DEBUG)
    season = Season(folder, year)
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file == file_name:
                season.run_team_season(os.path.join(root, file), [game_num])

def main():
    folder = r"C:\Users\ktara\Downloads\Retrosheet Event Files"
    year = 2024

    # run_game_debug(folder, year, file_name="2010FLO.EVN", game_num=15)

    run_season(folder, year)

if __name__ == "__main__":
    main()
