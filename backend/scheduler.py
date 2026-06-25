import calendar
import csv
from datetime import datetime, timedelta
from datetime import date
import pandas as pd
import numpy as np
class ScheduleMaker:

    def __init__(self, people=None):
        self.people = people or ['a', 'b', 'c', 'd', 'e', 'f', 'g']

    # ─────────────────────────────────────────────
    # CORE ENTRY POINT
    # ─────────────────────────────────────────────
    def generate(self, start_date, end_date, forced_days,
                 sunday_quotas, prefs, targets, fixed_holidays,fixed_holidays_quotas,zeezwemmen=[5,6]):

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        self.start = start
        self.end = end
        self.num_days = (end - start).days + 1

        self.forced_days = forced_days
        self.sunday_quotas = sunday_quotas
        self.fixedh_quotas = fixed_holidays_quotas
        self.fixedh= fixed_holidays
        def convert(day, month=None, year=None):
            month = month or start.month
            year  = year  or start.year

            d = date(year, month, day)
            return (d - self.start).days + 1

        self.prefs = {
            p: {
                tier: [convert(d) for d in days]
                for tier, days in pref.items()
            }
            for p, pref in prefs.items()
        }
        self.unfulfilled_days = {p: set() for p in self.people}
        for p in self.people:
            print(f"  {p}: {self.prefs[p]}")

        self.targets = targets
        self.fixed_holidays = fixed_holidays

        self.schedule = {p: [2] * self.num_days for p in self.people}
        self.zeezwemmen = zeezwemmen
        # Sundays
        self.sundays = [
            i + 1
            for i in range(self.num_days)
            if (start + timedelta(days=i)).weekday() == 6
        ]

        # ── PIPELINE ─────────────────────────────
        self.apply_forced_days()

        print("\n── fixed holidays summary ──")

        print(self.schedule)
        self.apply_preference_pass()
        self.fill_holidays()
        self.fill_sundays()
        self.fill_mandatory()
        print("\n── mandatory summary ──")
        print(self.schedule )
        self.balance_regular_days()
        print(self.schedule)


        return self.schedule, self.num_days

    # ─────────────────────────────────────────────
    # PASS 1
    # ─────────────────────────────────────────────
    def fill_mandatory(self):
        for d_idx in range(self.num_days):
            day_num = d_idx + 1
            if day_num in self.forced_days or day_num in self.sundays or day_num in self.fixed_holidays:
                continue

            must_work_list = []
            must_holiday_list = []

            for p in self.people:
                if self.schedule[p][d_idx]:  # already assigned, skip
                    if self.schedule[p][d_idx] == 1:
                        must_holiday_list.append(p)
                    else:
                        must_work_list.append(p)

                if self.must_work(p, d_idx):
                    must_work_list.append(p)
                    self.schedule[p][d_idx] = 0

                elif self._needs_holiday(p, d_idx):
                    must_holiday_list.append(p)
                    self.schedule[p][d_idx] = 1

            # if 3+ must work -> all remaining unassigned also work
            if len(must_work_list) == 4:
                for p in [p for p in self.people if p not in must_work_list]:
                    if self.schedule[p][d_idx] == 2:
                        self.schedule[p][d_idx] = 1

            # if 3+ must holiday -> all remaining unassigned also holiday
            # but respect coverage minimum of 4 workers
            if len(must_holiday_list) == 3:
                for p in [p for p in self.people if p not in must_holiday_list]:
                    if self.schedule[p][d_idx] == 2:
                        self.schedule[p][d_idx] = 0



    def number_working_4_in_a_row(self,d_idx):
        working_4 = {}
        for p in self.people:
            hist = self.schedule[p][max(0, d_idx-5):d_idx]
            working = 0
            for x in hist[::-1]:
                if x == 0:
                    working += 1
                else:
                    working = 0
            if working >= 4:
              working_4[p] =1
        print(working_4,'working 4')
        return working_4

    def number_working_3_in_a_row(self,d_idx):
        working_3 = {}
        for p in self.people:
            hist = self.schedule[p][max(0, d_idx-5):d_idx]
            working = 0
            for x in hist[::-1]:
                if x == 0:
                    working += 1
                else:
                    working = 0
            if working >= 3:
              working_3[p] =1
        print(working_3,'working 3')
        return working_3

    def apply_forced_days(self):
        for d in self.forced_days:
            for p in self.people:
                self.schedule[p][d - 1] = 0



    # ─────────────────────────────────────────────
    # PREF PASS
    # ─────────────────────────────────────────────
    def current_off(self,d_idx):
      #currentoff gebruik dan nog aanpassen in functie van p
          currentoff = sum(1 for p in self.people if self.schedule[p][d_idx] == 1)

          return currentoff

    def apply_preference_pass(self):
        MIN_PREF_DAYS = 3
        rank = {p: i for i, p in enumerate(self.people)}


        def try_assign(p, d_idx):

            print('try',p,d_idx)
            currentoff = self.current_off(d_idx)

            if p == 'a' and self.schedule['b'][d_idx] == 1:
                print('a')
                return False
            if p == 'b' and self.schedule['a'][d_idx] == 1:
                return False


            if currentoff >= 3:
                for other in self.people:
                    if self.schedule[other][d_idx] == 2:
                        self.schedule[other][d_idx] = 0
                return False


            if not self._can_take_holiday(p, d_idx):
                print('cannot take holiday')
                return False


            hist_off = self.schedule[p][max(0, d_idx - 4):d_idx-1]  # last 3 without today
            next_idx = d_idx + 1
            if len(hist_off) == 3 and all(x == 1 for x in hist_off):
                next_day_num = next_idx + 1
                if next_day_num in self.sundays:
                    if next_idx < self.num_days:
                          # 1-based


                        # Next day is a Sunday
                        sundays_worked = sum(1 for s in self.sundays if self.schedule[p][s-1] == 0)
                        sunday_debt = self.sunday_quotas[p] - sundays_worked
                        sundays_remaining = sum(1 for s in self.sundays if self.schedule[p][s-1] == 2)
                        if sunday_debt >= sundays_remaining:
                            # Still have Sunday work quota to fill → work on Sunday
                            self.schedule[p][next_idx] = 0

                        else:
                            # No Sunday debt left → work TODAY instead, give off on Sunday
                            self.schedule[p][d_idx] = 0    # undo today's holiday
                            self.schedule[p][next_idx] = 1  # give off on Sunday instead

                            # Give today's holiday to someone else who needs it most
                            # Prioritise people who had today as a preference
                            if not any(self.schedule[other][d_idx] == 2 for other in self.people if other != p):
                              for other in self.people:
                                  if other != p and self.schedule[other][d_idx] == 0 and self._can_take_holiday(other, d_idx):
                                      self.schedule[other][d_idx] = 2
                                      print(f"  STREAK BREAKER: reset {other} to unset (day {d_idx+1})")
                                      break
                            return False

                elif next_day_num in self.fixed_holidays:
                    if next_idx < self.num_days:
                          # 1-based


                        # Next day is a Sunday
                        holidays_worked = sum(1 for s in self.fixed_holidays if self.schedule[p][s-1] == 0)
                        holidays_debt = self.fixed_holidays_quotas[p] - holidays_worked
                        holidays_remaining = sum(1 for s in self.fixed_holidays if self.schedule[p][s-1] == 2)
                        if holidays_debt >= holidays_remaining:
                            # Still have Sunday work quota to fill → work on Sunday
                            self.schedule[p][next_idx] = 0

                        else:
                            # No Sunday debt left → work TODAY instead, give off on Sunday
                            self.schedule[p][d_idx] = 0    # undo today's holiday
                            self.schedule[p][next_idx] = 1  # give off on Sunday instead

                            # Give today's holiday to someone else who needs it most
                            # Prioritise people who had today as a preference
                            if not any(self.schedule[other][d_idx] == 2 for other in self.people if other != p):
                              for other in self.people:
                                  if other != p and self.schedule[other][d_idx] == 0 and self._can_take_holiday(other, d_idx):
                                      self.schedule[other][d_idx] = 2
                                      print(f"  STREAK BREAKER: reset {other} to unset (day {d_idx+1})")
                                      break
                            return False

                    else:
                        if next_idx < self.num_days:
                        # Next day is a regular day → just force work
                          self.schedule[p][next_idx] = 0
                          return False



            hist_off = self.schedule[p][max(0, d_idx - 5):d_idx-2]  # last 3 except yesterday and today
            if len(hist_off) == 3 and all(x == 1 for x in hist_off):
                last_idx = d_idx -1
                if last_idx < self.num_days:
                    last_day_num = last_idx + 1  # 1-based

                    if last_day_num in self.sundays:
                        # Next day is a Sunday
                        sundays_worked = sum(1 for s in self.sundays if self.schedule[p][s-1] == 0)

                        sundays_remaining = sum(1 for s in self.sundays if self.schedule[p][s-1] == 2)
                        sunday_debt = self.sunday_quotas[p] - sundays_worked
                        if sunday_debt >=sundays_remaining and (self.schedule[p][last_idx] == 2):
                            # Still have Sunday work quota to fill → work on Sunday
                            self.schedule[p][last_idx] = 0

                        else:
                            # No Sunday debt left → work TODAY instead, give off on Sunday
                            self.schedule[p][d_idx] = 0    # undo today's holiday
                            self.schedule[p][last_idx] = 1  # give off on Sunday instead

                            # Give today's holiday to someone else who needs it most
                            # Prioritise people who had today as a preference
                            if not any(self.schedule[other][d_idx] == 2 for other in self.people if other != p):
                              for other in self.people:
                                  if other != p and self.schedule[other][d_idx] == 0 and self._can_take_holiday(other, d_idx):
                                      self.schedule[other][d_idx] = 2
                                      print(f"  STREAK BREAKER: reset {other} to unset (day {d_idx+1})")
                                      break
                            return False
                    if last_day_num in self.fixed_holidays:
                      # Next day is a Sunday
                      holidays_worked = sum(1 for s in self.holidays if self.schedule[p][s-1] == 0)

                      holidays_remaining= sum(1 for s in self.holidays if self.schedule[p][s-1] == 2)
                      holidays_debt = self.holidays_quotas[p] - holidays_worked
                      if holidays_debt >= holidays_remaining and (self.schedule[p][last_idx] == 2):
                          # Still have Sunday work quota to fill → work on Sunday
                          self.schedule[p][last_idx] = 0

                      else:
                          # No Sunday debt left → work TODAY instead, give off on Sunday
                          self.schedule[p][d_idx] = 0    # undo today's holiday
                          self.schedule[p][last_idx] = 1  # give off on Sunday instead

                          # Give today's holiday to someone else who needs it most
                          # Prioritise people who had today as a preference
                          if not any(self.schedule[other][d_idx] == 2 for other in self.people if other != p):
                            for other in self.people:
                                if other != p and self.schedule[other][d_idx] == 0 and self._can_take_holiday(other, d_idx):
                                    self.schedule[other][d_idx] = 2
                                    print(f"  STREAK BREAKER: reset {other} to unset (day {d_idx+1})")
                                    break
                          return False





            get_workingcount = self.number_working_4_in_a_row(d_idx)
            get_workingcount_people = list(get_workingcount.keys())
            get_wourkingcount_people_length = len(get_workingcount_people)
            if ['a','b'] not in get_workingcount_people:
                get_wourkingcount_people_length +=1

            if get_wourkingcount_people_length >= 4:
                if p in get_workingcount_people:
                  pass
                else:
                  candidates = sorted(self.people , key=lambda p: (
                    self._needs_holiday(p, d_idx),
                    self.rank_preferences_for_day(p,d_idx), # 2. Your Streak Points (2nd holiday, etc)


                      self.get_priority_score(p, d_idx )                # 4. WANTS HOLIDAY SCORE
                  ), reverse=True)

                  remove = ['a','b',p]
                  for x in remove:
                      if x in candidates:
                        candidates.remove(x)
                  for x in candidates:
                      if x not in get_workingcount_people:
                        candidates.remove(x)

                  print(candidates,'candidates')
                  if len(candidates) >= 4:

                    p_new = candidates[0]

                    if self._can_take_holiday(p_new,d_idx) and (p_new) not in ['a','b']: #check if possible
                        self.schedule[p_new][d_idx] = 1
                        if self.get_ab_combined_priority('a', d_idx) == 0 and ('a' not in get_workingcount_people and 'b' not in get_workingcount_people) :
                            self.schedule['a'][d_idx] = 0
                            self.schedule['b'][d_idx] = 0

                    return False
                  elif len(candidates) >= 3 and self.get_ab_combined_priority('a', d_idx) == 0 and ('a' not in get_workingcount_people and 'b' not in get_workingcount_people) :
                        self.schedule['a'][d_idx] = 0
                        self.schedule['b'][d_idx] = 0



                  elif len(candidates) >=3 and ('a' in get_workingcount_people or 'b' in get_workingcount_people):
                      if 'a' in get_workingcount_people:
                        p_new = 'b'
                      if 'b' in get_workingcount_people:
                        p_new = 'a'

                      if self._can_take_holiday(p_new,d_idx): #check if possible
                          self.schedule[p_new][d_idx] = 1
                      return False
                  else:
                    pass






            if (d_idx + 1) in self.sundays:
                  get_workingcount = self.number_working_3_in_a_row(d_idx)
                  get_workingcount_people = list(get_workingcount.keys())
                  get_workingcount_people_length = len(get_workingcount_people)
                  if ['a','b'] not in get_workingcount_people and self.get_ab_combined_priority!=0:
                      get_workingcount_people_length +=1
                      if get_workingcount_people is not None:
                          get_workingcount_people.append('a')




                  if get_workingcount_people_length>= 4:
                      if p in get_workingcount_people:
                        pass
                      else:
                        candidates = sorted(self.people , key=lambda p: (
                          self._needs_holiday(p, d_idx),
                          self.rank_preferences_for_day(p,d_idx), # 2. Your Streak Points (2nd holiday, etc)

                            self.get_priority_score(p, d_idx, )                # 4. Rank Tie-breaker
                        ), reverse=True)
                        remove = ['a','b',p]
                        for x in remove:
                            if x in candidates:
                              candidates.remove(x)
                        print(candidates,'candidates')
                        p_new = candidates[0]

                        if self._can_take_holiday(p_new,d_idx) and (p_new) not in ['a','b']: #check if possible
                            self.schedule[p_new][d_idx] = 1
                            if self.get_ab_combined_priority('a', d_idx) ==0 :
                                self.schedule['a'][d_idx] = 0
                                self.schedule['b'][d_idx] = 0

            if (d_idx + 1) in self.fixed_holidays:
                  get_workingcount = self.number_working_3_in_a_row(d_idx)
                  get_workingcount_people = list(get_workingcount.keys())
                  get_workingcount_people_length = len(get_workingcount_people)
                  if ['a','b'] not in get_workingcount_people and self.get_ab_combined_priority!=0:
                      get_workingcount_people_length +=1
                      if get_workingcount_people is not None:
                          get_workingcount_people.append('a')




                  if get_workingcount_people_length>= 4:
                      if p in get_workingcount_people:
                        pass
                      else:
                        candidates1 = sorted(self.people , key=lambda p: (
                          self._can_take_holiday(p,d_idx),
                          self._needs_holiday(p, d_idx),
                          self.rank_preferences_for_day(p,d_idx), # 2. Your Streak Points (2nd holiday, etc)

                            self.get_priority_score(p, d_idx, )                # 4. Rank Tie-breaker
                        ), reverse=True)
                        candidates = candidates1.copy()
                        remove = ['a','b',p]
                        for x in remove:
                            if x in candidates:
                              candidates.remove(x)
                        print(candidates,'candidates')
                        p_new = candidates[0]
                        if self.get_ab_combined_priority('a', d_idx) ==0 :
                                self.schedule['a'][d_idx] = 0
                                self.schedule['b'][d_idx] = 0
                                self.schedule[p_new][d_idx] = 1
                                return False

                        else:
                            if 'a' in candidates1:
                              p_new = 'b'
                            if 'b' in candidates1:
                              p_new = 'a'

                            self.schedule[p_new][d_idx] = 1
                            return False






            self.schedule[p][d_idx] = 1
            if self.current_off(d_idx) >= 3:
              for other in self.people:
                  if self.schedule[other][d_idx] == 2:
                      self.schedule[other][d_idx] = 0

            if self.current_off(d_idx) >=2 and p not in ['a','b']:

              needs_holiday_sum = 0
              for other in self.people:
                if self._needs_holiday(other,d_idx) == True:
                    if other not in ['a','b',p]:
                      needs_holiday_sum +=1

              if needs_holiday_sum >= 1:
                if self.get_ab_combined_priority('a',d_idx) >0:
                  self.schedule[p][d_idx] = 0
                  for p in self.people:
                    if p not in ['a','b'] and self.schedule[p][d_idx]==2:
                      self.schedule[p][d_idx] = 0
                  return False
                  print('could not get holiday due to priority')
                else:
                  if needs_holiday_sum ==1:
                    if self._needs_holiday('a',d_idx) == False and self._needs_holiday('b',d_idx)==False:
                      self.schedule['a'][d_idx] = 0
                      self.schedule['b'][d_idx] = 0
                    else:
                      print('could not get holiday due to needing holiday for A/B')
                      self.schedule[p][d_idx] =0
                      for p in self.people:
                        if p not in ['a','b'] and self.schedule[p][d_idx]==2:
                          self.schedule[p][d_idx] = 0
                      return False


            if self.current_off(d_idx) >=1 and p not in ['a','b']:
              print('check current of validation')

              needs_holiday_sum = 0
              for other in self.people:
                if self._needs_holiday(other,d_idx) == True:
                    if other not in ['a','b',p]:
                      needs_holiday_sum +=1

              if needs_holiday_sum >= 2:
                if self.get_ab_combined_priority('a', d_idx) >0:
                    self.schedule[p][d_idx] = 0
                    return False
                    print('could not get holiday due to priority')
                elif (self.schedule['a'] or self.schedule['b']) ==1:
                    self.schedule[p][d_idx] = 0
                    return False
                    print('could not get holiday due to priority')
                else:
                    if needs_holiday_sum ==2:
                      if self._needs_holiday('a',d_idx) == False and self._needs_holiday('b',d_idx)==False and not ((self.schedule['a'] or self.schedule['b']) ==1) :
                        self.schedule['a'][d_idx] = 0
                        self.schedule['b'][d_idx] = 0
                        print('can get holiday, a and b take over')
                      else:
                        print('could not get holiday due to needing holiday for A/B')
                        self.schedule[p][d_idx] =0
                        return False
                    else:
                        self.schedule[p][d_idx]=0
                        return False
                        print('too many ppl need a holiday')






            print(f"  PREF HOLIDAY → {p} on day {d_idx+1}, schedule so far: {[self.schedule[q][d_idx] for q in self.people]}")
              # A/B constraint

            if self.schedule[p][d_idx] == 1 :
                if p == 'a':
                    self.schedule['b'][d_idx]=0
                if p == 'b':
                    self.schedule['a'][d_idx]=0

            return True

        def req(day, tier):
            r = [p for p in self.people if day in self.prefs[p].get(tier, [])]
            if 'a' in r and 'b' in r:
                r.remove('b')
            return sorted(r, key=lambda x: rank[x])

        received = {p: 0 for p in self.people}

        # HIGH
        for day in sorted({d for p in self.people for d in self.prefs[p].get('high', [])}):
            if day in self.forced_days:
                continue
            for p in req(day, 'high'):
                if try_assign(p, day - 1):
                    received[p] += 1

                    if p =='a':
                      self.schedule['b'][day-1] = 0
                    if p =='b':
                      self.schedule['a'][day-1] = 0
                else:
                   self.unfulfilled_days[p].add(day-1)



        # BOOST MID
        boosted = {p for p in self.people if received[p] < MIN_PREF_DAYS}

        for day in sorted({d for p in boosted for d in self.prefs[p].get('mid', [])}):
            if day in self.forced_days:
                continue
            for p in req(day, 'mid'):
                if p in boosted and self.schedule[p][day - 1] == 2:
                    if try_assign(p, day - 1):
                        received[p] += 1
                        if p =='a':
                          self.schedule['b'][day-1] = 0
                        if p =='b':
                          self.schedule['a'][day-1] = 0
                    else:
                       self.unfulfilled_days[p].add(day-1)

        # MID
        for day in sorted({d for p in self.people for d in self.prefs[p].get('mid', [])}):
            if day in self.forced_days:
                continue
            for p in req(day, 'mid'):
                if self.schedule[p][day - 1] == 2:
                    if try_assign(p, day - 1):
                        if p =='a':
                              self.schedule['b'][day-1] = 0
                        if p =='b':
                          self.schedule['a'][day-1] = 0
                    else:
                      self.unfulfilled_days[p].add(day-1)

        # LOW
        for day in sorted({d for p in self.people for d in self.prefs[p].get('low', [])}):
            if day in self.forced_days:
                continue
            for p in req(day, 'low'):
                if self.schedule[p][day - 1] == 2:
                  if try_assign(p, day - 1):
                      if p =='a':
                        self.schedule['b'][day-1] = 0
                      if p =='b':
                        self.schedule['a'][day-1] = 0
                  else:
                      self.unfulfilled_days[p].add(day-1)

        print("Schedule after preference pass:")
        for p in self.people:
            print(f"  {p}: {self.schedule[p]}")

    # ─────────────────────────────────────────────
    # SUNDAYS
    # ─────────────────────────────────────────────
    def fill_sundays(self):

                # Initialize your debt tracker

        free_sundays = [s for s in self.sundays if s not in self.forced_days]


        sunday_debt = {
        p: max(0, self.sunday_quotas[p] - sum(1 for t in self.sundays if self.schedule[p][t - 1] == 0))
        for p in self.people
        }
        sunday_flex= {
            p: self.sunday_quotas[p] - sum(1 for t in self.sundays if self.schedule[p][t - 1] == 0 or self.schedule[p][t-1]==2)
            for p in self.people
        }
        print(sunday_debt,sunday_flex)
        print('debt/flex')

        for i, s in enumerate(free_sundays):
            print('free sunday')
            print(sunday_debt['d'],'sunday debt for d')
            d_idx = s - 1

            print(d_idx,'d_idx')


            already_working = [p for p in self.people if self.schedule[p][d_idx] == 0]
            already_off     = [p for p in self.people if self.schedule[p][d_idx] == 1]
            current_unset   = [p for p in self.people if self.schedule[p][d_idx] == 2]
            assigned_workers = list(already_working)
            assigned_off     = list(already_off)
            workers_needed   = max(0, 4 - len(assigned_workers))
            for worker in list(current_unset):  # iterate over a copy
              if self._needs_holiday(worker, d_idx):

                  if sunday_flex[worker] <0:
                      print('worker', worker, 'needs holiday today', d_idx, "sunday")
                      self.schedule[worker][d_idx] = 1
                      sunday_flex[worker] = min(0, sunday_flex[worker] + 1)
                      assigned_off.append(worker)
                      current_unset.remove(worker)

              else:
                if self.must_work(worker, d_idx):
                  print('worker',worker,'must work,')
                  if sunday_debt[worker] > 0:
                    self.schedule[worker][d_idx] = 0
                    sunday_debt[worker] = max(0, sunday_debt[worker] - 1)



        free_sundays = [s for s in self.sundays if s not in self.forced_days]


        sunday_debt = {
        p: max(0, self.sunday_quotas[p] - sum(1 for t in self.sundays if self.schedule[p][t - 1] == 0))
        for p in self.people
        }
        sunday_flex= {
            p: self.sunday_quotas[p] - sum(1 for t in self.sundays if self.schedule[p][t - 1] == 0 or self.schedule[p][t-1]==2)
            for p in self.people
        }

        for i, s in enumerate(free_sundays):
            print('free sunday')
            print(sunday_debt['d'],'sunday debt for d')
            d_idx = s - 1

            print(d_idx,'d_idx')


            already_working = [p for p in self.people if self.schedule[p][d_idx] == 0]
            already_off     = [p for p in self.people if self.schedule[p][d_idx] == 1]
            current_unset   = [p for p in self.people if self.schedule[p][d_idx] == 2]
            assigned_workers = list(already_working)
            assigned_off     = list(already_off)
            workers_needed   = max(0, 4 - len(assigned_workers))


            # 1. ── MANDATORY FUTURE LOOK-AHEAD ──────────────────────────────────
            # If anyone's debt matches their remaining availability, they MUST work
            for p in list(current_unset):
                future_avail = sum(
                    1 for future_s in free_sundays[i:]
                    if self.schedule[p][future_s - 1] == 2
                )
                print('p',p,'future_available',future_avail, sunday_debt[p],'sunday debt')
                if sunday_debt[p] >= future_avail and workers_needed > 0:
                    print('assign bigger than futur debt',p)
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    sunday_debt[p] = max(0, sunday_debt[p] - 1)
                    workers_needed -= 1
                    current_unset.remove(p)

            # 2. ── YOUR NEW RULE: FORCE A OR B FIRST IF NEITHER IS WORKING ──────
            # Check if a or b is already in the assigned_workers pool
            if self.schedule['a'][d_idx] ==0 or  self.schedule['b'][d_idx] == 0:
                has_ab_coverage= True
            else:
                has_ab_coverage = False

            if not has_ab_coverage and workers_needed > 0:
                print('assign a or b')

                a_avail = True if self.schedule['a'][d_idx] == 2 else False
                b_avail = True if self.schedule['b'][d_idx] == 2 else False
                print(a_avail,b_avail, 'avail','bvail')

                if a_avail or b_avail:
                    if a_avail and b_avail:
                        # Assign the one with the most Sundays still in debt
                        chosen = 'a' if sunday_debt['a'] >= sunday_debt['b'] else 'b'
                    else:
                        chosen = 'a' if a_avail else 'b'

                    self.schedule[chosen][d_idx] = 0
                    print(chosen,'chosen')
                    print( assigned_workers,'aasigned workers')
                    assigned_workers.append(chosen)
                    sunday_debt[chosen] = max(0, sunday_debt[chosen] - 1)
                    workers_needed -= 1
                    print(assigned_workers,'assigned workers')
                    current_unset.remove(chosen)
                    print(current_unset,'current unset')




            def ab_score(p):
              if p in ['a', 'b']:
                  return 1   # first OR last depending on condition
              return 2

            unset_sorted = sorted(
                current_unset,
                key=lambda p: (

                    sunday_true_dynamic := (
                        sunday_debt[p]
                        - sum(
                            1 for future_s in free_sundays[i:]
                            if self.schedule[p][future_s - 1] ==2
                        )
                    ),ab_score(p),

                    -sunday_debt[p]
                ), reverse=True
            )
            print(unset_sorted,'unset_sorted')
            print('already off',already_off)
            print( 'already working',already_working)
            for p in list(unset_sorted):
                  if workers_needed <=0:

                    self.schedule[p][d_idx] = 1
                    assigned_off.append(p)
                    unset_sorted.remove(p)
                    sunday_flex[p] = min(0, sunday_flex[p] + 1)

                  else:
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    unset_sorted.remove(p)
                    sunday_debt[p] = max(0, sunday_debt[p] - 1)
                    workers_needed -= 1
                    print('assigned',p,'to workers')



            # Finalize day's off-status
            for p in assigned_off:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] = 1
                    sunday_flex[p] = min(0, sunday_flex[p] + 1)
            print(assigned_off,'assigned off')
            print(assigned_workers,'assignd workers')

            # 4. ── SAFETY PROMOTE ───────────────────────────────────────────────
            while len(assigned_workers) < 4 and assigned_off:
                promoted = sorted(assigned_off, key=lambda p: self.people.index(p))[0]
                self.schedule[promoted][d_idx] = 0
                assigned_workers.append(promoted)
                sunday_debt[promoted] = max(0, sunday_debt[promoted] - 1)
                sunday_flex[p] = min(0, sunday_flex[p] - 1)
                assigned_off.remove(promoted)
                print(assigned_workers,'did a promotion')

            for p in self.people:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] = 1
                    sunday_flex[p] = min(0, sunday_flex[p] + 1)
        print("Schedule after sundays pass:")
        for p in self.people:
            print(f"  {p}: {self.schedule[p]}")


    def fill_holidays(self):

                # Initialize your debt tracker

        free_h = [s for s in self.fixed_holidays if s not in self.forced_days]


        h_debt = {
        p: max(0, self.fixedh_quotas[p] - sum(1 for t in self.fixed_holidays if self.schedule[p][t - 1] == 0))
        for p in self.people
        }
        h_flex= {p: self.fixedh_quotas[p] - sum(1 for t in self.fixed_holidays if self.schedule[p][t - 1] == 0 or self.schedule[p][t-1]==2)
            for p in self.people
        }
      

        for i, s in enumerate(free_h):
            
            d_idx = s - 1

            print(d_idx,'d_idx')


            already_working = [p for p in self.people if self.schedule[p][d_idx] == 0]
            already_off     = [p for p in self.people if self.schedule[p][d_idx] == 1]
            current_unset   = [p for p in self.people if self.schedule[p][d_idx] == 2]
            assigned_workers = list(already_working)
            assigned_off     = list(already_off)
            workers_needed   = max(0, 4 - len(assigned_workers))
            for worker in list(current_unset):  # iterate over a copy
              if self._needs_holiday(worker, d_idx):

                  if h_flex[worker] <0:
                      self.schedule[worker][d_idx] = 1
                      h_flex[worker] = min(0, h_flex[worker] + 1)
                      assigned_off.append(worker)
                      current_unset.remove(worker)

              else:
                if self.must_work(worker, d_idx):
                  print('worker',worker,'must work,')
                  if h_debt[worker] > 0:
                    self.schedule[worker][d_idx] = 0
                    h_debt[worker] = max(0, h_debt[worker] - 1)

        

        free_h = [s for s in self.fixed_holidays if s not in self.forced_days]


        h_debt = {
        p: max(0, self.fixedh_quotas[p] - sum(1 for t in self.fixed_holidays if self.schedule[p][t - 1] == 0))
        for p in self.people
        }
        h_flex= {
            p: self.fixedh_quotas[p] - sum(1 for t in self.fixed_holidays if self.schedule[p][t - 1] == 0 or self.schedule[p][t-1]==2)
            for p in self.people
        }

        for i, s in enumerate(free_h):
            
            d_idx = s - 1

            print(d_idx,'d_idx')


            already_working = [p for p in self.people if self.schedule[p][d_idx] == 0]
            already_off     = [p for p in self.people if self.schedule[p][d_idx] == 1]
            current_unset   = [p for p in self.people if self.schedule[p][d_idx] == 2]
            assigned_workers = list(already_working)
            assigned_off     = list(already_off)
            workers_needed   = max(0, 4 - len(assigned_workers))


            # 1. ── MANDATORY FUTURE LOOK-AHEAD ──────────────────────────────────
            # If anyone's debt matches their remaining availability, they MUST work
            for p in list(current_unset):
                future_avail = sum(
                    1 for future_s in free_h[i:]
                    if self.schedule[p][future_s - 1] == 2
                )
                print('p',p,'future_available',future_avail, h_debt[p],'sunday debt')
                if h_debt[p] >= future_avail and workers_needed > 0:
                    print('assign bigger than futur debt',p)
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    h_debt[p] = max(0,h_debt[p] - 1)
                    workers_needed -= 1
                    current_unset.remove(p)

            # 2. ── YOUR NEW RULE: FORCE A OR B FIRST IF NEITHER IS WORKING ──────
            # Check if a or b is already in the assigned_workers pool
            if self.schedule['a'][d_idx] ==0 or  self.schedule['b'][d_idx] == 0:
                has_ab_coverage= True
            else:
                has_ab_coverage = False

            if not has_ab_coverage and workers_needed > 0:
                print('assign a or b')

                a_avail = True if self.schedule['a'][d_idx] == 2 else False
                b_avail = True if self.schedule['b'][d_idx] == 2 else False
                print(a_avail,b_avail, 'avail','bvail')

                if a_avail or b_avail:
                    if a_avail and b_avail:
                        # Assign the one with the most Sundays still in debt
                        chosen = 'a' if h_debt['a'] >= h_debt['b'] else 'b'
                    else:
                        chosen = 'a' if a_avail else 'b'

                    self.schedule[chosen][d_idx] = 0
                    print(chosen,'chosen')
                    print( assigned_workers,'aasigned workers')
                    assigned_workers.append(chosen)
                    h_debt[chosen] = max(0, h_debt[chosen] - 1)
                    workers_needed -= 1
                    print(assigned_workers,'assigned workers')
                    current_unset.remove(chosen)
                    print(current_unset,'current unset')




            def ab_score(p):
              if p in ['a', 'b']:
                  return 1   # first OR last depending on condition
              return 2

            unset_sorted = sorted(
                current_unset,
                key=lambda p: (

                    sunday_true_dynamic := (
                        h_debt[p]
                        - sum(
                            1 for future_s in free_h[i:]
                            if self.schedule[p][future_s - 1] ==2
                        )
                    ),ab_score(p),

                    -h_debt[p]
                ), reverse=True
            )
            for p in list(unset_sorted):
                print(p)
                x =h_debt[p]- sum(1 for future_s in free_h[i:] if self.schedule[p][future_s - 1] ==2)
                print(x)
                y= ab_score(p)
                z =-h_debt[p]
                print(y,'ab')
                print(z,'-hdebt')

            
                        

            for p in list(unset_sorted):
                  if workers_needed <=0:

                    self.schedule[p][d_idx] = 1
                    assigned_off.append(p)
                    unset_sorted.remove(p)
                    h_flex[p] = min(0, h_flex[p] + 1)

                  else:
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    unset_sorted.remove(p)
                    h_debt[p] = max(0, h_debt[p] - 1)
                    workers_needed -= 1
                    print('assigned',p,'to workers')



            # Finalize day's off-status
            for p in assigned_off:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] = 1
                    h_flex[p] = min(0, h_flex[p] + 1)
            print(assigned_off,'assigned off')
            print(assigned_workers,'assignd workers')

            # 4. ── SAFETY PROMOTE ───────────────────────────────────────────────
            while len(assigned_workers) < 4 and assigned_off:
                promoted = sorted(assigned_off, key=lambda p: self.people.index(p))[0]
                self.schedule[promoted][d_idx] = 0
                assigned_workers.append(promoted)
                h_debt[promoted] = max(0, h_debt[promoted] - 1)
                h_flex[p] = min(0, h_flex[p] - 1)
                assigned_off.remove(promoted)
                print(assigned_workers,'did a promotion')

            for p in self.people:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] = 1
                    h_flex[p] = min(0, h_flex[p] + 1)
        print("Schedule after sundays pass:")
        for p in self.people:
            print(f"  {p}: {self.schedule[p]}")


    

    def count_future_mandatory_work_before(self, p, d_idx):
        # How many Sundays has p already worked?
        sundays_worked = sum(1 for s in self.sundays if (s-1) < d_idx and self.schedule[p][s-1] == 0)
        sundays_remaining = max(0, self.sunday_quotas[p] - sundays_worked)

        # Forced days remaining
        forced_remaining = sum(1 for f in self.forced_days if f >= d_idx + 1 and f not in self.sundays)

        # Regular days remaining (neither sunday nor forced)
        regular_days_remaining = sum(
            1 for day_pos in range(d_idx , self.num_days)
            if (day_pos ) not in self.sundays and (day_pos ) not in self.forced_days
        )

        # On regular days, one of the pair works -> each carries 0.5
        return sundays_remaining + forced_remaining + (regular_days_remaining * 0.5)


    def count_future_mandatory_work(self, p, d_idx):
        total = 0

        for day_pos in range(d_idx, self.num_days):
            day_num = day_pos + 1
            cell = self.schedule[p][day_pos]

            # Already confirmed work
            if cell == 0:
                total += 1
                continue

            # Already confirmed holiday - contributes 0
            if cell == 1:
                continue

            # Unassigned - figure out how forced this day is
            if day_num in self.forced_days:
                total += 1
                continue

            if day_num in self.sundays:
                # Use sunday quota debt logic
                sundays_worked = sum(1 for s in self.sundays if (s-1) < day_pos and self.schedule[p][s-1] == 0)
                if self.sunday_quotas[p] - sundays_worked > 0:
                    total += 1
                continue

            # Regular unassigned day: count confirmed holidays from others
            others_off = sum(
                1 for other in self.people
                if other not in ['a', 'b']
                and self.schedule[other][day_pos] == 1
            )

            # If 3+ others have holidays, both a and b MUST work
            if others_off >= 3:
                total += 1.0
            # If 2 others have holidays, a or b must work (high probability)
            elif others_off == 2:
                total += 0.8
            # If 1 other has holiday, one of them probably needs to work
            elif others_off == 1:
                total += 0.6
            else:
                total += 0.5

        return total

    def get_workload_score(self, p):
        # Calculate how many holidays this person has had compared to others
        my_offs = sum(self.schedule[p])
        max_offs = max(sum(self.schedule[pers]) for pers in self.people)

        # If I have 2+ fewer holidays than the 'luckiest' person,
        # I get a small boost to help me catch up.
        if max_offs - my_offs >= 2:
            return 1
        return 0

    def holiday_blocks(self,schedular):
        """
        Counts consecutive holiday runs.
        O O O W O O W O  -> 3 blocks
        """
        blocks = 0
        in_block = False

        for x in schedular:
            if x == 1:
                if not in_block:
                    blocks += 1
                    in_block = True
            else:
                in_block = False

        return blocks


    def get_work_balance_score(self, p, d_idx):
      worked_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
      holidays_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 1)
      confirmed_future_work = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 0)
      unassigned_days = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 2)
      confirmed_future_holidays = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 1)


      remaining_work_needed = self.targets[p] - worked_so_far - confirmed_future_work
      available_days = unassigned_days

      remaining_holidays_needed = self.num_days - self.targets[p] - confirmed_future_holidays - holidays_so_far


      future = self.schedule[p][d_idx:]
      confirmed_blocks = self.holiday_blocks([x for x in future])

      if remaining_work_needed>= available_days:
          return 0
      elif (remaining_work_needed+confirmed_future_work)//5 + remaining_work_needed >= (available_days + (remaining_holidays_needed + confirmed_blocks)//4):
          return 2
      elif (remaining_work_needed+confirmed_future_work)//5  + remaining_work_needed >= available_days:
          return 1
      elif (remaining_work_needed+confirmed_future_work)//5  + remaining_work_needed+1 >= (available_days + (remaining_holidays_needed + confirmed_blocks)//4):
          return 2
      elif ((remaining_work_needed+confirmed_future_work)//5 + remaining_work_needed + 1) and (d_idx < self.num_days-6)>= available_days:
          return 2.5



      elif remaining_holidays_needed + (remaining_holidays_needed + confirmed_blocks)//4 >= available_days:
          return 5
      elif remaining_holidays_needed + (remaining_holidays_needed + confirmed_blocks)//4 +1 >= available_days and ((remaining_work_needed+confirmed_future_work)//5  + remaining_work_needed < self.num_days):
          return 4
      else:
          return 3



    def get_ab_combined_priority(self,p,d_idx):
        ab_pair = ('a', 'b')
        if p not in ab_pair:
            return 0

        # Combined target for the pair (e.g., 35 or 36)
        combined_target = self.targets[ab_pair[0]] + self.targets[ab_pair[1]]

        # 1. WORK DONE: How many days have A and B worked up to yesterday?
        work_done = sum(1 for d in range(d_idx) for pers in ab_pair if self.schedule[pers][d] == 0)

        # 2. TODAY'S IMPACT: If they both work today, that's +2 days
        today_impact = 2


        # If this total is higher than their combined budget,
        # the algorithm MUST prioritize giving one of them a holiday today.
        total_pairs = sum(
            1 for d in range(self.num_days)
            if self.schedule['a'][d] == 0 and self.schedule['b'][d] == 0
        )
        total_alone = sum(
            1 for d in range(self.num_days)
            if (self.schedule['a'][d] == 1 )
            or (self.schedule['b'][d] == 1 )
        )
        total_available = sum(
            1 for d in range(self.num_days)
            if (self.schedule['a'][d] == 2 and self.schedule['b'][d] == 2)
            or (self.schedule['a'][d] == 2 and self.schedule['b'][d] == 0)
            or (self.schedule['b'][d] == 2 and self.schedule['a'][d] == 0)
        )
        total_empty= sum(
            1 for d in range(self.num_days)
            if (self.schedule['a'][d] == 2 and self.schedule['b'][d] == 2))

        print(total_pairs,'total pairs')
        print(total_alone,'total alone')
        print(total_available,'total available')
        print(combined_target,'combined target')

        for d in range(self.num_days):
            a_cell = self.schedule['a'][d]
            b_cell = self.schedule['b'][d]
            if not ((a_cell == 2 and b_cell == 2) or
                    (a_cell == 2 and b_cell == 0) or
                    (b_cell == 2 and a_cell == 0)):
                continue  # not a flexible day

            day_num = d + 1
            if day_num in self.forced_days:
                total_pairs += 1  # contributes 2 work days
                total_available -=1
            elif day_num in self.sundays:
                # Only compute once per schedule (not per-day) — move this outside the loop
                # But if computing incrementally, here's the logic:

                # What's already locked in (1=work, 0=off, 2=flexible)
                if self.schedule['a'][day_num]==1:
                    self.schedule['b'][day_num]=0
                if self.schedule['b'][day_num]==1:
                    self.schedule['a'][day_num]=0

            elif day_num in self.fixed_holidays:
                # Only compute once per schedule (not per-day) — move this outside the loop
                # But if computing incrementally, here's the logic:

                # What's already locked in (1=work, 0=off, 2=flexible)
                if self.schedule['a'][day_num]==1:
                    self.schedule['b'][day_num]=0
                if self.schedule['b'][day_num]==1:
                    self.schedule['a'][day_num]=0

            else:
                continue
        a_worked = sum(1 for s in self.sundays if self.schedule['a'][s-1] == 0)
        b_worked = sum(1 for s in self.sundays if self.schedule['b'][s-1] == 0)

        # Already counted pairs (both == 1)
        already_pairs = sum(1 for s in self.sundays
                            if self.schedule['a'][s-1] == 0 and self.schedule['b'][s-1] == 0)
        total_pairs_should =  self.sunday_quotas['a'] + self.sunday_quotas['b'] - len(self.sundays)
        if already_pairs == total_pairs_should:
            pass

        else:
            total_pairs += total_pairs_should
            total_available-=1



        a_worked = sum(1 for s in self.fixed_holidays if self.schedule['a'][s-1] == 0)
        b_worked = sum(1 for s in self.fixed_holidays if self.schedule['b'][s-1] == 0)

        # Already counted pairs (both == 1)
        already_pairs = sum(1 for s in self.fixed_holidays
                            if self.schedule['a'][s-1] == 0 and self.schedule['b'][s-1] == 0)
        total_pairs_should =  self.fixedh_quotas['a'] + self.fixedh_quotas['b'] - len(self.fixed_holidays)
        if already_pairs == total_pairs_should:
            pass
        else:


            total_pairs += total_pairs_should
            total_available-=1






        # Total projected work for the pair
        projected_total = (total_pairs * 2) + total_alone + total_available +1
        combined_target = self.targets['a'] + self.targets['b']


        print(projected_total,'proj total')
        print(total_pairs,'total pairs')
        print(total_alone,'total alone')
        print(total_available,'total available')
        print(combined_target,'combined target')
        if combined_target < total_available + total_pairs*2 +1 + total_alone:
            return 50000


        else:
            return 0


    def _get_streak_debug(self, p, d_idx):
        hist = self.schedule[p][max(0, d_idx-8):d_idx]
        consec_work = 0
        for day in reversed(hist):
            if day == 0: consec_work += 1
            else: break
        return consec_work

    def balance_regular_days(self):

        for d_idx in range(self.num_days):
            print('d_idx = ',d_idx)
            day_num = d_idx + 1
            if day_num in self.forced_days:
                continue
            if day_num in self.sundays:
                continue
            if day_num in self.fixed_holidays:
                continue
            print(f"Day {d_idx+1}: " + " ".join(
                f"{p}={sum(1 for d in range(d_idx) if self.schedule[p][d]==0)}w/{sum(1 for d in range(d_idx) if self.schedule[p][d]==1)}off"
                for p in self.people
            ))
            print(f"B day {d_idx+1}: remaining={self.targets['b'] - sum(1 for d in range(d_idx) if self.schedule['b'][d]==0) - sum(1 for d in range(d_idx, self.num_days) if self.schedule['b'][d]==0)}, available={sum(1 for d in range(d_idx, self.num_days) if self.schedule['b'][d]==2)}, wbs={self.get_work_balance_score('b', d_idx)}")

            print(f"\n=== Day {d_idx+1} ===")
            for p in self.people:
                consec = self._get_streak_debug(p, d_idx)
                wbs = self.get_work_balance_score(p, d_idx)
                nht = self._needs_holiday_today(p, d_idx)
                mwt = self.must_work_today(p, d_idx)
                worked = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
                print(f"  {p}: consec_work={consec}, work_balance={wbs}, needs_holiday={nht}, must_work={mwt}, worked_so_far={worked}")



            # If too few are OFF, pick people to give holidays to
            current_off_people = [p for p in self.people if p not in ['a','b'] and self.schedule[p][d_idx] == 1]

            non_ab_working = [p for p in self.people if p in ['a', 'b'] and self.schedule[p][d_idx] != 1]
            if d_idx in [28,29]:
                print(non_ab_working,'non ab working')

            if len(non_ab_working) == 2 and self.current_off(d_idx) ==3 :

              ab_needs_holiday = self._needs_holiday_today('a', d_idx) or self._needs_holiday_today('b', d_idx)
              if ab_needs_holiday or self.get_ab_combined_priority('a', d_idx) > 0:
                  # Force the non-ab person who doesn't need holiday and has lowest priority to work
                  to_work = sorted(
                      [p for p in current_off_people if not self._needs_holiday_today(p, d_idx)],
                      key=lambda p: (self.get_work_balance_score(p, d_idx), -self.people.index(p))
                  )
                  if to_work:
                      self.schedule[to_work[0]][d_idx] = 0
                      print(f"  AB PRIORITY OVERRIDE: {to_work[0]} forced WORK day {d_idx+1}")

                      # Now give the holiday to whichever of a/b needs it most
                      ab_holiday = sorted(
                          [p for p in ['a', 'b'] if self.schedule[p][d_idx] != 1],
                          key=lambda p: (
                              self._needs_holiday_today(p, d_idx),
                              self.get_work_balance_score(p, d_idx),

                              self.rank_preferences_for_day(p,d_idx),
                              self.get_priority_score(p, d_idx),# 2. Your Streak Points (2nd holiday, etc)

                          ), reverse=True
                      )
                      if ab_holiday and self.schedule[ab_holiday[0]][d_idx] != 0:
                          self.schedule[ab_holiday[0]][d_idx] = 1
                          print(f"  AB HOLIDAY ASSIGNED: {ab_holiday[0]} OFF day {d_idx+1}")


            while self.current_off(d_idx) < 3:
                # Priority for Holiday:
                # 1. Not A or B (if the other is off)
                # 2. People with the MOST total work days so far
                # 3. Lower rank (G) preferred for holiday to keep A working
                # --- THE UPDATED SORTING KEY --- #



                candidates = sorted(self.people, key=lambda p: (
                  self.schedule[p][d_idx] == 2 and (not self.must_work_today(p, d_idx) or self._needs_holiday_today(p, d_idx)),
                  self._needs_holiday_today(p, d_idx),
                  self.get_work_balance_score(p, d_idx),
                            # 1. Must be working today
                  self.get_ab_combined_priority(p, d_idx), # 2. A/B Combined Priority
                  # SUBTRACT Urgency: If urgency is 10000, holiday score becomes -10000
                  self.rank_preferences_for_day(p,d_idx),
                  self.get_priority_score(p, d_idx),
                  # 2. Your Streak Points (2nd holiday, etc)
                  self.people.index(p)                    # 4. Rank Tie-breaker
                ), reverse=True)

                if d_idx + 2 in self.sundays:
                  get_workingcount = self.number_working_3_in_a_row(d_idx)
                  get_workingcount_people = list(get_workingcount.keys())
                  get_workingcount_people_length = len(get_workingcount_people)
                  for p in get_workingcount_people:
                      if self.schedule[p][d_idx]==1:
                        get_workingcount_people_length -=1
                        get_workingcount_people.remove(p)
                  if get_workingcount_people_length >= 3 and candidates[0] not in get_workingcount_people and self._needs_holiday_today(candidates[0],d_idx)!=True :
                      for i, p in enumerate(candidates):
                          if p in get_workingcount_people:
                              candidates.insert(0, candidates.pop(i))
                              break

                print('candidates0',candidates)

                if d_idx+1 in self.zeezwemmen:
                    candidates = sorted(self.people, key=lambda p: (
                    self.schedule[p][d_idx] == 2 and (not self.must_work_today(p, d_idx) or self._needs_holiday_today(p, d_idx)),
                    self._needs_holiday_today(p, d_idx),
                              # 1. Must be working today
                    self.get_ab_combined_priority(p, d_idx), # 2. A/B Combined Priority
                    # SUBTRACT Urgency: If urgency is 10000, holiday score becomes -10000
                    self.rank_preferences_for_day(p,d_idx),
                    # 2. Your Streak Points (2nd holiday, etc)
                    self.people.index(p)                    # 4. Rank Tie-breaker
                  ), reverse=True)



                for p in candidates:
                    if self.schedule[p][d_idx] == 1: continue
                    if p == 'a' and self.schedule['b'][d_idx] == 1: continue
                    if p == 'b' and self.schedule['a'][d_idx] == 1: continue

                    # Check consecutive rules
                    hist_work = self.schedule[p][max(0, d_idx-5):d_idx]
                    hist_off = self.schedule[p][max(0, d_idx-4):d_idx]

                    MAX_CONSECUTIVE_WORK = 5  # adjust to your rule

                    hist_work = self.schedule[p][max(0, d_idx - MAX_CONSECUTIVE_WORK):d_idx]
                    hist_off  = self.schedule[p][max(0, d_idx - 4):d_idx]



                    # Block if already had 4 consecutive holidays
                    if len(hist_off) >= 4 and all(x == 1 for x in hist_off):
                        continue


                    self.schedule[p][d_idx] = 1

                    break




          # Force highest-rank back to work if too many are off
            while self.current_off(d_idx) > 3:
                offs = [p for p in self.people if self.schedule[p][d_idx] == 1]
                if not offs:
                    break
                to_work = sorted(offs, key=lambda p: -self.get_work_balance_score(p, d_idx))[0]
                self.schedule[to_work][d_idx] = 0


            # Any remaining '2' entries default to WORK
            for p in self.people:
                if self.schedule[p][d_idx] == 2:
                  self.schedule[p][d_idx] = 0


        return self.schedule, self.num_days
    def _needs_holiday_today(self, p, d_idx):
        if self._needs_holiday(p, d_idx)==True:
            return True
        worked_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
        confirmed_future_work = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 0)
        unassigned_days = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 2)


        holidays_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 1)
        confirmed_future_holidays = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 1)


        hist = self.schedule[p][max(0, d_idx-5):d_idx]

        future = self.schedule[p][d_idx+1:min(d_idx+6,self.num_days)]
        near_future = self.schedule[p][d_idx+2:min(d_idx+8,self.num_days)]
        # Calculate streaks
        work_streak = 0
        off_streak = 0

        for day in hist:
            if day == 0:
                work_streak += 1
                off_streak = 0 # Reset off streak if we find work
            elif day == 1:
                off_streak += 1
                work_streak = 0 # Reset work streak if we find off
            else: # day == 2 (unassigned)
                work_streak = 0
                off_streak = 0 # Reset off streak if we find work

        work_streak_a = 0
        off_streak_a = 0
        if len(future) >1:
          for day in future[::-1]:
              if day == 0:
                  work_streak_a += 1
                  off_streak_a =0
              elif day == 1:
                  off_streak_a += 1
                  work_streak_a =0
              else:
                  work_streak_a=0
                  off_streak_a=0
        work_streak_n = 0
        off_streak_n = 0
        if len(near_future) > 1 :
            for day in near_future[::-1]:
                if day == 0:
                    work_streak_n += 1
                    off_streak_n= 0 # Reset off streak if we find work
                elif day == 1:
                    off_streak_n += 1
                    work_streak_n = 0
                else:
                    work_streak_n = 0
                    off_streak_n = 0

        if work_streak + work_streak_a >=5:
            print('need holiday today, because reached maximum')
            return True
        if off_streak >=3 and work_streak_n>=5:
            return False
        if work_streak >=4 and off_streak_n >=4:
            print('needs holiday today for future')
            return True
        if work_streak_a + work_streak >=4:
            unassigned_days-=1

        target_work_days = self.targets[p]
        remaining_work_needed = target_work_days - worked_so_far - confirmed_future_work
        available_days = unassigned_days  # days still flexible
        #print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)

        if self.schedule[p][d_idx] ==2 and remaining_work_needed >= available_days:
            print('needs work today',d_idx,p)
            return False

        # ── off-budget check: must take holiday ────────────────
        target_off_days = self.num_days - self.targets[p]
        remaining_off_needed = target_off_days - holidays_so_far - confirmed_future_holidays
          # days still flexible
        #print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)
        if self.schedule[p]==2 and (remaining_off_needed + (remaining_off_needed +confirmed_future_holidays)//4 >= available_days):
            print('needs holiday today (off budget)', d_idx, p)
            return True

        return False

    def _needs_holiday(self, p, d_idx):
        worked_so_far = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 0)
        unassigned_days = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 2)
        holidays_so_far = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 1)

        for past_d in range(max(0, d_idx - 5), d_idx):
            if self.schedule[p][past_d] == 2:  # still unassigned
                # Check if this past day was a Sunday
                # Assumes day 0 = Monday; adjust offset if your week starts differently
                if past_d+1 in self.sundays:  # Sunday
                    # Next day is a Sunday
                    sundays_worked = sum(1 for s in self.sundays if self.schedule[p][s-1] == 0)

                    sundays_remaining = sum(1 for s in self.sundays if self.schedule[p][s-1] == 2)
                    sunday_debt = self.sunday_quotas[p] - sundays_worked
                    if sunday_debt >=sundays_remaining and (self.schedule[p][past_d] == 2):
                        # Still have Sunday work quota to fill → work on Sunday
                        self.schedule[p][past_d] = 0


                if past_d+1 in self.fixed_holidays:  # Sunday
                    # Next day is a Sunday
                    fholidays_worked = sum(1 for s in self.fixed_holidays if self.schedule[p][s-1] == 0)

                    fholidays_remaining = sum(1 for s in self.fixed_holidays if self.schedule[p][s-1] == 2)
                    fholidays_debt = self.fixedh_quotas[p] - fholidays_worked
                    if fholidays_debt >=fholidays_remaining and (self.schedule[p][past_d] == 2):
                        # Still have Sunday work quota to fill → work on Sunday
                        self.schedule[p][past_d] = 0
                if self.schedule[p][past_d] == 2:
                    simulated = self.schedule[p].copy()
                    simulated[past_d] = 0  # imagine sunday/holiday worked
                    simulated[d_idx] = 0   # imagine today worked

                    # count streak around past_d
                    streak = 0
                    max_streak = 0
                    for d in range(max(0, past_d - 4), min(self.num_days, d_idx + 1)):
                        if simulated[d] == 0:
                            streak += 1
                            max_streak = max(max_streak, streak)
                        else:
                            streak = 0

                    if max_streak > 5:
                      if past_d+1 in self.fixed_holidays:
                        # would create too long a streak -> try assign off
                        fholidays_worked = sum(1 for s in self.fixed_holidays if self.schedule[p][s-1] == 0)

                        fholidays_remaining = sum(1 for s in self.fixed_holidays if self.schedule[p][s-1] == 2)
                        fholidays_debt = self.fixedh_quotas[p] - fholidays_worked
                        if fholidays_debt >=fholidays_remaining and (self.schedule[p][past_d] == 2):
                            # Still have Sunday work quota to fill → work on Sunday
                            self.schedule[p][past_d] = 0
                            return True
                        else:
                            self.schedule[p][past_d] = 1
                      if past_d+1 in self.sundays:  # Sunday
                        # Next day is a Sunday
                        sundays_worked = sum(1 for s in self.sundays if self.schedule[p][s-1] == 0)

                        sundays_remaining = sum(1 for s in self.sundays if self.schedule[p][s-1] == 2)
                        sunday_debt = self.sunday_quotas[p] - sundays_worked
                        if sunday_debt >=sundays_remaining and (self.schedule[p][past_d] == 2):
                            # Still have Sunday work quota to fill → work on Sunday
                            self.schedule[p][past_d] = 0
                            return True
                        else:
                            self.schedule[p][past_d] = 1


        hist = self.schedule[p][max(d_idx-5,0):d_idx]

        future = self.schedule[p][d_idx+1:min(d_idx+6,self.num_days)]
        near_future = self.schedule[p][d_idx+2:min(d_idx+8,self.num_days)]
        # Calculate streaks
        work_streak = 0
        off_streak = 0

        for day in hist:
            if day == 0:
                work_streak += 1
                off_streak = 0 # Reset off streak if we find work
            elif day == 1:
                off_streak += 1
                work_streak = 0 # Reset work streak if we find off
            else: # day == 2 (unassigned)
                work_streak = 0
                off_streak = 0 # Reset off streak if we find work

        work_streak_a = 0
        off_streak_a = 0
        if len(future) >1:
          for day in future[::-1]:
              if day == 0:
                  work_streak_a += 1
                  off_streak_a =0
              elif day == 1:
                  off_streak_a += 1
                  work_streak_a =0
              else:
                  work_streak_a=0
                  off_streak_a=0
        work_streak_n = 0
        off_streak_n = 0
        if len(near_future) > 1 :
            for day in near_future[::-1]:
                if day == 0:
                    work_streak_n += 1
                    off_streak_n= 0 # Reset off streak if we find work
                elif day == 1:
                    off_streak_n += 1
                    work_streak_n = 0
                else:
                    work_streak_n = 0
                    off_streak_n = 0

        if work_streak + work_streak_a >=5:
            print('need holiday today, because reached maximum')
            return True
        if off_streak >=3 and work_streak_n>=5:
            return False
        if work_streak >=4 and off_streak_n >=4:
            print('needs holiday today for future')
            return True
        if work_streak_a + work_streak >=4:
            unassigned_days-=1






        # ── off-budget check: must take holiday ────────────────
        target_off_days = self.num_days - self.targets[p]
        remaining_off_needed = target_off_days - holidays_so_far

        if self.schedule[p][d_idx] ==2 and remaining_off_needed >= unassigned_days:
            return True



        target_work_days = self.targets[p]
        remaining_work_needed = target_work_days - worked_so_far
        #print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)



        worked_total = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 0)
        if self.schedule[p][d_idx] == 2 and worked_total >= self.targets[p]:
            print(f'over target, needs holiday {d_idx} {p}')
            return True

        target_work_days = self.targets[p]
        remaining_work_needed = target_work_days - worked_so_far
        available_days = unassigned_days  # days still flexible
        #print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)

        if self.schedule[p][d_idx] ==2 and remaining_work_needed >= unassigned_days:
            print('needs work today',d_idx,p)
            return False



        return False



    def must_work_today(self,p, d_idx):
        """
        Returns True if giving this person a holiday today is mathematically impossible
        — i.e. they have no holiday budget left, or every remaining day must be work.
        """
        # No holiday budget left
        if self.must_work(p,d_idx) ==True:
            return True
        worked_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
        confirmed_future_work = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 0)
        unassigned_days = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 2)



        target_work_days = self.targets[p]
        remaining_work_needed = target_work_days - worked_so_far - confirmed_future_work
        available_days = unassigned_days  # days still flexible
        if d_idx==28:
            print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)
            print(confirmed_future_work,'confirmed_futureWork')


        if remaining_work_needed >= available_days:
            return True




        return False

    def must_work(self,p, d_idx):
        """
        Returns True if giving this person a holiday today is mathematically impossible
        — i.e. they have no holiday budget left, or every remaining day must be work.
        """
        # No holiday budget left
        worked_so_far = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 0)
        unassigned_days = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 2)


        hist = self.schedule[p][max(0, d_idx-5):d_idx]
        future = self.schedule[p][d_idx+1:min(d_idx+6,self.num_days)]
        near_future = self.schedule[p][d_idx+2:min(d_idx+8,self.num_days)]


        # Calculate streaks
        work_streak = 0
        off_streak = 0

        for day in hist:
            if day == 0:
                work_streak += 1
                off_streak = 0 # Reset off streak if we find work
            elif day == 1:
                off_streak += 1
                work_streak = 0 # Reset work streak if we find off
            else:
                work_streak = 0
                off_streak = 0 # Reset off streak if we find work

        work_streak_a = 0
        off_streak_a = 0
        if len(future) >1:
            for day in future[::-1]:
                if day == 0:
                    work_streak_a += 1
                    off_streak_a =0
                elif day == 1:
                    off_streak_a += 1
                    work_streak_a =0
                else:
                    work_streak_a=0
                    off_streak_a=0
        work_streak_n = 0
        off_streak_n = 0
        if len(near_future) > 1 :
            for day in near_future[::-1]:
                if day == 0:
                    work_streak_n += 1
                    off_streak_n= 0 # Reset off streak if we find work
                elif day == 1:
                    off_streak_n += 1
                    work_streak_n = 0
                else:
                    work_streak_n = 0
                    off_streak_n = 0

        if work_streak_a + work_streak >=4:
            unassigned_days-=1

        target_work_days = self.targets[p]
        remaining_work_needed = target_work_days - worked_so_far
        available_days = unassigned_days  # days still flexible
        #print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)

        if work_streak_a + work_streak >=5:
            return False
        if off_streak_a + off_streak >=4:
          return True
        if (work_streak+work_streak_a ==4) and off_streak_n ==4:
          return False

        if self.schedule[p][d_idx] ==2 and remaining_work_needed >= available_days:
            return True




        return False

    def rank_preferences_for_day(self, p, d_idx):
        """
        Returns a sorted list of (person, score) for all people who have a preference
        for the given day (1-based), ranked by tier then by person order.
        """
        tier_scores = {'high': 1000, 'mid': 300, 'low': 150}
        day = d_idx +1
        for tier, score in tier_scores.items():
            if day in self.prefs[p].get(tier, []):
                person_bonus = (len(self.people) - self.people.index(p))
                return score + person_bonus

        return 0

    def get_priority_score(self,p, d_idx):
        # Get history of last 4 days
        hist = self.schedule[p][max(0, d_idx-5):d_idx]
        future = self.schedule[p][d_idx+1:min(d_idx+6,31)]
        near_future = self.schedule[p][d_idx+2:min(d_idx+8,31)]
        # Calculate streaks
        work_streak = 0
        off_streak = 0

        for day in hist:
            if day == 0:
                work_streak += 1
                off_streak = 0 # Reset off streak if we find work
            elif day == 1:
                off_streak += 1
                work_streak = 0 # Reset work streak if we find off
            else: # day == 2 (unassigned)
                work_streak = 0
                off_streak = 0 # Reset off streak if we find work

        work_streak_a = 0
        off_streak_a = 0
        if len(future) >1:
          for day in future[::-1]:
              if day == 0:
                  work_streak_a += 1
                  off_streak_a =0
              elif day == 1:
                  off_streak_a += 1
                  work_streak_a =0
              else:
                  work_streak_a=0
                  off_streak_a=0
        work_streak_n = 0
        off_streak_n = 0
        if len(near_future) > 1 :
            for day in near_future[::-1]:
                if day == 0:
                    work_streak_n += 1
                    off_streak_n= 0 # Reset off streak if we find work
                elif day == 1:
                    off_streak_n += 1
                    work_streak_n = 0
                else:
                    work_streak_n = 0
                    off_streak_n = 0
        if p =='b':
          print(work_streak_n, work_streak)
        # YOUR SPECIFIC RANKING (Mapped to points):
        # 1. 1 holiday yesterday -> Highest (700 pts)
        # 2. 2 holidays yesterday -> (600 pts)
        # 3. Worked 4 days -> (500 pts)
        # 4. Worked 3 days -> (400 pts)
        # 5. 3 holidays yesterday -> (300 pts)
        # 6. Worked 2 days -> (200 pts)
        # 7. Worked 1 day -> (100 pts)


        ratios = []
        for pp in self.people:

            row = self.schedule[pp]

            zeros = sum(
                1 for d in range(d_idx)
                if d < len(row) and row[d] == 0
            )

            ones = sum(
                1 for d in range(d_idx)
                if d < len(row) and row[d] == 1
            )

            ratio = zeros / max(1, ones)
            ratios.append(ratio)

        avg_ratio = sum(ratios) / len(self.people)

        diff_per_person = {
            pp: ratios[i] - avg_ratio
            for i, pp in enumerate(self.people)
        }
        diff =diff_per_person[p]*100



        off_streak_t = off_streak_a + off_streak
        work_streak_t = work_streak_a + work_streak

        if work_streak_t ==4 and off_streak_n ==4: return 1000 +diff
        if off_streak_t ==3 and work_streak_n ==5: return 0
        if off_streak_t == 4: return 0
        if work_streak_t == 5: return 1000 +diff

        if off_streak_t == 1: return 600 +diff
        if work_streak_a ==4 or work_streak ==4: return 800  +diff


        if off_streak_a >0 and off_streak >0 and off_streak_t ==3: return 500  +diff

        if off_streak_t == 2: return 400 +diff
        if work_streak ==2 and work_streak_t == 4: return 375+diff

        if off_streak_t == 3: return 350 +diff
        if work_streak > 0 and work_streak_a>0 and work_streak_t == 4: return 300 +diff


        if work_streak_t == 2 and work_streak_a ==1: return 0
        if work_streak_t == 2: return 200 + diff

        if work_streak_t == 1: return 50 + diff
        if work_streak_t == 3 and work_streak_a in [3,0]: return 450  +diff
        if work_streak_t == 3 and work_streak_a==3: return 450 + diff
        if work_streak_t ==3 and work_streak_a in [2,1]: return 100 + diff
        return 0


    # ─────────────────────────────────────────────
    # RULE CHECKS
    # ─────────────────────────────────────────────
    def _can_take_holiday(self, p, d_idx):
      # already off
      if self.schedule[p][d_idx] == 1:
          print('alreadu off')
          return True

      # A/B constraint
      partner = 'b' if p == 'a' else ('a' if p == 'b' else None)
      if partner and self.schedule[partner][d_idx] == 1:
          print('partner has taken')
          return False
      if self.current_off(d_idx) >=3:
          print('too many off')
          return False
      if self.current_off(d_idx) ==2:
          for pp in self.people:
              if self.schedule[pp][d_idx]!=1:
                if self._needs_holiday_today(pp, d_idx) and pp !=p:
                    self.schedule[pp][d_idx] =1
                    self.schedule[p][d_idx]=0
                    print('someone else needs holiday')
                    return False
          if p not in ['a','b']:
              print('d',d_idx)
              print(self.get_ab_combined_priority('a',d_idx), 'ab priority')
              if self.get_ab_combined_priority('a',d_idx) >0 and self.schedule['a'][d_idx] !=1 and self.schedule['b'][d_idx]!=1:
                  for pp in self.people:
                      if self.schedule[pp][d_idx]==2:
                          if self._needs_holiday_today(pp, d_idx)==False and pp !=p and pp not in ['a','b']:
                              self.schedule[pp][d_idx] =0
                  return False
      if self.current_off(d_idx) >=1:
          needs_holiday_index = 0
          current_off_people = list(x for x in self.people if self.schedule[x][d_idx] == 1)
          print(current_off_people,'current off people')
          for pp in self.people:
              if self.schedule[pp][d_idx]!=1 and pp !=p:
                print(pp,'p','needs holiday',self._needs_holiday_today(pp, d_idx))
                if self._needs_holiday_today(pp, d_idx) == True and pp not in current_off_people: needs_holiday_index +=1
          print(needs_holiday_index,'so many people need a holiday')
          if needs_holiday_index + self.current_off(d_idx) >= 3:
              self.schedule[p][d_idx] =0
              print('too many people need a holiday')
              return False

      # 4-consecutive-off check
      hist_off = self.schedule[p][max(0, d_idx - 4):d_idx]
      if len(hist_off) >= 4 and all(x == 1 for x in hist_off):
          self.schedule[p][d_idx] = 0
          return False
      if partner:
        hist_work_partner = self.schedule[partner][max(0, d_idx - 5):d_idx]
        if len(hist_work_partner) >= 5 and all(x == 0 for x in hist_work_partner):
            self.schedule[partner][d_idx] = 1
            self.schedule[p][d_idx] = 0
            return False


      # total holiday budget
      holiday_target = self.num_days - self.targets[p]
      holidays_taken = sum(1 for v in self.schedule[p] if v == 1)
      if holidays_taken >= holiday_target:
          print('taken too many holidays taken')
          return False

      confirmed_work = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 0)
      holidays_confirmed = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 1)
      unassigned_days = sum(1 for d in range(self.num_days) if self.schedule[p][d] == 2)


      remaining_work_needed = self.targets[p] - confirmed_work
      available_days = unassigned_days

      remaining_holidays_needed = self.num_days - self.targets[p] - holidays_confirmed


      future = self.schedule[p][:]

      confirmed_blocks = self.holiday_blocks([x for x in future])
      x = max(0,(remaining_work_needed)//5 -confirmed_blocks)



      if remaining_work_needed + x >= available_days:
          return False

      # sunday-specific checks
      day_num = d_idx + 1
      if day_num in self.sundays:
          # can't take more sunday-offs than budget allows
          sunday_off_budget = len(self.sundays) - self.sunday_quotas.get(p, 0)
          sundays_already_off = sum(1 for s in self.sundays if self.schedule[p][s - 1] == 1)
          print(p, sunday_off_budget, sundays_already_off)
          if sundays_already_off >= sunday_off_budget:
              print('SUNDAY not allowed')
              return False


          available_sundays= sum(
              1
              for s in self.sundays
              if self.schedule[p][s - 1] in (0, 2)
          )
          # can't take this sunday off if debt can't be fulfilled on remaining sundays
          current_debt = self.sunday_quotas.get(p, 0) - sum(
              1 for s in self.sundays if self.schedule[p][s - 1] == 1
          )

          if current_debt >= available_sundays:
              return False
      if day_num in self.fixed_holidays:
            # can't take more sunday-offs than budget allows
            fixed_holidays_off_budget = len(self.fixed_holidays) - self.fixedh_quotas.get(p, 0)
            fixed_holidays_already_off = sum(1 for s in self.fixed_holidays if self.schedule[p][s - 1] == 1)
            if fixed_holidays_already_off >= fixed_holidays_off_budget:
                print('HOLIDAY not allowed')
                return False


            available_fixedh= sum(
                1
                for s in self.fixed_holidays
                if self.schedule[p][s - 1] in (0, 2)
            )
            # can't take this sunday off if debt can't be fulfilled on remaining sundays
            current_debt = self.fixedh_quotas.get(p, 0) - sum(
                1 for s in self.fixed_holidays if self.schedule[p][s - 1] == 1
            )

            if current_debt >= available_fixedh:
                return False



      return True


    # ─────────────────────────────────────────────
    # EXPORT
    # ─────────────────────────────────────────────
    def save_csv(self, filename="schedule.csv"):
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)

            header = ["Name"] + [f"{i+1}" for i in range(self.num_days)]
            writer.writerow(header)

            for p in self.people:
                row = ["OFF" if x == 1 else "WORK" for x in self.schedule[p]]
                writer.writerow([p.upper()] + row)

    def to_dataframe(self):
        data = []

        # Daily schedule
        for d_idx in range(self.num_days):
            current_day = self.start + timedelta(days=d_idx)

            row = {
                "Date": current_day.strftime("%Y-%m-%d")
            }

            for p in self.people:
                row[p.upper()] = "OFF" if self.schedule[p][d_idx] == 1 else "WORK"

            data.append(row)

        # Totals
        total_work = {"Date": "Total Work Days"}
        total_sunday = {"Date": "Total Sundays Worked"}
        total_fixed = {"Date": "Total Fixed Holidays Worked"}

        for p in self.people:
            total_work[p.upper()] = sum(x == 0 for x in self.schedule[p])

            total_sunday[p.upper()] = sum(
                self.schedule[p][s-1] == 0
                for s in self.sundays
            )

            total_fixed[p.upper()] = sum(
                self.schedule[p][h-1] == 0
                for h in self.fixedh
            )

        data.append(total_work)
        data.append(total_sunday)
        data.append(total_fixed)

        return pd.DataFrame(data)