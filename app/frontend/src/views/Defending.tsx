import type { CSSProperties } from "react";
import type { TeamData } from "../api";
import { Note, Pitch, RankRow, rib } from "../charts";
import { pc } from "../format";

const THIRDS = ["own third", "middle third", "final third"] as const;

/* Pressures per match in a 6 x 4 grid on the same pitch, with the mean height of the defensive actions as a line. */
function PressureMap({ grid, height }: { grid: number[][]; height: number }) {
  const max = Math.max(...grid.flat(), 0.1);
  return (
    <Pitch label={`Pressures per match by zone; defensive actions at mean x ${height.toFixed(0)}`}>
      {grid.map((col, i) => col.map((v, j) => {
        const a = 0.08 + 0.85 * (v / max);
        return (
          <g key={`${i}-${j}`}>
            <rect x={i * 20 + 0.6} y={j * 20 + 0.6} width="18.8" height="18.8" rx="1.5" fill="var(--sticker)" />
            <rect x={i * 20 + 0.6} y={j * 20 + 0.6} width="18.8" height="18.8" rx="1.5" fill={`color-mix(in srgb, var(--coral) ${Math.round(a * 100)}%, transparent)`} />
            <text x={i * 20 + 10} y={j * 20 + 11.6} textAnchor="middle" fontSize="4.2" fontWeight="850" fontStyle="italic" fill="var(--sticker-ink)">{v.toFixed(1)}</text>
          </g>
        );
      }))}
      <line x1={height} x2={height} y1="-1" y2="81" stroke="var(--yellow)" strokeWidth="0.9" strokeDasharray="2 1.4" />
      <rect x={height - 13} y="-2.6" width="26" height="4.6" rx="1.2" fill="var(--sticker-ink)" />
      <text x={height} y="0.6" textAnchor="middle" fontSize="2.8" fontWeight="750" fill="var(--yellow)">defensive actions, mean x {height.toFixed(0)}</text>
    </Pitch>
  );
}

export default function Defending({ d }: { d: TeamData }) {
  const D = d.defending;
  if (!D) return <div className="state"><h2>No defending sheet</h2><p>defending_{d.key}.json is not in the data folder. It needs StatsBomb-style defensive events (Pressure, Duel, Interception); run src/oppreport.py on StatsBomb data.</p></div>;
  const ranks = d.ranks.filter((r) => r.group === "Defending");
  return (
    <>
      <div className="section-head">
        <h2>Defending</h2>
        <p>How {d.team} defends without the ball: pressing intensity, where it presses, how high it defends, what it concedes. {D.matches} matches; intervals are 95% bootstrap over matches.</p>
      </div>

      <div className="layout-split">
        <section className="sticker" style={rib(3)} aria-labelledby="pm-h">
          <span className="no">Pressing</span>
          <div className="pitch-wrap"><PressureMap grid={D.pressures.grid_per_match} height={D.height.mean_x} /></div>
          <div className="replay-cap"><div>
            <h2 id="pm-h">{D.pressures.per_match.toFixed(0)} pressures per match</h2>
            <p>Attacking left to right: the right of the pitch is the opponent's half. {pc(D.pressures.by_third["final third"].share)} of pressures in the final third; {pc(D.pressures.counterpress_share)} are counter-pressures (within 5 s of losing the ball).</p>
          </div></div>
        </section>
        <div className="stack">
          <div className="fam-row" style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
            {[
              { k: "PPDA", v: D.ppda.value.toFixed(1), ci: `${D.ppda.ci[0].toFixed(1)}–${D.ppda.ci[1].toFixed(1)}`, l5: D.ppda.last5.toFixed(1), sub: "opponent passes per defensive action; lower = more intense", i: 3 },
              { k: "Height", v: D.height.mean_x.toFixed(1), ci: `${D.height.ci[0].toFixed(1)}–${D.height.ci[1].toFixed(1)}`, l5: D.height.last5.toFixed(1), sub: "mean x of defensive actions (0 own goal, 120 opponent goal)", i: 1 },
              { k: "Shots against", v: D.conceded.shots_per_match.toFixed(1), ci: `${D.conceded.shots_ci[0].toFixed(1)}–${D.conceded.shots_ci[1].toFixed(1)}`, l5: D.conceded.last5_shots.toFixed(1), sub: "opponent shots per match", i: 0 },
              { k: "xG against", v: D.conceded.xg_per_match.toFixed(2), ci: `${D.conceded.xg_ci[0].toFixed(2)}–${D.conceded.xg_ci[1].toFixed(2)}`, l5: D.conceded.last5_xg.toFixed(2), sub: "StatsBomb xG of opponent shots per match", i: 4 },
            ].map((c, n) => (
              <div key={c.k} className="sticker fam-front enter" style={{ ...rib(c.i), "--i": n } as CSSProperties}>
                <div className="ribbon" />
                <div className="body">
                  <div className="line"><span className="code" style={{ fontSize: 22 }}>{c.k}</span><span className="share">{c.v}</span></div>
                  <p>{c.sub}</p>
                  <p>95%: {c.ci} · last 5: <b style={{ color: "var(--sticker-ink)" }}>{c.l5}</b></p>
                </div>
              </div>
            ))}
          </div>
          <div className="sticker pad">
            <h3>Where they press</h3>
            <table style={{ marginTop: 6 }}>
              <thead><tr><th>Third</th><th>Share of pressures</th><th>Per match</th></tr></thead>
              <tbody>{THIRDS.map((t) => <tr key={t}><td><b>{t}</b></td><td>{pc(D.pressures.by_third[t].share)}</td><td>{D.pressures.by_third[t].per_match.toFixed(0)}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="section-head"><h2>Against the other teams</h2><p>Each dot is a team in this folder; the big yellow dot is {d.team}. Left = lowest, right = highest.</p></div>
        <div className="ranks" style={{ gridTemplateColumns: "minmax(0, 1fr)" }}>{ranks.map((r) => <RankRow key={r.id} r={r} current={d.key} />)}</div>
      </section>
      <div className="stack" style={{ marginTop: 18 }}>
        <Note kind="caution" tag="PPDA">PPDA also depends on how much the opponent has the ball: against a team that dominates possession opponents make few passes, so its PPDA can be high even when it presses high. Read it with the pressures in the final third and the height.</Note>
        <Note kind="info" tag="Limits">Pressures and the counterpress flag are StatsBomb definitions; seasons and data versions differ between teams (2015/16 vs 2023/24), so compare ranks loosely. Event data do not show positions off the ball: the defensive line itself is not observed, the height of defensive actions is a proxy.</Note>
      </div>
    </>
  );
}
