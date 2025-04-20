import logging
import re

from Player import Player
from Game_Info import Game_Info

class Half_Inning:

    OUTS= ["K", "\d+", "\d+\([1-3]\)"]  # TODO handle double plays
    FIELDERS_CHOICES = ["FC[1-9]", "FO[1-9]"]
    HITS = {"S[1-9]?": 1, "D[1-9]?": 2, "T[1-9]?": 3, "H[1-9]?": 4, "HR[1-9]?": 4, "DGR": 2}
    WALKS = {"W": 1, "I": 1, "IW": 1, "HP": 1}
    ERRORS = ["[1-9]?E[1-9]", "C", "PO[1-3](E[1-9])"]

    BALKS = ["BK"]
    WILD_OR_PASSEDS = ["WP", "PB"]
    ISOLATED_RUNNER_OUTS = {"CS[2|3|H]\([1-9]+\)": -1, "POCS[2|3|H]\([1-9]+\)": -1, "PO[1-3]\([1-9]+\)": 0}  # value is what to add to get starting base of runner
    STEALS = {"SB[2|3|H]": -1}

    BASE_MOTIONS = {"[B|1-3]-[1-3|H](\([^E]+\))*"}
    BASE_OUTS = ["[B|1-3]X[1-3|H](\(\d+\))?"]
    BASE_ERRORS = {"[B|1-3]X[1-3|H](\(\d*E\d.*\))": 'X', "[B|1-3]-[1-3|H](\(\d*E\d.*\))": '-'}

    IGNORES = ["NP", "FLE[1-9]"]

    def __init__(self, game_info: Game_Info, inning: int, team: int):
        self.outs = 0
        self.on_base: [str] = [""]*4
        self.advancements: [int] = [i for i in range(4)]
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

    def advance_runners(self):
        new_bases = [""]*4
        scored = []
        for cur_base in range(4):
            if self.on_base[cur_base] != "":
                if self.advancements[cur_base] == 4:
                    scored += [self.on_base[cur_base]]
                elif self.advancements[cur_base] == -1:
                    self.player_out(cur_base)
                else:
                    assert new_bases[self.advancements[cur_base]] == ""
                    new_bases[self.advancements[cur_base]] = self.on_base[cur_base]

        # Check scores
        for player_id in scored:
            assert self.game_info.get_player(player_id).current_base == 4
            self.player_scored(player_id)
        self.advancements = [i for i in range(4)]
        self.on_base = new_bases

    def check_ignore_events(self, hitter_id: str, event_text: str):
        for event in Half_Inning.IGNORES:
            match = re.fullmatch(event, event_text)
            if match is not None:
                return True
        return False

    def check_independent_runner_events(self, hitter_id: str, event_text: str):
        is_error = False
        triggered = False

        for event in Half_Inning.ISOLATED_RUNNER_OUTS:
            match = re.fullmatch(event, event_text)
            if match is not None:
                if "CS" in event:
                    runner_base = int(event_text[event_text.find("CS") + 2]) + Half_Inning.ISOLATED_RUNNER_OUTS[event]
                elif "PO" in event:
                    runner_base = int(event_text[event_text.find("PO") + 2]) + Half_Inning.ISOLATED_RUNNER_OUTS[event]
                else:
                    raise NotImplementedError(f"Cannot handle event {event}")
                runner_id: str = self.on_base[runner_base]
                self.advancements[runner_base] = -1
                logging.debug(f"Runner {runner_id} out on the basepaths")
                triggered = True

        for event in Half_Inning.STEALS:
            match = re.fullmatch(event, event_text)
            if match is not None:
                end_base = event_text[event_text.find("SB")+2]
                end_base = 4 if end_base == "H" else int(end_base)
                cur_base = end_base + Half_Inning.STEALS[event]
                runner = self.game_info.get_player(self.on_base[cur_base])
                runner.runner_event(end_base, None, 0, False)
                self.advancements[cur_base] = end_base
                triggered = True

        for event in Half_Inning.WILD_OR_PASSEDS + Half_Inning.BALKS:
            match = re.fullmatch(event, event_text)
            if match is not None:
                is_error = True
                triggered = True

        return triggered, is_error

    def check_hitter_events(self, hitter_id, event_text):
        triggered = False
        hitter_max_credit = None
        hitter_base = None
        is_error = False

        for event in Half_Inning.HITS.keys():
            match = re.fullmatch(event, event_text)
            if match is not None:
                hitter_max_credit = Half_Inning.HITS[event] + 0.5
                hitter_base = Half_Inning.HITS[event]
                triggered = True

        for event in Half_Inning.WALKS.keys():
            match = re.fullmatch(event, event_text)
            if match is not None:
                hitter_max_credit = Half_Inning.WALKS[event]
                hitter_base = Half_Inning.WALKS[event]
                triggered = True

        for event in Half_Inning.OUTS:  # TODO figure baserunner vs batter credit
            match = re.fullmatch(event, event_text)
            if match is not None:
                runner_outs = re.search("\(\d\)", event_text)
                if runner_outs is not None:
                    out_base = int(runner_outs.group()[1])
                    self.advancements[out_base] = -1
                hitter_max_credit = 1  # should be 0 or 0.5 in some situations, need modifiers
                self.advancements[0] = -1
                triggered = True

        for event in Half_Inning.ERRORS:
            match = re.fullmatch(event, event_text)
            if match is not None:
                hitter_max_credit = 0
                hitter_base = 1
                is_error = True
                triggered = True

        for event in Half_Inning.FIELDERS_CHOICES:  # TODO make sure runner out is handled, give credit to runner out
            match = re.fullmatch(event, event_text)
            if match is not None:
                hitter_max_credit = 1  # TODO runner out
                hitter_base = 1
                triggered = True

        assert [] != [player for player in self.lineup if player.id == hitter_id]  # check hitter in lineup

        if hitter_base is not None:
            hitter = self.game_info.player_dict[hitter_id]
            hitter.batter_event(hitter_base, hitter_max_credit)
            self.advancements[0] = hitter_base

        return triggered, hitter_max_credit, is_error

    def check_dependent_running_events(self, runner_events: [str], hitter_id, hitter_max_credit, is_error):

        for running_event in runner_events:
            runner_base = running_event[0]
            runner_base = 0 if runner_base == "B" else int(runner_base)
            runner_id = self.on_base[runner_base]
            runner = self.game_info.get_player(runner_id)

            final_base = None
            is_out = False

            for event in Half_Inning.BASE_OUTS:
                match = re.fullmatch(event, running_event)
                if match is not None:
                    is_out = True
                    self.advancements[runner_base] = -1
                    final_base = 0  # to show that an event has been registered

            for event in Half_Inning.BASE_MOTIONS:
                match = re.fullmatch(event, running_event)
                if match is not None:
                    final_base = running_event[running_event.find("-")+1]
                    final_base = 4 if final_base == "H" else int(final_base)

            for event in Half_Inning.BASE_ERRORS.keys():
                match = re.fullmatch(event, running_event)
                if match is not None:
                    final_base = running_event[running_event.find(Half_Inning.BASE_ERRORS[event])+1]
                    final_base = 4 if final_base == "H" else int(final_base)
                    is_error = True

            if final_base is None:
                raise ValueError(
                    f"Running event {running_event} is not known by this program (runner id {runner_id})")

            if not is_out:
                runner.runner_event(final_base, hitter_id, hitter_max_credit, is_error)
                self.advancements[runner_base] = final_base

    def parse_play(self, player_id: str, play_code: str):
        if self.on_base[0] == "":
            self.on_base[0] = player_id
        else:
            assert self.on_base[0] == player_id
        basic_play = play_code
        running_extension: [str] = None
        modifiers: [str] = None
        if '.' in basic_play:
            index_run = basic_play.find('.')
            running_extension_text = basic_play[index_run+1:]
            running_extension = running_extension_text.split(";")
            basic_play = basic_play[:index_run]
        if "/" in basic_play:
            index_mod = basic_play.find('/')
            modifiers_text = basic_play[index_mod+1:]
            modifiers = modifiers_text.split("/")  # TODO use modifiers to read double plays, give credit based type of out
            basic_play = basic_play[:index_mod]

        triggered = self.check_ignore_events(player_id, basic_play)
        hitter_id = player_id
        hitter_max_credit = 0
        is_error = False
        if not triggered:
            triggered, hitter_max_credit, is_error = self.check_hitter_events(player_id, basic_play)
        if not triggered:
            triggered, is_error = self.check_independent_runner_events(player_id, basic_play)
        if not triggered:
            logging.warning(f"{basic_play} not recognized")
        if running_extension is not None:
            self.check_dependent_running_events(running_extension, hitter_id, hitter_max_credit, is_error)

        self.advance_runners()

    def parse_event(self, event_text: str):
        logging.debug(f"Play: {event_text}")
        event_list = event_text.split(",")
        if event_list[0] == "play":
            player_id = event_list[3]
            count = event_list[4]  # unused
            pitches = event_list[5]  # unused
            play_code = event_list[6].strip("!?+-")
            self.parse_play(player_id, play_code)
        elif event_list[0] == "sub":
            player = self.game_info.read_player(event_list)
            replaced_player_id = self.game_info.replace_player(player)
            for i in range(len(self.on_base)):
                if self.on_base[i] == replaced_player_id:
                    self.on_base[i] = player.id

