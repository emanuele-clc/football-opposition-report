import { useEffect, useMemo, useState } from "react";
import { api, type ClipRef, type ClipRow, type TeamData } from "../api";
import { Explain, Icon, Note, PlayIcon, Replay, rib } from "../charts";
import { clock } from "../format";
import { clipId, toRef, useClips, useGoals } from "../useClips";
import VideoSync from "./VideoSync";
import MoreLikeThis from "./MoreLikeThis";

const KINDS: [string, string][] = [
  ["sequences", "Sequences"],
  ["restarts", "Restarts"],
  ["setpieces", "Set pieces"],
  ["transitions", "Transitions"],
  ["threat", "Biggest xT moves"],
];
type SortKey = "date" | "minute" | "passes" | "duration_s" | "family";
const PAGE = 40;
const time = (r: ClipRow) => r.half * 1e4 + r.minute * 60 + r.second;

export default function Clips({
  d,
  kind,
  family,
  events,
  setFilter,
}: {
  d: TeamData;
  kind: string;
  family: string;
  events: boolean;
  setFilter: (kind: string, family: string) => void;
}) {
  const { rows, error } = useClips(d.key, kind);
  const [opponent, setOpponent] = useState(
    () => new URLSearchParams(location.hash.split("?")[1] ?? "").get("opponent") ?? "",
  );
  const [half, setHalf] = useState(0);
  const [shot, setShot] = useState(false);
  const [goal, setGoal] = useState(false);
  const goals = useGoals(d.key, kind, events);
  const isGoal = (r: ClipRow) => !!goals?.has(clipId(r));
  const goalOn = goal && !!goals;
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "date", dir: 1 });
  const [page, setPage] = useState(0);
  const [sel, setSel] = useState(0);
  const [like, setLike] = useState<{ clips: ClipRef[]; index: number } | null>(null);
  useEffect(() => {
    setPage(0);
    setSel(0);
    setLike(null);
  }, [family, opponent, half, shot, goalOn, kind, d.key]);

  const families = useMemo(() => [...new Set((rows ?? []).map((r) => r.family))].sort(), [rows]);
  const opponents = useMemo(() => [...new Set((rows ?? []).map((r) => r.opponent))].sort(), [rows]);
  const shown = useMemo(() => {
    const out = (rows ?? []).filter(
      (r) =>
        (!family || r.family === family) &&
        (!opponent || r.opponent === opponent) &&
        (!half || r.half === half) &&
        (!shot || r.ended_in_shot === 1) &&
        (!goalOn || isGoal(r)),
    );
    const k = sort.key;
    return out.sort((a, b) => {
      const va = k === "minute" ? time(a) : a[k],
        vb = k === "minute" ? time(b) : b[k];
      return (va < vb ? -1 : va > vb ? 1 : time(a) - time(b)) * sort.dir;
    });
  }, [rows, family, opponent, half, shot, goalOn, goals, sort]);
  const pages = Math.max(1, Math.ceil(shown.length / PAGE));
  const filters = { family, opponent, shot, half, goal: goalOn };
  const refs = useMemo(() => shown.map((r) => toRef(r, kind === "transitions")), [shown, kind]);
  const hasVideo = (rows ?? []).some((r) => r.video_time);
  const famIndex = (f: string) => {
    const m = /^[AB](\d+)$/.exec(f);
    return m ? Number(m[1]) - 1 : Math.max(0, families.indexOf(f));
  };
  const th = (key: SortKey, label: string, cls = "") => (
    <th className={cls} aria-sort={sort.key === key ? (sort.dir === 1 ? "ascending" : "descending") : undefined}>
      <button type="button" onClick={() => setSort((s) => ({ key, dir: s.key === key ? (-s.dir as 1 | -1) : 1 }))}>
        {label}
      </button>
    </th>
  );
  const goSel = (i: number) => {
    setSel(i);
    setPage(Math.floor(i / PAGE));
  };

  return (
    <>
      <div className="section-head">
        <h2>Clips</h2>
        <Explain>
          Every possession with its label, match and time. Pick one to watch it replayed; filter, then export for the
          video tool.
        </Explain>
      </div>
      <div className="pills" role="group" aria-label="Clip list">
        {KINDS.filter(([k]) => d.clips.includes(k)).map(([k, label]) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setFilter(k, "")}>
            {label}
          </button>
        ))}
      </div>
      <div className="filters">
        <label className="field">
          Label
          <select value={family} onChange={(e) => setFilter(kind, e.target.value)}>
            <option value="">All labels</option>
            {families.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Opponent
          <select value={opponent} onChange={(e) => setOpponent(e.target.value)}>
            <option value="">All opponents</option>
            {opponents.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Half
          <select value={half} onChange={(e) => setHalf(Number(e.target.value))}>
            <option value={0}>Both</option>
            <option value={1}>First</option>
            <option value={2}>Second</option>
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={shot} onChange={(e) => setShot(e.target.checked)} /> Ended in a shot
        </label>
        {goals && (
          <label className="check">
            <input type="checkbox" checked={goal} onChange={(e) => setGoal(e.target.checked)} /> Ended in a goal
          </label>
        )}
        <span style={{ marginLeft: "auto", display: "flex", gap: 10, flexWrap: "wrap" }}>
          <a
            className="btn"
            href={api.exportUrl(d.key, kind, "csv", filters)}
            aria-disabled={!shown.length}
            onClick={(e) => !shown.length && e.preventDefault()}
          >
            {Icon.download} CSV · {shown.length} clips
          </a>
          <a
            className="btn ghost"
            href={api.exportUrl(d.key, kind, "zip", filters)}
            aria-disabled={!shown.length}
            onClick={(e) => !shown.length && e.preventDefault()}
          >
            {Icon.download} XML for video tool
          </a>
        </span>
      </div>
      {kind === "transitions" && (
        <p className="small measure" style={{ marginBottom: 14 }}>
          For losses, shot and goal are the opponent's within 10 s, before the team wins the ball back; for recoveries,
          the team's within 10 s.
        </p>
      )}
      {!hasVideo && rows && rows.length > 0 && (
        <p className="small measure" style={{ marginBottom: 14 }}>
          Times are the match clock (no video offsets in this list). XML clips start 3 s before the possession and end 3
          s after; without offsets the times must be shifted in the tool. Not yet tested by importing into Sportscode or
          Nacsport: try one match first.
        </p>
      )}
      {error && (
        <Note kind="caution" tag="Not loaded">
          {error}
        </Note>
      )}
      {!rows && !error && (
        <div aria-busy="true">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="skeleton" />
          ))}
        </div>
      )}
      {rows && shown.length === 0 && (
        <div className="state" style={{ padding: "40px 0" }}>
          <h2>No clips match these filters</h2>
          <p>{rows.length} clips in this list.</p>
          <p>
            <button
              className="btn ghost"
              type="button"
              onClick={() => {
                setFilter(kind, "");
                setOpponent("");
                setHalf(0);
                setShot(false);
                setGoal(false);
              }}
            >
              Clear filters
            </button>
          </p>
        </div>
      )}
      {rows && shown.length > 0 && (
        <div className="layout-split layout-clips">
          <div>
            <div className="table-wrap">
              <table className="clip-table">
                <thead>
                  <tr>
                    <th></th>
                    {th("family", "Label", "l")}
                    {th("date", "Match", "l")}
                    {th("minute", "Half, time")}
                    {th("passes", "Passes")}
                    {th("duration_s", "Duration")}
                    <th>Shot</th>
                    {hasVideo && <th>Video</th>}
                  </tr>
                </thead>
                <tbody>
                  {shown.slice(page * PAGE, (page + 1) * PAGE).map((r, j) => {
                    const i = page * PAGE + j;
                    return (
                      <tr
                        key={`${r.match}-${r.half}-${r.minute}-${r.second}-${i}`}
                        className={`clickable${i === sel ? " sel" : ""}`}
                        onClick={() => setSel(i)}
                      >
                        <td>
                          <button
                            type="button"
                            className="play-btn"
                            aria-label={`Replay ${r.family}, ${r.date}, ${clock(r.minute, r.second)}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSel(i);
                            }}
                          >
                            {PlayIcon}
                          </button>
                        </td>
                        <td className="l">
                          <span className="chip" style={rib(famIndex(r.family))}>
                            {r.family}
                          </span>
                        </td>
                        <td className="l">
                          {r.opponent}
                          <small>
                            {r.date} · {r.start_type}
                          </small>
                        </td>
                        <td>
                          {r.half}, {clock(r.minute, r.second)}
                        </td>
                        <td>{r.passes}</td>
                        <td>{r.duration_s} s</td>
                        <td>
                          {isGoal(r) ? (
                            <strong>{r.start_type === "loss" ? "goal against" : "goal"}</strong>
                          ) : r.ended_in_shot ? (
                            "yes"
                          ) : (
                            ""
                          )}
                        </td>
                        {hasVideo && <td>{r.video_time}</td>}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <span>
                {page * PAGE + 1}–{Math.min(shown.length, (page + 1) * PAGE)} of {shown.length}
              </span>
              <button className="btn ghost" type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <button
                className="btn ghost"
                type="button"
                disabled={page >= pages - 1}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </div>
          <aside style={{ position: "sticky", top: 84 }}>
            <div className="sticker" style={rib(famIndex(shown[sel]?.family ?? ""))}>
              <span className="no">{shown[sel]?.family}</span>
              {events ? (
                like ? (
                  <Replay
                    teamKey={d.key}
                    clips={like.clips}
                    index={like.index}
                    onIndex={(i) => setLike({ ...like, index: i })}
                  />
                ) : (
                  <Replay teamKey={d.key} clips={refs} index={Math.min(sel, refs.length - 1)} onIndex={goSel} />
                )
              ) : (
                <div className="note info" style={{ margin: 14 }}>
                  <span className="tag">Replays</span>Replays need the raw event files: start the app with --data-dir on
                  the StatsBomb folder.
                </div>
              )}
              {like && (
                <div className="replay-cap">
                  <p>
                    Similar sequence {like.index + 1} of {like.clips.length}: {like.clips[like.index].detail}.{" "}
                    <button type="button" className="ctl" onClick={() => setLike(null)}>
                      Back to the list
                    </button>
                  </p>
                </div>
              )}
              {!like && refs[sel] && (
                <div className="replay-cap">
                  <p>
                    {refs[sel].detail}
                    {kind === "transitions" ? " · from 6 s before to 10 s after; opponent in red" : ""}
                  </p>
                </div>
              )}
            </div>
            {kind === "sequences" && events && (
              <MoreLikeThis teamKey={d.key} row={shown[sel]} onPlay={(c, i) => setLike({ clips: c, index: i })} />
            )}
            <VideoSync row={shown[sel]} />
          </aside>
        </div>
      )}
    </>
  );
}
