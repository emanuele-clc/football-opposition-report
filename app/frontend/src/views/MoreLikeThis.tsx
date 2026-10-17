import { useEffect, useState } from "react";
import { api, type ClipRef, type ClipRow, type SimilarData } from "../api";
import { rib } from "../charts";
import { clock } from "../format";

/* The sequences of the season closest to the selected one, on the same numbers the families are built from. Click to replay. */
const famIdx = (f: string) => { const m = /^[AB](\d+)$/.exec(f); return m ? Number(m[1]) - 1 : 0; };

export default function MoreLikeThis({ teamKey, row, onPlay }: { teamKey: string; row: ClipRow | undefined; onPlay: (clips: ClipRef[], index: number) => void }) {
  const [d, setD] = useState<SimilarData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!row) return;
    let live = true; setD(null); setErr(null);
    api.similar(teamKey, row).then((x) => live && setD(x)).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [teamKey, row?.match, row?.half, row?.minute, row?.second]);
  if (!row) return null;
  const refs: ClipRef[] = (d?.similar ?? []).map((s) => ({ match: Number(s.match), half: Number(s.half), minute: Number(s.minute), second: Number(s.second), title: s.family,
    detail: `${s.family} · vs ${s.opponent}, ${s.date}, half ${s.half} ${clock(Number(s.minute), Number(s.second))} · ${s.passes} passes, ${s.duration_s} s` }));
  return (
    <div className="sticker pad" style={{ marginTop: 16 }}>
      <h3>More like this</h3>
      <p className="s-muted" style={{ fontSize: 12.5, margin: "4px 0 10px" }}>The 8 sequences of the season with the closest start, end, path, passes and duration. Neighbouring sequences can fall in different families.</p>
      {err && <p className="s-muted">{err}</p>}
      {!d && !err && <div className="skeleton" style={{ height: 120, background: "#eef1f8" }} />}
      <div className="like-grid">
        {d?.similar.map((s, i) => (
          <button key={i} type="button" className="like" onClick={() => onPlay(refs, i)} title={refs[i].detail}>
            <svg viewBox="-2 -2 124 84" aria-hidden="true">
              <rect x="-2" y="-2" width="124" height="84" rx="4" fill="#163a2a" />
              <line x1="60" y1="0" x2="60" y2="80" stroke="rgba(255,255,255,.3)" strokeWidth="0.8" />
              <polyline points={s.pts.map((q) => q.join(",")).join(" ")} fill="none" stroke="#ffd23f" strokeWidth="1.6" strokeLinejoin="round" />
              <circle cx={s.pts[0][0]} cy={s.pts[0][1]} r="2.6" fill="#fff" />
            </svg>
            <span className="like-meta"><span className="chip" style={rib(famIdx(s.family))}>{s.family}</span> <span>{s.opponent}</span><small>{s.passes} passes · {s.duration_s} s{Number(s.ended_in_shot) ? " · shot" : ""}</small></span>
          </button>
        ))}
      </div>
    </div>
  );
}
