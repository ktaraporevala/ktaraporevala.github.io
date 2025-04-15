from Half_Inning import Half_Inning
from Game_Info import Game_Info
import logging

class Game:

    MAX_INNINGS = 30

    def __init__(self, filepath):
        f = open(filepath, "r").read()
        self.game_info = Game_Info(f)

    def run_half_inning(self, inning: int, is_home: bool):
        half_inning = Half_Inning(self.game_info, inning, is_home)
        if half_inning.events is not None:
            for event in half_inning.events:
                half_inning.parse_event(event)

            assert half_inning.outs == 3
        a = half_inning.on_base
        return

    def run_game(self):
        for inning in range(1, self.game_info.total_innings+1):
            for is_home in (False, True):
                logging.debug(f"\nInning: {inning}, Home team: {is_home}")
                self.run_half_inning(inning, is_home)
        logging.info(f"Away team summary: {self.game_info.away_score_dict}")
        logging.info(f"Home team summary: {self.game_info.home_score_dict}")



def main():
    logging.basicConfig(level=logging.DEBUG)
    test_game = Game(r"C:\Users\ktara\Downloads\test_game.txt")
    # test_game = Game(r"C:\Users\ktara\Downloads\test_game_1.txt")
    # test_game = Game(r"C:\Users\ktara\Downloads\test_game_2.txt")
    # test_game = Game(r"C:\Users\ktara\Downloads\test_game_3.txt")
    # test_game = Game(r"C:\Users\ktara\Downloads\test_game_4.txt")
    test_game.run_game()

if __name__ == "__main__":
    main()