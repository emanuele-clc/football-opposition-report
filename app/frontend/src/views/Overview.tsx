import { useEffect, useState, type CSSProperties } from "react";
import { api, type ClipRef, type Evidence, type Family, type Rank, type TeamData } from "../api";
import { evidenceHref, FamilyLanes, Replay, rib, ShareStrip, third } from "../charts";
import { fmt, n1, ordinal, pc } from "../format";

const TAB_OF: Record<string, string> = {
  report: "build-up",
  restarts: "restarts",
  setpieces: "setpieces",
  transitions: "transitions",
  defending: "defending",
  xthreat: "threat",
};

/* Five facts where this team sits furthest from the middle of the other teams: the most extreme fact of each section first, then the next most extreme. */
function keyPoints(ranks: Rank[]) {
  const ext = (r: Rank) => Math.min(r.rank - 1, r.of - r.rank) + (r.caution ? 0.5 : 0);
  const sorted = [...ranks].filter((r) => r.of >= 3).sort((a, b) => ext(a) - ext(b));
  const firsts = [...new Set(sorted.map((r) => r.group))].map((g) => sorted.find((r) => r.group === g)!);
  return [...firsts, ...sorted.filter((r) => !firsts.includes(r))].slice(0, 5).sort((a, b) => ext(a) - ext(b));
}
/* How to say "highest" and "lowest" for each fact. */
const WORDS: Record<string, [string, string]> = {
  passes: ["Most passes per sequence", "Fewest passes per sequence"],
  long: ["Most long passes (30+)", "Fewest long passes (30+)"],
  dur: ["Longest sequences", "Shortest sequences"],
  shot: ["Most sequences ending in a shot", "Fewest sequences ending in a shot"],
  buildup_share: ["Most sequences starting in own half", "Fewest sequences starting in own half"],
  gk_short: ["Most goal kicks played short", "Fewest goal kicks played short"],
  gk_opp_half: ["Most goal kicks reaching the opponent half", "Fewest goal kicks reaching the opponent half"],
  kp_short: ["Most keeper distributions played short", "Fewest keeper distributions played short"],
  corner_pm: ["Most corners per match", "Fewest corners per match"],
  corner_shot: ["Most shots after corners", "Fewest shots after corners"],
  losses_pm: ["Most losses per match", "Fewest losses per match"],
  regain5: ["Most balls regained within 5 s of a loss", "Fewest balls regained within 5 s of a loss"],
  high_rec_pm: ["Most recoveries in the final third", "Fewest recoveries in the final third"],
  ppda: ["Highest PPDA (least intense pressing)", "Lowest PPDA (most intense pressing)"],
  press_pm: ["Most pressures per match", "Fewest pressures per match"],
  press_final: ["Most pressures in the final third", "Fewest pressures in the final third"],
  def_height: ["Highest defensive actions", "Deepest defensive actions"],
  xga_pm: ["Most xG conceded per match", "Least xG conceded per match"],
};
const phrase = (r: Rank) => {
  const w = WORDS[r.id];
  if (r.provisional) return r.label;
  if (w && r.rank === 1) return w[0];
  if (w && r.rank === r.of) return w[1];
  if (w && r.rank === 2) return `Second-${w[0].split(" ")[0].toLowerCase()} ${w[0].split(" ").slice(1).join(" ")}`;
  if (w && r.rank === r.of - 1)
    return `Second-${w[1].split(" ")[0].toLowerCase()} ${w[1].split(" ").slice(1).join(" ")}`;
  return r.label;
};
const where = (r: Rank, key: string) => {
  const o = r.teams.filter((t) => t.key !== key),
    m = o.reduce((s, t) => s + t.value, 0) / Math.max(o.length, 1);
  return `${r.group} · the other ${o.length} teams: ${fmt(m, r.unit)} on average`;
};

export function familyClips(f: Family): ClipRef[] {
  return f.examples
    .filter((e) => e.match)
    .map((e, j) => ({
      match: e.match!,
      half: e.half,
      minute: e.minute,
      second: e.second,
      title: `${f.fam} example ${j + 1}`,
      detail: `vs ${e.opponent}, ${e.date}, half ${e.half} · starts ${e.start.toLowerCase()} · ${e.passes} passes${e.shot ? " · ended in a shot" : ""}`,
    }));
}
/* The hero opens on the most common family of the phase (codes are ordered by start position, not by share). */
const mostCommon = (fs: Family[]) => fs.reduce((a, b) => (b.share > a.share ? b : a));
export const famLine = (f: Family) =>
  `${third(f.x0) === third(f.x1) ? `Stays in the ${third(f.x0)}` : `From the ${third(f.x0)} to the ${third(f.x1)}`} · ${n1(f.passes)} passes · ${Math.round(f.dur)} s · ended in a shot ${pc(f.shot)}`;

export default function Overview({
  d,
  events,
  go,
}: {
  d: TeamData;
  events: boolean;
  go: (tab: string, family?: string) => void;
}) {
  const [phase, setPhase] = useState<"build-up" | "advanced">("build-up");
  const P = d.report.phases[phase];
  const top = mostCommon(P.families);
  const [pick, setPick] = useState<string>(top.fam);
  const [idx, setIdx] = useState(0);
  const fam = P.families.find((f) => f.fam === pick) ?? top;
  const fi = P.families.indexOf(fam);
  const clips = events ? familyClips(fam) : [];
  const kps = keyPoints(d.ranks);
  const choose = (f: string) => {
    setPick(f);
    setIdx(0);
  };
  const [ev, setEv] = useState<Evidence | null>(null);
  useEffect(() => {
    api
      .evidence()
      .then(setEv)
      .catch(() => undefined);
  }, []);
  const evRows = Object.values(ev?.statements ?? {});

  return (
    <>
      <div className="layout-hero">
        <section className="sticker enter" style={rib(fi, fam.fam)} aria-labelledby="hero-h">
          <span className="no">{fam.fam}</span>
          <Replay
            teamKey={d.key}
            clips={clips}
            index={idx}
            onIndex={setIdx}
            loop
            fallback={<FamilyLanes families={P.families} pick={fam.fam} onPick={choose} />}
            head={null}
          />
          <div className="replay-cap">
            <div>
              <h2 id="hero-h">
                {fam.fam} · {pc(fam.share)} of {phase === "build-up" ? "build-up" : "advanced"} sequences
              </h2>
              <p>{famLine(fam)}</p>
              {clips[idx] && <p>Replaying {clips[idx].detail}.</p>}
              {!events && (
                <p>
                  Replays need the raw event files: start the app with --data-dir pointing at the StatsBomb folder.
                  Shown: average start to end of each family.
                </p>
              )}
            </div>
            <button type="button" className="ctl no-print" onClick={() => go("clips", fam.fam)}>
              All {fam.n} clips
            </button>
          </div>
        </section>

        <section aria-labelledby="kp-h">
          <h3 id="kp-h" style={{ color: "var(--accent-text)", marginBottom: 14 }}>
            Key points
          </h3>
          <div className="kp-list">
            {kps.map((r, i) => (
              <a
                key={r.id}
                className="kp sticker enter"
                style={{ "--i": i + 1 } as CSSProperties}
                href={`#/${encodeURIComponent(d.key)}/${TAB_OF[r.sheet]}`}
              >
                <span className="dot" aria-hidden="true">
                  {i + 1}
                </span>
                <span>
                  <p>
                    {phrase(r)}: <b>{fmt(r.value, r.unit)}</b>
                  </p>
                  <p className="sub">
                    {where(r, d.key)}
                    {r.caution ? ` · rough: ${r.caution}` : ""}
                  </p>
                </span>
                {r.provisional ? (
                  <span className="badge prov">
                    <b>{d.matches}</b>
                    <small>matches · not ranked</small>
                  </span>
                ) : (
                  <span className="badge">
                    <b>{ordinal(r.rank)}</b>
                    <small>of {r.of}</small>
                  </span>
                )}
              </a>
            ))}
          </div>
          <p className="small" style={{ marginTop: 12, marginBottom: 4 }}>
            {d.provisional
              ? `Only ${d.matches} matches: ${d.team} is not ranked. Each line compares it with the average of the ${d.references.length} reference teams (${d.min_matches ?? 8}+ matches each); read the numbers as rough.`
              : `Where ${d.team} differs most from the other ${d.references.length} teams. 1st = highest value.`}
          </p>
          <div className="fam-head">
            <h3 style={{ color: "var(--accent-text)" }}>Families</h3>
            <div className="pills" role="group" aria-label="Phase">
              {(["build-up", "advanced"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  aria-pressed={phase === p}
                  onClick={() => {
                    setPhase(p);
                    choose(mostCommon(d.report.phases[p].families).fam);
                  }}
                >
                  {p === "build-up" ? "Build-up" : "Advanced"}
                </button>
              ))}
            </div>
          </div>
          <ShareStrip families={P.families} pick={fam.fam} onPick={choose} />
          <p className="small" style={{ marginTop: 10 }}>
            B1, A2… are labels, not tactical categories.{" "}
            <a href={`#/${encodeURIComponent(d.key)}/${phase}`}>Every number per family →</a>
          </p>
        </section>
      </div>

      <section className="section" aria-labelledby="trust-h">
        <div className="section-head">
          <h2 id="trust-h">How much can you trust this?</h2>
        </div>
        <ul className="trust">
          {(["build-up", "advanced"] as const).map((p) => {
            const Q = d.report.phases[p];
            return (
              <li key={p} className={Q.margin >= 0.1 ? "ok" : "caution"}>
                <b>{p === "build-up" ? "Build-up families" : "Advanced families"}</b>
                <span>
                  {Q.verdict}
                  {Q.verdict !== "clear structure" && ": a convenient partition, not separate behaviours"}
                </span>
              </li>
            );
          })}
          <li className={d.matches < 8 ? "caution" : "ok"}>
            <b>{d.matches} matches</b>
            <span>
              {d.matches < 8
                ? "With fewer than 8 matches, treat style numbers as rough."
                : "Enough for passes and long-pass tendencies to be reliable."}
            </span>
          </li>
          {evRows.length > 0 && (
            <li className="info">
              <b>Grades</b>
              <span>
                {`Checked on ${ev!.n_teams} unseen teams: ${ev!.grades?.A ?? 0} A, ${ev!.grades?.B ?? 0} B, ${ev!.grades?.C ?? 0} C, ${ev!.grades?.D ?? 0} D.`}{" "}
                <a href={evidenceHref(d.key)}>Which numbers can you trust?</a>
              </span>
            </li>
          )}
        </ul>
        <p className="small no-print" style={{ marginTop: 14 }}>
          <a href={`#/${encodeURIComponent(d.key)}/compare`}>All {d.ranks.length} measures against the other teams →</a>
        </p>
        <details className="more">
          <summary>How to read this report</summary>
          <div className="layout-2">
            <div className="stack">
              {(["build-up", "advanced"] as const).map((p) => {
                const Q = d.report.phases[p];
                return (
                  <p key={p} className="small">
                    {p}: stability {Q.jaccard_mean.toFixed(2)} against {Q.null_shuffle.toFixed(2)} (shuffled features)
                    and {Q.null_gauss.toFixed(2)} (single Gaussian blob).
                  </p>
                );
              })}
              {d.ranks.some((r) => r.caution) && (
                <ul className="cautions small">
                  {[...new Set(d.ranks.filter((r) => r.caution).map((r) => r.caution!))].map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
              <p className="small">
                Reference teams ({d.references.length}): {d.references.join(", ") || "none"}. They may come from other
                leagues and seasons, so ranks are a rough guide.
              </p>
            </div>
            <div>
              <p className="measure small">
                If you only had <i>n</i> matches of this team, the numbers would typically (90% of the time) differ from
                the ones above by at most:
              </p>
              <div className="table-wrap" style={{ marginTop: 8 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Matches</th>
                      <th>Passes per sequence</th>
                      <th>Long-pass share (points)</th>
                      <th>Shot rate (points)</th>
                      <th>Family share, build-up (points)</th>
                      <th>Family share, advanced (points)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(d.report.reliability).map(([n, v]) => (
                      <tr key={n}>
                        <td>
                          <b>{n}</b>
                        </td>
                        <td>±{v.passes.toFixed(1)}</td>
                        <td>±{(100 * v.long).toFixed(1)}</td>
                        <td>±{(100 * v.shot).toFixed(1)}</td>
                        <td>±{Math.round(100 * v.build_up)}</td>
                        <td>±{Math.round(100 * v.advanced)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div className="layout-2">
            <ul className="read measure">
              <li>
                Families are slices of how this team builds up, fitted on its own matches: they describe tendencies, not
                fixed tactical plans. Names such as B1 are labels, not tactical categories.
              </li>
              <li>
                Stability is the mean best-match Jaccard under bootstrap over matches (stable 0.75 or more, moderate
                0.60-0.75, unstable below). When the structure check says 'slices of a continuum', treat the families as
                a convenient partition, not as separate behaviours.
              </li>
              <li>
                Validation on held-out matches (10 teams): families are reproduced (shares change by at most 10 points)
                and how a sequence starts explains almost all of the predictability; score, home/away, minute and
                previous family added nothing (exploratory).
              </li>
            </ul>
            <ul className="read measure">
              <li>
                The families do <b>not</b> predict whether a sequence ends in a shot better than a one-variable rule
                based on where the sequence ends (families better in 0 of 10 teams, simple rule better in 5 of 10). Read
                them as a description of how the team builds up, not as a better shot predictor.
              </li>
              <li>
                Limits: event data only, no player positions off the ball; the tactical meaning of the families has not
                been validated by coaches; shot rates per family are descriptive, not causal.
              </li>
              <li>
                Computed by repeatedly drawing n matches from this team's season and comparing with all of them. Across
                10 teams (thesis validation), 8 to 10 matches were needed for passes and long-pass tendencies to be
                within half the gap between teams; shot rate and the share of sequences starting in the own half could
                not be told apart between teams reliably even with 15 matches.
              </li>
            </ul>
          </div>
        </details>
        <p className="small no-print" style={{ marginTop: 18 }}>
          Printable sheets from the pipeline:{" "}
          {[
            ["prep", "one-page preparation"],
            ["report", "families and style"],
            ["restarts", "restarts"],
            ["setpieces", "set pieces"],
            ["transitions", "transitions"],
            ["defending", "defending"],
            ["xthreat", "threat"],
          ].map(([k, l], i) => (
            <span key={k}>
              {i ? " · " : ""}
              <a href={`/sheets/${k}_${d.key}.html`} target="_blank" rel="noreferrer">
                {l}
              </a>
            </span>
          ))}
        </p>
      </section>
    </>
  );
}
