import { useEffect, useRef, useState } from "react";
import { api, type TrackClip, type TrackMatch, type TrackResults } from "../api";
import { Note, Pitch, plain } from "../charts";

const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const lerp = (a: [number, number] | null, b: [number, number] | null, u: number): [number, number] | null =>
  a && b ? [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u] : (a ?? b);
const surname = (n: string) => n.split(" ").slice(-1)[0];
const r2 = (x: number) => x.toFixed(2),
  m1 = (x: number) => x.toFixed(1);
const MODELS: [string, string][] = [
  ["persistence", "Stays where he is"],
  ["constant_velocity", "Keeps his current velocity"],
  ["ridge", "Linear regression (ridge)"],
  ["lstm", "LSTM neural network"],
];

/* What the two exploratory checks found, read from results/exploratory_*.json; no number is computed here. */
function Findings({ R }: { R: TrackResults }) {
  const A = R.pitch_control?.A_pass_check,
    G = R.ghosting;
  return (
    <section className="section" aria-labelledby="tf-h">
      <div className="section-head">
        <h2 id="tf-h">What the checks found</h2>
        <p>
          Exploratory: definitions fixed in the scripts before one run each; no protocol committed in advance. 95%
          intervals by bootstrap.
        </p>
      </div>
      <div className="layout-2">
        <div className="sticker pad">
          <h3>Pitch control: does it tell completed from failed passes?</h3>
          {A ? (
            <>
              <table style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>Predictor (positions at the pass)</th>
                    <th>AUC</th>
                    <th>95%</th>
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["pc", "Pitch control at the end point"],
                      ["margin", "Nearest opponent minus nearest team-mate"],
                      ["length", "Shorter pass"],
                    ] as const
                  ).map(([k, l]) => (
                    <tr key={k}>
                      <td>
                        <b>{l}</b>
                      </td>
                      <td>{r2(A.auc[k].value)}</td>
                      <td>
                        {r2(A.auc[k].ci[0])}–{r2(A.auc[k].ci[1])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p style={{ marginTop: 8 }}>
                {A.passes.toLocaleString("en")} open-play passes, {Math.round(100 * A.completed_share)}% completed. AUC
                0.5 = no information, 1 = perfect. Pitch control minus nearest-player: {r2(A.auc.pc_minus_margin.value)}{" "}
                ({r2(A.auc.pc_minus_margin.ci[0])} to {r2(A.auc.pc_minus_margin.ci[1])}),{" "}
                {A.pc_adds_over_margin
                  ? "so it adds over the simpler rule"
                  : "so it does not clearly add over the simpler rule"}
                ; minus pass length: {r2(A.auc.pc_minus_length.value)} ({r2(A.auc.pc_minus_length.ci[0])} to{" "}
                {r2(A.auc.pc_minus_length.ci[1])}), {A.pc_adds_over_length ? "adds" : "does not clearly add"}.
              </p>
              <p style={{ marginTop: 6 }}>
                <b>Caution:</b> the end point is where the next player touches the ball, which already favours whoever
                is closest there; so both AUCs are optimistic, and short failed passes (blocks) make "shorter pass" look
                worse than chance. The comparison between the two models is fair; the absolute values are not.
              </p>
            </>
          ) : (
            <p>Not run yet: python -X utf8 src/tracking/pitch_control.py &lt;dfl folder&gt;</p>
          )}
        </div>
        <div className="sticker pad">
          <h3>Ghosting: where will each defender be in {G?.horizon_s ?? 3} s?</h3>
          {G ? (
            <>
              <table style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Position error (m)</th>
                    <th>Back-line height error (m)</th>
                  </tr>
                </thead>
                <tbody>
                  {MODELS.map(([k, l]) => (
                    <tr key={k}>
                      <td>
                        <b>{l}</b>
                      </td>
                      <td>
                        {m1(G.position_error_m[k].mean)}{" "}
                        <span style={{ opacity: 0.6 }}>
                          ({m1(G.position_error_m[k].ci[0])}–{m1(G.position_error_m[k].ci[1])})
                        </span>
                      </td>
                      <td>
                        {m1(G.line_height_error_m[k].mean)}{" "}
                        <span style={{ opacity: 0.6 }}>
                          ({m1(G.line_height_error_m[k].ci[0])}–{m1(G.line_height_error_m[k].ci[1])})
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p style={{ marginTop: 8 }}>
                Trained on 5 matches, tested once on the 2 latest ({G.samples.test.toLocaleString("en")} moments;
                defenders move {m1(G.test_mean_displacement_m)} m in 3 s on average). The LSTM{" "}
                {G.position_diff.lstm_minus_ridge.lstm_beats ? "beats" : "does not beat"} the linear regression and{" "}
                {G.position_diff.lstm_minus_persistence.lstm_beats ? "beats" : "does not beat"} 'stays where he is'.
                With this little data a simple model is as good or better; clubs train such models on seasons of
                tracking.
              </p>
            </>
          ) : (
            <p>Not run yet: python -X utf8 src/tracking/ghosting.py &lt;dfl folder&gt;</p>
          )}
        </div>
      </div>
    </section>
  );
}

/* Control of the home team per cell (0-100): sky above 50, coral below, stronger the clearer the control. */
function ControlLayer({ pc, grid }: { pc: number[]; grid: [number, number] }) {
  const [gx, gy] = grid,
    w = 120 / gx,
    h = 80 / gy;
  return (
    <g aria-hidden="true">
      {pc.map((v, i) => {
        const ix = Math.floor(i / gy),
          iy = i % gy,
          a = Math.abs(v - 50) / 50;
        return (
          <rect
            key={i}
            x={ix * w}
            y={80 - (iy + 1) * h}
            width={w + 0.05}
            height={h + 0.05}
            fill={v >= 50 ? "var(--sky)" : "var(--coral)"}
            fillOpacity={(0.08 + 0.55 * a).toFixed(2)}
          />
        );
      })}
    </g>
  );
}

export default function TrackingLab() {
  const [list, setList] = useState<TrackMatch[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [mi, setMi] = useState(0);
  const [gi, setGi] = useState(0);
  const [clip, setClip] = useState<TrackClip | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [layer, setLayer] = useState(true);
  const raf = useRef<number>();
  const [R, setR] = useState<TrackResults | null>(null);
  useEffect(() => {
    api
      .trackResults()
      .then(setR)
      .catch(() => setR(null));
  }, []);

  useEffect(() => {
    api
      .trackMatches()
      .then(setList)
      .catch((e) => setErr(String(e.message ?? e)));
  }, []);
  const m = list?.[mi];
  const g = m?.goals[gi];
  useEffect(() => {
    if (!m || !g) return;
    let live = true;
    setClip(null);
    setPlaying(false);
    api
      .trackClip(m.match, g.half, g.frame)
      .then((c) => {
        if (!live) return;
        setClip(c);
        setT(reduced() ? c.frames[c.frames.length - 1].t : c.frames[0].t);
        setPlaying(!reduced());
      })
      .catch((e) => live && setErr(String(e.message ?? e)));
    return () => {
      live = false;
    };
  }, [m?.match, g?.frame]);

  const t0 = clip?.frames[0].t ?? 0,
    t1 = clip?.frames[clip.frames.length - 1].t ?? 0;
  useEffect(() => {
    if (!playing || !clip) return;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = ((now - last) / 1000) * speed;
      last = now;
      setT((x) => {
        const n = x + dt;
        if (n >= t1) {
          setPlaying(false);
          return t1;
        }
        return n;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current!);
  }, [playing, clip, speed, t1]);

  if (err)
    return (
      <div className="state">
        <h2>No tracking data</h2>
        <p>{err}</p>
      </div>
    );
  if (!list)
    return (
      <main aria-busy="true">
        <div className="skeleton" style={{ height: 420 }} />
      </main>
    );

  const k = clip ? Math.min(Math.max((t - t0) * 5, 0), clip.frames.length - 1) : 0,
    i0 = Math.floor(k),
    u = k - i0;
  const F0 = clip?.frames[i0],
    F1 = clip?.frames[Math.min(i0 + 1, (clip?.frames.length ?? 1) - 1)];
  const atEnd = t >= t1 - 1e-6;

  return (
    <>
      <div className="section-head">
        <h2>Tracking lab</h2>
        <p>
          What tracking data add to event data: every player's position 25 times a second, so space can be measured.
          Seven open matches from the DFL (Bundesliga and 2. Bundesliga 2022/23), not the teams of the report. Each goal
          is replayed from 10 s before, with pitch control: for every patch of grass, which team would most likely reach
          a ball played there first.
        </p>
      </div>

      <div className="pills no-print" role="group" aria-label="Match">
        {list.map((x, i) => (
          <button
            key={x.match}
            type="button"
            aria-pressed={i === mi}
            onClick={() => {
              setMi(i);
              setGi(0);
            }}
          >
            {x.home} {x.result} {x.guest}
          </button>
        ))}
      </div>

      <div className="layout-split" style={{ marginTop: 16 }}>
        <section className="sticker" style={plain} aria-labelledby="tl-h">
          <span className="no">{clip ? `${clip.clock} · half ${clip.half}` : "Loading"}</span>
          <div className="pitch-wrap">
            <Pitch
              label={
                clip
                  ? `Goal replay with pitch control, ${clip.home} against ${clip.guest}`
                  : "Loading the tracking clip"
              }
            >
              {clip && F0 && F1 && (
                <>
                  {layer && <ControlLayer pc={(u < 0.5 ? F0 : F1).pc} grid={clip.grid} />}
                  {clip.players.map((p, j) => {
                    const q = lerp(F0.p[j], F1.p[j], u);
                    if (!q) return null;
                    const col = p.side === "home" ? "var(--sky)" : "var(--coral)";
                    return (
                      <g key={j} transform={`translate(${q[0]} ${q[1]})`}>
                        <circle
                          r={1.45}
                          fill={col}
                          stroke={p.gk ? "var(--yellow)" : "var(--sticker-ink)"}
                          strokeWidth={p.gk ? 0.6 : 0.3}
                        />
                        <text
                          y={-2}
                          textAnchor="middle"
                          fontSize="1.6"
                          fontWeight="700"
                          fill="var(--sticker)"
                          paintOrder="stroke"
                          stroke="var(--pitch)"
                          strokeWidth="0.6"
                        >
                          {surname(p.name)}
                        </text>
                      </g>
                    );
                  })}
                  {(() => {
                    const b = lerp(F0.ball, F1.ball, u);
                    return (
                      b && (
                        <circle
                          cx={b[0]}
                          cy={b[1]}
                          r={0.9}
                          fill="var(--yellow)"
                          stroke="var(--sticker-ink)"
                          strokeWidth="0.3"
                        />
                      )
                    );
                  })()}
                </>
              )}
              {!clip && (
                <text x="60" y="41" textAnchor="middle" fontSize="3" fill="var(--pitch-line)">
                  Computing pitch control…
                </text>
              )}
            </Pitch>
          </div>
          <div className="controls no-print">
            <button
              type="button"
              className="ctl primary"
              disabled={!clip}
              onClick={() => {
                if (atEnd) {
                  setT(t0);
                  setPlaying(true);
                } else setPlaying((p) => !p);
              }}
            >
              <span>{atEnd ? "Again" : playing ? "Pause" : "Play"}</span>
            </button>
            <input
              className="scrub"
              type="range"
              min={t0}
              max={t1}
              step={0.04}
              value={t}
              disabled={!clip}
              aria-label="Time in the clip"
              onChange={(e) => {
                setPlaying(false);
                setT(Number(e.target.value));
              }}
            />
            <button
              type="button"
              className="ctl"
              onClick={() => setSpeed((s) => (s >= 2 ? 0.5 : s * 2))}
              aria-label={`Speed ${speed} times, change`}
            >
              {speed}×
            </button>
            <button type="button" className="ctl" aria-pressed={layer} onClick={() => setLayer((v) => !v)}>
              Pitch control
            </button>
          </div>
          <div className="replay-cap">
            <div>
              <h2 id="tl-h">{g ? `${g.player} (${g.team}), ${g.clock}` : "No goals in this match's events"}</h2>
              <p>
                {clip ? (
                  <>
                    {t < 0
                      ? `${(-t).toFixed(1)} s before the goal shot`
                      : t < 0.05
                        ? "the shot"
                        : `${t.toFixed(1)} s after the shot`}
                    . <b style={{ color: "var(--sky)" }}>Blue: {clip.home}</b> (attacking {clip.home_attacks} in this
                    half) · <b style={{ color: "var(--coral)" }}>red: {clip.guest}</b>. Ball in yellow, goalkeepers
                    ringed in yellow.
                  </>
                ) : (
                  "Loading…"
                )}
              </p>
            </div>
          </div>
        </section>
        <div className="stack">
          <div className="sticker pad">
            <h3>Goals in this match</h3>
            <table style={{ marginTop: 6 }}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Scorer</th>
                  <th>Team</th>
                  <th>xG</th>
                </tr>
              </thead>
              <tbody>
                {m?.goals.map((x, i) => (
                  <tr key={i} aria-selected={i === gi} onClick={() => setGi(i)} style={{ cursor: "pointer" }}>
                    <td>{x.clock}</td>
                    <td>
                      <b>{x.player}</b>
                    </td>
                    <td>{x.team}</td>
                    <td>{x.xg == null ? "–" : x.xg.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ marginTop: 8, fontSize: 12, color: "var(--sticker-ink)", opacity: 0.72 }}>
              Goals = DFL 'successful shot' events; own goals and penalties are not in this list, so it can be shorter
              than the score.
            </p>
          </div>
          <Note kind="info" tag="How control is computed">
            Spearman's model (2018) with the published parameters: each player reacts in 0.7 s, then runs at up to 5
            m/s; the ball travels at 15 m/s. Nothing was fitted to these matches. It ignores body orientation, a
            player's real speed and the ball's height.
          </Note>
          <Note kind="caution" tag="Not the report">
            These are seven other matches, five of them with Fortuna Düsseldorf. The report's teams have event data
            only; the open StatsBomb 360 frames show a snapshot, not movement, so this is what a club with tracking data
            could add.
          </Note>
        </div>
      </div>
      {R && <Findings R={R} />}
      <p className="small" style={{ marginTop: 14 }}>
        Data: Bassek, Rein, Weber &amp; Memmert (2025), An integrated dataset of spatiotemporal and event data in elite
        soccer, Scientific Data 12:195, CC BY 4.0, with the authorisation of the DFL.
      </p>
    </>
  );
}
