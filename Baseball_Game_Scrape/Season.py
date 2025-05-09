from Half_Inning import Half_Inning
from Game_Info import Game_Info
import logging
import os
import pandas as pd

class Season:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.credit_dicts = {}
        self.game_counts = {}

    def run_season(self):
        for root, dirs, files in os.walk(self.folder_path):
            for file in files:
                logging.info(file[-4:])
                if file[-4:].lower() == ".evn":
                    file_path = os.path.join(root, file)
                    team_season = Team_Season(file_path)
                    team_season.run_games()
                    for team in team_season.game_counts.keys():
                        if team not in self.credit_dicts:
                            self.credit_dicts[team] = {}
                        credit_dict = team_season.credit_dicts[team]
                        for player_id in credit_dict.keys():
                            if player_id not in self.credit_dicts[team].keys():
                                self.credit_dicts[team][player_id] = 0
                            self.credit_dicts[team][player_id] += credit_dict[player_id]

        for team in self.credit_dicts.keys():
            logging.info(f"For team {team}, there have been {self.game_counts[team]} games played.")
            logging.info(f"    credit dict is {self.credit_dicts[team]}")

class Team_Season:

    def __init__(self, filepath):
        full_text = open(filepath, "r").read()
        full_text = full_text.strip("id,")
        self.games = full_text.split("\nid,")
        self.credit_dicts = {}
        self.game_counts = {}

    def run_game(self, game_num: int):
        game_text: str = self.games[game_num]
        game_info = Game_Info(game_text)

        cur_half_inning: Half_Inning = None
        cur_team = -1
        cur_inning = 0

        for play_or_sub in game_info.play_list:
            if play_or_sub.startswith("play,"):
                play = play_or_sub.split(",")
                inning = int(play[1])
                team = int(play[2])
                if cur_team != team or cur_inning != inning:
                    if cur_half_inning is not None:
                        assert cur_half_inning.outs == 3
                        cur_half_inning.end_half_inning()
                    logging.debug(f"\nInning: {inning}, Team: {team}")
                    cur_half_inning = Half_Inning(game_info, inning, team)
                    assert cur_inning == inning or cur_inning == inning-1
                cur_inning = inning
                cur_team = team
            cur_half_inning.parse_event(play_or_sub)

        logging.info(f"Away team scored {sum(game_info.score_dicts[0].values())} runs. Credit summary: {game_info.score_dicts[0]}")
        logging.info(f"Home team scored {sum(game_info.score_dicts[1].values())} runs. Credit summary: {game_info.score_dicts[1]}")
        for team in game_info.teams:
            if team not in self.game_counts.keys():
                self.game_counts[team] = 0
            self.game_counts[team] += 1
        # score_dicts = {}
        # for i in range(2):
        #     score_dicts[game_info.teams[i]] = game_info.score_dicts[i]
        return game_info

    def run_games(self, game_list: [int]=None):
        if game_list is None: game_list = [i for i in range(len(self.games))]
        for game_num in game_list:
            logging.info(f"Running game number {game_num}")
            game_info: Game_Info = self.run_game(game_num)
            for i in range(2):
                team = game_info.teams[i]
                if team not in self.credit_dicts:
                    self.credit_dicts[team] = {}
                credit_dict = game_info.score_dicts[i]
                for player_id in credit_dict.keys():
                    if player_id not in self.credit_dicts[team].keys():
                        self.credit_dicts[team][player_id] = 0
                    self.credit_dicts[team][player_id] += credit_dict[player_id]

        for team in self.credit_dicts.keys():
            logging.info(f"For team {team}, there have been {self.game_counts[team]} games played.")
            logging.info(f"    credit dict is {self.credit_dicts[team]}")


def main():
    logging.basicConfig(level=logging.DEBUG)
    sfg_2024_filepath = r"C:\Users\ktara\Downloads\2024eve\2024SFN.EVN"
    folder_2024 = r"C:\Users\ktara\Downloads\2024eve"
    # test_season = Team_Season(sfg_2024_filepath)
    # test_season.run_games(None)
    #test_season.run_game(7)
    season = Season(folder_2024)
    season.run_season()

if __name__ == "__main__":
    main()