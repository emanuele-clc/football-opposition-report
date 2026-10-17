import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { api, type ClipRef, type GPEvents, type TeamData } from "../api";
import { Note, Pitch, Replay, rib } from "../charts";

/* Every goal scored and conceded, on one pitch and replayable. Origin = StatsBomb play pattern (how the possession started). */
const COLOR: Record<string, string> = {
  "Open play": "var(--lime)", "Counter-attack": "var(--yellow)", Corner: "var(--coral)", "Free kick": "var(--lilac)", "Throw-in": "var(--sky)",
  Penalty: "var(--sticker)", "Goal kick": "#9aa3bd", Keeper: "#9aa3bd", "Kick-off": "#9aa3bd", "Own goal": "#9aa3bd", Other: "#9aa3bd",
};
const ORDER = ["Open play", "Counter-attack", "Throw-in", "Corner", "Free kick", "Penalty", "Goal kick", "Keeper", "Kick-off", "Own goal", "Other"];
type Side = "for" | "against";

function OriginBar({ counts, label }: { counts: Record<string, number>; label: string }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const keys = ORDER.filter((o) => counts[o]);
  return (
    <div className="origin">
      <div className="origin-head"><b>{label}</b><span>{total}</span></div>
      <div className="origin-bar" role="img" aria-label={`${label}: ${keys.map((o) => `${o} ${counts[o]}`).join(", ")}`}>
        {keys.map((o, i) => <span key={o} className="enter" style={{ flex: counts[o], background: COLOR[o], "--i": i } as CSSProperties} title={`${o}: ${counts[o]}`} />)}
      </div>
      <div className="origin-keys">{keys.map((o) => <span key={o}><i style={{ background: COLOR[o] }} />{o} <b>{counts[o]}</b> <small>{Math.round((100 * counts[o]) / total)}%</small></span>)}</div>
    </div>
  );
}

export default function Goals({ d, events }: { d: TeamData; events: boolean }) {
  const [kp, setKp] = useState<GPEvents | null | "none">(null);
  const [side, setSide] = useState<Side>("for");
  const [origin, setOrigin] = useState("");
  const [sel, setSel] = useState(0);
  useEffect(() => { setKp(null); api.gameplanEvents(d.key).then(setKp).catch(() => setKp("none")); }, [d.key]);
  useEffect(() => setSel(0), [side, origin, d.key]);

  const goals = useMemo(() => (kp && kp !== "none" ? kp.goals.filter((g) => g.side === side && (!origin || g.origin === origin)) : []), [kp, side, origin]);
  if (kp === null) return <div className="state"><p>Loading…</p></div>;
  if (kp === "none" || !kp.goals) return <div className="state"><h2>No goal list</h2><p>keyplayers_{d.key}.json is missing or old: run src/oppreport.py (or src/report/keyplayers.py) on StatsBomb data.</p></div>;

  const refs: ClipRef[] = goals.map((g) => ({ match: g.match, half: g.half, minute: g.start_minute, second: g.start_second, possession: g.possession ?? undefined,
    title: `${g.scorer} ${g.minute}' vs ${g.opponent}`, detail: `${g.origin}${g.xg != null ? ` · xG ${g.xg.toFixed(2)}` : ""}` }));
  const all = kp.goals; const g0 = goals[Math.min(sel, goals.length - 1)];
  const xgSum = (s: Side) => all.filter((g) => g.side === s && g.xg != null).reduce((a, g) => a + (g.xg ?? 0), 0);
  const n = (s: Side) => all.filter((g) => g.side === s).length;

  return (
    <>
      <div className="section-head">
        <h2>Goals</h2>
        <p>Every goal {d.team} scored and conceded in {kp.matches} matches, where it was shot from and how the move started. Click a goal to watch the move that led to it.</p>
      </div>

      <div className="layout-split">
        <section className="sticker" style={rib(0)} aria-labelledby="gm-h">
          <span className="no">Goal map</span>
          <div className="pitch-wrap">
            <Pitch label={`Goals: ${n("for")} scored at the right end, ${n("against")} conceded at the left end`}>
              {all.filter((g) => g.x != null).map((g, i) => {
                const on = g.side === side && (!origin || g.origin === origin); const r = 0.9 + 2.2 * Math.sqrt(g.xg ?? 0.3);
                const isSel = g0 && g === g0;
                return (
                  <circle key={i} cx={g.x!} cy={g.y!} r={isSel ? r + 0.8 : r} fill={COLOR[g.origin]} fillOpacity={on ? 0.92 : 0.18}
                    stroke={isSel ? "var(--yellow)" : "var(--sticker-ink)"} strokeWidth={isSel ? 0.8 : 0.3}
                    style={{ cursor: on ? "pointer" : "default" }} onClick={() => { if (on) setSel(goals.indexOf(g)); else { setSide(g.side); setOrigin(""); } }}>
                    <title>{`${g.side === "for" ? "Scored" : "Conceded"}: ${g.scorer}, ${g.minute}' vs ${g.opponent} (${g.origin}${g.xg != null ? `, xG ${g.xg.toFixed(2)}` : ""})`}</title>
                  </circle>
                );
              })}
              <text x="117" y="77.6" textAnchor="end" fontSize="2.8" fontWeight="800" fill="var(--pitch-line)">scored →</text>
              <text x="3" y="77.6" fontSize="2.8" fontWeight="800" fill="var(--pitch-line)">← conceded</text>
            </Pitch>
          </div>
          <div className="replay-cap"><div>
            <h2 id="gm-h">{n("for")} scored, {n("against")} conceded</h2>
            <p>Dot size = xG of the shot. xG of the scored shots {xgSum("for").toFixed(1)}, of the conceded ones {xgSum("against").toFixed(1)} (own goals have no xG). Dots in the opposite half are long-range shots or misplaced coordinates in the data.</p>
          </div></div>
        </section>
        <div className="stack">
          <div className="sticker pad">
            <h3>How the goals started</h3>
            <OriginBar counts={kp.goals_by_origin.for} label="Scored" />
            <OriginBar counts={kp.goals_by_origin.against} label="Conceded" />
            <p className="s-muted" style={{ fontSize: 12.5, marginTop: 8 }}>StatsBomb's label for how the possession started: "Throw-in" means the move began with a throw-in, maybe many passes before the goal. Penalties and own goals are counted apart.</p>
          </div>
        </div>
      </div>

      <section className="section" aria-labelledby="gl-h">
        <div className="section-head"><h2 id="gl-h">Watch them</h2><p>{goals.length} goals selected. The replay shows the whole move from the first action of the possession; {side === "for" ? d.team : "the opponent"} attacks {side === "for" ? "left to right" : "right to left (red)"}.</p></div>
        <div className="pills" role="group" aria-label="Goals">
          {(["for", "against"] as Side[]).map((s) => <button key={s} type="button" aria-pressed={side === s} onClick={() => { setSide(s); setOrigin(""); }}>{s === "for" ? `Scored (${n("for")})` : `Conceded (${n("against")})`}</button>)}
          <select className="pill-select" value={origin} onChange={(e) => setOrigin(e.target.value)} aria-label="Origin" style={{ marginLeft: 8 }}>
            <option value="">All origins</option>
            {ORDER.filter((o) => kp.goals_by_origin[side][o]).map((o) => <option key={o} value={o}>{o} ({kp.goals_by_origin[side][o]})</option>)}
          </select>
        </div>
        <div className="layout-split" style={{ marginTop: 18 }}>
          <div>
            {events && refs.length ? <Replay teamKey={d.key} clips={refs} index={Math.min(sel, refs.length - 1)} onIndex={setSel} />
              : <Note kind="info" tag="Replays">{events ? "No goal in this selection." : "Replays need the raw StatsBomb events (ev/ in the data folder). The goal map and the list work without them."}</Note>}
          </div>
          <div className="sticker pad"><div className="table-wrap" style={{ maxHeight: 540, overflow: "auto" }}>
            <table>
              <thead><tr><th className="l">Opponent</th><th>Min</th><th className="l">Scorer</th><th className="l">Origin</th><th>xG</th></tr></thead>
              <tbody>
                {goals.map((g, i) => (
                  <tr key={i} onClick={() => setSel(i)} aria-selected={i === sel} style={{ cursor: "pointer", background: i === sel ? "color-mix(in srgb, var(--yellow) 30%, transparent)" : undefined }}>
                    <td className="l">{g.opponent}<small style={{ display: "block", opacity: 0.65 }}>{g.date ?? ""}</small></td><td>{g.minute}'</td><td className="l"><b>{g.scorer}</b></td>
                    <td className="l"><span className="chip" style={{ background: COLOR[g.origin] }}>{g.origin}</span></td><td>{g.xg != null ? g.xg.toFixed(2) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div></div>
        </div>
      </section>
    </>
  );
}
