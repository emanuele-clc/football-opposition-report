import { useEffect, useState, type CSSProperties } from "react";
import { api, type GamePlan as Plan, type TeamData, type TeamSummary } from "../api";
import { Note, Pitch, rib } from "../charts";
import { fmt, ordinal } from "../format";

const TAB_LABEL: Record<string, string> = { restarts: "Restarts", defending: "Defending", transitions: "Transitions", "build-up": "Families", setpieces: "Set pieces", matchups: "Matchups" };
const MINE_KEY = "oppreport.mine";
const store = { get: () => { try { return localStorage.getItem(MINE_KEY) ?? ""; } catch { return ""; } }, set: (v: string) => { try { localStorage.setItem(MINE_KEY, v); } catch { /* private mode */ } } };

const place = (r: number, of: number) => (r === 1 ? `highest of ${of}` : r === of ? `lowest of ${of}` : `${ordinal(r)} of ${of}`);
const unit = (u: string) => u as "pct" | "num" | "num2";

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
  const [q, setQ] = useState(""); const [answer, setAnswer] = useState(""); const [asking, setAsking] = useState(false);
  const my = mine && mine !== d.key && teams.some((t) => t.key === mine) ? mine : "";

  useEffect(() => {
    setPlan(null); setErr(""); setAnswer("");
    api.gameplan(d.key, my).then(setPlan).catch((e) => setErr(String(e.message ?? e)));
  }, [d.key, my]);

  const ask = async () => {
    setAsking(true); setAnswer("");
    try { setAnswer((await api.askGameplan(d.key, q, my)).answer); } catch (e) { setAnswer(`⚠ ${(e as Error).message}`); }
    setAsking(false);
  };

  if (err) return <div className="state"><h2>No game plan</h2><p>{err}</p></div>;
  const P = plan; const fo = P?.formations.opponent; const fm = P?.formations.mine;
  return (
    <>
      <div className="section-head">
        <h2>Game plan</h2>
        <p>Preparing to play {d.team}: their shape, how they play and where to look. Hints come from fixed rules on how they rank among the {P?.teams_in_folder ?? "…"} teams in this folder. They say where to look on video, not what will work.</p>
      </div>
      <div className="filters" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
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
            <div className="section-head"><h2 id="ai-h">Ask the AI</h2><p>Claude answers using only the numbers on this page, and says when they cannot answer. The question and these numbers are sent to the Claude API.</p></div>
            {P.ai ? (
              <div className="sticker pad">
                <label htmlFor="q" style={{ fontWeight: 750 }}>Your question</label>
                <textarea id="q" rows={3} value={q} maxLength={1000} onChange={(e) => setQ(e.target.value)} placeholder={`e.g. How could we get out of ${d.team}'s press?`} style={{ width: "100%", marginTop: 6, font: "inherit", padding: 10, borderRadius: 10 }} />
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                  {[`What are ${d.team}'s weak points in these numbers?`, `Should we press their goal kicks?`, `Which matches of ${d.team} should I watch first?`].map((s) => <button key={s} type="button" className="chip" style={{ border: 0, cursor: "pointer" }} onClick={() => setQ(s)}>{s}</button>)}
                  <button type="button" className="play-btn" disabled={asking || !q.trim()} onClick={ask} style={{ marginLeft: "auto" }}>{asking ? "Thinking…" : "Ask"}</button>
                </div>
                {answer && <div style={{ marginTop: 14, whiteSpace: "pre-wrap", lineHeight: 1.5 }} aria-live="polite">{answer}</div>}
              </div>
            ) : (
              <Note kind="info" tag="Off">To turn it on, set an Anthropic API key before starting the app: in PowerShell <code>$env:ANTHROPIC_API_KEY = "sk-ant-…"</code>, then start the app from the same window. The numbers on this page are sent to the Claude API: do not use it with club data you may not share.</Note>
            )}
          </section>

          <div style={{ marginTop: 18 }}>
            <Note kind="caution" tag="Hints, not advice">The rules were fixed in advance and are simple (top or bottom among the teams here). None was tested for whether following it wins matches: data like these cannot say which formation or style will work. Use them to choose what to watch, and decide with the staff.</Note>
          </div>
        </>
      )}
    </>
  );
}
