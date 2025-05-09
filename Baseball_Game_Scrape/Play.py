import logging
import re


class Play:

    OUTS = ["K", "\d+"]
    DOUBLE_PLAYS = ["\d+\(\d\)\d+", "\d+\([B|1-3]\)\d+\([B|1-3]\)"]
    TRIPLE_PLAYS = ["\d+\(\d\)\d+\(\d\)\d+"]
    FIELDERS_CHOICES = ["FC[1-9]?"]
    FORCE_OUTS = ["\d+\([1-3]\)"]
    HITS = {"S[1-9]*": 1, "D[1-9]*": 2, "T[1-9]*": 3, "H[1-9]*": 4, "HR[1-9]*": 4, "DGR": 2}
    WALKS = {"W": 1, "I": 1, "IW": 1, "HP": 1}
    ERRORS = ["[1-9]?E[1-9]", "C"]

    BALKS = ["BK"]
    WILD_OR_PASSEDS = ["WP", "PB", "PO[1-3]\(E[1-9].*\)"]
    ISOLATED_RUNNER_OUTS = {"CS[2|3|H]\([1-9]+\)": -1, "POCS[2|3|H]\([1-9]+\)": -1,
                            "PO[1-3]\([1-9]+\)": 0}  # value is what to add to get starting base of runner
    STEALS = {"SB[2|3|H]": -1}
    DEFENSIVE_INDIFFERENCE = {"DI"}

    BASE_MOTIONS = {"[B|1-3]-[1-3|H](\([^E]+\))*"}
    BASE_OUTS = ["[B|1-3]X[1-3|H](\(\d+\))?"]
    BASE_ERRORS = {"[B|1-3]X[1-3|H](\(\d*E\d.*\))": 'X', "[B|1-3]-[1-3|H](\(\d*E\d.*\))": '-'}

    IGNORES = ["NP", "FLE[1-9]", "OA"]

    def __init__(self, play_list: [str]):
        self.error_credits: [int] = [0]*4
        self.hitter_max_credit: int = 0
        self.advancements = [i for i in range(4)]
        self.is_processed = False
        self.fielders_choice_credit = None  # base of credit if fielder's choice

        assert play_list[0] == "play"
        self.hitter_id: str = play_list[3]
        count = play_list[4]  # unused
        pitches = play_list[5]  # unused
        play_code = play_list[6].strip("!?+-")  # remove unimportant symbols

        self.basic_play = play_code
        self.runner_movements: [str] = None
        self.modifiers: [str] = []
        if '.' in self.basic_play:
            index_run = self.basic_play.find('.')
            running_extension_text = self.basic_play[index_run+1:]
            self.runner_movements = running_extension_text.split(";")
            self.basic_play = self.basic_play[:index_run]
        count_parentheses = 0
        first_separator = None
        for i in range(len(self.basic_play)):
            play_char = self.basic_play[i]
            if count_parentheses == 0 and play_char == '/':
                first_separator = i
                break
            elif play_char == '(':
                count_parentheses += 1
            elif play_char == ')':
                count_parentheses -= 1
        if first_separator is not None:
            modifiers_text = self.basic_play[first_separator+1:]
            self.modifiers = modifiers_text.split("/")  # TODO use modifiers to read double plays,
            # give credit based type of out
            self.basic_play = self.basic_play[:first_separator]

    def check_ignore_events(self, play):
        for event in Play.IGNORES:
            match = re.fullmatch(event, play)
            if match is not None:
                assert not self.is_processed
                self.is_processed = True

    def check_independent_runner_events(self, play):

        for event in Play.ISOLATED_RUNNER_OUTS:
            match = re.fullmatch(event, play)
            if match is not None:
                if "CS" in event:
                    runner_base = int(play[play.find("CS") + 2]) + \
                                  Play.ISOLATED_RUNNER_OUTS[event]
                elif "PO" in event:
                    runner_base = int(play[play.find("PO") + 2]) + \
                                  Play.ISOLATED_RUNNER_OUTS[event]
                else:
                    raise NotImplementedError(f"Cannot handle event {event}")
                self.advancements[runner_base] = -1
                logging.debug(f"Runner at base {runner_base} out on the basepaths")
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a runner out")

        for event in Play.STEALS:
            match = re.fullmatch(event, play)
            if match is not None:
                end_base = play[play.find("SB")+2]
                end_base = 4 if end_base == "H" else int(end_base)
                cur_base = end_base + Play.STEALS[event]
                self.advancements[cur_base] = end_base
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a steal")

        for event in Play.WILD_OR_PASSEDS + Play.BALKS:
            match = re.fullmatch(event, play)
            if match is not None:
                self.error_credits = [num + 1 for num in self.error_credits]
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a wild pitch, passed ball, or balk")

        for event in Play.DEFENSIVE_INDIFFERENCE:
            match = re.fullmatch(event, play)
            if match is not None:
                self.error_credits = [num + 0.5 for num in self.error_credits]
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is defensive indifference")


    def check_hitter_events(self, play):

        for event in Play.HITS.keys():
            match = re.fullmatch(event, play)
            if match is not None:
                self.hitter_max_credit = Play.HITS[event] + 0.5
                self.advancements[0] = Play.HITS[event]
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a hit")

        for event in Play.WALKS.keys():
            match = re.fullmatch(event, play)
            if match is not None:
                self.hitter_max_credit = Play.WALKS[event]
                self.advancements[0] = Play.WALKS[event]
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a walk")

        for event in Play.OUTS:  # TODO figure baserunner vs batter credit
            match = re.fullmatch(event, play)
            if match is not None:# and "FO" not in self.modifiers:
                self.hitter_max_credit = 1  # should be 0 or 0.5 in some situations, need modifiers
                self.advancements[0] = -1
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is an out")

        for event in Play.DOUBLE_PLAYS:
            match = re.fullmatch(event, play)
            if match is not None:
                assert "DP" in self.modifiers or "GDP" in self.modifiers
                runner_outs = re.findall("\(\d\)", play)
                if runner_outs is not None:
                    assert len(runner_outs) == 1
                    out_base = int(runner_outs[0][1])
                    self.advancements[out_base] = -1
                self.hitter_max_credit = 1  # should be 0 or 0.5 in some situations, need modifiers
                self.advancements[0] = -1
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a double play")

        for event in Play.TRIPLE_PLAYS:
            match = re.fullmatch(event, play)
            if match is not None:
                assert "TP" in self.modifiers or "GTP" in self.modifiers
                runner_outs = re.findall("\(\d\)", play)
                if runner_outs is not None:
                    assert len(runner_outs) == 2
                    out_base = int(runner_outs[0][1])
                    self.advancements[out_base] = -1
                self.hitter_max_credit = 0  # should be 0 or 0.5 in some situations, need modifiers
                self.advancements[0] = -1
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a triple play")

        for event in Play.ERRORS:
            match = re.fullmatch(event, play)
            if match is not None:
                self.hitter_max_credit = 0
                self.advancements[0] = 1
                self.error_credits = [num + 1 for num in self.error_credits]
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is an error")

        for event in Play.FIELDERS_CHOICES:  # TODO make sure runner out is handled, give credit to runner out
            match = re.fullmatch(event, play)
            if match is not None:# or "FO" in self.modifiers:
                # if "FO" in self.modifiers:
                #     assert re.fullmatch(Play.OUTS[1], play) is not None
                self.fielders_choice_credit = 0  # to be filled in in runners events
                self.hitter_max_credit = 1
                self.advancements[0] = 1
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a fielders choice")

        for event in Play.FORCE_OUTS:  # TODO make sure runner out is handled, give credit to runner out
            match = re.fullmatch(event, play)
            if match is not None:
                runner_outs = re.findall("\(\d\)", play)
                assert len(runner_outs) == 1
                out_base = int(runner_outs[0][1])
                for i in range(4):
                    if i == out_base:
                        self.advancements[i] = -1
                        self.fielders_choice_credit = out_base
                        break  # all baserunners before the forced runner advance
                    else:
                        self.advancements[i] += i+1
                self.hitter_max_credit = 1  # TODO runner out
                self.advancements[0] = 1
                assert not self.is_processed
                self.is_processed = True
                logging.debug(f"Play is a force out")

    def check_dependent_running_events(self):

        for running_event in self.runner_movements:
            runner_base = running_event[0]
            runner_base = 0 if runner_base == "B" else int(runner_base)
            is_processed = False

            for event in Play.BASE_OUTS:
                match = re.fullmatch(event, running_event)
                if match is not None:
                    self.advancements[runner_base] = -1
                    if self.fielders_choice_credit == 0:
                        self.fielders_choice_credit = runner_base
                    assert not is_processed
                    is_processed = True
                    logging.debug(f"The runner on base {runner_base} is out on the bases")

            for event in Play.BASE_MOTIONS:
                match = re.fullmatch(event, running_event)
                if match is not None:
                    final_base_str = running_event[running_event.find("-")+1]
                    final_base = 4 if final_base_str == "H" else int(final_base_str)
                    self.advancements[runner_base] = final_base
                    assert not is_processed
                    is_processed = True
                    logging.debug(f"The runner on base {runner_base} advanced")

            for event in Play.BASE_ERRORS.keys():  # TODO fix assigning credit on base errors
                match = re.fullmatch(event, running_event)
                if match is not None:
                    final_base_str = running_event[running_event.find(Play.BASE_ERRORS[event])+1]
                    final_base = 4 if final_base_str == "H" else int(final_base_str)
                    self.error_credits[runner_base] += 1
                    self.advancements[runner_base] = final_base
                    if self.fielders_choice_credit == 0:
                        self.fielders_choice_credit = runner_base
                    assert not is_processed
                    is_processed = True
                    logging.debug(f"The runner on base {runner_base} advanced on an error")


            if not is_processed:
                raise ValueError(
                    f"Running event {running_event} is not known by this program (runner base {runner_base})")

    def run_play(self):
        plays = re.split(";|\+", self.basic_play)
        for play in plays:
            self.check_ignore_events(play)
            self.check_hitter_events(play)
            self.check_independent_runner_events(play)
            if not self.is_processed:
                raise NotImplementedError(f"{self.basic_play} not recognized")
            self.is_processed = False
        if self.runner_movements is not None:
            self.check_dependent_running_events()
