import React, { useEffect, useMemo, useState } from "react";
import { api, type ClipRef, type RestartPass } from "../api";
import { Note, Pitch } from "../charts";
import { clock, pc } from "../format";

/* Where the first pass of each restart goes, who receives it, and how often the possession then ends in the own half.
   Same definitions as the restart sheet (src/report/restarts.py); descriptive, it does not say where pressing works. */
const cache = new Map<string, Promise<{ restarts: RestartPass[] }>>();
const lastName = (n: string) => n.split(" ").slice(-1)[0] ?? "";
const OUT = { lost: "var(--coral)", opp: "var(--lime)", other: "var(--on-board-3)" };
const outcome = (r: RestartPass) => (r.lost_own_half ? "lost" : r.opp_half ? "opp" : "other") as keyof typeof OUT;

export default function PressingMap({ teamKey, kind, onWatch }: { teamKey: string; kind: string; onWatch: (clips: ClipRef[], label: string) => void }) {
  const [all, setAll] = useState<RestartPass[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [who, setWho] = useState("");
  useEffect(() => {
    let live = true;
    if (!cache.has(teamKey)) cache.set(teamKey, api.pressing(teamKey));
    cache.get(teamKey)!.then((d) => live && setAll(d.restarts)).catch((e) => { cache.delete(teamKey); if (live) setErr(String(e.message ?? e)); });
    return () => { live = false; };
  }, [teamKey]);
  useEffect(() => setWho(""), [kind, teamKey]);

  const rows = useMemo(() => (all ?? []).filter((r) => r.kind === kind), [all, kind]);
  const byRec = useMemo(() => {
    const m = new Map<string, RestartPass[]>();
    rows.forEach((r) => { const k = r.receiver || "(no receiver: pass not completed)"; m.set(k, [...(m.get(k) ?? []), r]); });
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 8);
  }, [rows]);
  if (err) return <Note kind="info" tag="Pressing map">{err}</Note>;
  if (!all) return <div aria-busy="true"><div className="skeleton" style={{ height: 260 }} /></div>;
  if (!rows.length) return null;
  const shown = who ? rows.filter((r) => (r.receiver || "(no receiver: pass not completed)") === who) : rows;
  const share = (xs: RestartPass[], f: (r: RestartPass) => number) => xs.reduce((s, r) => s + f(r), 0) / Math.max(xs.length, 1);
  const refs = (xs: RestartPass[], label: string): ClipRef[] => xs.slice(0, 12).map((r) => ({
    match: r.match, half: r.half, minute: r.minute, second: r.second, title: `${kind} to ${lastName(r.receiver) || "nobody"}`,
    detail: `${label} · half ${r.half} ${clock(r.minute, r.second)}${r.lost_own_half ? " · ended in own half" : r.opp_half ? " · reached the opponent half" : ""}`,
  }));

  return (
    <div className="layout-split">
      <div className="sticker">
        <span className="no" style={{ "--rib": "var(--coral)" } as React.CSSProperties}>Pressing map</span>
        <div className="pitch-wrap">
          <Pitch label={`${kind}: first pass of ${shown.length} restarts`}>
            <defs>{Object.entries(OUT).map(([k, c]) => <marker key={k} id={`pm-${k}`} viewBox="0 0 6 6" refX="5" refY="3" markerWidth="3" markerHeight="3" orient="auto"><path d="M0 0 6 3 0 6z" fill={c} /></marker>)}</defs>
            <rect x="0" y="0" width="60" height="80" fill="var(--coral)" fillOpacity="0.06" />
            {shown.map((r, i) => { const o = outcome(r); return <line key={i} x1={r.x} y1={r.y} x2={r.ex} y2={r.ey} stroke={OUT[o]} strokeWidth={0.45} strokeOpacity={o === "other" ? 0.35 : 0.75} markerEnd={`url(#pm-${o})`} />; })}
            {shown.map((r, i) => <circle key={`s${i}`} cx={r.x} cy={r.y} r="0.6" fill="var(--run)" fillOpacity="0.6" />)}
          </Pitch>
        </div>
        <div className="now-row">
          <div className="now">{who ? <><b>{who}</b> receives {shown.length} of {rows.length}</> : <>{rows.length} first passes from {kind.toLowerCase()}</>}: possession ended in own half <b>{pc(share(shown, (r) => r.lost_own_half))}</b>, reached the opponent half <b>{pc(share(shown, (r) => r.opp_half))}</b>.</div>
          <div className="legend"><span><i className="lg" style={{ borderTopColor: "var(--coral)" }} /> ended in own half</span><span><i className="lg" style={{ borderTopColor: "#3c9a2a" }} /> reached opp. half</span><span><i className="lg" style={{ borderTopColor: "var(--on-board-3)" }} /> neither</span></div>
        </div>
      </div>
      <div>
        <h3 style={{ color: "var(--accent-text)", marginBottom: 10 }}>Who receives the first pass, and what happens next</h3>
        <div className="table-wrap">
          <table>
            <thead><tr><th>First receiver</th><th>Restarts</th><th>Short</th><th>Ended in own half</th><th>Reached opp. half</th><th></th></tr></thead>
            <tbody>
              {byRec.map(([name, xs]) => (
                <tr key={name} className={`clickable${who === name ? " sel" : ""}`} onClick={() => setWho(who === name ? "" : name)}>
                  <td>{name}</td><td>{xs.length}</td><td>{pc(share(xs, (r) => r.short))}</td>
                  <td><b>{pc(share(xs, (r) => r.lost_own_half))}</b></td><td>{pc(share(xs, (r) => r.opp_half))}</td>
                  <td><button type="button" className="btn ghost" style={{ padding: "5px 12px" }} onClick={(e) => { e.stopPropagation(); onWatch(refs(xs, `${kind} to ${name}`), `${kind} to ${name}`); }}>Watch</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small" style={{ marginTop: 10 }}>Click a receiver to draw only the restarts to that player; Watch replays them in the sticker above. Small groups move a lot: a receiver with few restarts is a hint to check on video, not a weakness. Ended in own half = no shot and the last action ends at x &lt; 60 (ball lost, out of play or foul), as in the restart sheet.</p>
      </div>
    </div>
  );
}
