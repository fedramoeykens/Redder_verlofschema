import { useState, useEffect, useRef } from "react";

const NAMES = ["a", "b", "c", "d", "e", "f", "g"];
const CLICK_MS = 380;
const PREF_LEVELS = { 1: "high", 2: "mid", 3: "low" };
const DOW = ["Zo", "Ma", "Di", "Wo", "Do", "Vr", "Za"];

function getDays(start, end) {
  const list = [];
  let d = new Date(start + "T00:00:00");
  const eDate = new Date(end + "T00:00:00");
  while (d <= eDate) {
    list.push(new Date(d));
    d.setDate(d.getDate() + 1);
  }
  return list;
}

function buildPrefs(prefs) {
  const out = { high: [], mid: [], low: [] };
  for (const [day, level] of Object.entries(prefs)) {
    if (out[level]) out[level].push(Number(day));
  }
  return out;
}

export default function App() {
  const [start, setStart] = useState("2026-07-01");
  const [end, setEnd] = useState("2026-07-31");
  const [days, setDays] = useState([]);
  const [forced, setForced] = useState([]);
  const [holidays, setHolidays] = useState([]);
  const [people, setPeople] = useState(
    NAMES.map((n) => ({ name: n, sundayQuota: 2, holidayQuota: 1, target: 19, prefs: {} }))
  );
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const clickState = useRef({});

  useEffect(() => {
    setDays(getDays(start, end));
  }, [start, end]);

  const sunCount = days.filter((d) => d.getDay() === 0 && !holidays.includes(d.getDate())).length;
  const holCount = holidays.length;

  const toggleForced = (d) => {
    const dn = d.getDate();
    setForced((prev) => (prev.includes(dn) ? prev.filter((x) => x !== dn) : [...prev, dn]));
    setHolidays((prev) => prev.filter((x) => x !== dn));
  };

  const toggleHoliday = (d) => {
    const dn = d.getDate();
    setHolidays((prev) => (prev.includes(dn) ? prev.filter((x) => x !== dn) : [...prev, dn]));
    setForced((prev) => prev.filter((x) => x !== dn));
  };

  const updatePerson = (i, field, value) => {
    setPeople((prev) => {
      const copy = [...prev];
      copy[i] = { ...copy[i], [field]: value };
      return copy;
    });
  };

  const handlePrefClick = (pi, d) => {
    const dn = d.getDate();
    const key = `${pi}-${dn}`;
    const entry = clickState.current[key] || { count: 0, timer: null };
    entry.count += 1;
    if (entry.timer) clearTimeout(entry.timer);
    entry.timer = setTimeout(() => {
      const level = PREF_LEVELS[Math.min(entry.count, 3)];
      setPeople((prev) => {
        const copy = [...prev];
        const person = { ...copy[pi], prefs: { ...copy[pi].prefs } };
        if (person.prefs[dn] === level) delete person.prefs[dn];
        else person.prefs[dn] = level;
        copy[pi] = person;
        return copy;
      });
      clickState.current[key] = { count: 0, timer: null };
    }, CLICK_MS);
    clickState.current[key] = entry;
  };

  const generate = async () => {
    setError("");
    setResult(null);
    const payload = {
      start, end, forced,
      fixed_holidays: holidays,
      sun_quotas: Object.fromEntries(people.map((p) => [p.name, p.sundayQuota])),
      fixed_holiday_quotas: Object.fromEntries(people.map((p) => [p.name, p.holidayQuota])),
      targets: Object.fromEntries(people.map((p) => [p.name, p.target])),
      prefs: Object.fromEntries(people.map((p) => [p.name, buildPrefs(p.prefs)])),
    };
    try {
      const base = window.location.origin;
      const res = await fetch(`${base}/api/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ? JSON.stringify(data.detail) : "Fout bij genereren.");
        return;
      }
      setResult(data.schedule);
    } catch (e) {
      setError("Kan de server niet bereiken — is die actief?");
    }
  };

  const firstDow = days.length ? days[0].getDay() : 0;

  return (
    <div style={s.app}>
      {/* TITLE */}
      <h1 style={s.title}>Verlofschema Knokke</h1>
      <p style={s.sub}>Plan en beheer de werkroosters voor het strandteam</p>

      {/* PERIOD */}
      <div style={s.section}>
        <div style={s.sectionLabel}>Periode</div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label style={s.metaLabel}>Van</label>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={s.dateInput} />
          <label style={s.metaLabel}>Tot</label>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={s.dateInput} />
        </div>
      </div>

      {/* GLOBAL CALENDAR */}
      <div style={s.section}>
        <div style={s.sectionLabel}>Globale kalender</div>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
          <LegendItem color="#FAEEDA" border="#FAC775" textColor="#633806" label="Zondag" />
          <LegendItem color="#378ADD" textColor="#fff" label="Verplichte werkdag (klik)" />
          <LegendItem color="#7F77DD" textColor="#fff" label="Feestdag (rechts klik)" />
        </div>
        <div style={s.calendar}>
          {DOW.map((d) => <div key={d} style={s.dayHeader}>{d}</div>)}
          {Array.from({ length: firstDow }).map((_, i) => <div key={`e-${i}`} />)}
          {days.map((d) => {
            const dn = d.getDate();
            const isSun = d.getDay() === 0;
            const isForced = forced.includes(dn);
            const isHol = holidays.includes(dn);
            let bg = "var(--color-background-primary)";
            let color = "var(--color-text-primary)";
            let border = "0.5px solid var(--color-border-tertiary)";
            if (isSun && !isForced && !isHol) { bg = "#FAEEDA"; color = "#633806"; border = "0.5px solid #FAC775"; }
            if (isForced) { bg = "#378ADD"; color = "#fff"; border = "0.5px solid #185FA5"; }
            if (isHol) { bg = "#7F77DD"; color = "#fff"; border = "0.5px solid #534AB7"; }
            return (
              <div
                key={dn}
                style={{ ...s.dayCell, background: bg, color, border }}
                onClick={() => toggleForced(d)}
                onContextMenu={(e) => { e.preventDefault(); toggleHoliday(d); }}
              >
                {dn}
              </div>
            );
          })}
        </div>
      </div>

      <div style={s.divider} />

      {/* QUOTA BAR */}
      <div style={s.section}>
        <div style={s.quotaBar}>
          <p style={s.quotaInfo}>
            Er zijn <strong>{sunCount} zondagen</strong> — verdeel deze over de redders.{" "}
            Er zijn <strong>{holCount} feestdag{holCount !== 1 ? "en" : ""}</strong> — verdeel deze eveneens.
          </p>
          <div style={{ display: "flex", gap: 32, flexWrap: "wrap", marginTop: 12 }}>
            <QuotaGroup label="Zondagquota per redder" people={people} field="sundayQuota" onChange={(i, v) => updatePerson(i, "sundayQuota", v)} />
            <QuotaGroup label="Feestdagquota per redder" people={people} field="holidayQuota" onChange={(i, v) => updatePerson(i, "holidayQuota", v)} />
          </div>
        </div>
      </div>

      <div style={s.divider} />

      {/* PEOPLE */}
      <div style={s.section}>
        <div style={s.sectionLabel}>Voorkeuren per redder</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {people.map((p, pi) => (
            <PersonBlock
              key={p.name}
              person={p}
              pi={pi}
              days={days}
              forced={forced}
              holidays={holidays}
              onTargetChange={(v) => updatePerson(pi, "target", v)}
              onPrefClick={(d) => handlePrefClick(pi, d)}
            />
          ))}
        </div>
      </div>

      {/* GENERATE */}
      <button style={s.genBtn} onClick={generate}>Schema genereren</button>

      {error && <div style={s.error}>{error}</div>}

      {/* RESULT */}
      {result && (
        <div style={{ marginTop: 32 }}>
          <div style={s.sectionLabel}>Gegenereerd schema</div>
          <div style={{ overflowX: "auto" }}>
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}>Redder</th>
                  {Object.values(result)[0].map((_, i) => (
                    <th key={i} style={s.th}>{i + 1}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(result).map(([person, vals]) => (
                  <tr key={person}>
                    <td style={{ ...s.td, fontWeight: 500, textAlign: "left", padding: "5px 10px" }}>{person}</td>
                    {vals.map((v, i) => (
                      <td key={i} style={{ ...s.td, background: v === 0 ? "#EAF3DE" : "var(--color-background-secondary)", color: v === 0 ? "#27500A" : "var(--color-text-tertiary)", fontWeight: v === 0 ? 500 : 400 }}>
                        {v === 0 ? "W" : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function LegendItem({ color, border, textColor, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--color-text-secondary)" }}>
      <div style={{ width: 12, height: 12, borderRadius: 3, background: color, border: border || "none" }} />
      {label}
    </div>
  );
}

function QuotaGroup({ label, people, field, onChange }) {
  return (
    <div>
      <div style={{ fontSize: 11, fontWeight: 500, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {people.map((p, i) => (
          <div key={p.name} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <label style={{ fontSize: 11, color: "var(--color-text-secondary)", fontWeight: 500 }}>{p.name}</label>
            <input type="number" min="0" value={p[field]} onChange={(e) => onChange(i, +e.target.value)} style={{ width: 54, fontSize: 13 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function PersonBlock({ person, pi, days, forced, holidays, onTargetChange, onPrefClick }) {
  const initials = person.name.substring(0, 2).toUpperCase();
  const firstDow = days.length ? days[0].getDay() : 0;
  return (
    <div style={s.personBlock}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div style={s.avatar}>{initials}</div>
        <div style={{ fontSize: 15, fontWeight: 500, color: "var(--color-text-primary)" }}>Redder {person.name.toUpperCase()}</div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 11, color: "var(--color-text-secondary)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.06em" }}>Doeltal</label>
          <input type="number" value={person.target} onChange={(e) => onTargetChange(+e.target.value)} style={{ width: 60, fontSize: 13 }} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 6, flexWrap: "wrap" }}>
        {[["#1D9E75", "Hoge voorkeur"], ["#EF9F27", "Middel"], ["#E24B4A", "Liever niet"]].map(([color, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--color-text-secondary)" }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: color }} />{label}
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginBottom: 8 }}>
        Klik 1× = hoog · 2× = midden · 3× = laag · nog eens = wissen
      </div>
      <div style={s.smallCal}>
        {DOW.map((d) => <div key={d} style={s.dayHeader}>{d}</div>)}
        {Array.from({ length: firstDow }).map((_, i) => <div key={`e-${i}`} />)}
        {days.map((d) => {
          const dn = d.getDate();
          const isSun = d.getDay() === 0;
          const isForced = forced.includes(dn);
          const isHol = holidays.includes(dn);
          const pref = person.prefs[dn];
          let bg = "var(--color-background-secondary)";
          let color = "var(--color-text-primary)";
          let border = "0.5px solid var(--color-border-tertiary)";
          let borderBottom = border;
          if (isSun) { bg = "#FAEEDA"; color = "#633806"; }
          if (isForced) borderBottom = "2.5px solid #378ADD";
          if (isHol) borderBottom = "2.5px solid #7F77DD";
          if (pref === "high") { bg = "#1D9E75"; color = "#fff"; border = "0.5px solid #0F6E56"; borderBottom = border; }
          if (pref === "mid") { bg = "#EF9F27"; color = "#fff"; border = "0.5px solid #BA7517"; borderBottom = border; }
          if (pref === "low") { bg = "#E24B4A"; color = "#fff"; border = "0.5px solid #A32D2D"; borderBottom = border; }
          return (
            <div
              key={dn}
              style={{ ...s.smallDay, background: bg, color, border, borderBottom }}
              onClick={() => onPrefClick(d)}
            >
              {dn}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const s = {
  app: { fontFamily: "system-ui, sans-serif", padding: "2rem 1.5rem", maxWidth: 900, margin: "0 auto" },
  title: { fontSize: 26, fontWeight: 500, color: "var(--color-text-primary, #111)", marginBottom: 4, letterSpacing: -0.5 },
  sub: { fontSize: 14, color: "var(--color-text-secondary, #666)", marginBottom: 32 },
  section: { marginBottom: 24 },
  sectionLabel: { fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-text-tertiary, #999)", marginBottom: 10 },
  dateInput: { fontSize: 13 },
  metaLabel: { fontSize: 13, color: "var(--color-text-secondary, #666)" },
  calendar: { display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 5, maxWidth: 460 },
  smallCal: { display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 3 },
  dayHeader: { fontSize: 10, fontWeight: 500, color: "var(--color-text-tertiary, #999)", textAlign: "center", padding: "4px 0", textTransform: "uppercase", letterSpacing: "0.05em" },
  dayCell: { aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 500, borderRadius: 6, cursor: "pointer", userSelect: "none", transition: "opacity 0.1s" },
  smallDay: { aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 500, borderRadius: 4, cursor: "pointer", userSelect: "none" },
  divider: { height: 0.5, background: "var(--color-border-tertiary, #e5e5e5)", margin: "24px 0" },
  quotaBar: { background: "var(--color-background-secondary, #f7f7f7)", borderRadius: 12, padding: "1rem 1.25rem", border: "0.5px solid var(--color-border-tertiary, #e5e5e5)" },
  quotaInfo: { fontSize: 13, color: "var(--color-text-secondary, #666)", lineHeight: 1.6 },
  personBlock: { border: "0.5px solid var(--color-border-tertiary, #e5e5e5)", borderRadius: 12, padding: "1.25rem", background: "var(--color-background-primary, #fff)" },
  avatar: { width: 32, height: 32, borderRadius: "50%", background: "#E6F1FB", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 500, color: "#185FA5", flexShrink: 0 },
  genBtn: { marginTop: 24, padding: "10px 28px", fontSize: 14, fontWeight: 500, background: "#111", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" },
  error: { marginTop: 12, padding: "10px 14px", background: "#FCEBEB", color: "#A32D2D", borderRadius: 8, fontSize: 13 },
  table: { borderCollapse: "collapse", fontSize: 12 },
  th: { background: "var(--color-background-secondary, #f7f7f7)", padding: "6px 10px", border: "0.5px solid var(--color-border-tertiary, #e5e5e5)", fontWeight: 500, color: "var(--color-text-secondary, #666)" },
  td: { padding: "5px 8px", border: "0.5px solid var(--color-border-tertiary, #e5e5e5)", textAlign: "center" },
};