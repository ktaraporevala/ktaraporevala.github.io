from Half_Inning import Half_Inning
from Game_Info import Game_Info
import logging

class Season:

    def __init__(self, filepath):
        full_text = open(filepath, "r").read()
        full_text = full_text.strip("id,")
        self.games = full_text.split("\nid,")

    def run_half_inning(self, game_info, inning: int, is_home: bool):
        half_inning = Half_Inning(game_info, inning, is_home)
        if half_inning.events is not None:
            for event in half_inning.events:
                half_inning.parse_event(event)
            assert half_inning.outs == 3

    def run_game(self, game_num: int):
        game_text: str = self.games[game_num]
        game_info = Game_Info(game_text)

        for inning in range(1, game_info.total_innings+1):
            for is_home in (False, True):
                logging.debug(f"\nInning: {inning}, Home team: {is_home}")
                self.run_half_inning(game_info, inning, is_home)
        logging.info(f"Away team summary: {game_info.away_score_dict}")
        logging.info(f"Home team summary: {game_info.home_score_dict}")



def main():
    logging.basicConfig(level=logging.DEBUG)
    sfg_2024_filepath = r"C:\Users\ktara\Downloads\2024eve\2024SFN.EVN"
    test_season = Season(sfg_2024_filepath)
    test_season.run_game(0)

if __name__ == "__main__":
    main()