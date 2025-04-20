from Half_Inning import Half_Inning
from Game_Info import Game_Info
import logging

class Season:

    def __init__(self, filepath):
        full_text = open(filepath, "r").read()
        full_text = full_text.strip("id,")
        self.games = full_text.split("\nid,")
        self.credit_dict = {}

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
                        #assert cur_half_inning.outs == 3
                        cur_half_inning.end_half_inning()
                    logging.debug(f"\nInning: {inning}, Team: {team}")
                    cur_half_inning = Half_Inning(game_info, inning, team)
                    assert cur_inning == inning or cur_inning == inning-1
                cur_inning = inning
                cur_team = team
            cur_half_inning.parse_event(play_or_sub)

        logging.info(f"Away team scored {sum(game_info.score_dicts[0].values())} runs. Credit summary: {game_info.score_dicts[0]}")
        logging.info(f"Home team scored {sum(game_info.score_dicts[1].values())} runs. Credit summary: {game_info.score_dicts[1]}")
        # score_dicts = {}
        # for i in range(2):
        #     score_dicts[game_info.teams[i]] = game_info.score_dicts[i]
        return game_info.score_dicts

    def run_games(self, game_list: [int]):
        for game_num in game_list:
            credit_dicts = self.run_game(game_num)
            for credit_dict in credit_dicts:
                for player in credit_dict.keys():
                    if player not in self.credit_dict.keys():
                        self.credit_dict[player] = 0
                    self.credit_dict[player] = credit_dict[player]

        logging.info(f"After games {game_list}, credit dict is {self.credit_dict}")


def main():
    logging.basicConfig(level=logging.DEBUG)
    sfg_2024_filepath = r"C:\Users\ktara\Downloads\2024eve\2024SFN.EVN"
    test_season = Season(sfg_2024_filepath)
    test_season.run_games([i for i in range(3)])

if __name__ == "__main__":
    main()