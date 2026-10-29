import { useEffect, useState } from "react";
import type { TeamData, Third } from "../api";
import { evidenceHref, Explain, GradeKey, GradeMark, Note, Pitch, plain, Replay, useGrades } from "../charts";
import { pc } from "../format";
import { clipId, pickRecent, toRef, useClips, useGoals } from "../useClips";
import GoalToggle from "./GoalToggle";

const THIRDS: [string, number][] = [
  ["own third", 0],
  ["middle third", 40],
  ["final third", 80],
];
const ci = (c: [number, number]) => `${pc(c[0])}–${pc(c[1])}`;
const REPLAYS: [string, string][] = [
  ["Recovery final third - shot within 10 s", "High recoveries that led to a shot"],
  ["Loss own third", "Losses in the own third"],
  ["Loss final third - regained in 5 s", "Losses regained within 5 s"],
];

/* The same pitch; each third filled by events per match. */
function Thirds({
  data,
  color,
  label,
  lines,
}: {
  data: Record<string, Third>;
  color: string;
  label: string;
  lines: (t: Third) => string[];
}) {
  const max = Math.max(...Object.values(data).map((t) => t.per_match), 1);
  return (
    <Pitch label={label}>
      {THIRDS.map(([name, x]) => {
        const t = data[name];
        if (!t) return null;
        const a = 0.14 + 0.62 * (t.per_match / max);
        return (
          <g key={name}>
            <rect
              x={x + 0.8}
              y="0.8"
              width="38.4"
              height="78.4"
              rx="2"
              fill={`color-mix(in srgb, ${color} ${Math.round(a * 100)}%, transparent)`}
            />
            <text
              x={x + 20}
              y="33"
              textAnchor="middle"
              fontSize="13"
              fontWeight="900"
              fontStyle="italic"
              fill={a > 0.55 ? "var(--sticker-ink)" : "var(--run)"}
            >
              {t.per_match.toFixed(1)}
            </text>
            <text
              x={x + 20}
              y="39.5"
              textAnchor="middle"
              fontSize="3"
              fontWeight="750"
              fill={a > 0.55 ? "var(--sticker-ink)" : "var(--run)"}
            >
              per match · {name}
            </text>
            <rect x={x + 1.6} y="47.6" width="36.8" height="11.6" rx="2" fill="#121a33" fillOpacity="0.88" />
            {lines(t).map((l, i) => (
              <text
                key={i}
                x={x + 20}
                y={52.4 + i * 4.6}
                textAnchor="middle"
                fontSize="2.6"
                fontWeight="650"
                fill="var(--sticker)"
              >
                {l}
              </text>
            ))}
          </g>
        );
      })}
    </Pitch>
  );
}

export default function Transitions({
  d,
  events,
  go,
}: {
  d: TeamData;
  events: boolean;
  go: (tab: string, family?: string) => void;
}) {
  const [which, setWhich] = useState(REPLAYS[0][0]);
  const [idx, setIdx] = useState(0);
  const [onlyGoals, setOnlyGoals] = useState(false);
  useEffect(() => setIdx(0), [d.key, which, onlyGoals]);
  const { rows } = useClips(d.key, "transitions");
  const goals = useGoals(d.key, "transitions", events);
  const G = useGrades();
  const T = d.transitions;
  if (!T)
    return (
      <div className="state">
        <h2>No transition sheet</h2>
        <p>transitions_{d.key}.json is not in the data folder. Run src/oppreport.py for this team.</p>
      </div>
    );
  const l = T.losses,
    r = T.recoveries;
  const ofKind = (rows ?? []).filter((x) => x.family === which);
  const goalRows = goals ? ofKind.filter((x) => goals.has(clipId(x))) : [];
  const clips =
    events && rows
      ? (onlyGoals && goalRows.length ? pickRecent(goalRows, goalRows.length) : pickRecent(ofKind, 10)).map((x) =>
          toRef(x, true),
        )
      : [];

  return (
    <>
      <div className="section-head">
        <h2>Transitions</h2>
        <Explain>
          Where {d.team} loses and wins the ball in open play. Built from the order of actions, so it does not depend on
          the provider's possession definition. {T.matches} matches.
        </Explain>
      </div>

      <div className="layout-2">
        <section className="sticker" style={plain} aria-labelledby="lo-h">
          <span className="no">Losses</span>
          <div className="pitch-wrap">
            <Thirds
              data={l.by_third}
              color="var(--run)"
              label="Losses per match by third"
              lines={(t) => [
                `regained in 5 s: ${pc(t.regain5 ?? 0)}`,
                `shot against in 10 s: ${pc(t.conceded10 ?? 0)}`,
              ]}
            />
          </div>
          <div className="replay-cap">
            <div>
              <h2 id="lo-h">
                {G && <GradeMark g={G.of("T18")} href={evidenceHref(d.key, "T18")} />}
                {l.per_match.toFixed(1)} losses per match
              </h2>
              <p>
                {G && <GradeMark g={G.of("T20")} href={evidenceHref(d.key, "T20")} />}
                Ball regained within 5 s after {pc(l.regain5)} ({ci(l.regain5_ci)}); opponent shoots within 10 s after{" "}
                {pc(l.conceded10)} ({ci(l.conceded10_ci)}). Last 5 matches: {T.last5.losses_per_match.toFixed(1)} per
                match, regained {pc(T.last5.regain5)}.
              </p>
            </div>
          </div>
        </section>
        <section className="sticker" style={plain} aria-labelledby="re-h">
          <span className="no">Recoveries</span>
          <div className="pitch-wrap">
            <Thirds
              data={r.by_third}
              color="var(--run)"
              label="Recoveries per match by third"
              lines={(t) => [`shot in 10 s: ${pc(t.shot10 ?? 0)}`, `reached final third: ${pc(t.final_third ?? 0)}`]}
            />
          </div>
          <div className="replay-cap">
            <div>
              <h2 id="re-h">
                {G && <GradeMark none />}
                {r.per_match.toFixed(1)} recoveries per match
              </h2>
              <p>
                {G && <GradeMark g={G.of("T22")} href={evidenceHref(d.key, "T22")} />}
                Shot within 10 s after {pc(r.shot10)} ({ci(r.shot10_ci)}). Final third:{" "}
                {r.by_third["final third"]?.per_match.toFixed(1) ?? "–"} per match
                {r.by_third["final third"]?.per_match_ci
                  ? ` (${r.by_third["final third"].per_match_ci![0].toFixed(1)}–${r.by_third["final third"].per_match_ci![1].toFixed(1)})`
                  : ""}
                ; last 5 matches {T.last5.recoveries_final_third_per_match.toFixed(1)}.
              </p>
            </div>
          </div>
        </section>
      </div>
      <div style={{ marginTop: 18 }}>
        {G && <GradeKey n={G.n} href={evidenceHref(d.key)} />}
        <Note kind="caution" tag="Caution">
          The counter-press share varied little between the teams we tested (17-19%): it describes, it does not separate
          styles.
        </Note>
      </div>

      <section className="section" aria-labelledby="tr-h">
        <div className="section-head">
          <h2 id="tr-h">Watch them</h2>
          <div className="pills" role="group" aria-label="Which transitions">
            {REPLAYS.map(([k, label]) => (
              <button key={k} type="button" aria-pressed={k === which} onClick={() => setWhich(k)}>
                {label}
              </button>
            ))}
          </div>
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
                  {events
                    ? rows
                      ? "No clips of this kind."
                      : "Loading the clip list…"
                    : "Replays need the raw event files."}
                </div>
              }
            />
            {clips[idx] && (
              <div className="replay-cap">
                <p>
                  From 6 s before to 10 s after: {clips[idx].detail}. Opponent actions in red.
                  {onlyGoals && goalRows.length
                    ? which.startsWith("Loss")
                      ? " Only losses after which the opponent scored within 10 s."
                      : " Only recoveries followed by a goal within 10 s."
                    : ""}
                </p>
              </div>
            )}
          </div>
          <div className="stack">
            <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Third</th>
                  <th>Recoveries per match (95%)</th>
                  <th>Shot in 10 s</th>
                  <th>Possession shot</th>
                </tr>
              </thead>
              <tbody>
                {THIRDS.map(
                  ([n]) =>
                    r.by_third[n] && (
                      <tr key={n}>
                        <td>
                          <b>{n}</b>
                        </td>
                        <td>
                          {r.by_third[n].per_match.toFixed(1)}{" "}
                          {r.by_third[n].per_match_ci && (
                            <span className="muted">
                              ({r.by_third[n].per_match_ci![0].toFixed(1)}–{r.by_third[n].per_match_ci![1].toFixed(1)})
                            </span>
                          )}
                        </td>
                        <td>{pc(r.by_third[n].shot10 ?? 0)}</td>
                        <td>{pc(r.by_third[n].shot ?? 0)}</td>
                      </tr>
                    ),
                )}
              </tbody>
            </table>
            </div>
            <button type="button" className="btn ghost no-print" onClick={() => go("clips:transitions")}>
              Every loss and recovery
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
