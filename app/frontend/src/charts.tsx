import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import { api, type Action, type ClipRef, type Family, type NetworkData, type PathsData, type Rank, type Replay as ReplayData } from "./api";
import { clock, fmt, n1, ordinal, pc } from "./format";

/* Each family wears one ribbon colour; its code is always printed on it, so colour is never the only cue. */
export const RIBS = ["var(--yellow)", "var(--sky)", "var(--lime)", "var(--coral)", "var(--lilac)"];
export const rib = (i: number) => ({ "--rib": RIBS[i % RIBS.length] }) as CSSProperties;
export const third = (x: number) => (x < 40 ? "own third" : x < 80 ? "middle third" : "final third");
const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/* The one pitch of the app: 120 x 80, attacking left to right, mown bands. Every view draws on it at the same scale. */
export function Pitch({ children, label, cut, crop, view }: { children?: ReactNode; label: string; cut?: number; crop?: [number, number]; view?: [number, number, number, number] }) {
  const [x0, x1] = crop ?? [0, 120];
  const vb = view ? view.join(" ") : `${x0 - 2} -2 ${x1 - x0 + 4} 84`;
  const L = { fill: "none", stroke: "var(--pitch-line)", strokeWidth: 0.4 } as const;
  return (
    <svg className="pitch-svg" viewBox={vb} role="img" aria-label={label}>
      <rect x={x0 - 2} y="-2" width={x1 - x0 + 4} height="84" fill="var(--pitch)" />
      {Array.from({ length: 12 }, (_, i) => i % 2 === 1 && <rect key={i} x={i * 10} y="0" width="10" height="80" fill="var(--pitch-band)" />)}
      <rect x="0" y="0" width="120" height="80" {...L} strokeWidth={0.55} />
      <line x1="60" y1="0" x2="60" y2="80" {...L} />
      <circle cx="60" cy="40" r="9.15" {...L} />
      <circle cx="60" cy="40" r="0.5" fill="var(--pitch-line)" />
      <rect x="0" y="18" width="18" height="44" {...L} />
      <rect x="102" y="18" width="18" height="44" {...L} />
      <rect x="0" y="30" width="6" height="20" {...L} />
      <rect x="114" y="30" width="6" height="20" {...L} />
      <path d="M 18 32.7 A 9.15 9.15 0 0 1 18 47.3" {...L} />
      <path d="M 102 32.7 A 9.15 9.15 0 0 0 102 47.3" {...L} />
      <rect x="-1.6" y="36" width="1.6" height="8" fill="var(--pitch-line)" />
      <rect x="120" y="36" width="1.6" height="8" fill="var(--pitch-line)" />
      {cut !== undefined && <line x1={cut} y1="0" x2={cut} y2="80" stroke="var(--pitch-line)" strokeWidth="0.35" strokeDasharray="1 1" />}
      {children}
    </svg>
  );
}

/* Zoom on the action when it uses only part of the pitch; keeps the pitch's aspect ratio. */
function zoomOn(acts: Action[]): [number, number, number, number] | undefined {
  if (!acts.length) return undefined;
  const xs = acts.flatMap((a) => [a.x, a.ex ?? a.x]), ys = acts.flatMap((a) => [a.y, a.ey ?? a.y]);
  const [lx, hx, ly, hy] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  let w = Math.max(hx - lx + 24, 56), h = (w * 84) / 124;
  if (h < hy - ly + 20) { h = hy - ly + 20; w = (h * 124) / 84; }
  if (w >= 108) return undefined;
  const cx = Math.min(Math.max((lx + hx) / 2, w / 2 - 2), 122 - w / 2), cy = Math.min(Math.max((ly + hy) / 2, h / 2 - 2), 82 - h / 2);
  return [cx - w / 2, cy - h / 2, w, h];
}

const lastName = (n: string) => n.split(" ").slice(-1)[0] ?? "";
function describe(a: Action) {
  if (a.type === "Pass") return <><b>{a.player || "Pass"}</b> {a.ok ? "passes to" : "pass not completed"} {a.ok && <b>{a.to}</b>}{a.long ? " (long)" : ""}{a.kind ? ` · ${a.kind}` : ""}</>;
  if (a.type === "Carry") return <><b>{a.player}</b> carries the ball</>;
  if (a.type === "Shot") return <><b>{a.player}</b> shoots: {a.outcome}{a.xg != null ? ` (xG ${a.xg.toFixed(2)})` : ""}</>;
  return <>{a.us ? "" : "Opponent: "}<b>{a.player}</b> · {a.type.toLowerCase()}</>;
}

const I = {
  play: <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" fill="currentColor" /></svg>,
  pause: <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5h3v11H4zM9 2.5h3v11H9z" fill="currentColor" /></svg>,
  again: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M3 8a5 5 0 1 0 1.5-3.6M3 2.5v3h3" /></svg>,
  next: <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 2.5v11l7-5.5zM11 2.5h2.5v11H11z" fill="currentColor" /></svg>,
  prev: <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13 2.5v11l-7-5.5zM2.5 2.5H5v11H2.5z" fill="currentColor" /></svg>,
};
export const PlayIcon = I.play;

/* Signature: the actual possession, read from the events, drawn pass by pass on the pitch. */
export function Replay({ teamKey, clips, index, onIndex, loop, fallback, head }: {
  teamKey: string; clips: ClipRef[]; index: number; onIndex: (i: number) => void; loop?: boolean; fallback?: ReactNode; head?: ReactNode;
}) {
  const clip = clips[index];
  const [data, setData] = useState<ReplayData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(2);
  const timer = useRef<number>();

  useEffect(() => {
    if (!clip) return;
    let live = true;
    setErr(null); setData(null); setStep(0);
    api.replay(teamKey, clip).then((d) => {
      if (!live) return;
      setData(d);
      if (reduced()) { setStep(d.actions.length); setPlaying(false); } else setPlaying(true);
    }).catch((e) => live && setErr(String(e.message ?? e)));
    return () => { live = false; };
  }, [teamKey, clip?.match, clip?.half, clip?.minute, clip?.second, clip?.window]);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!data || !playing) return;
    const n = data.actions.length;
    if (step >= n) {
      if (loop && clips.length > 1) timer.current = window.setTimeout(() => onIndex((index + 1) % clips.length), 2600);
      else setPlaying(false);
      return;
    }
    const gap = step === 0 ? 0.5 : (data.actions[step].t - data.actions[step - 1].t) / speed;
    timer.current = window.setTimeout(() => setStep((s) => s + 1), Math.min(Math.max(gap, 0.28), 1.5) * 1000);
    return () => clearTimeout(timer.current);
  }, [data, step, playing, speed, loop, index, clips.length]);

  if (!clip) return <>{fallback}</>;
  const acts = data?.actions ?? [];
  const shown = acts.slice(0, step);
  const cur = shown[shown.length - 1];
  const ballAt = cur ? [cur.ex ?? cur.x, cur.ey ?? cur.y] : acts[0] ? [acts[0].x, acts[0].y] : [60, 40];
  const dur = `${Math.round(Math.min(Math.max((cur && acts[step] ? acts[step].t - cur.t : 0.6) / speed, 0.28), 1.2) * 900)}ms`;
  const atEnd = data && step >= acts.length;
  const view = zoomOn(acts), k = view ? view[2] / 124 : 1;
  const sw = (w: number, dash?: [number, number]) => ({ strokeWidth: w * k, ...(dash ? { strokeDasharray: `${dash[0] * k} ${dash[1] * k}` } : {}) });
  const togglePlay = () => { if (atEnd) { setStep(0); setPlaying(true); } else setPlaying((p) => !p); };

  return (
    <div className="replay">
      {head}
      <div className="pitch-wrap">
        {err ? (fallback ?? <div className="note caution" style={{ margin: 12 }}><span className="tag">No replay</span>{err}</div>) : (
          <Pitch label={`Replay of ${clip.title}: ${acts.length} actions`} view={view}>
            <defs>
              <marker id="arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="3.2" markerHeight="3.2" orient="auto"><path d="M0 0 6 3 0 6z" fill="var(--trail)" /></marker>
              <marker id="arrow-t" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="3.2" markerHeight="3.2" orient="auto"><path d="M0 0 6 3 0 6z" fill="var(--them)" /></marker>
            </defs>
            {shown.map((a, i) => {
              const last = i === shown.length - 1, dr = last ? " draw" : "";
              const d = { "--d": dur, ...sw(a.type === "Shot" ? 1.1 : a.type === "Carry" ? 0.45 : 0.7, a.type === "Carry" || (a.type === "Pass" && !a.ok) ? [0.8, 1] : undefined) } as CSSProperties;
              const end = a.ex !== undefined && a.ey !== undefined;
              if (a.type === "Shot" && end) return <g key={i}><line className={`shot${dr}`} pathLength={1} style={d} x1={a.x} y1={a.y} x2={a.ex} y2={a.ey} /><circle cx={a.ex} cy={a.ey} r={1.6 * k} fill="none" stroke="var(--coral)" strokeWidth={0.5 * k} /></g>;
              if (a.type === "Pass" && end) return <line key={i} className={`pass${dr}${a.ok ? "" : " fail"}${a.us ? "" : " them"}`} pathLength={1} style={d} x1={a.x} y1={a.y} x2={a.ex} y2={a.ey} markerEnd={a.ok ? (a.us ? "url(#arrow)" : "url(#arrow-t)") : undefined} />;
              if (a.type === "Carry" && end) return <line key={i} className={`carry${dr}${a.us ? "" : " them"}`} style={d} x1={a.x} y1={a.y} x2={a.ex} y2={a.ey} />;
              return <g key={i} stroke={a.us ? "var(--run)" : "var(--them)"} strokeWidth={0.5 * k}><line x1={a.x - k} y1={a.y - k} x2={a.x + k} y2={a.y + k} /><line x1={a.x - k} y1={a.y + k} x2={a.x + k} y2={a.y - k} /></g>;
            })}
            {shown.filter((a) => a.type === "Pass" && a.us).map((a, i) => <circle key={`p${i}`} cx={a.x} cy={a.y} r={0.75 * k} fill="var(--trail)" />)}
            {data && (
              <g className="ball" style={{ transform: `translate(${ballAt[0]}px, ${ballAt[1]}px)`, "--move": dur } as CSSProperties}>
                <circle r={1.55 * k} fill="var(--sticker)" stroke="var(--sticker-ink)" strokeWidth={0.35 * k} />
                {cur && <text y={-2.6 * k} textAnchor="middle" fontSize={2.6 * k} fontWeight="750" fill="var(--run)" paintOrder="stroke" stroke="var(--pitch)" strokeWidth={0.8 * k}>{lastName(cur.type === "Pass" && cur.ok && cur.to ? cur.to : cur.player)}</text>}
              </g>
            )}
            {!data && <text x="60" y="41" textAnchor="middle" fontSize="3" fill="var(--pitch-line)">Loading the events…</text>}
          </Pitch>
        )}
      </div>
      <div className="controls no-print">
        <button type="button" className="ctl primary" onClick={togglePlay} disabled={!data} aria-label={atEnd ? "Replay again" : playing ? "Pause" : "Play"}>
          {atEnd ? I.again : playing ? I.pause : I.play}<span>{atEnd ? "Again" : playing ? "Pause" : "Play"}</span>
        </button>
        {clips.length > 1 && <>
          <button type="button" className="ctl" onClick={() => onIndex((index - 1 + clips.length) % clips.length)} aria-label="Previous clip">{I.prev}</button>
          <button type="button" className="ctl" onClick={() => onIndex((index + 1) % clips.length)} aria-label="Next clip">{I.next}</button>
        </>}
        <input className="scrub" type="range" min={0} max={acts.length} value={step} aria-label="Position in the possession"
          onChange={(e) => { setPlaying(false); setStep(Number(e.target.value)); }} disabled={!data} />
        {clips.length > 1 && <span className="clip-count">{index + 1} / {clips.length}</span>}
        <button type="button" className="ctl" onClick={() => setSpeed((s) => (s >= 4 ? 1 : s * 2))} aria-label={`Speed ${speed} times, change`}>{speed}×</button>
        <a className="ctl" href={api.gifUrl(teamKey, clip)} download title="Download this replay as an animated GIF to send to the players" aria-label="Download this replay as a GIF">{Icon.download}<span className="gif-lab">GIF</span></a>
      </div>
      <div className="now-row">
        <div className="now" aria-live="polite">
          {cur ? <>{clock(clip.minute + Math.floor((clip.second + cur.t) / 60), Math.floor(clip.second + cur.t) % 60)} · {describe(cur)}</> : data ? <span className="s-muted">{data.play_pattern} · {acts.length} actions</span> : null}
        </div>
        <div className="legend" aria-hidden="true">
          <span><i className="lg" /> pass</span><span><i className="lg carry" /> run</span><span><i className="lg them" /> opponent</span><span><i className="lg shot" /> shot</span>
        </div>
      </div>
    </div>
  );
}

/* Without event files: average start to end of every family on the same pitch. Families are stacked; vertical position means nothing. */
export function FamilyLanes({ families, pick, onPick }: { families: Family[]; pick?: string; onPick?: (f: string) => void }) {
  const max = Math.max(...families.map((f) => f.share));
  const step = 80 / (families.length + 1);
  return (
    <Pitch cut={45} label={"Average start and end of each family: " + families.map((f) => `${f.fam} from x ${Math.round(f.x0)} to ${Math.round(f.x1)}`).join(", ")}>
      {families.map((f, i) => {
        const y = step * (i + 1), h = 2.4 + 5 * (f.share / max), on = !pick || pick === f.fam;
        return (
          <g key={f.fam} className="lane" opacity={on ? 1 : 0.3} onClick={() => onPick?.(f.fam)}>
            <title>{`${f.fam}: from x ${Math.round(f.x0)} to ${Math.round(f.x1)}, ${pc(f.share)} of sequences`}</title>
            <rect x={Math.min(f.x0, f.x1)} y={y - h / 2} width={Math.max(Math.abs(f.x1 - f.x0), 1)} height={h} rx={h / 2} fill={RIBS[i % RIBS.length]} />
            <text x={Math.min(f.x0, f.x1) - 2} y={y + 1.5} textAnchor="end" fontSize="4.2" fontWeight="900" fontStyle="italic" fill="var(--run)">{f.fam}</text>
          </g>
        );
      })}
    </Pitch>
  );
}

export function FamilySticker({ f, i, total, selected, onPick }: { f: Family; i: number; total: number; selected?: boolean; onPick?: () => void }) {
  return (
    <button type="button" className="flip enter" style={{ ...rib(i), "--i": i } as CSSProperties} aria-pressed={selected} onClick={onPick}
      aria-label={`${f.fam}: ${pc(f.share)} of ${total} sequences. Show its replay.`}>
      <div className="flip-inner">
        <div className="face sticker fam-front">
          <div className="ribbon" />
          <div className="body">
            <div className="line"><span className="code">{f.fam}</span><span className="share">{pc(f.share)}</span></div>
            <svg className="mini-pitch" viewBox="-1 -1 122 42" aria-hidden="true">
              <rect x="-1" y="-1" width="122" height="42" rx="3" fill="var(--pitch)" />
              <g fill="none" stroke="var(--pitch-line)" strokeWidth="0.6"><rect x="0" y="0" width="120" height="40" /><line x1="60" y1="0" x2="60" y2="40" /><circle cx="60" cy="20" r="6" /><rect x="0" y="9" width="12" height="22" /><rect x="108" y="9" width="12" height="22" /></g>
              <rect x={Math.min(f.x0, f.x1)} y="15" width={Math.max(Math.abs(f.x1 - f.x0), 2)} height="10" rx="5" fill={RIBS[i % RIBS.length]} />
              <path d={f.x1 >= f.x0 ? `M ${f.x1 + 5} 20 L ${f.x1 - 1} 13 L ${f.x1 - 1} 27 Z` : `M ${f.x1 - 5} 20 L ${f.x1 + 1} 13 L ${f.x1 + 1} 27 Z`} fill={RIBS[i % RIBS.length]} />
              <circle cx={f.x0} cy="20" r="3" fill="var(--sticker)" stroke="var(--sticker-ink)" strokeWidth="0.8" />
            </svg>
            <p>{third(f.x0) === third(f.x1) ? `Stays in the ${third(f.x0)}` : `From the ${third(f.x0)} to the ${third(f.x1)}`} · {n1(f.passes)} passes</p>
          </div>
        </div>
        <div className="face sticker back fam-back" aria-hidden="true">
          <span className="code">{f.fam}</span> <span className="s-muted">{f.n} sequences</span>
          <dl>
            <dt>Share (95%)</dt><dd>{pc(f.share_ci[0])}–{pc(f.share_ci[1])}</dd>
            <dt>Duration</dt><dd>{Math.round(f.dur)} s</dd>
            <dt>Long passes</dt><dd>{pc(f.long)}</dd>
            <dt>Shot rate</dt><dd>{pc(f.shot)}</dd>
            <dt>Per match (p10-p90)</dt><dd>{pc(f.per_match_p10_p90[0])}–{pc(f.per_match_p10_p90[1])}</dd>
            <dt>Stability</dt><dd>{f.jaccard.toFixed(2)} {f.reliability}</dd>
          </dl>
        </div>
      </div>
    </button>
  );
}

export function ShareStrip({ families, pick, onPick }: { families: Family[]; pick?: string; onPick: (f: string) => void }) {
  return (
    <div className="share-strip" role="group" aria-label="Share of sequences by family">
      {families.map((f, i) => (
        <button key={f.fam} type="button" style={{ ...rib(i), flexGrow: f.share, flexBasis: 0 }} aria-pressed={pick === f.fam} onClick={() => onPick(f.fam)} title={`${f.fam}: ${pc(f.share)}`}>
          <b>{f.fam}</b><span>{pc(f.share)}</span>
        </button>
      ))}
    </div>
  );
}

/* This team's value among every team in the data folder, placed by value. Hover, or focus and use the arrow keys, to name each dot. */
export function RankRow({ r, current }: { r: Rank; current: string }) {
  const [hot, setHot] = useState<number | null>(null);
  const id = useId();
  const vals = r.teams.map((t) => t.value), lo = Math.min(...vals), hi = Math.max(...vals);
  const pos = (v: number) => (hi === lo ? 50 : 4 + ((v - lo) / (hi - lo)) * 92);
  const key = (e: KeyboardEvent) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const order = r.teams.map((_, i) => i).sort((a, b) => r.teams[a].value - r.teams[b].value);
    const at = hot === null ? order.indexOf(r.rank - 1) : order.indexOf(hot);
    setHot(order[Math.min(order.length - 1, Math.max(0, at + (e.key === "ArrowRight" ? 1 : -1)))]);
  };
  const t = hot !== null ? r.teams[hot] : null;
  return (
    <div className="rank-row">
      <span className="lab">{r.label}{r.ci && <small>95%: {fmt(r.ci[0], r.unit)}–{fmt(r.ci[1], r.unit)}</small>}</span>
      <span className="val">{fmt(r.value, r.unit)}</span>
      <div className="track-cell">
        <div className="track" tabIndex={0} role="group" onKeyDown={key} onBlur={() => setHot(null)} onMouseLeave={() => setHot(null)} aria-describedby={id}
          aria-label={`${r.label}: ${ordinal(r.rank)} of ${r.of}. Arrow keys name each team.`}>
          {r.teams.map((tm, i) => (
            <span key={tm.key} className={`d${tm.key === current ? " us" : ""}${hot === i ? " hot" : ""}`} style={{ left: `${pos(tm.value)}%` }} onMouseEnter={() => setHot(i)} />
          ))}
          {t && <span className="tip" style={{ left: `${pos(t.value)}%` }}>{t.team} · {fmt(t.value, r.unit)}</span>}
          <span id={id} className="sr" aria-live="polite">{t ? `${t.team}, ${fmt(t.value, r.unit)}` : ""}</span>
        </div>
      </div>
      <span className="ord"><b>{ordinal(r.rank)}</b> / {r.of}{r.caution && <span className="flagged" title={r.caution}> *</span>}</span>
    </div>
  );
}

export function Interval({ value, ci, last5, last5ci, max = 1, label, onSticker }: { value: number; ci?: [number, number] | null; last5?: number | null; last5ci?: [number, number] | null; max?: number; label: string; onSticker?: boolean }) {
  const X = (v: number) => 4 + (Math.min(Math.max(v, 0), max) / max) * 292;
  const ink = onSticker ? "var(--sticker-ink)" : "var(--on-board)";
  return (
    <svg className="ivl" viewBox="0 0 300 26" preserveAspectRatio="none" role="img" aria-label={label}>
      <line x1="4" y1="13" x2="296" y2="13" stroke={ink} strokeOpacity="0.2" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      {ci && <rect x={X(ci[0])} y="8" width={Math.max(X(ci[1]) - X(ci[0]), 2)} height="10" rx="5" fill={ink} fillOpacity="0.3" />}
      <rect x={X(value) - 3} y="3" width="6" height="20" rx="3" fill={onSticker ? "var(--sticker-ink)" : "var(--yellow)"} />
      {last5 != null && (
        <g>
          {last5ci && <line x1={X(last5ci[0])} x2={X(last5ci[1])} y1="24" y2="24" stroke="var(--coral)" strokeWidth="2" vectorEffect="non-scaling-stroke" />}
          <path d={`M ${X(last5)} 17 l 4 5 l -4 3.5 l -4 -3.5 z`} fill="var(--coral)" />
        </g>
      )}
    </svg>
  );
}

export function Note({ kind, tag, children }: { kind: "caution" | "ok" | "info"; tag: string; children: ReactNode }) {
  return <div className={`note ${kind}`}><span className="tag">{tag}</span><div>{children}</div></div>;
}

export function Bars({ items, total, i = 0 }: { items: [string, number][]; total?: number; i?: number }) {
  const max = Math.max(...items.map((x) => x[1]), 1);
  return (
    <ul className="bars" style={rib(i)}>
      {items.map(([name, v]) => (
        <li key={name}><span title={name}>{name}</span><span className="fill" style={{ width: `${(v / max) * 100}%` }} /><span className="n">{total ? pc(v / total) : v}</span></li>
      ))}
    </ul>
  );
}

export const Icon = {
  download: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M8 2v8M4.5 6.5 8 10l3.5-3.5M2.5 13.5h11" /></svg>,
  print: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M4 6V2h8v4M4 11H2.5V6h11v5H12M4 9h8v5H4z" /></svg>,
  sun: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="8" cy="8" r="3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.4 1.4M11.6 11.6 13 13M3 13l1.4-1.4M11.6 4.4 13 3" /></svg>,
  moon: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M13 9.5A5.5 5.5 0 0 1 6.5 3a5.5 5.5 0 1 0 6.5 6.5z" /></svg>,
  tour: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><rect x="1.5" y="2.5" width="13" height="9" rx="1.5" /><path d="M7 5.2v3.6L10 7z" fill="currentColor" /><path d="M5 14h6" /></svg>,
  plus: <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg>,
};

/* Every sequence of one family laid over the same pitch: shows how much the sequences inside a family differ. */
const pathCache = new Map<string, Promise<PathsData>>();
export function AllPaths({ teamKey, family, color, shotsOnly }: { teamKey: string; family: string; color: string; shotsOnly?: boolean }) {
  const [data, setData] = useState<PathsData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    if (!pathCache.has(teamKey)) pathCache.set(teamKey, api.paths(teamKey));
    pathCache.get(teamKey)!.then((d) => live && setData(d)).catch((e) => { pathCache.delete(teamKey); if (live) setErr(String(e.message ?? e)); });
    return () => { live = false; };
  }, [teamKey]);
  if (err) return <div className="note caution" style={{ margin: 12 }}><span className="tag">No paths</span>{err}</div>;
  const ps = (data?.paths ?? []).filter((p) => p.family === family && (!shotsOnly || p.shot));
  const op = Math.min(0.55, Math.max(0.1, 14 / Math.max(ps.length, 1)));
  return (
    <Pitch label={`${ps.length} ${family} sequences drawn from start to end`}>
      {!data && <text x="60" y="41" textAnchor="middle" fontSize="3" fill="var(--pitch-line)">Reading every possession from the events (first time only)…</text>}
      <g key={family + (shotsOnly ? "s" : "")} className="paths-in">
        {ps.map((p, i) => (
          <polyline key={i} points={p.pts.map((q) => q.join(",")).join(" ")} fill="none" stroke={color} strokeOpacity={op} strokeWidth="0.45" strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {ps.map((p, i) => { const e = p.pts[p.pts.length - 1]; return <circle key={`e${i}`} cx={e[0]} cy={e[1]} r="0.7" fill={p.shot ? "var(--coral)" : color} fillOpacity={p.shot ? 0.95 : Math.min(1, op * 2)} />; })}
      </g>
    </Pitch>
  );
}

/* Who passes to whom inside one family: players at their average position, line width = completed passes between them. */
const netCache = new Map<string, Promise<NetworkData>>();
export function PassNetwork({ teamKey, family, color }: { teamKey: string; family: string; color: string }) {
  const [data, setData] = useState<NetworkData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    if (!netCache.has(teamKey)) netCache.set(teamKey, api.network(teamKey));
    netCache.get(teamKey)!.then((d) => live && setData(d)).catch((e) => { netCache.delete(teamKey); if (live) setErr(String(e.message ?? e)); });
    return () => { live = false; };
  }, [teamKey]);
  if (err) return <div className="note caution" style={{ margin: 12 }}><span className="tag">No network</span>{err}</div>;
  const f = data?.families[family];
  const nodes = (f?.nodes ?? []).filter((n) => n.touches >= Math.max(8, (f?.sequences ?? 0) * 0.15)).sort((a, b) => b.touches - a.touches).slice(0, 11);
  const at = new Map(nodes.map((n) => [n.player, n]));
  const edges = (f?.edges ?? []).filter((e) => at.has(e.a) && at.has(e.b));
  const maxE = Math.max(...edges.map((e) => e.passes), 1), maxN = Math.max(...nodes.map((n) => n.touches), 1);
  const top = [...edges].sort((a, b) => b.passes - a.passes).slice(0, 4);
  const num = (p: string) => { const s = at.get(p)?.shirt; return s != null ? `#${s}` : p; };
  return (
    <div>
      <div className="pitch-wrap">
      <Pitch label={`${family} pass network: ${nodes.length} players, strongest link ${top[0] ? `${top[0].a} and ${top[0].b}, ${top[0].passes} passes` : "none"}`}>
        {!data && <text x="60" y="41" textAnchor="middle" fontSize="3" fill="var(--pitch-line)">Reading the passes of every sequence (first time only)…</text>}
        <g className="paths-in" key={family}>
          {edges.filter((e) => e.passes >= Math.max(3, maxE * 0.12)).map((e, i) => {
            const a = at.get(e.a)!, b = at.get(e.b)!;
            return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={color} strokeOpacity={0.25 + 0.65 * (e.passes / maxE)} strokeWidth={0.3 + 2.4 * (e.passes / maxE)} strokeLinecap="round" />;
          })}
          {[...nodes].sort((a, b) => a.touches - b.touches).map((n) => (
            <g key={n.player}>
              <title>{n.player}: {n.touches} passes made or received</title>
              <circle cx={n.x} cy={n.y} r={2.6 + 1.8 * Math.sqrt(n.touches / maxN)} fill="var(--sticker)" stroke={color} strokeWidth="0.8" />
              <text x={n.x} y={n.y + 1.3} textAnchor="middle" fontSize="3.6" fontWeight="900" fontStyle="italic" fill="var(--sticker-ink)">{n.shirt ?? n.player.split(" ").map((w) => w[0]).join("").slice(0, 2)}</text>
            </g>
          ))}
        </g>
      </Pitch>
      </div>
      {f && (
        <div className="now-row" style={{ display: "block" }}>
          <div className="now">Strongest links in {family} ({f.sequences} sequences): {top.map((e, i) => <span key={i}>{i ? " · " : ""}<b>{num(e.a)}–{num(e.b)}</b> {e.passes}</span>)}</div>
          <div className="net-key">{nodes.map((n) => <span key={n.player}><b>{n.shirt ?? "–"}</b> {n.player}</span>)}</div>
        </div>
      )}
    </div>
  );
}
