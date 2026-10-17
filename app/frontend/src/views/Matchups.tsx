import { useEffect, useState, type CSSProperties } from "react";
import { api, type MatchupMetric, type TeamData, type WithoutData } from "../api";
import { Note, rib } from "../charts";
import { fmt } from "../format";

/* What happened in past matches against different opponents. Descriptive: never a recommendation. */
const SPLITS: [string, string][] = [["opp_press", "Opponent pressing"], ["back_line", "Opponent back line"], ["venue", "Home or away"], ["without", "Without a player"]];
const VERDICT: Record<string, { tag: string; rib: number }> = { clear: { tag: "clear difference", rib: 0 }, uncertain: { tag: "uncertain", rib: 1 }, "small group": { tag: "group too small", rib: 3 } };

function DiffBar({ m }: { m: MatchupMetric }) {
  const span = Math.max(Math.abs(m.ci[0]), Math.abs(m.ci[1]), Math.abs(m.diff), 1e-6) * 1.15;
  const X = (v: number) => 150 + (v / span) * 140;
  const col = m.verdict === "clear" ? "var(--yellow)" : "var(--on-board-3)";
  return (
    <svg viewBox="0 0 300 26" className="ivl" role="img" aria-label={`${m.label}: difference ${fmt(m.diff, m.unit as "num")}, 95% ${fmt(m.ci[0], m.unit as "num")} to ${fmt(m.ci[1], m.unit as "num")}`}>
      <line x1="10" x2="290" y1="13" y2="13" stroke="var(--board-line)" strokeWidth="2" />
      <line x1="150" x2="150" y1="3" y2="23" stroke="var(--on-board-3)" strokeWidth="1.5" />
      <rect x={Math.min(X(m.ci[0]), X(m.ci[1]))} y="8" width={Math.max(Math.abs(X(m.ci[1]) - X(m.ci[0])), 2)} height="10" rx="5" fill={col} fillOpacity="0.35" />
      <rect x={X(m.diff) - 3} y="3" width="6" height="20" rx="3" fill={col} />
    </svg>
  );
}

/* Matches a player started vs matches he did not start. Same verdict rule as the other splits. */
function WithoutPlayer({ d }: { d: TeamData }) {
  const [player, setPlayer] = useState(() => new URLSearchParams(location.search).get("player") ?? "");
  const [res, setRes] = useState<WithoutData | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setErr(""); api.without(d.key, player).then(setRes).catch((e) => setErr(String(e.message ?? e))); }, [d.key, player]);
  const first = useState(d.key)[0];
  useEffect(() => { if (d.key !== first) setPlayer(""); }, [d.key, first]);
  if (err) return <div className="state" style={{ marginTop: 24 }}><p>{err}</p></div>;
  if (!res) return <div className="state" style={{ marginTop: 24 }}><p>Loading…</p></div>;
  const unit = (u: string) => u as "pct" | "num" | "num2";
  return (
    <div style={{ marginTop: 24 }}>
      <div className="filters" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <label htmlFor="wp" style={{ fontWeight: 750 }}>Player</label>
        <select id="wp" className="pill-select" value={player} onChange={(e) => setPlayer(e.target.value)}>
          <option value="">Choose a player…</option>
          {res.players.map((p) => <option key={p.player} value={p.player}>{p.player} · started {p.starts}, not {p.not_started}{p.usable ? "" : " (too few)"}</option>)}
        </select>
      </div>
      {!player || !res.metrics ? <p style={{ marginTop: 16 }}>Pick a player: the app compares the matches he started with the matches he did not (starting elevens in the data). Useful when he is injured or suspended for the next match. Players who started almost every match leave too few matches without them.</p> : (
        <div className="layout-split layout-matchup" style={{ marginTop: 20 }}>
          <section className="sticker pad">
            <h3>With {res.player} starting ({res.n_with}) vs without ({res.n_without})</h3>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table>
                <thead><tr><th>Per match</th><th>With</th><th>Without</th><th style={{ minWidth: 170 }}>Difference</th><th className="l">Verdict</th></tr></thead>
                <tbody>{res.metrics.map((x) => (
                  <tr key={x.id}>
                    <td>{x.label}</td><td className="num">{x.a != null ? fmt(x.a, unit(x.unit)) : "–"}</td><td className="num">{x.b != null ? fmt(x.b, unit(x.unit)) : "–"}</td>
                    <td>{x.diff != null && x.ci ? <DiffBar m={{ ...x, diff: x.diff, ci: x.ci, a: x.a ?? 0, b: x.b ?? 0, direction: "", linked: false } as MatchupMetric} /> : null}</td>
                    <td className="l"><span className="chip" style={rib(VERDICT[x.verdict].rib)}>{VERDICT[x.verdict].tag}</span></td>
                  </tr>))}</tbody>
              </table>
            </div>
          </section>
          <div className="stack">
            <div className="sticker pad">
              <h3>In words</h3>
              {res.metrics.some((x) => x.verdict === "clear")
                ? <ul className="read" style={{ marginTop: 6 }}>{res.metrics.filter((x) => x.verdict === "clear").map((x) => <li key={x.id}><b>{x.label}</b>: {fmt(x.a ?? 0, unit(x.unit))} with him, {fmt(x.b ?? 0, unit(x.unit))} without.</li>)}</ul>
                : <p style={{ marginTop: 8 }}>{Math.min(res.n_with ?? 0, res.n_without ?? 0) < 6 ? "Too few matches in one group: nothing can be said." : "No clear difference: without him the numbers stay within chance."}</p>}
              {res.without_matches && res.without_matches.length > 0 && <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>Matches without him: {res.without_matches.map((w) => `${w.opponent} ${w.score}`).join(", ")}.</p>}
            </div>
            <Note kind="caution" tag="Not cause and effect">The matches without him also differ in opponent, venue and other absences. About one 'clear' result in 20 is expected by chance with this many rows.</Note>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Matchups({ d }: { d: TeamData }) {
  const M = d.matchups;
  const [split, setSplit] = useState(() => new URLSearchParams(location.search).get("split") ?? "opp_press");
  if (!M) return <div className="state"><h2>No matchup sheet</h2><p>matchups_{d.key}.json is not in the data folder. It needs StatsBomb-style events with formations; run src/oppreport.py on StatsBomb data.</p></div>;
  const pills = (
    <div className="pills" role="group" aria-label="Split the matches by">
      {SPLITS.map(([k, l]) => <button key={k} type="button" aria-pressed={split === k} onClick={() => setSplit(k)}>{l}</button>)}
    </div>
  );
  if (split === "without") return (<><div className="section-head"><h2>Matchups</h2><p>How {d.team}'s numbers changed without one of its players. What happened in the past, to check on video.</p></div>{pills}<WithoutPlayer d={d} /></>);
  const S = M.splits[split]; const [ga, gb] = S.groups;
  const clear = S.metrics.filter((m) => m.verdict === "clear" && !m.linked);
  const unit = (m: MatchupMetric) => m.unit as "pct" | "num" | "num2";
  const groupOf = (r: (typeof M.per_match)[number]) => split === "opp_press" ? (r.opp_press === "high press" ? ga : gb) : split === "back_line" ? (r.opp_back_line === "back four" ? gb : r.opp_back_line === "unknown" ? "unknown" : ga) : (r.venue === "home" ? ga : gb);

  return (
    <>
      <div className="section-head">
        <h2>Matchups</h2>
        <p>How {d.team}'s numbers differed in its {M.matches} matches depending on the opponent. What happened in the past, to check on video: not a recommendation of formation or style.</p>
      </div>
      <div className="pills" role="group" aria-label="Split the matches by">
        {SPLITS.map(([k, l]) => <button key={k} type="button" aria-pressed={split === k} onClick={() => setSplit(k)}>{l}</button>)}
      </div>

      <div className="layout-split layout-matchup" style={{ marginTop: 24 }}>
        <section className="sticker pad" aria-labelledby="mu-h">
          <h3 id="mu-h">{ga} ({S.n_a} matches) vs {gb} ({S.n_b})</h3>
          <p className="s-muted" style={{ fontSize: 12.5, margin: "4px 0 10px" }}>Rule: {S.rule}. Bar = difference ({ga} minus {gb}) with its 95% interval; yellow = clear, grey = uncertain.</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Per match</th><th>{ga}</th><th>{gb}</th><th style={{ minWidth: 170 }}>Difference</th><th className="l">Verdict</th></tr></thead>
              <tbody>
                {S.metrics.map((m) => (
                  <tr key={m.id}>
                    <td>{m.label}{m.linked && <small style={{ display: "block", color: "var(--sticker-ink-2)" }}>partly by construction</small>}</td>
                    <td className="num">{fmt(m.a, unit(m))}</td><td className="num">{fmt(m.b, unit(m))}</td>
                    <td><DiffBar m={m} /></td>
                    <td className="l"><span className="chip" style={rib(VERDICT[m.verdict].rib)}>{VERDICT[m.verdict].tag}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <div className="stack">
          <div className="sticker pad">
            <h3>In words</h3>
            {S.metrics.every((m) => m.verdict === "small group") ? (
              <p style={{ marginTop: 8 }}>One group has fewer than {M.min_group} matches: nothing can be said from these data.</p>
            ) : clear.length ? (
              <ul className="read" style={{ marginTop: 6 }}>
                {clear.map((m) => <li key={m.id}><b>{m.label}</b>: {fmt(m.a, unit(m))} {ga} vs {fmt(m.b, unit(m))} {gb} per match.</li>)}
              </ul>
            ) : (
              <p style={{ marginTop: 8 }}>No clear difference between the two groups, apart from measures linked to how the groups are defined.</p>
            )}
            <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>With about 10 comparisons, one "clear" result in 20 is expected by chance. The groups also differ in opponent strength, score and venue.</p>
          </div>
          <Note kind="caution" tag="Not advice">This shows what happened, not what would work. It cannot say which formation or style to choose: matches differ in many ways at once and the groups are small. Use it to pick matches to watch.</Note>
        </div>
      </div>

      <section className="section" aria-labelledby="mm-h">
        <div className="section-head"><h2 id="mm-h">Match by match</h2><p>Opponent PPDA = passes {d.team} could make in its own 60% per opponent defensive action (lower = the opponent pressed more). Median {M.median_opp_ppda.toFixed(1)}.</p></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th className="l">Date</th><th className="l">Opponent</th><th className="l">Venue</th><th>Score</th><th>Opp. formation</th><th>Opp. PPDA</th><th className="l">Group</th><th>xG for</th><th>xG against</th><th>Lost in own half</th></tr></thead>
            <tbody>
              {M.per_match.map((r) => (
                <tr key={r.match}>
                  <td className="l">{r.date}</td><td className="l">{r.opponent}</td><td className="l">{r.venue}</td><td><b>{r.score}</b></td>
                  <td>{r.opp_formation || "–"}</td><td>{r.opp_ppda.toFixed(1)}</td>
                  <td className="l"><span className="chip" style={{ ...rib(groupOf(r) === ga ? 0 : 1) } as CSSProperties}>{groupOf(r)}</span></td>
                  <td>{r.xg_for.toFixed(2)}</td><td>{r.xg_against.toFixed(2)}</td><td>{r.lost_own_half}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
