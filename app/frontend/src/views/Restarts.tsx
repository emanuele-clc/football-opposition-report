import { useEffect, useState } from "react";
import type { ClipRef, RestartKind, TeamData } from "../api";
import { Bars, Explain, Interval, Note, plain, Replay } from "../charts";
import { pc } from "../format";
import { clipId, pickRecent, toRef, useClips, useGoals } from "../useClips";
import GoalToggle from "./GoalToggle";
import PressingMap from "./PressingMap";

const LABELS: [string, string][] = [
  ["short", "First pass short (under 30 m)"],
  ["left", "First pass ends left"],
  ["centre", "First pass ends centre"],
  ["right", "First pass ends right"],
  ["opp_half", "Reached the opponent half"],
  ["final_third", "Reached the final third"],
  ["lost_own_half", "Ended in own half"],
  ["shot", "Ended in a shot"],
];
const ci = (c: [number, number] | null) => (c ? `${pc(c[0])}–${pc(c[1])}` : "–");
const outside = (m: RestartKind["metrics"][string]) => m.last5 != null && !(m.ci[0] <= m.last5 && m.last5 <= m.ci[1]);

export default function Restarts({
  d,
  events,
  go,
}: {
  d: TeamData;
  events: boolean;
  go: (tab: string, family?: string) => void;
}) {
  const kinds = Object.keys(d.restarts?.kinds ?? {});
  const [kind, setKind] = useState(kinds[0] ?? "");
  const [idx, setIdx] = useState(0);
  const [custom, setCustom] = useState<{ clips: ClipRef[]; label: string } | null>(null);
  useEffect(() => {
    setKind(kinds[0] ?? "");
    setIdx(0);
    setCustom(null);
  }, [d.key]);
  const { rows } = useClips(d.key, "restarts");
  const goals = useGoals(d.key, "restarts", events);
  const [onlyGoals, setOnlyGoals] = useState(false);
  if (!d.restarts || !kind)
    return (
      <div className="state">
        <h2>No restart sheet</h2>
        <p>restarts_{d.key}.json is not in the data folder. Run src/oppreport.py for this team.</p>
      </div>
    );
  const k = d.restarts.kinds[kind],
    ki = kinds.indexOf(kind);
  const ofKind = (rows ?? []).filter((r) => r.family.startsWith(kind + " "));
  const goalRows = goals ? ofKind.filter((r) => goals.has(clipId(r))) : [];
  const recent =
    events && rows
      ? (onlyGoals && goalRows.length ? pickRecent(goalRows, goalRows.length) : pickRecent(ofKind, 10)).map((r) =>
          toRef(r),
        )
      : [];
  const clips = custom?.clips ?? recent;
  const flagged = LABELS.filter(([m]) => k.metrics[m] && outside(k.metrics[m])).length;
  const rec = Object.entries(k.receivers).map(([p, v]) => [p, v.n] as [string, number]);

  return (
    <>
      <div className="section-head">
        <h2>Restarts</h2>
        <Explain>
          How the team plays out from goal kicks, keeper distributions and throw-ins. {d.restarts.matches} matches;
          intervals are 95% bootstrap over matches.
        </Explain>
      </div>
      <div className="pills" role="group" aria-label="Restart type">
        {kinds.map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={n === kind}
            onClick={() => {
              setKind(n);
              setIdx(0);
              setCustom(null);
            }}
          >
            {n} · {d.restarts!.kinds[n].per_match.toFixed(1)} per match
          </button>
        ))}
      </div>

      <div className="layout-split" style={{ marginTop: 28 }}>
        <section className="sticker" style={plain} aria-labelledby="rs-h">
          <span className="no">{kind}</span>
          <Replay
            teamKey={d.key}
            clips={clips}
            index={Math.min(idx, Math.max(clips.length - 1, 0))}
            onIndex={setIdx}
            fallback={
              <div className="note info" style={{ margin: 14 }}>
                <span className="tag">Replays</span>
                {events
                  ? "Loading the clip list…"
                  : "Replays need the raw event files (start the app on the StatsBomb folder)."}
              </div>
            }
          />
          <div className="replay-cap">
            <div>
              <h2 id="rs-h">
                {k.n} {kind.toLowerCase()} possessions
              </h2>
              <p>
                {k.per_match.toFixed(1)} per match · {k.passes.toFixed(1)} passes on average · {k.n_last5} in the last 5
                matches
              </p>
              {clips[idx] && (
                <p>
                  {custom
                    ? "Replaying"
                    : onlyGoals && goalRows.length
                      ? "Replaying the goals:"
                      : "Replaying the most recent:"}{" "}
                  {clips[idx].detail}.
                </p>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
              <GoalToggle
                count={goals && goalRows.length}
                on={onlyGoals}
                set={(v) => {
                  setOnlyGoals(v);
                  setIdx(0);
                  setCustom(null);
                }}
              />
              <button type="button" className="ctl no-print" onClick={() => go("clips:restarts")}>
                All restart clips
              </button>
            </div>
          </div>
        </section>

        <section className="sticker pad" aria-labelledby="out-h">
          <h3 id="out-h">What happens next</h3>
          <p className="s-muted" style={{ fontSize: 13, margin: "4px 0 6px" }}>
            Dark mark = season with its interval, coral diamond = last 5 matches.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Outcome</th>
                  <th>Season</th>
                  <th style={{ minWidth: 130 }}>0 to 100%</th>
                  <th style={{ whiteSpace: "nowrap" }}>Last 5</th>
                </tr>
              </thead>
              <tbody>
                {LABELS.filter(([m]) => k.metrics[m]).map(([m, label]) => {
                  const v = k.metrics[m],
                    off = outside(v);
                  return (
                    <tr key={m}>
                      <td>{label}</td>
                      <td>
                        <b>{pc(v.season)}</b> <span className="s-muted">({ci(v.ci)})</span>
                      </td>
                      <td>
                        <Interval
                          onSticker
                          value={v.season}
                          ci={v.ci}
                          last5={v.last5}
                          last5ci={v.last5_ci}
                          label={`${label}: season ${pc(v.season)}, last 5 ${v.last5 == null ? "none" : pc(v.last5)}`}
                        />
                      </td>
                      <td style={off ? { background: "var(--flag-soft)", fontWeight: 800 } : undefined}>
                        {v.last5 == null ? "–" : pc(v.last5)}
                        {off && <span className="sr"> outside the season interval</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {flagged > 0 && (
            <div style={{ marginTop: 12 }}>
              <Note kind="caution" tag="Check on video">
                Highlighted: the last 5 matches fall outside the season interval. A hint, not proof of a change; with 5
                matches the interval is wide.
              </Note>
            </div>
          )}
        </section>
      </div>

      {events && (
        <section className="section" aria-label="Pressing map">
          <div className="section-head">
            <h2>Where the first pass goes</h2>
            <Explain>
              Every first pass from {kind.toLowerCase()}, coloured by how the possession ended. Use it to prepare the
              press, then check on video.
            </Explain>
          </div>
          <PressingMap
            teamKey={d.key}
            kind={kind}
            onWatch={(c, label) => {
              setCustom({ clips: c, label });
              setIdx(0);
              scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        </section>
      )}

      <div className="layout-2 section">
        {Object.keys(k.by_length).length > 0 && (
          <section aria-labelledby="len-h">
            <div className="section-head">
              <h2 id="len-h">Short or long first pass</h2>
            </div>
            <table>
              <thead>
                <tr>
                  <th>First pass</th>
                  <th>n</th>
                  <th>Reached opponent half</th>
                  <th>Ended in own half</th>
                  <th>Shot</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(k.by_length).map(([l, v]) => (
                  <tr key={l}>
                    <td>
                      <b>{l}</b>
                    </td>
                    <td>{v.n}</td>
                    <td>{pc(v.opp_half)}</td>
                    <td>{pc(v.lost_own_half)}</td>
                    <td>{pc(v.shot)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="small" style={{ marginTop: 10 }}>
              Short = under 30 m. Side = end of the first pass, y in thirds. Ended in own half = no shot and the last
              team action ends at x &lt; 60 (ball lost, out of play or foul).
            </p>
          </section>
        )}
        {!events && rec.length > 0 && (
          <section className="sticker pad" aria-labelledby="rc-h">
            <h3 id="rc-h">Who receives the first pass</h3>
            <div style={{ marginTop: 10 }}>
              <Bars items={rec} total={k.n} i={ki} />
            </div>
          </section>
        )}
      </div>
    </>
  );
}
