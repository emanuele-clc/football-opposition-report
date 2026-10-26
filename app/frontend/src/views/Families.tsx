import { useEffect, useState } from "react";
import type { ClipRef, TeamData } from "../api";
import { AllPaths, evidenceHref, Explain, FamilyLanes, GradeKey, GradeMark, Interval, Note, PassNetwork, PlayIcon, Replay, rib, RIBS, ShareStrip, useGrades } from "../charts";
import { clock, pc } from "../format";
import { famLine, familyClips } from "./Overview";

const ci = (c: [number, number]) => `${pc(c[0])}–${pc(c[1])}`;

export default function Families({
  d,
  phase,
  events,
  family,
  go,
}: {
  d: TeamData;
  phase: "build-up" | "advanced";
  events: boolean;
  family: string;
  go: (tab: string, family?: string) => void;
}) {
  const P = d.report.phases[phase];
  const G = useGrades();
  const shareId = phase === "build-up" ? "F07" : "F08";
  const fams = P.families.map((f) => f.fam);
  const [pick, setPick] = useState(fams.includes(family) ? family : fams[0]);
  const [idx, setIdx] = useState(0);
  const [mode, setMode] = useState<"replay" | "all" | "shots" | "network">(() =>
    location.hash.includes("mode=all") ? "all" : location.hash.includes("mode=network") ? "network" : "replay",
  );
  useEffect(() => {
    setPick(fams.includes(family) ? family : fams[0]);
    setIdx(0);
  }, [phase, d.key]);
  const fam = P.families.find((f) => f.fam === pick) ?? P.families[0];
  const fi = P.families.indexOf(fam);
  const allClips: ClipRef[] = events ? P.families.flatMap(familyClips) : [];
  const clips = allClips.filter((c) => c.title.startsWith(fam.fam + " "));
  const choose = (f: string) => {
    setPick(f);
    setIdx(0);
  };

  return (
    <>
      <div className="pills" role="group" aria-label="Phase" style={{ marginBottom: 18 }}>
        <a
          className="pill-link"
          aria-current={phase === "build-up" ? "page" : undefined}
          href={`#/${encodeURIComponent(d.key)}/build-up`}
        >
          Build-up (start x &lt; 45)
        </a>
        <a
          className="pill-link"
          aria-current={phase === "advanced" ? "page" : undefined}
          href={`#/${encodeURIComponent(d.key)}/advanced`}
        >
          Advanced (start x ≥ 45)
        </a>
      </div>
      <div className="section-head">
        <h2>{phase === "build-up" ? "Build-up" : "Advanced"} families</h2>
        <Explain>
          k = {P.k} · {P.n} open-play sequences with at least 3 passes,{" "}
          {phase === "build-up" ? "starting at x < 45" : "starting at x ≥ 45"}. Click a family to replay it.
        </Explain>
      </div>
      <ShareStrip families={P.families} pick={fam.fam} onPick={choose} />

      <div className="layout-split" style={{ marginTop: 28 }}>
        <section className="sticker" style={rib(fi, fam.fam)} aria-labelledby="rp-h">
          <span className="no">{fam.fam}</span>
          {events && (
            <div className="sticker-top no-print">
              <div className="seg-toggle" role="group" aria-label="What to draw">
                <button type="button" aria-pressed={mode === "replay"} onClick={() => setMode("replay")}>
                  Replay typical
                </button>
                <button type="button" aria-pressed={mode === "all"} onClick={() => setMode("all")}>
                  All {fam.n} sequences
                </button>
                <button type="button" aria-pressed={mode === "shots"} onClick={() => setMode("shots")}>
                  Ending in a shot
                </button>
                <button type="button" aria-pressed={mode === "network"} onClick={() => setMode("network")}>
                  Pass network
                </button>
              </div>
            </div>
          )}
          {mode === "replay" || !events ? (
            <Replay
              teamKey={d.key}
              clips={clips}
              index={idx}
              onIndex={setIdx}
              fallback={<FamilyLanes families={P.families} pick={fam.fam} onPick={choose} />}
            />
          ) : mode === "network" ? (
            <PassNetwork teamKey={d.key} family={fam.fam} color={RIBS[fi % RIBS.length]} />
          ) : (
            <div className="pitch-wrap">
              <AllPaths teamKey={d.key} family={fam.fam} color={RIBS[fi % RIBS.length]} shotsOnly={mode === "shots"} />
            </div>
          )}
          <div className="replay-cap">
            <div>
              <h2 id="rp-h">
                {fam.fam} · {pc(fam.share)}
              </h2>
              <p>{famLine(fam)}</p>
              {mode === "replay" && clips[idx] && <p>Replaying {clips[idx].detail}.</p>}
              {mode === "network" && (
                <p>
                  Completed passes between players inside the {fam.fam} sequences; each player at the average place
                  where they pass or receive. Line width = number of passes. Only players often involved are drawn.
                </p>
              )}
              {(mode === "all" || mode === "shots") && (
                <p>
                  Every {fam.fam} sequence{mode === "shots" ? " that ended in a shot" : ""}, start to end through each
                  pass and run; red dot = ended in a shot. The spread shows how much the sequences inside one family
                  differ; read it together with the structure check.
                </p>
              )}
            </div>
            <button type="button" className="ctl no-print" onClick={() => go("clips", fam.fam)}>
              All {fam.n} clips
            </button>
          </div>
        </section>
        <div>
          <section className="sticker pad fam-detail" style={rib(fi, fam.fam)} aria-label={`${fam.fam} in numbers`}>
            <span className="no">{fam.fam}</span>
            <div className="line" style={{ marginTop: 8 }}>
              <span className="code">{fam.fam}</span>
              <span className="s-muted">{fam.n} sequences</span>
              <span className="share">{pc(fam.share)}</span>
            </div>
            <dl>
              <dt>
                {G && <GradeMark g={G.of(shareId)} href={evidenceHref(d.key, shareId)} none />}
                Share (95%)
              </dt>
              <dd>{ci(fam.share_ci)}</dd>
              <dt>Per match (p10–p90)</dt>
              <dd>{ci(fam.per_match_p10_p90)}</dd>
              <dt>Passes</dt>
              <dd>{fam.passes.toFixed(1)}</dd>
              <dt>Duration</dt>
              <dd>{Math.round(fam.dur)} s</dd>
              <dt>Long passes</dt>
              <dd>{pc(fam.long)}</dd>
              <dt>Start to end (x)</dt>
              <dd>
                {Math.round(fam.x0)} → {Math.round(fam.x1)}
              </dd>
              <dt>
                {G && <GradeMark none />}
                Shot rate (95%)
              </dt>
              <dd>
                {pc(fam.shot)} ({ci(fam.shot_ci)})
              </dd>
              <dt>Stability</dt>
              <dd>
                {fam.jaccard.toFixed(2)} {fam.reliability}
              </dd>
            </dl>
          </section>
          <div style={{ marginTop: 18 }}>
            {G && <GradeKey n={G.n} href={evidenceHref(d.key)} />}
            <Note kind={P.margin >= 0.1 ? "info" : "caution"} tag={P.verdict}>
              Stability {P.jaccard_mean.toFixed(2)} against {P.null_shuffle.toFixed(2)} (shuffled features) and{" "}
              {P.null_gauss.toFixed(2)} (single Gaussian blob).
              {P.verdict !== "clear structure"
                ? " Treat the families as a convenient partition, not as separate behaviours."
                : " Against a stricter check (synthetic data with the same correlations and no clusters), the families of the 10 thesis teams were only slightly better: read them as slices of a continuum."}
            </Note>
            <div style={{ marginTop: 10 }}>
              <Note kind="caution" tag="Shots">
                Families do not predict whether a sequence ends in a shot better than a one-variable rule based on where
                it ends (families better in 0 of 10 teams). Read the shot rate as a description of the family.
              </Note>
            </div>
          </div>
        </div>
      </div>

      <section className="section" aria-labelledby="st-h">
        <div className="section-head">
          <h2 id="st-h">How sequences start decides the family</h2>
          <Explain>Row shares; this is the strongest regularity found in the validation.</Explain>
        </div>
        <div className="table-wrap">
          <table className="heat">
            <thead>
              <tr>
                <th>Start type</th>
                <th>n</th>
                {fams.map((f, i) => (
                  <th key={f}>
                    <span className="chip" style={rib(i, f)}>
                      {f}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {P.by_start.map((s) => (
                <tr key={s.start}>
                  <td>{s.start}</td>
                  <td className="muted">{s.n}</td>
                  {fams.map((f, i) => {
                    const v = s.shares[f] ?? 0;
                    return (
                      <td key={f} className="c" style={rib(i, f)}>
                        {pc(v)}
                        <span className="hb" style={{ width: `${Math.max(v * 100, 1)}%`, opacity: v ? 1 : 0.25 }} />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section" aria-labelledby="tb-h">
        <div className="section-head">
          <h2 id="tb-h">Every number per family</h2>
          <Explain>
            Share interval: yellow mark = season share, bar = per-match share from the 10th to the 90th percentile (axis
            0 to 60%).
          </Explain>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Family</th>
                <th>Share (95%)</th>
                <th style={{ minWidth: 150 }}>Per match</th>
                <th>Passes</th>
                <th>Duration</th>
                <th>Long</th>
                <th>Start to end (x)</th>
                <th>Shot rate (95%)</th>
                <th>Share of shots</th>
                <th>Stability</th>
              </tr>
            </thead>
            <tbody>
              {P.families.map((f, i) => (
                <tr
                  key={f.fam}
                  className={`clickable${f.fam === fam.fam ? " sel" : ""}`}
                  onClick={() => {
                    choose(f.fam);
                    scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  <td>
                    <span className="chip" style={rib(i, f.fam)}>
                      {f.fam}
                    </span>
                  </td>
                  <td>
                    <b>{pc(f.share)}</b> <span className="muted">({ci(f.share_ci)})</span>
                  </td>
                  <td>
                    <Interval
                      value={f.share}
                      ci={f.per_match_p10_p90}
                      max={0.6}
                      label={`${f.fam}: per-match share ${ci(f.per_match_p10_p90)}`}
                    />
                  </td>
                  <td>{f.passes.toFixed(1)}</td>
                  <td>{Math.round(f.dur)} s</td>
                  <td>{pc(f.long)}</td>
                  <td>
                    {Math.round(f.x0)} → {Math.round(f.x1)}
                  </td>
                  <td>
                    <b>{pc(f.shot)}</b> <span className="muted">({ci(f.shot_ci)})</span>
                  </td>
                  <td>{pc(f.shot_share)}</td>
                  <td>
                    {f.jaccard.toFixed(2)} {f.reliability}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section" aria-labelledby="ex-h">
        <div className="section-head">
          <h2 id="ex-h">Typical sequences to find on video</h2>
          <Explain>The three closest to the centre of each family.</Explain>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th></th>
                <th className="l">Family</th>
                <th className="l">Date</th>
                <th className="l">Opponent</th>
                <th>Half, minute</th>
                <th className="l">Start</th>
                <th>Passes</th>
                <th>Duration</th>
                <th>Shot</th>
              </tr>
            </thead>
            <tbody>
              {P.families.flatMap((f, i) =>
                f.examples.map((e, j) => {
                  const on = f.fam === fam.fam && idx === j;
                  return (
                    <tr key={f.fam + j} className={on ? "sel" : ""}>
                      <td>
                        {events && e.match ? (
                          <button
                            type="button"
                            className="play-btn"
                            aria-label={`Replay ${f.fam} example ${j + 1}`}
                            onClick={() => {
                              setPick(f.fam);
                              setIdx(j);
                              scrollTo({ top: 0, behavior: "smooth" });
                            }}
                          >
                            {PlayIcon}
                          </button>
                        ) : null}
                      </td>
                      <td className="l">
                        <span className="chip" style={rib(i, f.fam)}>
                          {f.fam}
                        </span>
                      </td>
                      <td className="l">{e.date}</td>
                      <td className="l">{e.opponent}</td>
                      <td>
                        half {e.half}, {clock(e.minute, e.second)}
                        {e.video ? ` (video ${e.video})` : ""}
                      </td>
                      <td className="l">{e.start}</td>
                      <td>{e.passes}</td>
                      <td>{Math.round(e.dur)} s</td>
                      <td>{e.shot ? "yes" : "no"}</td>
                    </tr>
                  );
                }),
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
