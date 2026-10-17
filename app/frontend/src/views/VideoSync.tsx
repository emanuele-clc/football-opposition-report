import { useEffect, useRef, useState } from "react";
import type { ClipRow } from "../api";
import { Icon } from "../charts";

/* The match video next to the replay. Video time = half kick-off in the video + match clock (minus 45:00 in the second half),
   as in docs/data_format.md; each clip starts 3 s early, like the XML export. Offsets stay in this browser only. */
type Offsets = Record<string, [number | null, number | null]>;
const load = (): Offsets => { try { return JSON.parse(localStorage.getItem("video-offsets") ?? "{}"); } catch { return {}; } };
const store = (o: Offsets) => { try { localStorage.setItem("video-offsets", JSON.stringify(o)); } catch { /* private window */ } };
const mmss = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

export default function VideoSync({ row }: { row: ClipRow | undefined }) {
  const [url, setUrl] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [offs, setOffs] = useState<Offsets>(load);
  const vid = useRef<HTMLVideoElement>(null);
  const m = row ? String(row.match) : "";
  const [h1, h2] = offs[m] ?? [null, null];
  const kick = row ? (row.half === 1 ? h1 : h2) : null;
  const at = row && kick != null ? kick + row.minute * 60 + row.second - (row.half === 1 ? 0 : 2700) : null;

  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  useEffect(() => {
    if (!vid.current || at == null) return;
    vid.current.currentTime = Math.max(at - 3, 0);
    vid.current.play().catch(() => undefined);
  }, [at, url]);

  const setHalf = (half: 0 | 1, v: number | null) => {
    const next = { ...offs, [m]: (offs[m] ?? [null, null]).map((x, i) => (i === half ? v : x)) as [number | null, number | null] };
    setOffs(next); store(next);
  };

  return (
    <div className="sticker pad video-box no-print">
      <h3>Match video</h3>
      {!url ? (
        <p className="s-muted" style={{ fontSize: 13.5, marginTop: 6 }}>
          Load the video file of this match to watch each clip next to its replay. Nothing is uploaded: the file plays in this browser.
          <span style={{ display: "block", marginTop: 10 }}>
            <span className="ctl file-btn">{Icon.plus} Load match video<input type="file" accept="video/*" onChange={(e) => { const f = e.target.files?.[0]; if (f) { setUrl(URL.createObjectURL(f)); setName(f.name); } }} /></span>
          </span>
        </p>
      ) : (
        <>
          <p className="s-muted" style={{ fontSize: 12.5, margin: "4px 0 8px" }}>{name}{row ? ` · clips of match ${row.match} (${row.opponent}, ${row.date})` : ""}</p>
          <video ref={vid} src={url} controls preload="metadata" />
          <div className="row">
            <span>Kick-off in the video, seconds:</span>
            <label>1st half <input type="number" min={0} step={0.1} value={h1 ?? ""} onChange={(e) => setHalf(0, e.target.value === "" ? null : Number(e.target.value))} /></label>
            <button type="button" className="ctl" onClick={() => setHalf(0, Math.round((vid.current?.currentTime ?? 0) * 10) / 10)}>Set to now</button>
            <label>2nd half <input type="number" min={0} step={0.1} value={h2 ?? ""} onChange={(e) => setHalf(1, e.target.value === "" ? null : Number(e.target.value))} /></label>
            <button type="button" className="ctl" onClick={() => setHalf(1, Math.round((vid.current?.currentTime ?? 0) * 10) / 10)}>Set to now</button>
          </div>
          <p className="s-muted" style={{ fontSize: 12.5, marginTop: 8 }}>
            {at != null ? `This clip: video ${mmss(at)} (starts 3 s early).` : "Pause the video at the kick-off of each half and press Set to now; clips of this match then jump to their moment."}
            {" "}Check that the video is the same match as the clip.
          </p>
        </>
      )}
    </div>
  );
}
