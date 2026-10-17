import React, { useEffect, useState } from "react";
import { api, type StyleMapData } from "../api";
import { Note } from "../charts";

/* Every team placed by its numbers: first two principal components of the standardised facts used for the ranks.
   Descriptive; teams come from different leagues and seasons. */
let cache: Promise<StyleMapData> | null = null;
const side = (l: { label: string; weight: number }[], sign: 1 | -1) => l.filter((x) => Math.sign(x.weight) === sign).slice(0, 2).map((x) => x.label.toLowerCase()).join(", ");

export default function StyleMap({ current, other }: { current: string; other?: string }) {
  const [d, setD] = useState<StyleMapData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { (cache ??= api.stylemap()).then(setD).catch((e) => { cache = null; setErr(e.message); }); }, []);
  if (err) return <Note kind="info" tag="Style map">{err}</Note>;
  if (!d) return <div className="skeleton" style={{ height: 380 }} />;
  const xs = d.teams.map((t) => t.x), ys = d.teams.map((t) => t.y);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const X = (v: number) => 110 + ((v - x0) / Math.max(x1 - x0, 1e-6)) * 780, Y = (v: number) => 330 - ((v - y0) / Math.max(y1 - y0, 1e-6)) * 270;
  const me = d.teams.find((t) => t.key === current);
  const [a1, a2] = d.axes;
  return (
    <div className="layout-split" style={{ gridTemplateColumns: "minmax(0, 1.6fr) minmax(280px, 1fr)" }}>
      <div className="sticker">
        <span className="no" style={{ "--rib": "var(--lilac)" } as React.CSSProperties}>Style map</span>
        <svg viewBox="0 0 1000 400" className="pitch-svg" role="img" aria-label={`Style map of ${d.teams.length} teams`} style={{ background: "#f4f6fb", borderRadius: 9 }}>
          <line x1="40" y1="200" x2="960" y2="200" stroke="#c9d1ea" strokeDasharray="4 6" /><line x1="500" y1="40" x2="500" y2="350" stroke="#c9d1ea" strokeDasharray="4 6" />
          <text x="955" y="390" textAnchor="end" fontSize="15" fill="#4b5574">→ {side(a1.loadings, 1)}</text>
          <text x="45" y="390" fontSize="15" fill="#4b5574">{side(a1.loadings, -1)} ←</text>
          <text x="20" y="28" fontSize="15" fill="#4b5574">↑ {side(a2.loadings, 1)}</text>
          {d.teams.map((t) => {
            const on = t.key === current, cmp = t.key === other;
            return (
              <g key={t.key} transform={`translate(${X(t.x)},${Y(t.y)})`} className="map-dot">
                <title>{t.team}: nearest {t.nearest.map((n) => n.team).join(", ")}</title>
                <circle r={on || cmp ? 14 : 9} fill={on ? "var(--yellow)" : cmp ? "var(--sky)" : "#98a3c7"} stroke="#121a33" strokeWidth={on || cmp ? 2.5 : 1} />
                <text y={on || cmp ? -22 : -15} textAnchor="middle" fontSize={on || cmp ? 19 : 15} fontWeight={on || cmp ? 900 : 650} fontStyle={on || cmp ? "italic" : "normal"} fill="#121a33">{t.team}</text>
              </g>
            );
          })}
        </svg>
        <div className="now-row"><div className="now">Horizontal axis explains {Math.round(100 * a1.explained)}% of the differences, vertical {Math.round(100 * a2.explained)}%. Built from {d.metrics.length} facts of the report.</div></div>
      </div>
      <div className="stack">
        {me && (
          <div className="sticker pad">
            <h3>Closest to {me.team}</h3>
            <ol className="near">{me.nearest.map((n) => <li key={n.team}><b>{n.team}</b> <span className="s-muted">distance {n.distance}</span></li>)}</ol>
          </div>
        )}
        <Note kind="info" tag="How to read">Each dot is a team placed by its numbers on build-up, restarts, set pieces and transitions (principal components of the standardised facts). Close dots = similar numbers, not the same tactics. Teams come from different leagues and seasons, so read it as a rough map.</Note>
      </div>
    </div>
  );
}
