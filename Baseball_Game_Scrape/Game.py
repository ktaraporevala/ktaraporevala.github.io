import logging
import re

from Play import Play
from Play import PlayType
from Player import Player
from Info import SeasonInfo


class Game:

    def __init__(self, game_text: str, new_player_fn):
        self.outs = 0
        self.on_base: [str] = [""]*4
        self.inning = 1
        self.new_player_fn = new_player_fn

        self.teams = [None, None]
        self.date = None
        self.game_type = None
        self.first_up = 0  # 0 or 1 for home or away (usually 0 but not always)

        self.play_list = []
        self.lineups: [[Player]] = [[None] * 10, [None] * 10]
        self.player_dict = {}

        self.score_dicts = [{}, {}]

        game_text_list = game_text.split("\n")
        self.read_info(game_text_list)
        self.read_lineup(game_text_list)
        self.section_innings(game_text_list)

        self.team_at_bat = self.first_up

    def run_game(self):
        play_ball = True  # Do certain things at start of game

        for event in self.play_list:
            if event.startswith(PlayType.PLAY):
                play = event.split(",")
                inning = int(play[1])
                team = int(play[2])
                assert self.team_at_bat == team
                assert self.inning == inning
                if play_ball:
                    logging.debug(f"\nInning: {inning}, Team: {team}")
                    self.inning = inning
                    self.team_at_bat = team
                    play_ball = False
            if event.startswith(PlayType.COMMENT) and play_ball:
                continue
            self.parse_event(event)
            if self.outs == 3:
                self.end_half_inning()
                self.inning = self.inning + (self.team_at_bat + self.first_up) % 2
                self.team_at_bat = (self.team_at_bat + 1) % 2
                logging.debug(f"\nInning: {self.inning}, Team: {self.team_at_bat}")

    # Get home team, away team, date, game type
    def read_info(self, full_text_list: [str]):
        info_list = [text.split(",")[1:] for text in full_text_list if text.startswith(PlayType.INFO)]
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
        if "htbf" in info_dict.keys():
            bat_first = info_dict["htbf"]
            self.first_up = 1 if bat_first else 0

        logging.debug(f"Away team is {self.teams[0]}. Home team is {self.teams[1]}")

    def read_player(self, player_info: [str]) -> Player:
        id = player_info[1]
        name = player_info[2].strip('\"')
        team = int(player_info[3])
        order_spot = int(player_info[4])
        position = int(player_info[5])  # TODO make work with shohei (2 pos listed)
        player = Player(id, name, position, team, order_spot)
        self.player_dict[id] = player
        self.new_player_fn(player_id=id, player_name=name)
        return player

    def read_lineup(self, full_text_list: [str]):
        player_list = [text.split(",") for text in full_text_list if text.startswith(PlayType.STARTING_LINEUP)]

        for player_info in player_list:
            player = self.read_player(player_info)
            self.lineups[player.team][player.order_spot] = player

        logging.debug(f"Away lineup is {self.lineups[0]}")
        logging.debug(f"Home lineup is {self.lineups[1]}")

    def section_innings(self, full_text_list: [str]):
        self.play_list = [text for text in full_text_list if text.startswith(PlayType.PLAY)
                          or text.startswith(PlayType.SUBSTITUTION)
                          or text.startswith(PlayType.RUNNER_ADJUSTMENT)
                          or text.startswith(PlayType.COMMENT)]

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

    def player_scored(self, player_id: str):
        logging.debug(f"{player_id} scored")
        player: Player = self.get_player(player_id)
        assert sum(player.base_dict.values()) == 4
        score_dict = self.score_dicts[self.team_at_bat]
        for credit_id, credit in player.base_dict.items():
            if credit_id not in score_dict.keys():
                score_dict[credit_id] = 0
            score_dict[credit_id] += credit / 4
            logging.debug(f"Player {credit_id} gets credit for {credit / 4} runs")
        player.clear_player()

    def in_lineup(self, player_id, team):
        for player in self.lineups[team]:
            if player is not None and player.id == player_id:
                return True
        return False

    def player_out(self, base: int):
        player: Player = self.get_player(self.on_base[base])
        logging.debug(f"{player.name} is out")
        self.outs += 1
        self.on_base[base] = ""
        player.clear_player()

    def end_half_inning(self):
        for player_id in self.on_base:
            if player_id != "":
                self.get_player(player_id).clear_player()
        self.outs = 0
        self.on_base = [""]*4

    def assign_credit(self, play: Play):
        error_id = self.teams[(self.team_at_bat + 1) % 2]
        for cur_base in range(4):
            player_id = self.on_base[cur_base]
            if player_id != "":
                player = self.get_player(player_id)
                assert player.get_current_base() == cur_base
                bases_advanced = play.advancements[cur_base] - cur_base
                if bases_advanced <= 0:  # runner hasn't moved or is out
                    continue
                player.advance(bases_advanced)
                if cur_base == 0:
                    hitter_credit_floor = min(bases_advanced, play.hitter_max_credit//1)
                    error_credit = min(bases_advanced-hitter_credit_floor, play.error_credits[cur_base])
                    hitter_credit = bases_advanced - error_credit
                    if play.fielders_choice_credit is not None:  # runner out gets credit for advancing hitter to
                        # first on FC
                        fc_player_id = self.on_base[play.fielders_choice_credit]
                        hitter_credit -= 1
                        assert hitter_credit >= 0
                        player.credit_player(fc_player_id, 1)
                    player.credit_player(error_id, error_credit)
                    player.credit_player(player_id, hitter_credit)
                else:
                    hitter_credit_floor = min(bases_advanced, play.hitter_max_credit//1)
                    error_credit = min(bases_advanced - hitter_credit_floor, play.error_credits[cur_base])
                    hitter_credit = min(bases_advanced - error_credit, play.hitter_max_credit)
                    runner_credit = bases_advanced - error_credit - hitter_credit
                    player.credit_player(error_id, error_credit)
                    player.credit_player(play.hitter_id, hitter_credit)
                    player.credit_player(player_id, runner_credit)

    def advance_runners(self, play: Play):
        new_bases = [""]*4
        scored = []
        for cur_base in range(4):
            end_base = play.advancements[cur_base]
            player_id = self.on_base[cur_base]
            if player_id != "":
                if end_base == 4:
                    scored += [self.on_base[cur_base]]
                elif end_base == -1:
                    self.player_out(cur_base)
                else:
                    assert new_bases[end_base] == ""
                    new_bases[end_base] = self.on_base[cur_base]

        # Check scores
        for player_id in scored:
            assert self.get_player(player_id).current_base == 4
            self.player_scored(player_id)
        self.on_base = new_bases

    @staticmethod
    def clean_event_text(text: str):
        for item_to_remove in PlayType.REMOVE_FROM_PLAY:
            text = text.replace(item_to_remove, "")
        return text

    def parse_event(self, event_text: str):
        logging.debug(f"Reading: {event_text}")
        event_text = Game.clean_event_text(event_text)
        event_list = event_text.split(",")
        if event_list[0] == PlayType.PLAY:
            play: Play = Play(event_list)
            if self.on_base[0] == "":
                self.on_base[0] = play.hitter_id
            else:
                assert self.on_base[0] == play.hitter_id
            assert self.in_lineup(player_id=play.hitter_id, team=self.team_at_bat)
            play.run_play()
            self.assign_credit(play)
            self.advance_runners(play)
        elif event_list[0] == PlayType.SUBSTITUTION:
            player = self.read_player(event_list)
            replaced_player_id = self.replace_player(player)
            for i in range(len(self.on_base)):
                if self.on_base[i] == replaced_player_id:
                    self.on_base[i] = player.id
        elif event_list[0] == PlayType.RUNNER_ADJUSTMENT:
            player_id = event_list[1]
            base = int(event_list[2])
            self.on_base[base] = player_id
            player = self.get_player(player_id)
            player.advance(base)
            player.credit_player(SeasonInfo.MANFRED_ID, base)
