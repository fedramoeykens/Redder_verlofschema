import { useState, useEffect, useRef } from "react";
import "./App.css";

const PREF_LEVELS = { 1: "high", 2: "mid", 3: "low" };
const CLICK_WINDOW_MS = 400;

export default function App() {
  const names = ["a", "b", "c", "d", "e", "f", "g"];

  // ---------------- DATE RANGE ----------------
  const [start, setStart] = useState("2026-07-01");
  const [end, setEnd] = useState("2026-07-31");
  const [days, setDays] = useState([]);

  // ---------------- GLOBAL RULES ----------------
  // Stored as day-of-month integers (e.g. 6 for the 6th) since the backend
  // only ever runs a single month at a time.
  const [forced, setForced] = useState([]);
  const [holidays, setHolidays] = useState([]);

  // ---------------- PER PERSON DATA ----------------
  // prefs is keyed by day-of-month integer -> "high" | "mid" | "low"
  const [people, setPeople] = useState(
    names.map((n) => ({
      name: n,
      sundayQuota: 2,
      holidayQuota: 1,
      target: 19,
      prefs: {},
    }))
  );

  // ---------------- RESULT ----------------
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // ---------------- GENERATE DAYS ----------------
  useEffect(() => {
    const s = new Date(start);
    const e = new Date(end);

    const list = [];
    let d = new Date(s);

    while (d <= e) {
      list.push(new Date(d));
      d.setDate(d.getDate() + 1);
    }

    setDays(list);
  }, [start, end]);

  const isSunday = (d) => d.getDay() === 0;

  // ---------------- GLOBAL TOGGLES (click = forced, right-click = holiday) ----------------
  const toggleForced = (d) => {
    const dayNum = d.getDate();
    setForced((prev) =>
      prev.includes(dayNum) ? prev.filter((x) => x !== dayNum) : [...prev, dayNum]
    );
    // a day can't be both forced and a fixed holiday
    setHolidays((prev) => prev.filter((x) => x !== dayNum));
  };

  const toggleHoliday = (d) => {
    const dayNum = d.getDate();
    setHolidays((prev) =>
      prev.includes(dayNum) ? prev.filter((x) => x !== dayNum) : [...prev, dayNum]
    );
    setForced((prev) => prev.filter((x) => x !== dayNum));
  };

  // ---------------- PERSON SETTINGS UPDATE ----------------
  const updatePerson = (i, field, value) => {
    setPeople((prev) => {
      const copy = [...prev];
      copy[i] = { ...copy[i], [field]: value };
      return copy;
    });
  };

  // ---------------- PREF CLICK-COUNT CYCLING (1=high, 2=mid, 3=low) ----------------
  const clickState = useRef({}); // { "personIndex-dayNum": { count, timer } }

  const applyPref = (personIndex, dayNum, level) => {
    setPeople((prev) => {
      const copy = [...prev];
      const person = { ...copy[personIndex], prefs: { ...copy[personIndex].prefs } };

      if (person.prefs[dayNum] === level) {
        delete person.prefs[dayNum]; // clicking the same level again clears it
      } else {
        person.prefs[dayNum] = level;
      }

      copy[personIndex] = person;
      return copy;
    });
  };

  const handlePrefClick = (personIndex, d) => {
    const dayNum = d.getDate();
    const key = `${personIndex}-${dayNum}`;
    const entry = clickState.current[key] || { count: 0, timer: null };

    entry.count += 1;
    if (entry.timer) clearTimeout(entry.timer);

    entry.timer = setTimeout(() => {
      const level = PREF_LEVELS[Math.min(entry.count, 3)];
      applyPref(personIndex, dayNum, level);
      clickState.current[key] = { count: 0, timer: null };
    }, CLICK_WINDOW_MS);

    clickState.current[key] = entry;
  };

  // ---------------- SHAPE PREFS FOR THE BACKEND ----------------
  // Frontend stores prefs as { dayNum: "high" }. The backend (ScheduleMaker)
  // expects, per person, { high: [...days], mid: [...days], low: [...days] }.
  const buildPrefsForBackend = (prefs) => {
    const out = { high: [], mid: [], low: [] };
    for (const [day, level] of Object.entries(prefs)) {
      if (out[level]) out[level].push(Number(day));
    }
    return out;
  };

  // ---------------- GENERATE ----------------
  const generate = async () => {
    setError("");

    const payload = {
      start,
      end,
      forced,
      fixed_holidays: holidays,

      sun_quotas: Object.fromEntries(people.map((p) => [p.name, p.sundayQuota])),
      fixed_holiday_quotas: Object.fromEntries(people.map((p) => [p.name, p.holidayQuota])),
      targets: Object.fromEntries(people.map((p) => [p.name, p.target])),

      // Sent already shaped the way ScheduleMaker.generate() expects it,
      // not the shape that's convenient to build in the UI.
      prefs: Object.fromEntries(
        people.map((p) => [p.name, buildPrefsForBackend(p.prefs)])
      ),
    };

    try {
      const res = await fetch("/api/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        console.error("Server error:", data);
        setError(data.detail ? JSON.stringify(data.detail) : "Failed to generate schedule.");
        return;
      }

      setResult(data.schedule);
    } catch (e) {
      console.error(e);
      setError("Could not reach the backend — is it running?");
    }
  };

  // ---------------- RENDER ----------------
  return (
    <div className="container">
      <h1>Schedule Maker</h1>

      {/* DATE RANGE */}
      <div className="row">
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
      </div>

      {/* GLOBAL CALENDAR (FIXED DAYS + HOLIDAYS) */}
      <h2>Global Calendar</h2>
      <p>Click = forced work day (blue) | Right click = fixed holiday (purple)</p>

      <div className="calendar">
        {days.map((d) => {
          const dayNum = d.getDate();

          let cls = "day";
          if (isSunday(d)) cls += " sunday";
          if (forced.includes(dayNum)) cls += " forced";
          if (holidays.includes(dayNum)) cls += " holiday";

          return (
            <div
              key={dayNum}
              className={cls}
              onClick={() => toggleForced(d)}
              onContextMenu={(e) => {
                e.preventDefault();
                toggleHoliday(d);
              }}
            >
              {dayNum}
            </div>
          );
        })}
      </div>

      {/* PEOPLE CONFIG */}
      <h2>People Settings</h2>

      {people.map((p, i) => (
        <div key={p.name} className="personBlock">
          <h3>{p.name}</h3>

          Sunday quota:
          <input
            type="number"
            value={p.sundayQuota}
            onChange={(e) => updatePerson(i, "sundayQuota", Number(e.target.value))}
          />

          Holiday quota:
          <input
            type="number"
            value={p.holidayQuota}
            onChange={(e) => updatePerson(i, "holidayQuota", Number(e.target.value))}
          />

          Target:
          <input
            type="number"
            value={p.target}
            onChange={(e) => updatePerson(i, "target", Number(e.target.value))}
          />

          {/* ---------------- PERSON PREF CALENDAR ---------------- */}
          <h4>Preferences</h4>
          <p className="hint">Click once = High, twice = Mid, three times = Low, again clears it.</p>

          <div className="calendar small">
            {days.map((d) => {
              const dayNum = d.getDate();
              const pref = p.prefs[dayNum];

              let cls = "day smallDay";
              if (pref === "high") cls += " prefHigh";
              if (pref === "mid") cls += " prefMid";
              if (pref === "low") cls += " prefLow";
              if (isSunday(d)) cls += " sunday";

              return (
                <div
                  key={dayNum}
                  className={cls}
                  onClick={() => handlePrefClick(i, d)}
                >
                  {dayNum}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* GENERATE */}
      <button onClick={generate}>Generate Schedule</button>

      {error && <p className="errorBanner">{error}</p>}

      {/* RESULT GRID */}
      {result && (
        <div>
          <h2>Schedule</h2>

          <div className="grid">
            {/* HEADER */}
            <div className="row header">
              <div className="cell name">Person</div>

              {Object.values(result)[0].map((_, i) => (
                <div key={i} className="cell">
                  {i + 1}
                </div>
              ))}
            </div>

            {/* ROWS */}
            {Object.entries(result).map(([person, values]) => (
              <div className="row" key={person}>
                <div className="cell name">{person}</div>

                {values.map((v, i) => (
                  <div key={i} className={"cell " + (v === 0 ? "work" : "off")}>
                    {v === 0? "Work" : "Off"}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}