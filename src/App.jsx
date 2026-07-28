import { useState, useEffect, useRef } from "react";
import * as XLSX from "xlsx";

const NAMES = ["a", "b", "c", "d", "e", "f", "g"];
const CLICK_MS = 380;
const PREF_LEVELS = { 1: "high", 2: "mid", 3: "low" };
const DOW = ["Zo", "Ma", "Di", "Wo", "Do", "Vr", "Za"];
const MONTHS_NL = [
  "januari", "februari", "maart", "april", "mei", "juni",
  "juli", "augustus", "september", "oktober", "november", "december",
];
const WEEKDAYS_NL = ["zondag", "maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag"];

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

const SUMMARY_LABELS = [
  "Total Work Days", "Total Sundays Worked", "Total Fixed Holidays Worked",
  "Gewerkte dagen", "Gewerkte zondagen", "Gewerkte feestdagen",
];
const isDataRow = (row) => !SUMMARY_LABELS.includes(row.Date);

// CSV Export Utility
function exportCSV(result) {
  if (!result || !result.length) return;
  const headers = Object.keys(result[0]);
  const rows = result.map((row) =>
    headers.map((h) => {
      const v = row[h];
      if (v === "WORK") return "";
      if (v === "OFF") return "v";
      return v ?? "";
    })
  );
  const csvContent = [headers, ...rows]
    .map((r) => r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", "Verlofschema.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Builds an .xlsx that mirrors the "Controlebestand verlofregeling" layout

function Chip({ children, color, textColor }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", fontSize: 11, fontWeight: 500,
      padding: "2px 8px", borderRadius: 20, background: color, color: textColor,
      letterSpacing: "0.03em",
    }}>
      {children}
    </span>
  );
}

function exportControleXLSX({ result, days, forced, holidays, people, start }) {
  if (!result || !result.length) return;

  const dayRows = result.filter(isDataRow);
  const nPeople = people.length;
  const firstCol = 2;
  const aanwezigCol = firstCol + nPeople;
  const verlofCol = aanwezigCol + 1;
  const commandCol = verlofCol + 1;
  const dataStartRow = 5;

  const startDate = new Date(start + "T00:00:00");
  const monthLabel = `${MONTHS_NL[startDate.getMonth()]} ${startDate.getFullYear()}`;
  const lastDataRow = dataStartRow + dayRows.length - 1;
  const inactRow = lastDataRow + 2;
  const sunRow = inactRow + 1;
  const aanwezigRow = sunRow + 1;
  const sunHolidayOffRow = aanwezigRow + 1;
  const totalCols = commandCol + 1;
  const totalRows = sunHolidayOffRow + 1;

  const aoa = Array.from({ length: totalRows }, () => Array.from({ length: totalCols }, () => null));
  const setAOA = (r, c, v) => { aoa[r][c] = v === undefined ? null : v; };

  setAOA(1, 0, "Reddingsdienst dienstrooster");
  setAOA(1, 4, monthLabel);
  setAOA(2, firstCol, "PO");
  if (nPeople > 1) setAOA(2, firstCol + 1, "2RED");
  for (let i = 2; i < nPeople; i++) setAOA(2, firstCol + i, "R");
  setAOA(2, aanwezigCol, "Aantal R aanwezig");
  setAOA(2, verlofCol, "Aantal in verlof");
  setAOA(2, commandCol, "Commando");
  people.forEach((p, i) => setAOA(3, firstCol + i, p.name.toUpperCase()));

  const sundayHolidayRows = [];
  dayRows.forEach((row, i) => {
    const excelRow = dataStartRow + i;
    const day = days[i];
    const isSun = day.getDay() === 0;
    const isHoliday = holidays.includes(day.getDate());
    const isForcedRow = forced.includes(day.getDate());

    if ((isSun || isHoliday) && !isForcedRow) sundayHolidayRows.push(excelRow);

    setAOA(excelRow, 0, WEEKDAYS_NL[day.getDay()]);
    setAOA(excelRow, 1, `${day.getDate()} ${MONTHS_NL[day.getMonth()]}`);

    people.forEach((p, pi) => {
      let value;
      if (Object.prototype.hasOwnProperty.call(row, p.name)) {
        value = row[p.name];
      } else {
        const found = Object.keys(row).find((k) => String(k).toLowerCase() === String(p.name).toLowerCase());
        value = found ? row[found] : undefined;
      }

      const normalized = typeof value === "string" ? value.trim().toUpperCase() : value;
      if (normalized === "WORK") value = "";
      if (normalized === "OFF") value = "v";
      setAOA(excelRow, firstCol + pi, value ?? "");
    });
  });

  const sheet = XLSX.utils.aoa_to_sheet(aoa);

  dayRows.forEach((row, i) => {
    const excelRow = dataStartRow + i;
    const startCell = XLSX.utils.encode_cell({ r: excelRow, c: firstCol });
    const endCell = XLSX.utils.encode_cell({ r: excelRow, c: firstCol + nPeople - 1 });
    const aanwezigRef = XLSX.utils.encode_cell({ r: excelRow, c: aanwezigCol });
    const verlofRef = XLSX.utils.encode_cell({ r: excelRow, c: verlofCol });
    const day = days[i];
    const isSun = day.getDay() === 0;
    const isHoliday = holidays.includes(day.getDate());
    const isForcedRow = forced.includes(day.getDate());

    sheet[XLSX.utils.encode_cell({ r: excelRow, c: aanwezigCol })] = { t: "n", f: `COUNTBLANK(${startCell}:${endCell})` };
    sheet[XLSX.utils.encode_cell({ r: excelRow, c: verlofCol })] = { t: "n", f: `COUNTIF(${startCell}:${endCell},"v")` };
    sheet[XLSX.utils.encode_cell({ r: excelRow, c: commandCol })] = {
      f: isForcedRow ? `IF(${aanwezigRef}>=${nPeople},"OK","NOK")` : `IF(AND(${aanwezigRef}>=4,${verlofRef}>=3),"OK","NOK")`
    };
  });

  people.forEach((p, pi) => {
    const c = firstCol + pi;
    const col = XLSX.utils.encode_col(c);
    sheet[XLSX.utils.encode_cell({ r: inactRow, c })] = { t: "n", f: `COUNTIF(${col}${dataStartRow + 1}:${col}${lastDataRow + 1},"v")` };
    if (sundayHolidayRows.length) {
      const refs = sundayHolidayRows.map((r) => `${col}${r + 1}`).join(",");
      sheet[XLSX.utils.encode_cell({ r: sunRow, c })] = { t: "n", f: `COUNTIF(${refs},"v")` };
      sheet[XLSX.utils.encode_cell({ r: sunHolidayOffRow, c })] = { t: "n", f: `COUNTIF(${refs},"v")` };
    } else {
      sheet[XLSX.utils.encode_cell({ r: sunRow, c })] = { t: "n", v: 0 };
      sheet[XLSX.utils.encode_cell({ r: sunHolidayOffRow, c })] = { t: "n", v: 0 };
    }
    sheet[XLSX.utils.encode_cell({ r: aanwezigRow, c })] = { t: "n", f: `COUNTBLANK(${col}${dataStartRow + 1}:${col}${lastDataRow + 1})` };
  });

  sheet[XLSX.utils.encode_cell({ r: inactRow, c: 0 })] = "Inactiviteit";
  sheet[XLSX.utils.encode_cell({ r: sunRow, c: 0 })] = "Inactiviteit (Zon- en feestdagen)";
  sheet[XLSX.utils.encode_cell({ r: aanwezigRow, c: 0 })] = "Aanwezig";
  sheet[XLSX.utils.encode_cell({ r: sunHolidayOffRow, c: 0 })] = "Aantal OFF op zon-/feestdagen";

  sheet["!ref"] = XLSX.utils.encode_range({
    s: { r: 0, c: 0 },
    e: { r: sunHolidayOffRow, c: commandCol }
  });

  sheet["!cols"] = [
    { wch: 12 },
    { wch: 15 },
    ...people.map(() => ({ wch: 8 })),
    { wch: 20 },
    { wch: 18 },
    { wch: 12 }
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, sheet, `Controle ${monthLabel}`.slice(0, 31));
  XLSX.writeFile(wb, `Controlebestand_verlofregeling_${monthLabel}.xlsx`);
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 500, textTransform: "uppercase",
      letterSpacing: "0.09em", color: "var(--color-text-tertiary)",
      marginBottom: 10,
    }}>
      {children}
    </div>
  );
}

function QuotaGroup({ label, people, field, onChange }) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {people.map((p, i) => (
          <div key={p.name} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <label style={{ fontSize: 11, color: "var(--color-text-tertiary)", fontWeight: 500, textTransform: "uppercase" }}>
              {p.name}
            </label>
            <input
              type="number" min="0" value={p[field]}
              onChange={(e) => onChange(i, e.target.value === "" ? "" : +e.target.value)}
              style={{ width: 50, fontSize: 13 }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function PersonBlock({ person, pi, days, forced, holidays, onTargetChange, onPrefClick }) {
  const firstDow = days.length ? days[0].getDay() : 0;
  const PREF_COLORS = {
    high: { bg: "#1D9E75", text: "#fff", border: "#0F6E56" },
    mid:  { bg: "#EF9F27", text: "#fff", border: "#BA7517" },
    low:  { bg: "#E24B4A", text: "#fff", border: "#A32D2D" },
  };
  return (
    <div style={{
      border: "0.5px solid var(--color-border-tertiary)",
      borderRadius: "var(--border-radius-lg)",
      padding: "1rem 1.25rem",
      background: "var(--color-background-primary)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <div style={{
          width: 30, height: 30, borderRadius: "50%",
          background: "#E6F1FB", display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 12, fontWeight: 500, color: "#185FA5",
        }}>
          {person.name.toUpperCase()}
        </div>
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>
          Redder {person.name.toUpperCase()}
        </span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>Doeltal</label>
          <input
            type="number" value={person.target}
            onChange={(e) => onTargetChange(e.target.value === "" ? "" : +e.target.value)}
            style={{ width: 56, fontSize: 13 }}
          />
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
        {[["#1D9E75", "Hoge voorkeur"], ["#EF9F27", "Middel"], ["#E24B4A", "Laag"]].map(([color, label]) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--color-text-secondary)" }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
            {label}
          </div>
        ))}
        <span style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginLeft: 4 }}>
          1× hoog · 2× midden · 3× laag · nogmaals = wissen
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 3 }}>
        {DOW.map((d) => (
          <div key={d} style={{ fontSize: 10, fontWeight: 500, color: "var(--color-text-tertiary)", textAlign: "center", padding: "3px 0", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {d}
          </div>
        ))}
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
          if (isSun) { bg = "#FAEEDA"; color = "#633806"; border = "0.5px solid #FAC775"; borderBottom = border; }
          if (isForced) borderBottom = "2.5px solid #378ADD";
          if (isHol) borderBottom = "2.5px solid #7F77DD";
          if (pref && PREF_COLORS[pref]) {
            const c = PREF_COLORS[pref];
            bg = c.bg; color = c.text; border = `0.5px solid ${c.border}`; borderBottom = border;
          }
          return (
            <div key={dn} onClick={() => onPrefClick(d)} style={{
              aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 10, fontWeight: 500, borderRadius: 4, cursor: "pointer",
              userSelect: "none", background: bg, color, border, borderBottom,
            }}>
              {dn}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ValidationPanel({ checks, displayedChecks }) {
  const allPass = checks.every((c) => c.pass);
  return (
    <div style={{
      marginTop: 16,
      padding: "1rem 1.25rem",
      borderRadius: "var(--border-radius-lg)",
      background: allPass ? "#EAF7EF" : "#FCEBEB",
      border: `1px solid ${allPass ? "#8FCBA5" : "#EBB4B3"}`,
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
        fontSize: 13, fontWeight: 600,
        color: allPass ? "#1D6B3E" : "#A32D2D",
      }}>
        <span style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 20, height: 20, borderRadius: "50%", fontSize: 12,
          background: allPass ? "#1D9E75" : "#E24B4A", color: "#fff",
        }}>
          {allPass ? "✓" : "!"}
        </span>
        {allPass ? "Alles klopt — je kan het schema genereren" : "Controleer eerst het volgende"}
      </div>
      <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
        {displayedChecks.map((c, i) => (
          <li key={i} style={{
            display: "flex", alignItems: "flex-start", gap: 8,
            fontSize: 12.5, color: c.pass ? "#27500A" : "#A32D2D",
          }}>
            <span style={{ flexShrink: 0 }}>{c.pass ? "✓" : "✗"}</span>
            <span>{c.pass ? c.okLabel : c.failLabel}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function App() {
  const [start, setStart] = useState("2026-08-01");
  const [end, setEnd] = useState("2026-08-31");
  const [days, setDays] = useState([]);
  const [forced, setForced] = useState([]);
  const [holidays, setHolidays] = useState([]);
  const [people, setPeople] = useState(
    NAMES.map((n) => ({ name: n, sundayQuota: 3, holidayQuota: 1, target: 19, prefs: {} }))
  );
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const clickState = useRef({});

  useEffect(() => { setDays(getDays(start, end)); }, [start, end]);

  const firstDow = days.length ? days[0].getDay() : 0;

  const sunCount = days.filter(
    (d) => d.getDay() === 0 && !holidays.includes(d.getDate()) && !forced.includes(d.getDate())
  ).length;
  const holCount = holidays.length;

  const toggleForced = (d) => {
    const dn = d.getDate();
    setForced((prev) => prev.includes(dn) ? prev.filter((x) => x !== dn) : [...prev, dn]);
    setHolidays((prev) => prev.filter((x) => x !== dn));
  };

  const toggleHoliday = (d) => {
    const dn = d.getDate();
    setHolidays((prev) => prev.includes(dn) ? prev.filter((x) => x !== dn) : [...prev, dn]);
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

  // ---------- Validation ----------
  const isValidNonNegNumber = (v) => v !== "" && Number.isFinite(v) && v >= 0;

  const sumSunQuota = people.reduce((s, p) => s + (Number.isFinite(p.sundayQuota) ? p.sundayQuota : 0), 0);
  const sumHolQuota = people.reduce((s, p) => s + (Number.isFinite(p.holidayQuota) ? p.holidayQuota : 0), 0);

  const PEOPLE_PER_DAY = 4;
  const sunRequired = sunCount * PEOPLE_PER_DAY;
  const holRequired = holCount * PEOPLE_PER_DAY;

  const sunMatches = sumSunQuota === sunRequired;
  const holMatches = sumHolQuota === holRequired;

  const allNumbersValid = people.every(
    (p) => isValidNonNegNumber(p.sundayQuota) && isValidNonNegNumber(p.holidayQuota) && isValidNonNegNumber(p.target)
  );

  const dateRangeValid = start !== "" && end !== "" && days.length > 0 && start <= end;

  const targetsWithinRange = days.length > 0 && people.every((p) => !Number.isFinite(p.target) || p.target <= days.length);

  const namesUnique = new Set(people.map((p) => p.name)).size === people.length && people.length > 0;

  const checks = [
    {
      key: "period",
      show: false,
      pass: dateRangeValid,
      okLabel: `Periode is geldig (${days.length} dagen).`,
      failLabel: "Controleer de periode: startdatum moet vóór (of gelijk aan) einddatum liggen en het bereik mag niet leeg zijn.",
    },
    {
      key: "numbers",
      show: false,
      pass: allNumbersValid,
      okLabel: "Alle quota's en doeltallen zijn geldige getallen (0 of hoger).",
      failLabel: "Alle quota's en doeltallen moeten ingevuld zijn met geldige getallen van 0 of hoger.",
    },
    {
      key: "sunday",
      show: true,
      pass: sunMatches,
      okLabel: `Zondagquota's kloppen: ${sumSunQuota} van ${sunRequired} benodigde toewijzingen (${sunCount} zondagen × ${PEOPLE_PER_DAY} personen).`,
      failLabel: `Zondagquota's kloppen niet: ${sumSunQuota} toegewezen, maar er zijn ${sunRequired} toewijzingen nodig (${sunCount} zondagen × ${PEOPLE_PER_DAY} personen per dag) ${
        sumSunQuota > sunRequired ? `(${sumSunQuota - sunRequired} te veel)` : `(${sunRequired - sumSunQuota} te weinig)`
      }.`,
    },
    {
      key: "holiday",
      show: true,
      pass: holMatches,
      okLabel: `Feestdagquota's kloppen: ${sumHolQuota} van ${holRequired} benodigde toewijzingen (${holCount} feestdag${holCount !== 1 ? "en" : ""} × ${PEOPLE_PER_DAY} personen).`,
      failLabel: `Feestdagquota's kloppen niet: ${sumHolQuota} toegewezen, maar er zijn ${holRequired} toewijzingen nodig (${holCount} feestdag${holCount !== 1 ? "en" : ""} × ${PEOPLE_PER_DAY} personen) ${
        sumHolQuota > holRequired ? `(${sumHolQuota - holRequired} te veel)` : `(${holRequired - sumHolQuota} te weinig)`
      }.`,
    },
    {
      key: "targets",
      show: false,
      pass: targetsWithinRange,
      okLabel: "Geen enkel doeltal overschrijdt het aantal dagen in de periode.",
      failLabel: `Eén of meer doeltallen zijn hoger dan het aantal dagen in de periode (${days.length} dagen). Dat kan niet.`,
    },
    {
      key: "names",
      show: false,
      pass: namesUnique,
      okLabel: "Alle redders hebben een unieke naam.",
      failLabel: "Er zijn dubbele of ontbrekende namen bij de redders.",
    },
  ];

  const canGenerate = checks.every((c) => c.pass);
  const displayedChecks = checks.filter((c) => c.show);

  // ---------- Generate ----------
  const generate = async () => {
    if (!canGenerate) return;
    setError(""); setResult(null); setLoading(true);
    const payload = {
      start, end, forced, fixed_holidays: holidays,
      sun_quotas: Object.fromEntries(people.map((p) => [p.name, p.sundayQuota])),
      fixed_holiday_quotas: Object.fromEntries(people.map((p) => [p.name, p.holidayQuota])),
      targets: Object.fromEntries(people.map((p) => [p.name, p.target])),
      prefs: Object.fromEntries(people.map((p) => [p.name, buildPrefs(p.prefs)])),
    };
    try {
      const apiBase = (typeof window !== "undefined" && window.location.port === "5173") ? "http://localhost:8000" : window.location.origin;
      const res = await fetch(`${apiBase}/api/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch {
        setError(`Server fout (${res.status}): ${text.slice(0, 300)}`); return;
      }
      if (!res.ok) {
        setError(data.detail ? JSON.stringify(data.detail) : `Fout ${res.status}: ${JSON.stringify(data)}`); return;
      }
      setResult(data.table);
    } catch (err) {
      setError("Netwerkfout: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const isSummaryRow = (row) => {
    const d = row.Date;
    return d === "Gewerkte dagen" || d === "Gewerkte zondagen" || d === "Gewerkte feestdagen";
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "2rem 1.5rem", maxWidth: 920, margin: "0 auto" }}>

      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 4, letterSpacing: -0.4 }}>
          Verlofschema Knokke
        </h1>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0 }}>
          Plan de werkroosters voor je post
        </p>
      </div>

      {/* Period */}
      <div style={{ marginBottom: 24 }}>
        <SectionLabel>Periode</SectionLabel>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>Van</label>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ fontSize: 13 }} />
          <label style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>Tot</label>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ fontSize: 13 }} />
          {!dateRangeValid && (
            <span style={{ fontSize: 12, color: "#A32D2D" }}>⚠ Controleer de periode</span>
          )}
        </div>
      </div>

      {/* Global calendar */}
      <div style={{ marginBottom: 24 }}>
        <SectionLabel>Globale kalender</SectionLabel>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
          {[
            ["#FAEEDA", "#FAC775", "#633806", "Zondag"],
            ["#378ADD", "#185FA5", "#fff", "Verplichte werkdag (1 klik)"],
            ["#cf44d8", "#cf44d8", "#fff", "Feestdag (dubbel klik)"],
          ].map(([bg, border, text, label]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--color-text-secondary)" }}>
              <div style={{ width: 12, height: 12, borderRadius: 3, background: bg, border: `0.5px solid ${border}` }} />
              {label}
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 5, maxWidth: 420 }}>
          {DOW.map((d) => (
            <div key={d} style={{ fontSize: 10, fontWeight: 500, color: "var(--color-text-tertiary)", textAlign: "center", padding: "3px 0", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {d}
            </div>
          ))}
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
            if (isHol) { bg = "#cf44d8"; color = "#fff"; border = "0.5px solid #534AB7"; }
            return (
              <div key={dn} onClick={() => toggleForced(d)} onDoubleClick={(e) => { e.preventDefault(); toggleHoliday(d); }}
                style={{ aspectRatio: "1", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 500, borderRadius: 6, cursor: "pointer", userSelect: "none", background: bg, color, border }}>
                {dn}
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ height: 0.5, background: "var(--color-border-tertiary)", margin: "20px 0" }} />

      {/* Quotas */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-lg)", padding: "1rem 1.25rem", border: "0.5px solid var(--color-border-tertiary)" }}>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6, marginBottom: 14 }}>
            Er zijn <strong>{sunCount} zondagen</strong> te verdelen (verplichte zondagen niet meegeteld), elk met {PEOPLE_PER_DAY} personen — dat zijn samen <strong>{sunRequired} toewijzingen</strong> om te verdelen.{" "}
            {holCount === 1 ? "Er is" : "Er zijn"} <strong>{holCount} feestdag{holCount !== 1 ? "en" : ""}</strong>, elk met {PEOPLE_PER_DAY} personen — dat zijn samen <strong>{holRequired} toewijzingen</strong> om te verdelen.
          </p>
          <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
            <QuotaGroup label="Zondagquota" people={people} field="sundayQuota" onChange={(i, v) => updatePerson(i, "sundayQuota", v)} />
            <QuotaGroup label="Feestdagquota" people={people} field="holidayQuota" onChange={(i, v) => updatePerson(i, "holidayQuota", v)} />
          </div>

          <ValidationPanel checks={checks} displayedChecks={displayedChecks} />
        </div>
      </div>

      <div style={{ height: 0.5, background: "var(--color-border-tertiary)", margin: "20px 0" }} />

      {/* People */}
      <div style={{ marginBottom: 28 }}>
        <SectionLabel>Voorkeuren per redder</SectionLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {people.map((p, pi) => (
            <PersonBlock key={p.name} person={p} pi={pi} days={days} forced={forced} holidays={holidays}
              onTargetChange={(v) => updatePerson(pi, "target", v)}
              onPrefClick={(d) => handlePrefClick(pi, d)} />
          ))}
        </div>
      </div>

      {/* Generate button */}
      <button
        onClick={generate}
        disabled={loading || !canGenerate}
        title={!canGenerate ? "Los eerst de openstaande controles hierboven op" : undefined}
        style={{
          padding: "10px 28px", fontSize: 14, fontWeight: 500,
          background: (loading || !canGenerate) ? "var(--color-background-secondary)" : "#111",
          color: (loading || !canGenerate) ? "var(--color-text-tertiary)" : "#fff",
          border: "none", borderRadius: 8,
          cursor: (loading || !canGenerate) ? "not-allowed" : "pointer",
          transition: "background 0.15s",
        }}
      >
        {loading ? "Bezig met genereren…" : "Schema genereren"}
      </button>

      {!canGenerate && (
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--color-text-tertiary)" }}>
          Los eerst de controles hierboven op ("Zondagquota" e.d.) voor je een schema genereert.
        </div>
      )}

      {error && (
        <div style={{ marginTop: 12, padding: "10px 14px", background: "#FCEBEB", color: "#A32D2D", borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ marginTop: 36 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
            <div>
              <SectionLabel>Gegenereerd schema</SectionLabel>
              <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                <Chip color="#EAF3DE" textColor="#27500A">WERK = leeg</Chip>
                <Chip color="var(--color-background-secondary)" textColor="var(--color-text-secondary)">VERLOF = v</Chip>
              </div>
            </div>
            
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => exportCSV(result)}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 18px", fontSize: 13, fontWeight: 500, background: "var(--color-background-primary)", color: "var(--color-text-primary)", border: "0.5px solid var(--color-border-secondary)", borderRadius: 8, cursor: "pointer" }}
              >
                <i className="ti ti-download" style={{ fontSize: 16 }} aria-hidden="true" />
                Opslaan als CSV
              </button>

              <button
                onClick={() => exportControleXLSX({ result, days, forced, holidays, people, start })}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 18px", fontSize: 13, fontWeight: 500, background: "var(--color-background-primary)", color: "var(--color-text-primary)", border: "0.5px solid var(--color-border-secondary)", borderRadius: 8, cursor: "pointer" }}
              >
                <i className="ti ti-download" style={{ fontSize: 16 }} aria-hidden="true" />
                Opslaan als Excel (controlebestand)
              </button>
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", fontSize: 12, width: "100%" }}>
              <thead>
                <tr>
                  {Object.keys(result[0]).map((col) => (
                    <th key={col} style={{ background: "var(--color-background-secondary)", padding: "6px 8px", border: "0.5px solid var(--color-border-tertiary)", fontWeight: 500, color: "var(--color-text-secondary)", whiteSpace: "nowrap", textAlign: col === "Date" ? "left" : "center" }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.map((row, ri) => {
                  const summary = isSummaryRow(row);
                  return (
                    <tr key={ri} style={{ background: summary ? "var(--color-background-secondary)" : undefined }}>
                      {Object.entries(row).map(([key, value], ci) => {
                        let cellStyle = { padding: "4px 7px", border: "0.5px solid var(--color-border-tertiary)", textAlign: "center", whiteSpace: "nowrap" };
                        if (key === "Date") cellStyle = { ...cellStyle, textAlign: "left", fontWeight: summary ? 500 : 400, color: "var(--color-text-secondary)", fontSize: 11 };
                        else if (value === "WORK") cellStyle = { ...cellStyle, background: "#EAF3DE", color: "#27500A" };
                        else if (value === "OFF") cellStyle = { ...cellStyle, color: "var(--color-text-tertiary)" };
                        if (summary) cellStyle = { ...cellStyle, fontWeight: 500 };
                        const display = value === "WORK" ? "" : value === "OFF" ? "v" : value;
                        return <td key={ci} style={cellStyle}>{display}</td>;
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}