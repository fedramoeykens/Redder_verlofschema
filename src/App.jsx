import { useState, useEffect, useRef } from "react";
import ExcelJS from "exceljs";

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

// A person's "id" (a, b, c...) is the stable identifier used for the backend
// payload and to match columns in the returned schedule table. It never
// changes, even if the person's display name is edited or left blank.
// getDisplayName resolves what should actually be *shown* to a human:
// the typed name if present, otherwise "Redder A" / "Redder B" / etc.
function getDisplayName(p) {
  const trimmed = (p.name || "").trim();
  return trimmed ? trimmed : `Redder ${(p.id || "").toUpperCase()}`;
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

function colLetter(colIdx0) {
  let n = colIdx0 + 1;
  let s = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    s = String.fromCharCode(65 + rem) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}
function cellAddr(r0, c0) {
  return `${colLetter(c0)}${r0 + 1}`;
}

async function exportControleXLSX({ result, days, forced = [], holidays = [], people = [], start }) {
  if (!result || !result.length) return;

  const startDate = new Date(start + "T00:00:00");
  const targetYear = startDate.getFullYear();
  const targetMonth = startDate.getMonth();
  const daysInMonth = new Date(targetYear, targetMonth + 1, 0).getDate();

  // Build (row, day) pairs together and drop anything that doesn't correspond
  // to a real, valid day inside the target month (guards against upstream
  // producing more rows than days, mismatched dates, duplicates, etc).
  const pairs = result
    .map((row, index) => ({ row, rawDay: days[index] }))
    .filter(({ row }) => row && typeof row === "object")
    .map(({ row, rawDay }) => ({
      row,
      day: rawDay instanceof Date ? rawDay : new Date(rawDay)
    }))
    .filter(({ day }) =>
      day instanceof Date &&
      !isNaN(day.getTime()) &&
      day.getFullYear() === targetYear &&
      day.getMonth() === targetMonth
    );

  const seen = new Set();
  const dayRows = [];
  const dayDates = [];
  for (const { row, day } of pairs) {
    const dom = day.getDate();
    if (seen.has(dom) || dom > daysInMonth) continue;
    seen.add(dom);
    dayRows.push(row);
    dayDates.push(day);
  }

  const nPeople = people.length;

  const firstCol = 2;
  const aanwezigCol = firstCol + nPeople;
  const verlofCol = aanwezigCol + 1;
  const commandCol = verlofCol + 1;

  const titleRow = 0;
  const headerRow = 1;
  const nameRow = 2;
  const dataStartRow = 4;

  const monthLabel = `${MONTHS_NL[targetMonth]} ${targetYear}`;

  const lastDataRow = dataStartRow + dayRows.length - 1;
  const inactRow = lastDataRow + 2;
  const sunRow = inactRow + 1;
  const aanwezigRow = sunRow + 1;
  const legendStart = aanwezigRow + 3;

  const legend = [
    "CV= betaalde compensatiedag voor gewerkte feestdag",
    "Blanco = GEPRESTEERDE DAG",
    "V = INACTIVITEIT",
    "",
    "Bij afwezigheid van één der redders (ziekte, AO) zorgt het vaste team voor vervanging.",
    "Redders B zijn belast met verantwoordelijkheid van eerste redders A bij hun afwezigheid."
  ];

  const totalRows = legendStart + legend.length;

  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(`Controle ${monthLabel}`.slice(0, 31), {
    pageSetup: { orientation: "landscape", fitToPage: true, fitToWidth: 1, fitToHeight: 0 }
  });

  const thin = { style: "thin", color: { argb: "FF000000" } };
  const border = { top: thin, bottom: thin, left: thin, right: thin };

  const styleCell = (r0, c0, { bold = false, fill = null, align = "center", color = "FF000000" } = {}) => {
    const cell = ws.getCell(r0 + 1, c0 + 1);
    cell.font = { name: "Arial", size: 10, bold, color: { argb: color } };
    cell.alignment = { horizontal: align, vertical: "middle" };
    cell.border = border;
    if (fill) cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: fill } };
  };

  const setVal = (r0, c0, v) => {
    ws.getCell(r0 + 1, c0 + 1).value = v ?? "";
  };

  /* 1. Header & Titles */
  setVal(titleRow, 0, "Reddingsdienst dienstrooster");
  setVal(titleRow, 4, monthLabel);

  setVal(headerRow, firstCol, "PO");
  if (nPeople > 1) setVal(headerRow, firstCol + 1, "2RED");
  for (let i = 2; i < nPeople; i++) setVal(headerRow, firstCol + i, "R");

  setVal(headerRow, aanwezigCol, "Aantal R aanwezig");
  setVal(headerRow, verlofCol, "Aantal in verlof");
  setVal(headerRow, commandCol, "Controle");

  // Name row: resolved display name (typed name, or "Redder A/B/C..." fallback)
  people.forEach((p, i) => {
    setVal(nameRow, firstCol + i, getDisplayName(p).toUpperCase());
  });

  /* 2. Process Data Rows */
  const greyRows = [];
  const sunHolidayRows = [];

  dayRows.forEach((row, index) => {
    const r = dataStartRow + index;
    const day = dayDates[index];

    const isSaturday = day.getDay() === 6;
    const isSunday = day.getDay() === 0;
    const holiday = holidays.includes(day.getDate());
    const forcedDay = forced.includes(day.getDate());

    if ((isSaturday || isSunday || holiday) && !forcedDay) greyRows.push(r);
    if ((isSunday || holiday) && !forcedDay) sunHolidayRows.push(r);

    setVal(r, 0, WEEKDAYS_NL[day.getDay()]);
    setVal(r, 1, `${day.getDate()} ${MONTHS_NL[day.getMonth()]}`);

    people.forEach((p, i) => {
      let value = "";
      if (Object.prototype.hasOwnProperty.call(row, p.id)) {
        value = row[p.id];
      } else {
        const key = Object.keys(row).find(k => k.toLowerCase() === (p.id || "").toLowerCase());
        if (key) value = row[key];
      }

      if (typeof value === "string") {
        const v = value.trim().toUpperCase();
        if (v === "WORK") value = "";
        if (v === "OFF") value = "v";
        if (v === "CV") value = "cv";
      }

      setVal(r, firstCol + i, value);
    });
  });

  /* 3. Labels */
  setVal(inactRow, 0, "Inactiviteit");
  setVal(sunRow, 0, "Zon- en feestdagen");
  setVal(aanwezigRow, 0, "Aanwezig");
  legend.forEach((txt, i) => setVal(legendStart + i, 0, txt));

  /* 4. Daily Row Formulas (live formulas — command status is computed by
     Excel itself, so it always reflects the current cell values, even
     after manual edits) */
  dayRows.forEach((row, index) => {
    const r = dataStartRow + index;
    const day = dayDates[index];

    const startAddr = cellAddr(r, firstCol);
    const endAddr = cellAddr(r, firstCol + nPeople - 1);
    const aanwezigAddr = cellAddr(r, aanwezigCol);
    const verlofAddr = cellAddr(r, verlofCol);

    ws.getCell(r + 1, aanwezigCol + 1).value = { formula: `COUNTBLANK(${startAddr}:${endAddr})` };
    ws.getCell(r + 1, verlofCol + 1).value = { formula: `COUNTIF(${startAddr}:${endAddr},"v")` };

    const forcedDay = forced.includes(day.getDate());
    ws.getCell(r + 1, commandCol + 1).value = {
      formula: forcedDay
        ? `IF(${aanwezigAddr}>=${nPeople},"OK","NOK")`
        : `IF(AND(${aanwezigAddr}>=4,${verlofAddr}>=3),"OK","NOK")`
    };
  });

  /* 5. Total Columns Formulas */
  people.forEach((p, i) => {
    const colIdx = firstCol + i;
    const colName = colLetter(colIdx);
    const startRowExcel = dataStartRow + 1;
    const endRowExcel = lastDataRow + 1;

    ws.getCell(inactRow + 1, colIdx + 1).value = {
      formula: `COUNTIF(${colName}${startRowExcel}:${colName}${endRowExcel},"v")`
    };

    if (sunHolidayRows.length > 0) {
      const vFormula = sunHolidayRows.map(r => `COUNTIF(${colName}${r + 1},"v")`).join("+");
      const cvFormula = sunHolidayRows.map(r => `COUNTIF(${colName}${r + 1},"cv")`).join("+");
      ws.getCell(sunRow + 1, colIdx + 1).value = { formula: `${vFormula}+${cvFormula}` };
    } else {
      ws.getCell(sunRow + 1, colIdx + 1).value = 0;
    }

    ws.getCell(aanwezigRow + 1, colIdx + 1).value = {
      formula: `COUNTBLANK(${colName}${startRowExcel}:${colName}${endRowExcel})`
    };
  });

  /* 6. Base Styling (border/font on every used cell) */
  for (let r = 0; r < totalRows; r++) {
    for (let c = 0; c <= commandCol; c++) {
      const cell = ws.getCell(r + 1, c + 1);
      if (cell.value !== null && cell.value !== undefined ) {
        styleCell(r, c);
      }
    }
  }

  for (let c = 0; c <= commandCol; c++) {
    styleCell(titleRow, c, { bold: true, align: "center" });
    styleCell(headerRow, c, { bold: true, fill: "FFD9EAD3" });
    styleCell(nameRow, c, { bold: true, fill: "FFEDEDED" });
  }

  // Dark grey: Saturday / Sunday / holiday rows
  greyRows.forEach(r => {
    for (let c = firstCol; c < firstCol + nPeople; c++) {
      styleCell(r, c, {  fill: "D9D9D9",
  color: "000000" });
    }
  });

  // Base bold styling for the Controle column (no static fill — color comes
  // from the live conditional formatting rule below, so it always tracks
  // the actual formula result even after manual edits).
  dayRows.forEach((row, index) => {
    const r = dataStartRow + index;
    styleCell(r, commandCol, { bold: true });
  });

  /* 6b. Live conditional formatting for the Controle column: green when the
     formula evaluates to "OK", red when "NOK". This is evaluated by Excel
     itself on every recalculation, so it stays correct after edits. */
  if (dayRows.length > 0) {
    const firstAddr = cellAddr(dataStartRow, commandCol);
    const lastAddr = cellAddr(lastDataRow, commandCol);
    ws.addConditionalFormatting({
      ref: `${firstAddr}:${lastAddr}`,
      rules: [
        {
          type: "expression",
          formulae: [`${firstAddr}="OK"`],
          priority: 1,
          style: {
            font: { bold: true, color: { argb: "FF006100" } },
            fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFC6EFCE" } }
          }
        },
        {
          type: "expression",
          formulae: [`${firstAddr}="NOK"`],
          priority: 2,
          style: {
            font: { bold: true, color: { argb: "FF9C0006" } },
            fill: { type: "pattern", pattern: "solid", fgColor: { argb: "FFFFC7CE" } }
          }
        }
      ]
    });
  }

  /* 7. Worksheet Properties */
  ws.columns = [
    { width: 13 },
    { width: 15 },
    ...people.map(() => ({ width: 9 })),
    { width: 18 },
    { width: 16 },
    { width: 12 }
  ];

  for (let r = 0; r < totalRows; r++) {
    ws.getRow(r + 1).height = r === titleRow ? 22 : 18;
  }

  /* 8. Export */
  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `Controlebestand_verlofregeling_${monthLabel}.xlsx`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
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
          <div key={p.id} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <label style={{ fontSize: 11, color: "var(--color-text-tertiary)", fontWeight: 500, textTransform: "uppercase" }}>
              {p.id}
              {p.name.trim() && (
                <span style={{ fontWeight: 400, textTransform: "none", color: "var(--color-text-tertiary)" }}>
                  {" · "}{p.name.trim()}
                </span>
              )}
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

function PersonBlock({ person, pi, days, forced, holidays, onTargetChange, onNameChange, onPrefClick }) {
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
          flexShrink: 0,
        }}>
          {person.id.toUpperCase()}
        </div>
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>
          Redder {person.id.toUpperCase()}
        </span>
        <input
          value={person.name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="Naam invullen"
          style={{
            fontSize: 13, color: "var(--color-text-primary)",
            border: "0.5px solid var(--color-border-tertiary)",
            background: "var(--color-background-secondary)",
            padding: "4px 8px", borderRadius: 6, outline: "none",
            minWidth: 120,
          }}
        />
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
  // Each person has a stable `id` (the letter, a/b/c/...) used internally for
  // the backend payload and to match schedule columns, and an editable
  // `name` shown in the UI/export. `name` starts blank; getDisplayName()
  // falls back to "Redder A" etc. wherever it's needed.
  const [people, setPeople] = useState(
    NAMES.map((n) => ({ id: n, name: "", sundayQuota: 3, holidayQuota: 1, target: 19, prefs: {} }))
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

  // Uniqueness is checked on the *resolved* display name (typed name, or the
  // "Redder A/B/C" fallback when blank) — since ids are always unique by
  // construction, this only ever flags genuine duplicate typed names.
  const namesUnique = new Set(people.map((p) => getDisplayName(p).toLowerCase())).size === people.length && people.length > 0;

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
      failLabel: "Er zijn dubbele namen bij de redders.",
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
      // Keyed by the stable letter id, not the (editable) display name —
      // this is the contract the backend expects and matches the columns
      // that come back in the schedule table.
      sun_quotas: Object.fromEntries(people.map((p) => [p.id, p.sundayQuota])),
      fixed_holiday_quotas: Object.fromEntries(people.map((p) => [p.id, p.holidayQuota])),
      targets: Object.fromEntries(people.map((p) => [p.id, p.target])),
      prefs: Object.fromEntries(people.map((p) => [p.id, buildPrefs(p.prefs)])),
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
            <PersonBlock key={p.id} person={p} pi={pi} days={days} forced={forced} holidays={holidays}
              onTargetChange={(v) => updatePerson(pi, "target", v)}
              onNameChange={(v) => updatePerson(pi, "name", v)}
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