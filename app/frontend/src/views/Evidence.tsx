import { useEffect, useRef, useState } from "react";
import { api, type Evidence as EvData, type EvStatement, type Grade, type TeamData } from "../api";
import { GRADE_SAYS, GradeMark, Note } from "../charts";
import { pc } from "../format";

/* How far each type of number in the report can be trusted: grades of the evidence study (docs/protocol_evidence_grade.md),
   read from results/evidence_grade_corrected.json. Nothing is recomputed here. */
const NAME: Record<string, string> = {
  S01: "Open-play sequences per match", S02: "Passes per sequence", S03: "Long-pass share of a sequence", S04: "Share of sequences starting in own half (x < 45)",
  S05: "Sequences ending in a shot", S06: "Sequence duration", F07: "Share of each build-up family", F08: "Share of each advanced family",
  R09: "Goal kicks: first pass short", R10: "Goal kicks: reached the opponent half", R11: "Goal kicks: ended in own half", R12: "Keeper: first pass short",
  R13: "Throw-ins in own half: ended in own half", P14: "Corners per match", P15: "Corners played short or outside the box", P16: "Corners to the far post",
  P17: "Corners ending in a shot", T18: "Open-play losses per match", T19: "Losses in own third", T20: "Ball regained within 5 s of a loss",
  T21: "Recoveries in the final third (share)", T22: "Recoveries followed by a shot within 10 s", D23: "PPDA", D24: "Pressures per match",
  D25: "Share of pressures in the final third", D26: "Height of defensive actions", D27: "Shots conceded per match", D28: "xG conceded per match",
  A29: "Shots per match", A30: "xG per match", A31: "xT added per match", A32: "Own-half pass completion under pressure",
  K33: "Main build-up receiver's share of receptions", K34: "Main corner taker's share of corners",
};
const GRADES: Grade[] = ["A", "B", "C", "D"];
const s2 = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(2)}`;

/* The map: x = tells teams apart (discrimination), y = beats the league average for the next match (forecast skill, with its 95% interval). */
const X0 = 0.3, X1 = 1, Y0 = -0.12, Y1 = 0.42, W = 640, H = 380, L = 54, R = 14, T = 14, B = 46;
const px = (d: number) => L + ((Math.min(Math.max(d, X0), X1) - X0) / (X1 - X0)) * (W - L - R);
const py = (s: number) => T + ((Y1 - Math.min(Math.max(s, Y0), Y1)) / (Y1 - Y0)) * (H - T - B);

function EvidenceMap({ rows, hot, setHot, pick }: { rows: [string, EvStatement][]; hot: string; setHot: (id: string) => void; pick: (id: string) => void }) {
  const pts = rows.filter(([, r]) => r.D != null);
  const named = (id: string, r: EvStatement) => id === hot || r.skill_ci[0] >= 0.1 || r.grade === "D";
  const h = pts.find(([id]) => id === hot);
  return (
    <svg className="ev-map" viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Every graded number placed by how well it tells teams apart and how well it forecasts the next match">
      {[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].map((v) => <text key={v} className="tick" x={px(v)} y={H - B + 18} textAnchor="middle">{v.toFixed(1)}</text>)}
      {[-0.1, 0, 0.1, 0.2, 0.3, 0.4].map((v) => <text key={v} className="tick" x={L - 8} y={py(v) + 4} textAnchor="end">{v.toFixed(1)}</text>)}
      <line className="ref zero" x1={L} x2={W - R} y1={py(0)} y2={py(0)} />
      <line className="ref" x1={L} x2={W - R} y1={py(0.1)} y2={py(0.1)} />
      <line className="ref" x1={px(0.5)} x2={px(0.5)} y1={T} y2={H - B} />
      <line className="ref" x1={px(0.7)} x2={px(0.7)} y1={T} y2={H - B} />
      <text className="ref-l" x={W - R - 4} y={py(0) - 6} textAnchor="end">no better than the league average</text>
      <text className="ref-l" x={px(0.7) + 5} y={T + 11}>high</text>
      <text className="ref-l" x={px(0.5) + 5} y={T + 11}>medium</text>
      <text className="axis" x={(L + W - R) / 2} y={H - 6} textAnchor="middle">Tells teams apart over a season (discrimination) →</text>
      <text className="axis" transform={`translate(13 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle">Forecasts the next match (skill) →</text>
      {pts.map(([id, r]) => (
        <g key={id} className={`pt g-${r.grade}${id === hot ? " hot" : ""}`} tabIndex={0} role="button" aria-label={`${id} ${NAME[id]}: grade ${r.grade}, forecast skill ${s2(r.skill)}, discrimination ${r.D!.toFixed(2)}`}
          onMouseEnter={() => setHot(id)} onFocus={() => setHot(id)} onClick={() => pick(id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(id); } }}>
          <line className="ci" x1={px(r.D!)} x2={px(r.D!)} y1={py(r.skill_ci[0])} y2={py(r.skill_ci[1])} />
          <circle cx={px(r.D!)} cy={py(r.skill)} r={id === hot ? 8 : 6} />
          {named(id, r) && <text className="pt-l" x={px(r.D!) + 10} y={py(r.skill) + 4}>{id}</text>}
        </g>
      ))}
      {h && <text className="pt-name" x={Math.min(px(h[1].D!), W - R - 4)} y={Math.max(py(h[1].skill_ci[1]) - 10, T + 28)} textAnchor={px(h[1].D!) > W - 200 ? "end" : "middle"}>{NAME[h[0]]}</text>}
    </svg>
  );
}

export default function Evidence({ d, focus }: { d: TeamData; focus: string }) {
  const [ev, setEv] = useState<EvData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hot, setHot] = useState(focus);
  const rowRef = useRef<Record<string, HTMLTableRowElement | null>>({});
  useEffect(() => { api.evidence().then(setEv).catch((e) => setErr(e.message)); }, []);
  useEffect(() => {
    if (!ev || !focus) return;
    setHot(focus);
    rowRef.current[focus]?.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [ev, focus]);

  if (err) return <div className="state"><h2>Could not load the evidence grades</h2><p>{err}</p></div>;
  if (!ev) return <div aria-busy="true"><div className="skeleton" style={{ height: 60, width: "45%" }} /><div className="skeleton" style={{ height: 380 }} /></div>;
  if (!ev.available || !ev.statements) {
    return <div className="state"><h2>No evidence grades yet</h2><p className="small">Run <code>src/week4/evidence_grade.py</code> as described in docs/protocol_evidence_grade.md; the app reads results/evidence_grade_corrected.json.</p></div>;
  }
  const S = ev.statements, rows = Object.entries(S);
  const byGrade = (g: Grade) => rows.filter(([, r]) => r.grade === g).sort((a, b) => b[1].skill - a[1].skill);
  const helps = rows.filter(([, r]) => r.forecast !== "none").length, strong = rows.filter(([, r]) => r.forecast === "strong").length;
  const apart = rows.filter(([, r]) => r.discrimination === "high" || r.discrimination === "medium").length, withD = rows.filter(([, r]) => r.discrimination !== "n/a").length;
  const l5worse = rows.filter(([, r]) => r.last5_verdict === "season better").length, l5better = rows.filter(([, r]) => r.last5_verdict === "last 5 better");
  const cov = rows.map(([, r]) => r.coverage_80), sc = Object.entries(ev.sanity_checks ?? {});
  const dropped = Object.entries(ev.dropped ?? {});
  const pick = (id: string) => { setHot(id); rowRef.current[id]?.scrollIntoView({ block: "center", behavior: "smooth" }); };

  return (
    <>
      <section aria-labelledby="ev-h">
        <div className="section-head">
          <h2 id="ev-h">How far each number can be trusted</h2>
          <p>{`Every type of number in this report was graded on ${ev.n_teams} teams it had never analysed (StatsBomb open data, Premier League, La Liga, Serie A and Ligue 1, 2015/16). Two questions: does the number tell teams apart over a season, and does a team's season so far forecast its next match better than the average team of its league? The grade is for the type of number, not for ${d.team}.`}</p>
        </div>
        <div className="layout-split">
          <figure className="sticker pad ev-fig">
            <span className="no">{`${rows.length} numbers`}</span>
            <EvidenceMap rows={rows} hot={hot} setHot={setHot} pick={pick} />
            <figcaption className="small s-muted">Each mark is one type of number with its 95% interval. The grade uses the lower end of the interval: above 0.10 is a strong forecast, above 0 a weak one. Families (F07, F08) are not on the map: each team has its own families, so they have no common value to compare between teams. Hover or focus a mark to name it; click to find it in the table.</figcaption>
          </figure>
          <div>
            <ul className="ev-legend">
              {GRADES.map((g) => (
                <li key={g}><GradeMark g={g} /><span>{GRADE_SAYS[g]}</span><b>{ev.grades?.[g] ?? 0}</b></li>
              ))}
            </ul>
            <div className="stack" style={{ marginTop: 20 }}>
              <Note kind="info" tag="Finding">{`${apart} of ${withD} numbers tell teams apart over a season, but only ${helps} of ${rows.length} forecast the next match better than the league average, and only ${strong} clearly. Telling teams apart and saying what they will do next are different things.`}</Note>
              <Note kind="info" tag="Last 5">{`The last 5 matches forecast the next match worse than the season so far for ${l5worse} of ${rows.length} numbers${l5better.length ? ` (better only for: ${l5better.map(([id]) => NAME[id]).join(", ")})` : ""}. Read a change in the last 5 as a reason to watch video, not as the new value.`}</Note>
              <Note kind="ok" tag="Intervals">{`The 80% interval for the next match contained the real value ${pc(Math.min(...cov))} to ${pc(Math.max(...cov))} of the time, across all ${rows.length} numbers: the uncertainty the report shows is about right.`}</Note>
            </div>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="ev-t">
        <div className="section-head">
          <h2 id="ev-t">Every graded number</h2>
          <p>Skill: 0 = no better than assuming an average team of the league, 1 = perfect; it is computed match by match from the 6th match of each team. Tells teams apart: share of the differences between teams that is not sampling noise (0.7 or more high, 0.5 medium). Interval held: how often the 80% interval contained the next match. Matches needed: to be within half the typical gap between teams.</p>
        </div>
        <div className="table-wrap">
          <table className="ev-table">
            <thead>
              <tr><th>Number</th><th>Next match: skill (95%)</th><th>Tells teams apart</th><th>80% interval held</th><th>Matches needed</th><th>Last 5 vs season</th>{ev.provider && <th>Same in Wyscout</th>}</tr>
            </thead>
            {GRADES.map((g) => byGrade(g).length > 0 && (
              <tbody key={g}>
                <tr className="grp"><th colSpan={ev.provider ? 7 : 6}><GradeMark g={g} /> {GRADE_SAYS[g]}</th></tr>
                {byGrade(g).map(([id, r]) => (
                  <tr key={id} ref={(el) => { rowRef.current[id] = el; }} className={id === hot ? "sel" : undefined} onMouseEnter={() => setHot(id)}>
                    <td><span className="ev-id">{id}</span>{NAME[id]}{ev.shown_in_app?.[id] && <small>{`In this app: ${ev.shown_in_app[id].join(", ")}`}</small>}</td>
                    <td><b>{s2(r.skill)}</b> <small className="inl">{`[${s2(r.skill_ci[0])}, ${s2(r.skill_ci[1])}]`}</small><small>{r.forecast}</small></td>
                    <td>{r.D == null ? "—" : <><b>{r.D.toFixed(2)}</b><small>{r.discrimination}</small></>}</td>
                    <td><b>{pc(r.coverage_80)}</b><small>{r.calibration}</small></td>
                    <td>{String(r.matches_needed) === "n/a" ? "—" : String(r.matches_needed)}</td>
                    <td>{r.last5_verdict}</td>
                    {ev.provider && <td>{ev.provider[id]?.label ?? "—"}{ev.provider[id]?.seen_before && <small>seen before</small>}</td>}
                  </tr>
                ))}
              </tbody>
            ))}
          </table>
        </div>
      </section>

      <section className="section" aria-labelledby="ev-l">
        <div className="section-head"><h2 id="ev-l">Limits</h2></div>
        <div className="layout-2">
          <div className="stack">
            <Note kind="caution" tag="Scope">One season (2015/16) and one data provider. The forecast does not adjust for the opponent, the venue or the line-up: an analyst who does can do better, so the skill is a floor, not a ceiling.</Note>
            {!ev.provider && <Note kind="caution" tag="Provider">The check with a second provider (Wyscout, Barcelona 2017/18) has not been run yet: the grades rest on StatsBomb definitions only.</Note>}
            <Note kind="caution" tag="Thresholds">The thresholds (0.10 for the forecast, 0.5 and 0.7 for telling teams apart) are conventions written down before the run, not derived from the data.</Note>
          </div>
          <div className="stack">
            {sc.filter(([, ok]) => !ok).map(([k]) => (
              <Note key={k} kind="caution" tag="Expectation failed">{k.startsWith("SC1") ? "Before the run we wrote that the counter-press share would not tell teams apart. It does (0.71): differences between teams are small but real over a season. It still does not forecast the next match. Reported as it came." : k}</Note>
            ))}
            {dropped.length > 0 && <Note kind="info" tag="Correction">{`${dropped.map(([t, m]) => `${m.length} matches of ${t}`).join(" and ")} were left out: in those event files StatsBomb names the team differently, so its own events were missing (protocol, note 1). The run before this correction is kept unedited in the repository.`}</Note>}
            <p className="small">{`Protocol written and pushed before the run: docs/protocol_evidence_grade.md. Results: ${ev.source}.`}</p>
          </div>
        </div>
      </section>
    </>
  );
}
