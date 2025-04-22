import logging
import re

from Play import Play
from Player import Player
from Game_Info import Game_Info


class Half_Inning:

    def __init__(self, game_info: Game_Info, inning: int, team: int):
        self.outs = 0
        self.on_base: [str] = [""]*4
        self.team = team
        self.game_info = game_info
        self.events = None

        self.lineup = game_info.lineups[team]

    def player_out(self, base: int):
        player: Player = self.game_info.get_player(self.on_base[base])
        logging.debug(f"{player.name} is out")
        self.outs += 1
        self.on_base[base] = ""
        player.clear_player()

    def end_half_inning(self):
        for player_id in self.on_base:
            if player_id != "":
                self.game_info.get_player(player_id).clear_player()

    def player_scored(self, player_id):
        logging.debug(f"{player_id} scored")
        player: Player = self.game_info.get_player(player_id)
        self.game_info.player_scored(player.base_dict, self.team)
        player.clear_player()

    def assign_credit(self, play: Play):
        error_id = self.game_info.teams[(self.team + 1) % 2]
        for cur_base in range(4):
            player_id = self.on_base[cur_base]
            if player_id != "":
                player = self.game_info.get_player(player_id)
                assert player.get_current_base() == cur_base
                bases_advanced = play.advancements[cur_base] - cur_base
                if bases_advanced <= 0:  # runner hasn't moved or is out
                    continue
                player.advance(bases_advanced)
                if cur_base == 0:
                    error_credit = min(bases_advanced, play.num_errors)
                    hitter_credit = bases_advanced - error_credit
                    player.credit_player(error_id, error_credit)
                    player.credit_player(player_id, hitter_credit)
                else:
                    hitter_credit = min(bases_advanced, play.hitter_max_credit)
                    error_credit = min(bases_advanced - hitter_credit, play.num_errors)
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
            assert self.game_info.get_player(player_id).current_base == 4
            self.player_scored(player_id)
        self.on_base = new_bases

    def parse_event(self, event_text: str):
        logging.debug(f"Reading: {event_text}")
        event_list = event_text.split(",")
        if event_list[0] == "play":
            play: Play = Play(event_list)
            if self.on_base[0] == "":
                self.on_base[0] = play.hitter_id
            else:
                assert self.on_base[0] == play.hitter_id
            assert [] != [player for player in self.lineup if player.id == play.hitter_id]  # check hitter in lineup
            play.run_play()
            self.assign_credit(play)
            self.advance_runners(play)
        elif event_list[0] == "sub":
            player = self.game_info.read_player(event_list)
            replaced_player_id = self.game_info.replace_player(player)
            for i in range(len(self.on_base)):
                if self.on_base[i] == replaced_player_id:
                    self.on_base[i] = player.id

