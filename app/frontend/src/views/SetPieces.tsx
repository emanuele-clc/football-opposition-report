import { useEffect, useState } from "react";
import type { SetPieceKind, TeamData } from "../api";
import { Bars, Interval, Note, Pitch, Replay, rib } from "../charts";
import { pc } from "../format";
import { pickRecent, toRef, useClips } from "../useClips";

const ci = (c: [number, number]) => `${pc(c[0])}–${pc(c[1])}`;
const xg = (v: number | null | undefined) => (v == null ? "–" : v.toFixed(3));

/* Attacking end of the same pitch, corner from the bottom right. Zones as in the corner analysis of the thesis. */
function CornerZones({ k }: { k: SetPieceKind }) {
  const share = (n: string) => k.zones[n]?.share ?? 0;
  const max = Math.max(...Object.values(k.zones).map((v) => v.share), 0.01);
  const box: [string, number, number, number, number][] = [["far post", 102, 18, 18, 12], ["centre", 102, 30, 18, 20], ["near post", 102, 50, 18, 12]];
  const a = (n: string) => 0.12 + 0.88 * (share(n) / max);
  const fill = (n: string) => `color-mix(in srgb, var(--yellow) ${Math.round(a(n) * 100)}%, transparent)`;
  const ink = () => "var(--sticker-ink)";
  return (
    <Pitch crop={[66, 120]} label={"Corner delivery zones: " + Object.entries(k.zones).map(([n, v]) => `${n} ${pc(v.share)}`).join(", ")}>
      <rect x="80" y="2" width="21" height="76" rx="2" fill="var(--sticker)" />
      <rect x="80" y="2" width="21" height="76" rx="2" fill={fill("short / outside box")} />
      {box.map(([n, x, y, w, h]) => <g key={n}><rect x={x + 0.4} y={y + 0.4} width={w - 0.8} height={h - 0.8} rx="1.2" fill="var(--sticker)" /><rect x={x + 0.4} y={y + 0.4} width={w - 0.8} height={h - 0.8} rx="1.2" fill={fill(n)} /></g>)}
      {box.map(([n, x, y, w, h]) => (
        <g key={n + "t"} fill={ink()}>
          <text x={x + w / 2} y={y + h / 2 - 0.6} fontSize="2.6" textAnchor="middle" fontWeight="750">{n}</text>
          <text x={x + w / 2} y={y + h / 2 + 3.4} fontSize="4" textAnchor="middle" fontWeight="900" fontStyle="italic">{pc(share(n))}</text>
        </g>
      ))}
      <g fill={ink()}>
        <text x="90.5" y="38" fontSize="2.6" textAnchor="middle" fontWeight="750">short / outside</text>
        <text x="90.5" y="42.5" fontSize="4" textAnchor="middle" fontWeight="900" fontStyle="italic">{pc(share("short / outside box"))}</text>
      </g>
      <circle cx="119.6" cy="79.6" r="1.5" fill="var(--yellow)" stroke="var(--sticker-ink)" strokeWidth="0.3" />
    </Pitch>
  );
}

function ZoneTable({ k }: { k: SetPieceKind }) {
  return (
    <table>
      <thead><tr><th>Zone</th><th>n</th><th>Share (95%)</th><th style={{ minWidth: 120 }}>0 to 100%</th><th>Shot after</th><th>Mean xG</th></tr></thead>
      <tbody>
        {Object.entries(k.zones).map(([n, v]) => (
          <tr key={n}><td><b>{n}</b></td><td>{v.n}</td><td><b>{pc(v.share)}</b> <span className="s-muted">({ci(v.ci)})</span></td>
            <td><Interval onSticker value={v.share} ci={v.ci} label={`${n}: ${pc(v.share)}`} /></td><td>{pc(v.shot)}</td><td>{xg(v.xg)}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

export default function SetPieces({ d, events, go }: { d: TeamData; events: boolean; go: (tab: string, family?: string) => void }) {
  const kinds = Object.keys(d.setpieces?.kinds ?? {});
  const [kind, setKind] = useState(kinds[0] ?? "");
  const [idx, setIdx] = useState(0);
  useEffect(() => { setKind(kinds[0] ?? ""); setIdx(0); }, [d.key]);
  const { rows } = useClips(d.key, "setpieces");
  if (!d.setpieces || !kind) return <div className="state"><h2>No set-piece sheet</h2><p>setpieces_{d.key}.json is not in the data folder. Run src/oppreport.py for this team.</p></div>;
  const k = d.setpieces.kinds[kind];
  const clips = events && rows ? pickRecent(rows.filter((r) => r.family.startsWith(kind + " ")), 10, true).map((r) => toRef(r)) : [];
  const plural = kind === "Corner" ? "corners" : "attacking free kicks";

  return (
    <>
      <div className="section-head">
        <h2>Set pieces</h2>
        <p>Corners and attacking free kicks, {d.setpieces.matches} matches. Descriptive.</p>
      </div>
      <div className="pills" role="group" aria-label="Set piece">
        {kinds.map((n) => <button key={n} type="button" aria-pressed={n === kind} onClick={() => { setKind(n); setIdx(0); }}>{n === "Corner" ? "Corners" : "Attacking free kicks"} · {d.setpieces!.kinds[n].per_match.toFixed(1)} per match</button>)}
      </div>

      <div className="layout-split" style={{ marginTop: 28 }}>
        <div className="stack">
        <section className="sticker" style={rib(3)} aria-labelledby="sp-h">
          <span className="no">{kind === "Corner" ? "Corners" : "Free kicks"}</span>
          <Replay teamKey={d.key} clips={clips} index={Math.min(idx, Math.max(clips.length - 1, 0))} onIndex={setIdx}
            fallback={kind === "Corner" ? <CornerZones k={k} /> : <div className="note info" style={{ margin: 14 }}><span className="tag">Replays</span>Replays need the raw event files.</div>} />
          <div className="replay-cap">
            <div>
              <h2 id="sp-h">{k.n} {plural}</h2>
              <p>{k.per_match.toFixed(1)} per match · shot after {pc(k.shot)} ({ci(k.shot_ci)}) · goals {k.goals}{k.xg != null ? ` · mean xG ${k.xg.toFixed(3)}` : ""}</p>
              {clips[idx] && <p>Replaying {clips[idx].detail}. Ones that ended in a shot come first.</p>}
            </div>
            <button type="button" className="ctl no-print" onClick={() => go("clips:setpieces")}>All set-piece clips</button>
          </div>
        </section>
        <div className="layout-2" style={{ gap: 16 }}>
          {Object.keys(k.takers).length > 0 && <section className="sticker pad"><h3>Takers</h3><div style={{ marginTop: 10 }}><Bars items={Object.entries(k.takers)} i={0} /></div></section>}
          {Object.keys(k.receivers).length > 0 && <section className="sticker pad"><h3>First receivers</h3><div style={{ marginTop: 10 }}><Bars items={Object.entries(k.receivers)} i={1} /></div></section>}
        </div>
        </div>
        <div className="stack">
          {kind === "Corner" && events && (
            <div className="sticker">
              <div className="pitch-wrap"><CornerZones k={k} /></div>
              <p className="s-muted" style={{ fontSize: 12.5, padding: "8px 6px 2px" }}>Where corners are delivered, drawn for a corner from the right. Stronger colour = larger share.</p>
            </div>
          )}
          <div className="sticker pad"><h3>Delivery</h3><div className="table-wrap" style={{ marginTop: 8 }}><ZoneTable k={k} /></div></div>
        </div>
      </div>

      {kind === "Corner" && Object.keys(k.by_side).length > 0 && (
        <section className="section">
          <div className="section-head"><h2>By side</h2></div>
          <table>
            <thead><tr><th>Side</th><th>n</th>{Object.keys(k.zones).map((z) => <th key={z}>{z}</th>)}</tr></thead>
            <tbody>{Object.entries(k.by_side).map(([s, v]) => <tr key={s}><td><b>{s}</b></td><td>{v.n}</td>{Object.keys(k.zones).map((z) => <td key={z}>{pc(v.zones[z] ?? 0)}</td>)}</tr>)}</tbody>
          </table>
        </section>
      )}
      <div style={{ marginTop: 24 }}>
        <Note kind="info" tag="Zones">Hand-defined delivery zones, as in the corner analysis of the thesis. Descriptive: that analysis had little power, so it neither shows nor rules out an exploitable pattern.</Note>
      </div>
    </>
  );
}
