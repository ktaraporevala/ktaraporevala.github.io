import logging

from Player import Player
from Game_Info import Game_Info

class Half_Inning:

    OUTS_CREDIT = ["grounded into a double play", "grounded out", "lined to", "flied to",
                   "out on a sacrifice fly to"]
    OUTS_NO_CREDIT = ["struck out", "was called out on strikes", "popped to"]
    FIELDERS_CHOICES = ["forced"]
    HITS = {"singled to": 1, "doubled to": 2, "tripled to": 3, "homered to": 4}
    WALKS = {"walked": 1, "was walked intentionally": 1}
    ERRORS = ["reached on an error by", "threw a wild pitch"]
    SWAPS = {"BATTED FOR": False, "RAN FOR": True}  # Value denotes if player is on bases
    ISOLATED_RUNNER_OUTS = ["was picked off and caught stealing"]
    STEALS = {"stole second": 2, "stole third": 3, "stole home": 4}

    BASE_MOTIONS = {"to first": 1, "to second": 2, "to third": 3, "scored": 4}
    BASE_OUTS = ["out at", "was picked off and caught stealing"]

    IGNORES = ["(PITCHING)", "STAYED IN GAME (PLAYING"]

    def __init__(self, game_info: Game_Info, inning: int, is_home: bool):
        self.outs = 0
        self.on_base = {}
        self.is_home = is_home
        self.game_info = game_info
        self.events = None

        if is_home:
            self.lineup = game_info.home_lineup
            inning_index = game_info.home_inning_indices[inning-1]
        else:
            self.lineup = game_info.away_lineup
            inning_index = game_info.away_inning_indices[inning-1]

        if inning_index is None:
            return

        full_inning_text = game_info.pbp[inning_index]
        assert full_inning_text.count(":") == 1
        full_text = full_inning_text.split(":")[1]  # preceding : is team/inning
        #full_text = full_text.replace(" and ", ";")  # items separated by
        self.events = full_text.split(";")[:-1]  # last section is summary
        self.events = [event.strip() for event in self.events]

    @staticmethod
    def remove_parentheses(text: str, parentheses_chars=('(', ')')):
        while "(" in text:
            text = text[0:text.find(parentheses_chars[0])] + text[text.find(parentheses_chars[1])+1:]
        return text

    def player_out(self, player_name):
        logging.debug(f"{player_name} is out")
        self.outs += 1
        if player_name in self.on_base.keys():
            self.on_base.pop(player_name)

    def player_scored(self, player_name):
        logging.debug(f"{player_name} scored")
        player = self.on_base[player_name]
        self.game_info.player_scored_fn(player.base_dict, self.is_home)
        self.on_base.pop(player_name)

    def check_scores(self):
        players_on_base = [name for name in self.on_base.keys()]
        for player_name in players_on_base:
            if self.on_base[player_name].current_base == 4:
                self.player_scored(player_name)

    def check_substitution_events(self, subject, event_text):
        for event in Half_Inning.IGNORES:
            if event in event_text:
                return True

        for event in Half_Inning.SWAPS.keys():
            if event in event_text:
                a = event.split(" ")
                old_player = event_text.replace(event, "").strip()
                old_player = Player.format_player_name(old_player)
                self.game_info.replace_player(old_player, subject, self.is_home)

                if Half_Inning.SWAPS[event]:
                    self.on_base[old_player].player_replaced(subject)
                    self.on_base[subject] = self.on_base.pop(old_player)
                return True

        return False

    def check_runner_events(self, runner_name: str, event_text: str):
        for event in Half_Inning.ISOLATED_RUNNER_OUTS:
            if event in event_text:
                self.player_out(runner_name)
                logging.debug(f"Runner {runner_name} out on the basepaths")
                return True

        for event in Half_Inning.STEALS:
            if event in event_text:
                end_base = Half_Inning.STEALS[event]
                self.on_base[runner_name].runner_event(end_base, None, 0, False, False)
                return True

    def check_batter_events(self, hitter_name, event_text):
        triggered = False

        hitter_credit = None
        hitter_base = None
        is_hit = False
        is_error = False

        event_text = Half_Inning.remove_parentheses(event_text)

        for event in Half_Inning.HITS.keys():
            if event in event_text:
                hitter_credit = Half_Inning.HITS[event]
                hitter_base = hitter_credit
                is_hit = True
                triggered = True

        for event in Half_Inning.WALKS.keys():
            if event in event_text:
                hitter_credit = Half_Inning.WALKS[event]
                hitter_base = hitter_credit
                triggered = True

        for event in Half_Inning.OUTS_CREDIT:
            if event in event_text:
                hitter_credit = 1
                self.player_out(hitter_name)
                triggered = True

        for event in Half_Inning.OUTS_NO_CREDIT:
            if event in event_text:
                hitter_credit = 0
                self.player_out(hitter_name)
                triggered = True

        for event in Half_Inning.ERRORS:
            if event in event_text:
                hitter_credit = 0
                hitter_base = 0
                is_error = True
                triggered = True

        for event in Half_Inning.FIELDERS_CHOICES:
            if event in event_text:
                options = event_text.split(" ")
                runner_out = Player.format_player_name(options[options.index(event)+1])
                hitter_credit = 1
                hitter_base = 0
                self.player_out(runner_out)
                triggered = True

        if not is_error:
            assert hitter_name in self.lineup

        if hitter_base is not None:
            batter = Player(hitter_name, self.player_scored)
            batter.batter_event(hitter_base, hitter_credit)
            self.on_base[hitter_name] = batter

        return triggered, hitter_name, hitter_credit, is_hit, is_error

    def check_dependent_running_events(self, runner_event_text, hitter_name, hitter_credit, is_hit, is_error):
        runner_event_text = Half_Inning.remove_parentheses(runner_event_text)
        runner_events = runner_event_text.split(",")

        for running_event in runner_events:
            running_event = running_event.strip()
            runner_name = Player.format_player_name(running_event.split(" ")[0])
            runner: Player = self.on_base[runner_name]
            running_event = running_event[len(runner_name) + 1:]

            final_base = None
            is_out = False

            for event in Half_Inning.BASE_OUTS:
                if event in running_event:
                    is_out = True
                    self.player_out(runner_name)
                    final_base = 0  # to show that an event has been registered

            for event in Half_Inning.BASE_MOTIONS.keys():
                if event in running_event:
                    final_base = Half_Inning.BASE_MOTIONS[event]

            if final_base is None:
                raise ValueError(
                    f"Running event {running_event} is not known by this program (runner name {runner_name})")

            if not is_out:
                runner.runner_event(final_base, hitter_name, hitter_credit, is_hit, is_error)

    def parse_event(self, full_event_text: str):
        full_event_text = full_event_text.replace('\n', ' ')
        logging.debug(f"Parsing event: {full_event_text}")
        subject = Player.format_player_name(full_event_text.split(" ")[0])
        event_text = full_event_text[len(subject)+1:]

        processed = False
        if self.check_substitution_events(subject, event_text):
            processed = True
        elif self.check_runner_events(subject, event_text):
            processed = True
            assert "[" not in event_text
        else:
            (processed, hitter_name, hitter_credit, is_hit, is_error) = self.check_batter_events(subject, event_text)
            if processed and "[" in event_text:
                runner_event_text = event_text[event_text.find("[")+1:event_text.find("]")]
                self.check_dependent_running_events(runner_event_text, hitter_name, hitter_credit, is_hit, is_error)

        if not processed:
            raise ValueError(f"Event {event_text} is not known by this program")

        self.check_scores()