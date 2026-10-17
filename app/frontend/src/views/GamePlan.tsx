import { useEffect, useState, type CSSProperties } from "react";
import { api, type GamePlan as Plan, type GPEvents, type TeamData, type TeamSummary } from "../api";
import { Icon } from "../charts";
import { Note, Pitch, rib } from "../charts";
import { fmt, ordinal } from "../format";

const TAB_LABEL: Record<string, string> = { restarts: "Restarts", defending: "Defending", transitions: "Transitions", "build-up": "Families", setpieces: "Set pieces", matchups: "Matchups" };
const MINE_KEY = "oppreport.mine";
type Topic = "priorities" | "with_ball" | "without_ball" | "transitions" | "set_pieces";
const QUESTIONS: [Topic, (t: string) => string][] = [
  ["priorities", () => "What matters most?"], ["with_ball", (t) => `How do we play out against ${t}?`], ["without_ball", (t) => `How do we defend against ${t}?`],
  ["transitions", () => "Where can we win the ball?"], ["set_pieces", () => "Set pieces?"],
];
const store = { get: () => { try { return localStorage.getItem(MINE_KEY) ?? ""; } catch { return ""; } }, set: (v: string) => { try { localStorage.setItem(MINE_KEY, v); } catch { /* private mode */ } } };

const place = (r: number, of: number) => (r === 1 ? `highest of ${of}` : r === of ? `lowest of ${of}` : `${ordinal(r)} of ${of}`);
const unit = (u: string) => u as "pct" | "num" | "num2";

/* Goals (numbers) and xG per match (bars) by 15-minute slot: scored above the line, conceded below. */
function Timeline({ t }: { t: GPEvents["timeline"] }) {
  const max = Math.max(...t.flatMap((s) => [s.xg_for, s.xg_against]), 0.05);
  const H = 70, W = 60;
  return (
    <svg viewBox={`0 0 ${t.length * W + 20} ${2 * H + 40}`} className="timeline" role="img" aria-label={t.map((s) => `${s.slot}: ${s.goals_for} scored, ${s.goals_against} conceded`).join("; ")}>
      <line x1="10" x2={t.length * W + 10} y1={H + 20} y2={H + 20} stroke="currentColor" strokeOpacity="0.35" />
      <line x1={10 + 3 * W} x2={10 + 3 * W} y1="8" y2={2 * H + 32} stroke="currentColor" strokeOpacity="0.25" strokeDasharray="3 3" />
      {t.map((s, i) => {
        const x = 10 + i * W + 10, w = W - 20, hf = (H * s.xg_for) / max, ha = (H * s.xg_against) / max;
        return (
          <g key={s.slot} className="enter" style={{ "--i": i } as CSSProperties}>
            <rect x={x} y={H + 20 - hf} width={w} height={hf} rx="4" fill="var(--lime)" />
            <rect x={x} y={H + 20} width={w} height={ha} rx="4" fill="var(--coral)" />
            <text x={x + w / 2} y={H + 14 - hf} textAnchor="middle" fontSize="13" fontWeight="850" fill="currentColor">{s.goals_for}</text>
            <text x={x + w / 2} y={H + 36 + ha} textAnchor="middle" fontSize="13" fontWeight="850" fill="currentColor">{s.goals_against}</text>
            <text x={x + w / 2} y={2 * H + 38} textAnchor="middle" fontSize="10.5" fill="currentColor" fillOpacity="0.7">{s.slot}'</text>
          </g>
        );
      })}
    </svg>
  );
}

/* Their own half (own goal on the left) in 3 x 3 zones: completion under pressure, against the other teams in the folder. */
function PressureZones({ pz, team }: { pz: NonNullable<Plan["pressure_zones"]>; team: string }) {
  return (
    <Pitch label={`${team}: pass completion under pressure by zone of their own half`}>
      {pz.zones.map((z, i) => {
        const d = z.diff ?? 0; const col = z.few ? "var(--board-raised)" : d < 0 ? "var(--coral)" : "var(--lime)";
        const a = z.few ? 0.35 : Math.min(0.9, 0.18 + Math.abs(d) * 5);
        const cx = (z.x0 + z.x1) / 2, cy = (z.y0 + z.y1) / 2;
        return (
          <g key={i} className="enter" style={{ "--i": i } as CSSProperties}>
            <rect x={z.x0 + 0.6} y={z.y0 + 0.6} width={z.x1 - z.x0 - 1.2} height={z.y1 - z.y0 - 1.2} rx="1.5" fill="var(--sticker)" />
            <rect x={z.x0 + 0.6} y={z.y0 + 0.6} width={z.x1 - z.x0 - 1.2} height={z.y1 - z.y0 - 1.2} rx="1.5" fill={col} fillOpacity={a}
              stroke={z.weaker ? "var(--sticker-ink)" : "none"} strokeWidth="0.9" strokeDasharray={z.weaker ? "2 1" : undefined} />
            <text x={cx} y={cy - 1.6} textAnchor="middle" fontSize="4.4" fontWeight="900" fontStyle="italic" fill="var(--sticker-ink)">{Math.round(100 * z.up_completion)}%</text>
            <text x={cx} y={cy + 3} textAnchor="middle" fontSize="2.3" fontWeight="700" fill="var(--sticker-ink)">others {z.ref_completion != null ? Math.round(100 * z.ref_completion) : "–"}%</text>
            <text x={cx} y={cy + 6.4} textAnchor="middle" fontSize="2" fill="var(--sticker-ink)" fillOpacity="0.75">{z.few ? `only ${z.under_pressure}` : `n ${z.under_pressure} · ${Math.round(100 * z.up_long_share)}% long`}</text>
          </g>
        );
      })}
      <text x="90" y="41" textAnchor="middle" fontSize="3.2" fontWeight="800" fill="var(--pitch-line)">← their own half · they attack →</text>
    </Pitch>
  );
}

/* Starting formation drawn schematically: goalkeeper, then one line per digit (e.g. 3-4-2-1), mirrored for the opponent. */
function Shape({ raw, side }: { raw: string; side: "left" | "right" }) {
  const lines = raw.split("").map(Number).filter((n) => n > 0);
  const X = (x: number) => (side === "left" ? x : 120 - x);
  const col = side === "left" ? "var(--sky)" : "var(--coral)";
  const dots: [number, number][] = [[4, 40]];
  lines.forEach((n, i) => {
    const x = lines.length > 1 ? 15 + (i * 38) / (lines.length - 1) : 30;
    for (let j = 0; j < n; j++) dots.push([x, (80 * (j + 1)) / (n + 1)]);
  });
  return (
    <g>
      {dots.map(([x, y], i) => (
        <g key={i} className="enter" style={{ "--i": i } as CSSProperties}>
          <circle cx={X(x)} cy={y} r="2.6" fill={col} stroke="var(--sticker-ink)" strokeWidth="0.5" />
          {i === 0 && <text x={X(x)} y={y + 1} textAnchor="middle" fontSize="2.6" fontWeight="850" fill="var(--sticker-ink)">GK</text>}
        </g>
      ))}
    </g>
  );
}

export default function GamePlan({ d, teams }: { d: TeamData; teams: TeamSummary[] }) {
  const [mine, setMine] = useState(() => new URLSearchParams(location.search).get("mine") ?? store.get());
  const [plan, setPlan] = useState<Plan | null>(null);
  const [err, setErr] = useState("");
  const [topic, setTopic] = useState<Topic>("priorities");
  const [evs, setEvs] = useState<GPEvents | null | "none">(null);
  useEffect(() => { setEvs(null); api.gameplanEvents(d.key).then(setEvs).catch(() => setEvs("none")); }, [d.key]);
  const my = mine && mine !== d.key && teams.some((t) => t.key === mine) ? mine : "";

  useEffect(() => {
    setPlan(null); setErr("");
    api.gameplan(d.key, my).then(setPlan).catch((e) => setErr(String(e.message ?? e)));
  }, [d.key, my]);


  if (err) return <div className="state"><h2>No game plan</h2><p>{err}</p></div>;
  const P = plan; const fo = P?.formations.opponent; const fm = P?.formations.mine;
  return (
    <>
      <div className="section-head">
        <h2>Game plan</h2>
        <p>Preparing to play {d.team}: their shape, how they play and where to look. Hints come from fixed rules on how they rank among the {P?.teams_in_folder ?? "…"} teams in this folder. They say where to look on video, not what will work.</p>
      </div>
      <div className="filters" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" className="icon-btn" onClick={() => window.print()} aria-label="Print the match plan" style={{ order: 2, marginLeft: "auto" }}>{Icon.print}<span>Print match plan</span></button>
        <label htmlFor="mine" style={{ fontWeight: 750 }}>Your team</label>
        <select id="mine" className="pill-select" value={my} onChange={(e) => { setMine(e.target.value); store.set(e.target.value); }}>
          <option value="">None (opponent only)</option>
          {teams.filter((t) => t.key !== d.key).map((t) => <option key={t.key} value={t.key}>{t.team}</option>)}
        </select>
      </div>
      {!P ? <div className="state" style={{ marginTop: 24 }}><p>Loading…</p></div> : (
        <>
          <div className="layout-split" style={{ marginTop: 24 }}>
            <section className="sticker" style={rib(3)} aria-labelledby="gp-shape">
              <span className="no">Shapes</span>
              <div className="pitch-wrap">
                <Pitch label={`Starting formations: ${fm ? `${P.mine} ${fm.most_used[0]?.formation} against ` : ""}${d.team} ${fo?.most_used[0]?.formation ?? "unknown"}`}>
                  {fm?.most_used[0] && <Shape raw={fm.most_used[0].raw} side="left" />}
                  {fo?.most_used[0] && <Shape raw={fo.most_used[0].raw} side="right" />}
                </Pitch>
              </div>
              <div className="replay-cap"><div>
                <h2 id="gp-shape">{fm ? `${fm.most_used[0]?.formation} vs ${fo?.most_used[0]?.formation ?? "?"}` : `${d.team}: ${fo?.most_used[0]?.formation ?? "formation unknown"}`}</h2>
                <p>Most used starting formation{fm ? <>s: <b style={{ color: "var(--sky)" }}>{P.mine}</b> left, <b style={{ color: "var(--coral)" }}>{d.team}</b> right</> : <>, <b style={{ color: "var(--coral)" }}>{d.team}</b> attacking right to left</>}. Schematic: the formation on the team sheet, not positions in play.</p>
              </div></div>
            </section>
            <div className="stack">
              {fo && (
                <div className="sticker pad">
                  <h3>{d.team}: formations</h3>
                  <table style={{ marginTop: 6 }}>
                    <thead><tr><th>Formation</th><th>Matches</th><th>Share</th></tr></thead>
                    <tbody>{fo.most_used.map((f) => <tr key={f.raw}><td><b>{f.formation}</b></td><td>{f.matches}</td><td>{fmt(f.matches / fo.matches, "pct")}</td></tr>)}</tbody>
                  </table>
                  <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>Last 5: {fo.last5.map((f, i) => <span key={i} className="chip" style={{ ...rib(4), marginRight: 4 }} title={`${f.date} vs ${f.opponent}`}>{f.formation}</span>)}</p>
                </div>
              )}
              <div className="sticker pad">
                <h3>How they play</h3>
                <ul className="read" style={{ marginTop: 6 }}>
                  {P.profile.map((r) => <li key={r.id}><b>{r.label}</b>: {fmt(r.value, unit(r.unit))} <span className="s-muted">({place(r.rank, r.of)})</span></li>)}
                </ul>
              </div>
            </div>
          </div>

          <section className="section" aria-labelledby="gp-h">
            <div className="section-head"><h2 id="gp-h">Where to look</h2><p>{P.hints.length} hints fired. Each one shows the numbers that triggered it. "Highest" or "lowest" is among the teams in this folder, which can be from other leagues and seasons.</p></div>
            {P.hints.length === 0 ? <p>No rule fired: {d.team} is not at the extremes of any measure here.</p> : (
              <div className="fam-row" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
                {P.hints.map((h, n) => (
                  <article key={h.id} className="sticker fam-front enter" style={{ ...rib(h.side === "both" ? 2 : n % 5), "--i": n } as CSSProperties}>
                    <div className="ribbon" />
                    <div className="body">
                      {h.side === "both" && <span className="chip" style={{ ...rib(1), marginBottom: 6 }}>you vs them</span>}
                      <h3 style={{ margin: "2px 0 6px" }}>{h.title}</h3>
                      <p>{h.why}</p>
                      <p style={{ color: "var(--sticker-ink)", fontWeight: 650 }}>{h.look}</p>
                      <p style={{ fontSize: 12 }}>
                        {h.evidence.map((e, i) => <span key={i} style={{ display: "block" }}>{e.team === "you" ? `${P.mine}: ` : e.team === "opponent" ? `${d.team}: ` : ""}{e.label} {fmt(e.value, unit(e.unit))} · {place(e.rank, e.of)}</span>)}
                      </p>
                      <a href={`#/${d.key}/${h.tab}`} style={{ fontWeight: 750, fontSize: 13 }}>Check in {TAB_LABEL[h.tab] ?? h.tab} →</a>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          {P.pressure_zones && (
            <section className="section" aria-labelledby="pz-h">
              <div className="section-head"><h2 id="pz-h">Where pressing hurts them</h2><p>Their own half, own goal on the left. Each zone: share of their open-play passes completed when under pressure, against the other {P.pressure_zones.teams_in_reference} teams in the same zone. Red = below the others, green = above; dashed outline = at least 5 points below with 40+ passes.</p></div>
              <div className="layout-split">
                <div className="sticker" style={rib(0)}><span className="no">Under pressure</span><div className="pitch-wrap"><PressureZones pz={P.pressure_zones} team={d.team} /></div></div>
                <div className="stack">
                  <div className="sticker pad">
                    <h3>Overall</h3>
                    <p style={{ marginTop: 6 }}>In their own half {d.team} complete <b>{Math.round(100 * P.pressure_zones.total.completion)}%</b> of passes under pressure and <b>{Math.round(100 * P.pressure_zones.total.free_completion)}%</b> when free ({P.pressure_zones.total.passes} passes under pressure in {P.pressure_zones.matches} matches).</p>
                    <p style={{ marginTop: 8 }}>{P.pressure_zones.zones.some((z) => z.weaker)
                      ? <>Zones clearly below the other teams: <b>{P.pressure_zones.zones.filter((z) => z.weaker).length}</b>. Start the pressing plan from the darkest red one and check it on video.</>
                      : <>No zone is clearly below the other teams: under pressure they play out about as well as the others or better. Pressing them is not suggested by these numbers.</>}</p>
                  </div>
                  <Note kind="caution" tag="Read with care">Pressure is StatsBomb's flag on the pass (a player pressing within a short time). Zones near their own goal are hard for every team, which is why each zone is compared with the others in the same place. Completion does not say whether the ball was then won.</Note>
                </div>
              </div>
            </section>
          )}

          {evs && evs !== "none" && (
            <section className="section" aria-labelledby="kp-h">
              <div className="section-head"><h2 id="kp-h">Key players</h2><p>From all {evs.matches} matches: top 3 per role. Per match = matches in which the player appears. Names and shirt numbers as in the StatsBomb data.</p></div>
              <div className="fam-row" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
                {evs.players.map((r, n) => (
                  <article key={r.id} className="sticker fam-front enter" style={{ ...rib(n), "--i": n } as CSSProperties}>
                    <div className="ribbon" />
                    <div className="body">
                      <h3 style={{ margin: "2px 0 8px" }}>{r.role}</h3>
                      <ol className="players">
                        {r.top.map((p, i) => (
                          <li key={p.full} title={p.full}>
                            <span className="shirt" data-first={i === 0 || undefined}>{p.shirt ?? "–"}</span>
                            <span className="pname">{p.player}{p.keeper && <small> GK</small>}</span>
                            <span className="pval"><b>{r.id === "xg" ? p.per_match.toFixed(2) : p.per_match.toFixed(1)}</b><small>/match · {r.id === "xg" ? p.total.toFixed(1) : p.total} in {p.matches}</small></span>
                          </li>
                        ))}
                      </ol>
                      <p style={{ fontSize: 12, marginTop: 8 }}>{r.unit}. {r.note}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          <div className="layout-2" style={{ marginTop: 28, display: "grid", gap: 24, gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
            {evs && evs !== "none" && (
              <div className="sticker pad">
                <h3>When they score and concede</h3>
                <Timeline t={evs.timeline} />
                <p className="s-muted" style={{ fontSize: 12.5 }}>Bars: xG per match in each 15 minutes, <b style={{ color: "var(--sticker-ink)" }}>created</b> above (green), <b style={{ color: "var(--sticker-ink)" }}>conceded</b> below (red). Numbers: goals in the season. Stoppage time counts in the last slot of each half. Goals per slot are few: a single slot can move a lot by chance.</p>
              </div>
            )}
            {P.watch_first && (
              <div className="sticker pad">
                <h3>Watch first</h3>
                <p className="s-muted" style={{ fontSize: 12.5, margin: "4px 0 8px" }}>{P.mine ? <>Their matches against {P.watch_first.rule}: the closest to how {P.mine} defends.</> : <>Pick your team above to see their matches against opponents that defended like you. Now: {P.watch_first.rule}.</>}</p>
                <ol className="watch">
                  {P.watch_first.matches.map((m) => (
                    <li key={m.match}>
                      <span><b>{m.opponent}</b> <small>{m.date} · {m.venue} · {m.opp_formation ? m.opp_formation.split("").join("-") : "–"} · opp. PPDA {m.opp_ppda.toFixed(1)}</small></span>
                      <span className="score">{m.score}</span>
                      <a href={`#/${d.key}/clips/sequences?opponent=${encodeURIComponent(m.opponent)}`}>Clips →</a>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>

          <div className="layout-2" style={{ marginTop: 28, display: "grid", gap: 24, gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
            <div className="sticker pad">
              <h3>What happened in their past matches</h3>
              {P.opp_past.length ? (
                <ul className="read" style={{ marginTop: 6 }}>
                  {P.opp_past.map((p, i) => <li key={i}><b>{p.label}</b> {p.ga} ({p.n_a} matches): {fmt(p.a, unit(p.unit))} vs {fmt(p.b, unit(p.unit))} {p.gb} ({p.n_b}).</li>)}
                </ul>
              ) : <p style={{ marginTop: 8 }}>No clear difference between groups of their matches (pressing, back line, home/away).</p>}
              <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>Only clear differences not linked to how the groups are formed; about one in 20 is expected by chance. Details in <a href={`#/${d.key}/matchups`}>Matchups</a>.</p>
            </div>
            {P.my_vs_press && (
              <div className="sticker pad">
                <h3>{P.mine} against a high press</h3>
                <table style={{ marginTop: 6 }}>
                  <thead><tr><th>Per match</th><th>{P.my_vs_press.groups[0]} ({P.my_vs_press.n_a})</th><th>{P.my_vs_press.groups[1]} ({P.my_vs_press.n_b})</th><th>Verdict</th></tr></thead>
                  <tbody>{P.my_vs_press.metrics.map((m) => <tr key={m.id}><td>{m.label}</td><td>{fmt(m.a, unit(m.unit))}</td><td>{fmt(m.b, unit(m.unit))}</td><td>{m.verdict}{m.linked ? "*" : ""}</td></tr>)}</tbody>
                </table>
                <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>From your own past matches. * partly by construction (shares events with the opponent PPDA that forms the groups).</p>
              </div>
            )}
          </div>

          <section className="section" aria-labelledby="ai-h">
            <div className="section-head"><h2 id="ai-h">Coach brief</h2><p>{P.brief.intro}</p></div>
            <div className="sticker pad">
              <div className="pills" role="group" aria-label="Choose a question">
                {QUESTIONS.map(([t, label]) => <button key={t} type="button" aria-pressed={topic === t} onClick={() => setTopic(t)}>{label(d.team)}</button>)}
              </div>
              <div className="brief enter" key={topic} aria-live="polite">
                <h3>{topic === "priorities" ? "Three priorities" : P.brief.phases[topic].title}</h3>
                <ol>{(topic === "priorities" ? (P.brief.priorities.length ? P.brief.priorities : [`No rule fired: nothing in ${d.team}'s numbers is at the extremes. Prepare as usual and use the video.`]) : P.brief.phases[topic].lines).map((l, i) => <li key={i}>{l}</li>)}</ol>
              </div>
            </div>
          </section>

          <div style={{ marginTop: 18 }}>
            <Note kind="caution" tag="Hints, not advice">The rules were fixed in advance and are simple (top or bottom among the teams here). None was tested for whether following it wins matches: data like these cannot say which formation or style will work. Use them to choose what to watch, and decide with the staff.</Note>
          </div>
        </>
      )}
    </>
  );
}
