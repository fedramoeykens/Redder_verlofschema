import calendar
import csv
from datetime import datetime, timedelta
from datetime import date

class ScheduleMaker:

    def __init__(self, people=None):
        self.people = people or ['a', 'b', 'c', 'd', 'e', 'f', 'g']

    # ─────────────────────────────────────────────
    # CORE ENTRY POINT
    # ─────────────────────────────────────────────
    def generate(self, start_date, end_date, forced_days,
                 sunday_quotas, prefs, targets, fixed_holidays,fixed_holidays_quotas):

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

        # Sundays
        self.sundays = [
            i + 1
            for i in range(self.num_days)
            if (start + timedelta(days=i)).weekday() == 6
        ]

        # ── PIPELINE ─────────────────────────────
        self.apply_forced_days()
        self.apply_fixed_holidays()
        print("\n── fixed holidays summary ──")

        print(self.schedule)
        self.apply_preference_pass()
        self.fill_sundays()
        self.balance_regular_days()

        return self.schedule, self.num_days

    # ─────────────────────────────────────────────
    # PASS 1
    # ─────────────────────────────────────────────
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
                    self._needs_holiday_today(p, d_idx),

                      self.get_priority_score(p, d_idx )                # 4. Rank Tie-breaker
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



            if (d_idx + 1) in self.sundays:
                  get_workingcount = self.number_working_3_in_a_row(d_idx)
                  get_workingcount_people = list(get_workingcount.keys())
                  get_wourkingcount_people_length = len(get_workingcount_people)
                  if ['a','b'] not in get_workingcount_people:
                      get_wourkingcount_people_length +=1


                  if len(get_workingcount_people) >= 4:
                      if p in get_workingcount_people:
                        pass
                      else:
                        candidates = sorted(self.people , key=lambda p: (
                          self._needs_holiday_today(p, d_idx),

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





            self.schedule[p][d_idx] = 1
            if self.current_off(d_idx) >= 3:
              for other in self.people:
                  if self.schedule[other][d_idx] == 2:
                      self.schedule[other][d_idx] = 0

            if self.current_off(d_idx) >=2 and p not in ['a','b']:
              print('check current of validation')
              for other in self.people:
                if other not in ['a','b',p]:
                  if self.schedule[other][d_idx] == 2 and self._needs_holiday_today(other,d_idx) == False:
                      self.schedule[other][d_idx] = 0
              needs_holiday_sum = 0
              for other in self.people:
                if self._needs_holiday_today(other,d_idx) == True:
                    if other not in ['a','b',p]:
                      needs_holiday_sum +=1

              if needs_holiday_sum >= 1:
                if self.get_ab_combined_priority('a',d_idx) >0:
                  self.schedule[p][d_idx] = 0
                  return False
                  print('could not get holiday due to priority')
                else:
                  if needs_holiday_sum ==1:
                    if self._needs_holiday_today('a',d_idx) == False and self._needs_holiday_today('b',d_idx)==False:
                      self.schedule['a'][d_idx] = 0
                      self.schedule['b'][d_idx] = 0
                    else:
                      print('could not get holiday due to needing holiday for A/B')
                      self.schedule[p][d_idx] =0
                      return False


            if self.current_off(d_idx) >=1 and p not in ['a','b']:
              print('check current of validation')

              needs_holiday_sum = 0
              for other in self.people:
                if self._needs_holiday_today(other,d_idx) == True:
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
                      if self._needs_holiday_today('a',d_idx) == False and self._needs_holiday_today('b',d_idx)==False and not ((self.schedule['a'] or self.schedule['b']) ==1) :
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
        sunday_debt = {
            p: max(0, self.sunday_quotas[p] - sum(1 for s in self.sundays if self.schedule[p][s - 1] == 0))
            for p in self.people
        }

        free_sundays = [s for s in self.sundays if s not in self.forced_days]

        for i, s in enumerate(free_sundays):
            d_idx = s - 1

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
                    if self.schedule[p][future_s - 1] == 0 or self.schedule[p][future_s - 1] == 2
                )
                if sunday_debt[p] >= future_avail and workers_needed > 0:
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    sunday_debt[p] = max(0, sunday_debt[p] - 1)
                    workers_needed -= 1
                    current_unset.remove(p)

            # 2. ── YOUR NEW RULE: FORCE A OR B FIRST IF NEITHER IS WORKING ──────
            # Check if a or b is already in the assigned_workers pool
            has_ab_coverage = any(p in assigned_workers for p in ['a', 'b'])

            if not has_ab_coverage and workers_needed > 0:
                a_avail = 'a' in current_unset
                b_avail = 'b' in current_unset

                if a_avail or b_avail:
                    if a_avail and b_avail:
                        # Assign the one with the most Sundays still in debt
                        chosen = 'a' if sunday_debt['a'] >= sunday_debt['b'] else 'b'
                    else:
                        chosen = 'a' if a_avail else 'b'

                    self.schedule[chosen][d_idx] = 0
                    assigned_workers.append(chosen)
                    sunday_debt[chosen] = max(0, sunday_debt[chosen] - 1)
                    workers_needed -= 1
                    current_unset.remove(chosen)


            # 3. ── YOUR NEW RULE: SORT OTHERS, PUTTING THE OTHER A/B LAST ───────
            def get_priority(p):
                # Determine who the "other" person is
                # If 'a' is working, 'b' is the other. If 'b' is working, 'a' is the other.
                # If neither is working yet (e.g. both are unavailable), this won't trigger.
                is_the_other_ab = p in ['a', 'b'] and any(x in assigned_workers for x in ['a', 'b'] if x != p)

                future_avail = sum(
                    1 for future_s in free_sundays[i:]
                    if self.schedule[p][future_s - 1] == 0 or self.schedule[p][future_s - 1] == 2
                )
                sunday_true_dynamic = sunday_debt[p] - future_avail

                # Tuple sorting priority:
                # Pass 1: Is this the duplicate A/B? (False/0 comes before True/1, pushing them to the back)
                # Pass 2: Deficit calculation (-sunday_true_dynamic)
                # Pass 3: Remaining raw debt (-sunday_debt)
                # Pass 4: Alphabetical tie-breaker
                return (is_the_other_ab, -sunday_true_dynamic, -sunday_debt[p], self.people.index(p))

            unset_sorted = sorted(current_unset, key=get_priority)

            # Fill remaining slots using the new sorted list
            for p in unset_sorted:
                if workers_needed > 0:
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    sunday_debt[p] = max(0, sunday_debt[p] - 1)
                    workers_needed -= 1
                else:
                    assigned_off.append(p)

            # Finalize day's off-status
            for p in assigned_off:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] = 1

            # 4. ── SAFETY PROMOTE ───────────────────────────────────────────────
            while len(assigned_workers) < 4 and assigned_off:
                promoted = sorted(assigned_off, key=lambda p: self.people.index(p))[0]
                self.schedule[promoted][d_idx] = 0
                assigned_workers.append(promoted)
                sunday_debt[promoted] = max(0, sunday_debt[promoted] - 1)
                assigned_off.remove(promoted)

        for p in self.people:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] == 1
        print("Schedule after preference pass:")
        for p in self.people:
            print(f"  {p}: {self.schedule[p]}")
    def apply_fixed_holidays(self):

                # Initialize your debt tracker
        fixedh_debt = {
            p: max(0, self.fixedh_quotas[p] - sum(1 for s in self.fixedh if self.schedule[p][s - 1] == 0))
            for p in self.people
        }

        free_fixedh = [s for s in self.fixedh if s not in self.forced_days]

        for i, s in enumerate(free_fixedh):
            d_idx = s - 1

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
                    1 for future_s in free_fixedh[i:]
                    if self.schedule[p][future_s - 1] == 0 or self.schedule[p][future_s - 1] == 2
                )
                if fixedh_debt[p] >= future_avail and workers_needed > 0:
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    fixedh_debt[p] = max(0, fixedh_debt[p] - 1)
                    workers_needed -= 1
                    current_unset.remove(p)

            # 2. ── YOUR NEW RULE: FORCE A OR B FIRST IF NEITHER IS WORKING ──────
            # Check if a or b is already in the assigned_workers pool
            has_ab_coverage = any(p in assigned_workers for p in ['a', 'b'])

            if not has_ab_coverage and workers_needed > 0:
                a_avail = 'a' in current_unset
                b_avail = 'b' in current_unset

                if a_avail or b_avail:
                    if a_avail and b_avail:
                        # Assign the one with the most Sundays still in debt
                        chosen = 'a' if fixedh_debt['a'] >= fixedh_debt['b'] else 'b'
                    else:
                        chosen = 'a' if a_avail else 'b'

                    self.schedule[chosen][d_idx] = 0
                    assigned_workers.append(chosen)
                    fixedh_debt[chosen] = max(0, fixedh_debt[chosen] - 1)
                    workers_needed -= 1
                    current_unset.remove(chosen)


            # 3. ── YOUR NEW RULE: SORT OTHERS, PUTTING THE OTHER A/B LAST ───────
            def get_priority(p):
                # Determine who the "other" person is
                # If 'a' is working, 'b' is the other. If 'b' is working, 'a' is the other.
                # If neither is working yet (e.g. both are unavailable), this won't trigger.
                is_the_other_ab = p in ['a', 'b'] and any(x in assigned_workers for x in ['a', 'b'] if x != p)

                future_avail = sum(
                    1 for future_s in free_fixedh[i:]
                    if self.schedule[p][future_s - 1] == 0 or self.schedule[p][future_s - 1] == 2
                )
                sunday_true_dynamic = fixedh_debt[p] - future_avail

                # Tuple sorting priority:
                # Pass 1: Is this the duplicate A/B? (False/0 comes before True/1, pushing them to the back)
                # Pass 2: Deficit calculation (-sunday_true_dynamic)
                # Pass 3: Remaining raw debt (-sunday_debt)
                # Pass 4: Alphabetical tie-breaker
                return (is_the_other_ab, -sunday_true_dynamic, -fixedh_debt[p], self.people.index(p))

            unset_sorted = sorted(current_unset, key=get_priority)

            # Fill remaining slots using the new sorted list
            for p in unset_sorted:
                if workers_needed > 0:
                    self.schedule[p][d_idx] = 0
                    assigned_workers.append(p)
                    fixedh_debt[p] = max(0, fixedh_debt[p] - 1)
                    workers_needed -= 1
                else:
                    assigned_off.append(p)

            # Finalize day's off-status
            for p in assigned_off:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] = 1

            # 4. ── SAFETY PROMOTE ───────────────────────────────────────────────
            while len(assigned_workers) < 4 and assigned_off:
                promoted = sorted(assigned_off, key=lambda p: self.people.index(p))[0]
                self.schedule[promoted][d_idx] = 0
                assigned_workers.append(promoted)
                fixedh_debt[promoted] = max(0, fixedh_debt[promoted] - 1)
                assigned_off.remove(promoted)

        for p in self.people:
                if self.schedule[p][d_idx] == 2:
                    self.schedule[p][d_idx] == 1
        print("Schedule after Fixed Holidays")
        for p in self.people:
            print(f"  {p}: {self.schedule[p]}")



    def count_future_mandatory_work(self, p, d_idx):
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




    def get_workload_score(self, p):
        # Calculate how many holidays this person has had compared to others
        my_offs = sum(self.schedule[p])
        max_offs = max(sum(self.schedule[pers]) for pers in self.people)

        # If I have 2+ fewer holidays than the 'luckiest' person,
        # I get a small boost to help me catch up.
        if max_offs - my_offs >= 2:
            return 1
        return 0


    def get_work_balance_score(self, p, d_idx):
      worked_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
      holidays_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 1)
      confirmed_future_work = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 0)
      unassigned_days = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 2)
      confirmed_future_holidays = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 1)
      x = -1 if confirmed_future_holidays >= 1 else 0
      x = -2 if confirmed_future_holidays >= 3 else x

      remaining_work_needed = self.targets[p] - worked_so_far - confirmed_future_work
      available_days = unassigned_days

      remaining_holidays_needed = self.num_days - self.targets[p] - confirmed_future_holidays - holidays_so_far


      if remaining_work_needed>= available_days:
          return 0
      elif (remaining_work_needed+confirmed_future_work)//5 + x + remaining_work_needed >= available_days:
          return 1
      elif ((remaining_work_needed+confirmed_future_work)//5 + x + remaining_work_needed + 1) and (d_idx < self.num_days-3)>= available_days:
          return 2
      elif remaining_holidays_needed + (remaining_holidays_needed + confirmed_future_holidays)//4 >= available_days:
          return 5
      elif remaining_holidays_needed + (remaining_holidays_needed + confirmed_future_holidays)//4 +1 >= available_days and ((remaining_work_needed+confirmed_future_work)//5 + x + remaining_work_needed < available_days):
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

        # 3. FUTURE BURDEN: Mandatory days from tomorrow onwards
        # We sum for both A and B
        future_a = self.count_future_mandatory_work('a', d_idx)
        future_b = self.count_future_mandatory_work('b', d_idx)

        future_mandatory = future_a + future_b

        # 4. THE TOTAL: Everything they've done + what they MUST do
        projected_total = work_done + today_impact + future_mandatory
        # If this total is higher than their combined budget,
        # the algorithm MUST prioritize giving one of them a holiday today.
        get_workingcount = self.number_working_4_in_a_row(d_idx)
        get_workingcount_people = list(get_workingcount.keys())

        if projected_total > combined_target:
            # We return a score that scales with how much they are "over"
            return 50000 + (projected_total - combined_target) * 1000
        elif ['a','b'] in get_workingcount_people:
            return 3000
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


            # Ensure exactly 3 OFF per day
            current_off = sum(self.schedule[p][d_idx]==1 for p in self.people)

            # If too few are OFF, pick people to give holidays to

            while current_off < 3:
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
                    self.get_priority_score(p, d_idx),      # 2. Your Streak Points (2nd holiday, etc)
                    -self.people.index(p)                    # 4. Rank Tie-breaker
                ), reverse=True)
                print('d_idx,candidates',d_idx,candidates)








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
                    current_off += 1
                    break




          # Force highest-rank back to work if too many are off
            while current_off > 3:
                offs = [p for p in self.people if self.schedule[p][d_idx] == 1]
                if not offs:
                    break
                to_work = sorted(offs, key=lambda p: -self.get_work_balance_score(p, d_idx))[0]
                self.schedule[to_work][d_idx] = 0
                current_off -= 1

            # Any remaining '2' entries default to WORK
            for p in self.people:
                if self.schedule[p][d_idx] == 2:
                  self.schedule[p][d_idx] = 0


        return self.schedule, self.num_days

    def _needs_holiday_today(self, p, d_idx):
        worked_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
        confirmed_future_work = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 0)
        unassigned_days = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 2)

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

        if remaining_work_needed >= available_days:
            print('needs work today',d_idx,p)
            return False
        return False

    def must_work_today(self,p, d_idx):
        """
        Returns True if giving this person a holiday today is mathematically impossible
        — i.e. they have no holiday budget left, or every remaining day must be work.
        """
        # No holiday budget left
        worked_so_far = sum(1 for d in range(d_idx) if self.schedule[p][d] == 0)
        confirmed_future_work = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 0)
        unassigned_days = sum(1 for d in range(d_idx, self.num_days) if self.schedule[p][d] == 2)


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
        remaining_work_needed = target_work_days - worked_so_far - confirmed_future_work
        available_days = unassigned_days  # days still flexible
        #print('available days', unassigned_days, 'remaining work needed', remaining_work_needed)

        if work_streak_a + work_streak >=5:
            return False
        if off_streak_a + off_streak >=4:
          return True
        if (work_streak+work_streak_a ==4) and off_streak_n ==4:
          return False

        if remaining_work_needed >= available_days:
            return True




        return False

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
        if off_streak_t == 1: return 700 +diff
        if work_streak_a ==4 or work_streak ==4: return 600  +diff

        if off_streak_a >0 and off_streak >0 and off_streak_t ==3: return 500  +diff
        if work_streak_t == 3 and work_streak_a in [3,0]: return 450  +diff
        if off_streak_t == 2: return 400 +diff
        if work_streak ==2 and work_streak_t == 4: return 375+diff

        if off_streak_t == 3: return 350 +diff
        if work_streak > 0 and work_streak_a>0 and work_streak_t == 4: return 300 +diff


        if work_streak_t == 2 and work_streak_a ==1: return 0
        if work_streak_t == 2: return 200 + diff
        if work_streak_t ==3 and work_streak_a in [2,1]: return 100 + diff
        if work_streak_t == 1: return 50 + diff
        return 0


    # ─────────────────────────────────────────────
    # RULE CHECKS
    # ─────────────────────────────────────────────
    def _can_take_holiday(self, p, d_idx):
      # already off
      if self.schedule[p][d_idx] == 1:
          return False

      # A/B constraint
      partner = 'b' if p == 'a' else ('a' if p == 'b' else None)
      if partner and self.schedule[partner][d_idx] == 1:
          return False
      if self.current_off(d_idx) >=3:
          return False
      if self.current_off(d_idx) ==2:
          for pp in self.people:
              if self._needs_holiday_today(pp, d_idx):
                  return False
      if self.current_off(d_idx) >=1:
          needs_holiday_index = 0
          print(self.current_off(d_idx),'so many are currently off')
          for pp in self.people:
              print(pp,'p','needs holiday',self._needs_holiday_today(pp, d_idx))
              if self._needs_holiday_today(pp, d_idx) == True : needs_holiday_index +=1
          print(needs_holiday_index,'so many people need a holiday')
          if needs_holiday_index + self.current_off(d_idx) >=3:
              return False

      # 4-consecutive-off check
      hist_off = self.schedule[p][max(0, d_idx - 4):d_idx]
      if len(hist_off) >= 4 and all(x == 1 for x in hist_off):
          return False
      if partner:
        hist_work_partner = self.schedule[partner][max(0, d_idx - 5):d_idx]
        if len(hist_work_partner) >= 5 and all(x == 0 for x in hist_work_partner):
            return False


      # total holiday budget
      holiday_target = self.num_days - self.targets[p]
      holidays_taken = sum(1 for v in self.schedule[p] if v == 1)
      if holidays_taken >= holiday_target:
          return False

      num_days = self.num_days
      holidays_after = holiday_target - holidays_taken - 1  # -1 for today
      days_remaining = sum(1 for d in range(num_days) if self.schedule[p][d] == 2)
      work_remaining = self.targets[p] - sum(1 for d in range(num_days) if self.schedule[p][d] == 0)
      forced_break_days = holidays_after // 4  # every 4 off days needs 1 break

      if work_remaining + forced_break_days >= days_remaining:
          print('not possible')
          print('work remain',work_remaining)
          print('forced_break_days',forced_break_days)
          print('days remaining',days_remaining)
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
          print(p)
          print('current debt', current_debt)
          print('remaining sundays', available_sundays)
          if current_debt >= available_sundays:
              return False
          print('can take holiday',p, day_num)

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
      people = self.people
      data = []

      start_date = self.start

      # ── Sundays in range ─────────────────────
      sundays = []
      for i in range(self.num_days):
          current_day = start_date + timedelta(days=i)
          if current_day.weekday() == 6:
              sundays.append(i)

      # ── daily rows ───────────────────────────
      for d_idx in range(self.num_days):
          current_day = start_date + timedelta(days=d_idx)

          day_entry = {"Date": current_day.strftime("%Y-%m-%d")}

          for p in people:
              day_entry[p.upper()] = "OFF" if self.schedule[p][d_idx] == 1 else "WORK"

          data.append(day_entry)

      # ── total work days ──────────────────────
      total_work_row = {"Date": "Total Work Days"}
      for p in people:
          total_work_row[p.upper()] = sum(1 for v in self.schedule[p] if v == 0)
      data.append(total_work_row)

      # ── total sundays worked ─────────────────
      total_sundays_row = {"Date": "Total Sundays Worked"}
      for p in people:
          total_sundays_row[p.upper()] = sum(
              1 for s in sundays if self.schedule[p][s] == 0
          )
      data.append(total_sundays_row)

      # ── dataframe ────────────────────────────
      df = pd.DataFrame(data)

      return df
      