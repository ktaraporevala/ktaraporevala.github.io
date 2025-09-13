import time
import os
import pandas as pd
from unidecode import unidecode

from Game import Game
from Info import TeamInfo, LeagueInfo, SeasonInfo
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
        self.clean_up_players()

    def run_team_season(self, file_path, game_list: [int] = None):
        full_text = open(file_path, "r").read()
        full_text = full_text.strip("id,")
        game_texts: [str] = full_text.split("\nid,")
        if game_list is None: game_list = [i for i in range(len(game_texts))]
        for game_num in game_list:
            logging.info(f"Running game number {game_num}")
            self.run_game(game_texts[game_num])

    def run_game(self, game_text: str):
        game = Game(game_text, self.info.player_encountered)
        game.run_game()

        logging.debug(f"Away team scored {sum(game.score_dicts[0].values())} runs. Credit summary: "
                      f"{game.score_dicts[0]}")
        logging.debug(f"Home team scored {sum(game.score_dicts[1].values())} runs. Credit summary: "
                      f"{game.score_dicts[1]}")
        self.assign_game_credit(game)

    def assign_game_credit(self, game_info: Game):
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

    def clean_up_players(self):
        for player_id in self.info.players.keys():
            team_matches = {}
            for team in self.credit_dicts:
                if player_id in self.credit_dicts[team]:
                    team_matches[team] = self.credit_dicts[team][player_id]

            if len(team_matches) > 1:
                matches = sorted(team_matches.keys(), key=lambda x: -team_matches[x])
                main_team = matches[0]
                for team in matches:
                    if team == main_team:
                        self.credit_dicts[team][player_id] = sum(team_matches.values())
                    else:
                        self.credit_dicts[team].pop(player_id)

    def get_rg_csv(self, traditional_stats=None, include_extras=False, delimeter=','):
        rg_csv = f"Team{delimeter}Player{delimeter}Runs Generated (new)"
        if traditional_stats is not None:
            traditional_stats['Player'] = traditional_stats['Player'].str.replace('[*|#]', '', regex=True)
            traditional_stats["RG"] = traditional_stats.R * 0.5 + traditional_stats.RBI * 0.5
            rg_csv += f"{delimeter}Runs Generated (old)"
        rg_csv += '\n'
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
                    rg_csv += f"{team_name}{delimeter}{name}{delimeter}{credit}"
                    if traditional_stats is not None:
                        try:
                            rg_trad = float(traditional_stats[traditional_stats.retro_id == player_id].RG.values[0])
                            rg_csv += f"{delimeter}{rg_trad}"
                        except IndexError as e:
                            logging.error(f"Could not read player {name}'s traditional runs generated")
                            logging.error(e)
                    rg_csv += '\n'
            rg_csv += f"{delimeter}{team_name} total{delimeter}{team_credit}\n"
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

    stats_df = get_season_stats(season.info)
    time.sleep(0.1)

    print(season.get_rg_readable())
    print()
    # print(season.get_rg_csv(traditional_stats=None, include_extras=False))
    print(season.get_rg_csv(traditional_stats=stats_df, include_extras=False))

def get_season_stats(info: SeasonInfo):

    player_id_map_path = r"C:\Users\ktara\Downloads\SFBB Player ID Map - PLAYERIDMAP.csv"
    id_map_df = pd.read_csv(player_id_map_path)
    player_id_map_path2 = r"C:\Users\ktara\Downloads\KeyCrossReference.csv"
    id_map_df2 = pd.read_csv(player_id_map_path2)

    stats_path = r"C:\Users\ktara\Downloads\2024_mlb_batter_stats.csv"
    stats_df = pd.read_csv(stats_path)
    stats_df["Player"] = stats_df["Player"].str.replace("[*|#]", "", regex=True)
    for i, player in enumerate(stats_df.Player):
        stats_df.loc[i, ["Player"]] = unidecode(player)

    # retro_ids = {'chapm001': "Matt Chapman"}

    stats_df["retro_id"] = ""
    name_count = 0
    match1_count = 0
    match2_count = 0
    nomatch_count = 0
    for retro_id, name in info.players.items():
        name_match = stats_df[stats_df.Player == name]
        bref_id_match_1 = id_map_df[id_map_df.RETROID == retro_id].BREFID.values
        bref_id_match_2 = id_map_df2[id_map_df2.PlayerKey == retro_id].BRKey.values
        if len(name_match) > 0:
            stats_df.loc[(stats_df['Player'] == name), ["retro_id"]] = retro_id
            name_count += 1
        elif len(bref_id_match_1) > 0:
            stats_df.loc[(stats_df['Player-additional'] == bref_id_match_1[0]), ["retro_id"]] = retro_id
            match1_count += 1
        elif len(bref_id_match_2) > 0:
            stats_df.loc[(stats_df['Player-additional'] == bref_id_match_2[0]), ["retro_id"]] = retro_id
            match2_count += 1
        else:
            logging.warning(f"Player {name} with retro id {retro_id} is unable to find a match")
            nomatch_count += 1

    logging.info(f"Was able to match {name_count} players by name, {match1_count} with first spreadsheet,"
                 f"{match2_count} with second spreadsheet, and {nomatch_count} were unable to be matched")

    return stats_df

def run_game_debug(folder, file_name, game_num):
    year = int(file_name[:4])
    logging.basicConfig(level=logging.DEBUG)
    season = Season(folder, year)
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file == file_name:
                season.run_team_season(os.path.join(root, file), [game_num])


def main():
    folder = r"C:\Users\ktara\Downloads\Retrosheet Event Files"
    years = [2024, 2023, 2022, 2021, 2020]

    # run_game_debug(folder, file_name="2023BAL.EVA", game_num=66)

    for year in years:
        run_season(folder, year)

if __name__ == "__main__":
    main()
