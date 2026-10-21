import { useEffect, useState, type CSSProperties } from "react";
import type { ClipRow, TeamData } from "../api";
import { Explain, Note, Pitch, plain, RankRow, Replay } from "../charts";
import { pc } from "../format";
import { clipId, toRef, useClips, useGoals } from "../useClips";
import GoalToggle from "./GoalToggle";

const THIRDS = ["own third", "middle third", "final third"] as const;
const CHAN = ["left", "centre", "right"] as const;
const ci2 = (c: [number, number]) => `${c[0].toFixed(2)}–${c[1].toFixed(2)}`;

/* xT added per match by start zone of the move, 6 x 4 grid on the pitch. Negative zones (back passes win) stay empty. */
function ThreatMap({ grid }: { grid: number[][] }) {
  const max = Math.max(...grid.flat(), 0.01);
  return (
    <Pitch label="xT added per match by the zone where the pass or carry starts">
      {grid.map((col, i) =>
        col.map((v, j) => {
          const a = 0.06 + (0.86 * Math.max(v, 0)) / max;
          return (
            <g key={`${i}-${j}`}>
              <rect x={i * 20 + 0.6} y={j * 20 + 0.6} width="18.8" height="18.8" rx="1.5" fill="var(--sticker)" />
              <rect
                x={i * 20 + 0.6}
                y={j * 20 + 0.6}
                width="18.8"
                height="18.8"
                rx="1.5"
                fill={`color-mix(in srgb, var(--lime) ${Math.round(a * 100)}%, transparent)`}
              />
              <rect
                x={i * 20 + 4.2}
                y={j * 20 + 7.4}
                width="11.6"
                height="5.6"
                rx="1.4"
                fill="var(--sticker)"
                fillOpacity="0.85"
              />
              <text
                x={i * 20 + 10}
                y={j * 20 + 11.6}
                textAnchor="middle"
                fontSize="4.2"
                fontWeight="850"
                fontStyle="italic"
                fill="var(--sticker-ink)"
              >
                {v.toFixed(2)}
              </text>
            </g>
          );
        }),
      )}
    </Pitch>
  );
}

export default function Threat({
  d,
  events,
  go,
}: {
  d: TeamData;
  events: boolean;
  go: (tab: string, family?: string) => void;
}) {
  const [idx, setIdx] = useState(0);
  const [onlyGoals, setOnlyGoals] = useState(false);
  useEffect(() => setIdx(0), [d.key, onlyGoals]);
  const { rows } = useClips(d.key, "threat");
  const goals = useGoals(d.key, "threat", events);
  const X = d.xthreat;
  if (!X)
    return (
      <div className="state">
        <h2>No threat sheet</h2>
        <p>
          xthreat_{d.key}.json is not in the data folder. It needs StatsBomb-style pass outcomes; run src/oppreport.py
          on StatsBomb data.
        </p>
      </div>
    );
  const ranks = d.ranks.filter((r) => r.group === "Threat");
  const xtOf = (r: ClipRow) => Number((r as ClipRow & { xt?: string }).xt ?? 0);
  const goalRows = goals && rows ? rows.filter((r) => goals.has(clipId(r))) : [];
  const pool = onlyGoals && goalRows.length ? goalRows : (rows ?? []);
  const best = events && rows ? [...pool].sort((a, b) => xtOf(b) - xtOf(a)).slice(0, 12) : [];
  const clips = best.map((r) => {
    const ref = toRef(r);
    const who = (r as ClipRow & { player?: string }).player;
    return {
      ...ref,
      detail: `${who ? `${who}, ` : ""}${ref.detail.replace(r.family, `${r.family} +${xtOf(r).toFixed(2)} xT`)}`,
    };
  });
  const carryShare = X.xt.per_match ? X.xt_carry.per_match / X.xt.per_match : 0;
  const best3 = Object.entries(X.origin_per_match).sort((a, b) => b[1] - a[1])[0];

  return (
    <>
      <div className="section-head">
        <h2>Threat</h2>
        <Explain>
          How much {d.team} moves the ball into dangerous zones with completed passes and carries (Expected Threat, xT):
          a move counts the value of the zone where it ends minus the zone where it starts. {X.matches} matches;
          intervals are 95% bootstrap over matches.
        </Explain>
      </div>

      <div className="layout-split">
        <section className="sticker" style={plain} aria-labelledby="xt-h">
          <span className="no">Where it starts</span>
          <div className="pitch-wrap">
            <ThreatMap grid={X.map_per_match} />
          </div>
          <div className="replay-cap">
            <div>
              <h2 id="xt-h">{X.xt.per_match.toFixed(2)} xT added per match</h2>
              <p>
                Attacking left to right; top = left side. Largest share from the {best3[0].replace("|", ", ")} (
                {best3[1].toFixed(2)} per match). Last 5 matches: {X.xt.last5.toFixed(2)}.
              </p>
            </div>
          </div>
        </section>
        <div className="stack">
          <div className="fam-row" style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
            {[
              {
                k: "xT added",
                v: X.xt.per_match.toFixed(2),
                sub: `per match · 95%: ${ci2(X.xt.ci)} · last 5: ${X.xt.last5.toFixed(2)}`,
              },
              {
                k: "By carries",
                v: pc(carryShare),
                sub: `${X.xt_carry.per_match.toFixed(2)} per match from carries, ${X.xt_pass.per_match.toFixed(2)} from passes`,
              },
              {
                k: "Given up",
                v: X.given_up.per_match.toFixed(2),
                sub: `xT of the start zone of incomplete passes, per match (not subtracted) · 95%: ${ci2(X.given_up.ci)}`,
              },
              {
                k: "Conceded",
                v: X.conceded.per_match.toFixed(2),
                sub: `xT added by the opponents per match · 95%: ${ci2(X.conceded.ci)} · last 5: ${X.conceded.last5.toFixed(2)}`,
              },
            ].map((c, n) => (
              <div key={c.k} className="sticker fam-front enter" style={{ ...plain, "--i": n } as CSSProperties}>
                <div className="ribbon" />
                <div className="body">
                  <div className="line">
                    <span className="code" style={{ fontSize: 22 }}>
                      {c.k}
                    </span>
                    <span className="share">{c.v}</span>
                  </div>
                  <p>{c.sub}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="sticker pad">
            <h3>Who adds it</h3>
            <table style={{ marginTop: 6 }}>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Per match played</th>
                  <th>Matches</th>
                  <th>Share of team</th>
                </tr>
              </thead>
              <tbody>
                {X.players.map((p) => (
                  <tr key={p.player}>
                    <td>
                      <b>{p.player}</b>
                    </td>
                    <td>{p.per_match.toFixed(2)}</td>
                    <td>{p.matches}</td>
                    <td>{p.share == null ? "–" : pc(p.share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <section className="section" aria-labelledby="xo-h">
        <div className="section-head">
          <h2 id="xo-h">By third and channel</h2>
          <Explain>xT added per match, by where the move starts.</Explain>
        </div>
        <table>
          <thead>
            <tr>
              <th>Third</th>
              {CHAN.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {THIRDS.map((t) => (
              <tr key={t}>
                <td>
                  <b>{t}</b>
                </td>
                {CHAN.map((c) => (
                  <td key={c}>{X.origin_per_match[`${t}|${c}`].toFixed(2)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="section" aria-labelledby="xw-h">
        <div className="section-head">
          <h2 id="xw-h">Watch the biggest moves</h2>
          <Explain>The season's passes and carries with the largest xT added, replayed with the possession around them.</Explain>
          <GoalToggle count={goals && goalRows.length} on={onlyGoals} set={setOnlyGoals} />
        </div>
        <div className="layout-split">
          <div className="sticker" style={plain}>
            <Replay
              teamKey={d.key}
              clips={clips}
              index={Math.min(idx, Math.max(clips.length - 1, 0))}
              onIndex={setIdx}
              fallback={
                <div className="note info" style={{ margin: 14 }}>
                  <span className="tag">Replays</span>
                  {events ? (rows ? "No clips." : "Loading the clip list…") : "Replays need the raw event files."}
                </div>
              }
            />
            {clips[idx] && (
              <div className="replay-cap">
                <p>{clips[idx].detail}</p>
              </div>
            )}
          </div>
          <div className="stack">
            <table>
              <thead>
                <tr>
                  <th>Move</th>
                  <th>xT</th>
                  <th>Match</th>
                </tr>
              </thead>
              <tbody>
                {best.map((r, i) => (
                  <tr key={i} aria-selected={i === idx} onClick={() => setIdx(i)} style={{ cursor: "pointer" }}>
                    <td>
                      <b>{(r as ClipRow & { player?: string }).player || r.family}</b>{" "}
                      <span className="muted">{r.family.replace("xT ", "")}</span>
                    </td>
                    <td>+{xtOf(r).toFixed(2)}</td>
                    <td>
                      vs {r.opponent}, {r.minute}'
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button type="button" className="btn ghost no-print" onClick={() => go("clips:threat")}>
              All 40 in the clip list
            </button>
          </div>
        </div>
      </section>

      {ranks.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Against the other teams</h2>
            <Explain>Each dot is a team in this folder; the big yellow dot is {d.team}. Left = lowest, right = highest.</Explain>
          </div>
          <div className="ranks" style={{ gridTemplateColumns: "minmax(0, 1fr)" }}>
            {ranks.map((r) => (
              <RankRow key={r.id} r={r} current={d.key} />
            ))}
          </div>
        </section>
      )}
      <div className="stack" style={{ marginTop: 18 }}>
        <Note kind="info" tag="What xT sees">
          Only where the ball goes, not how: pressure, defenders' positions and the receiver's situation are not in the
          model, and failed passes are not penalised in the main figure (see 'given up'). One grid for every team,
          fitted on {X.grid.matches} matches of the 10 thesis teams and their opponents (
          {X.grid.shots.toLocaleString("en")} open-play shots).
        </Note>
        <Note kind="caution" tag="Not by family">
          xT is not split by sequence family on purpose: the families did not explain shots better than a simple rule on
          where the sequence ends (pre-registered test, 10 teams), and xT is itself a value of where the ball ends.
        </Note>
      </div>
    </>
  );
}
