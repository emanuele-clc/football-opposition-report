import { useEffect, useRef, useState } from "react";
import { api, type Evidence as EvData, type EvStatement, type Grade, type TeamData } from "../api";
import { Explain, GRADE_SAYS, GRADE_TITLE, GradeMark, Note, plain } from "../charts";
import { pc } from "../format";
import { PROVIDER } from "../provider";

/* Which numbers of the report can be trusted: grades of the evidence study (docs/protocol_evidence_grade.md),
   read from the results file of the provider in use (StatsBomb: evidence_grade_corrected.json, Wyscout: evidence_grade_wyscout.json),
   with the letter the same statement got on the other provider. Plain words first, the technical map and table on demand. Nothing is recomputed here. */
const NAME: Record<string, string> = {
  S01: "Sequences per match",
  S02: "Passes per sequence",
  S03: "Long passes (share)",
  S04: "Sequences starting in own half",
  S05: "Sequences ending in a shot",
  S06: "Length of sequences (seconds)",
  F07: "Build-up family shares (B1, B2…)",
  F08: "Advanced family shares (A1, A2…)",
  R09: "Goal kicks played short",
  R10: "Goal kicks reaching the opponent half",
  R11: "Goal kicks that end in own half",
  R12: "Keeper distributions played short",
  R13: "Throw-ins in own half that end there",
  P14: "Corners per match",
  P15: "Corners played short",
  P16: "Corners to the far post",
  P17: "Corners ending in a shot",
  T18: "Balls lost per match",
  T19: "Balls lost in own third",
  T20: "Ball won back within 5 s (counter-press)",
  T21: "Balls won in the final third",
  T22: "Balls won followed by a shot",
  D23: "PPDA (pressing intensity)",
  D24: "Pressures per match",
  D25: "Pressures in the final third",
  D26: "How high they defend",
  D27: "Shots conceded per match",
  D28: "xG conceded per match",
  A29: "Shots per match",
  A30: "xG per match",
  A31: "xT per match (dangerous passes and carries)",
  A32: "Passes completed under pressure",
  K33: "Main build-up receiver",
  K34: "Main corner taker",
};
const GRADES: Grade[] = ["A", "B", "C", "D"];
const PNAME = { statsbomb: "StatsBomb", wyscout: "Wyscout" } as const;
const OTHER = PROVIDER === "statsbomb" ? "wyscout" : "statsbomb";
/* What each provider's grades rest on (results files and protocols). */
const BASIS = {
  statsbomb: "StatsBomb Open Data, 2015/16, four leagues",
  wyscout: "Wyscout public data, 2017/18, five leagues",
} as const;
const WHY_MISSING: Record<string, string> = {
  "needs pressures": "no pressures in this data",
  "needs xG": "no xG in this data",
};
const s2 = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(2)}`;

/* Expert map: x = tells teams apart (discrimination), y = beats the league average for the next match (forecast skill, with its 95% interval). */
const X0 = 0.3,
  X1 = 1,
  Y0 = -0.12,
  Y1 = 0.42,
  W = 640,
  H = 380,
  L = 54,
  R = 14,
  T = 14,
  B = 46;
const px = (d: number) => L + ((Math.min(Math.max(d, X0), X1) - X0) / (X1 - X0)) * (W - L - R);
const py = (s: number) => T + ((Y1 - Math.min(Math.max(s, Y0), Y1)) / (Y1 - Y0)) * (H - T - B);

function EvidenceMap({
  rows,
  hot,
  setHot,
}: {
  rows: [string, EvStatement][];
  hot: string;
  setHot: (id: string) => void;
}) {
  const pts = rows.filter(([, r]) => r.D != null);
  const named = (id: string, r: EvStatement) => id === hot || r.skill_ci[0] >= 0.1 || r.grade === "D";
  const h = pts.find(([id]) => id === hot);
  return (
    <svg
      className="ev-map"
      viewBox={`0 0 ${W} ${H}`}
      role="group"
      aria-label="Every graded number placed by how well it tells teams apart and how well it forecasts the next match"
    >
      {[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].map((v) => (
        <text key={v} className="tick" x={px(v)} y={H - B + 18} textAnchor="middle">
          {v.toFixed(1)}
        </text>
      ))}
      {[-0.1, 0, 0.1, 0.2, 0.3, 0.4].map((v) => (
        <text key={v} className="tick" x={L - 8} y={py(v) + 4} textAnchor="end">
          {v.toFixed(1)}
        </text>
      ))}
      <line className="ref zero" x1={L} x2={W - R} y1={py(0)} y2={py(0)} />
      <line className="ref" x1={L} x2={W - R} y1={py(0.1)} y2={py(0.1)} />
      <line className="ref" x1={px(0.5)} x2={px(0.5)} y1={T} y2={H - B} />
      <line className="ref" x1={px(0.7)} x2={px(0.7)} y1={T} y2={H - B} />
      <text className="ref-l" x={W - R - 4} y={py(0) - 6} textAnchor="end">
        no better than the league average
      </text>
      <text className="ref-l" x={px(0.7) + 5} y={T + 11}>
        high
      </text>
      <text className="ref-l" x={px(0.5) + 5} y={T + 11}>
        medium
      </text>
      <text className="axis" x={(L + W - R) / 2} y={H - 6} textAnchor="middle">
        Tells teams apart over a season (discrimination) →
      </text>
      <text className="axis" transform={`translate(13 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle">
        Forecasts the next match (skill) →
      </text>
      {pts.map(([id, r]) => (
        <g
          key={id}
          className={`pt g-${r.grade}${id === hot ? " hot" : ""}`}
          tabIndex={0}
          role="img"
          aria-label={`${NAME[id]}: grade ${r.grade}, forecast skill ${s2(r.skill)}, discrimination ${r.D!.toFixed(2)}`}
          onMouseEnter={() => setHot(id)}
          onFocus={() => setHot(id)}
        >
          <line className="ci" x1={px(r.D!)} x2={px(r.D!)} y1={py(r.skill_ci[0])} y2={py(r.skill_ci[1])} />
          <circle cx={px(r.D!)} cy={py(r.skill)} r={id === hot ? 8 : 6} />
          {named(id, r) && (
            <text className="pt-l" x={px(r.D!) + 10} y={py(r.skill) + 4}>
              {id}
            </text>
          )}
        </g>
      ))}
      {h && (
        <text
          className="pt-name"
          x={Math.min(px(h[1].D!), W - R - 4)}
          y={Math.max(py(h[1].skill_ci[1]) - 10, T + 28)}
          textAnchor={px(h[1].D!) > W - 200 ? "end" : "middle"}
        >
          {NAME[h[0]]}
        </text>
      )}
    </svg>
  );
}

export default function Evidence({ d, focus }: { d: TeamData; focus: string }) {
  const [ev, setEv] = useState<EvData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hot, setHot] = useState(focus);
  const itemRef = useRef<Record<string, HTMLLIElement | null>>({});
  useEffect(() => {
    api
      .evidence()
      .then(setEv)
      .catch((e) => setErr(e.message));
  }, []);
  useEffect(() => {
    if (!ev || !focus) return;
    setHot(focus);
    itemRef.current[focus]?.scrollIntoView({
      block: "center",
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    });
  }, [ev, focus]);

  if (err)
    return (
      <div className="state">
        <h2>Could not load the evidence grades</h2>
        <p>{err}</p>
      </div>
    );
  if (!ev)
    return (
      <div aria-busy="true">
        <div className="skeleton" style={{ height: 60, width: "45%" }} />
        <div className="skeleton" style={{ height: 380 }} />
      </div>
    );
  if (!ev.available || !ev.statements) {
    return (
      <div className="state">
        <h2>No evidence grades yet</h2>
        <p className="small">
          Run <code>src/week4/evidence_grade.py</code> (StatsBomb) or <code>src/week4/evidence_grade_wyscout.py</code>{" "}
          (Wyscout) as described in the protocols in docs/.
        </p>
      </div>
    );
  }
  const S = ev.statements,
    rows = Object.entries(S);
  const byGrade = (g: Grade) => rows.filter(([, r]) => r.grade === g).sort((a, b) => b[1].skill - a[1].skill);
  const helps = rows.filter(([, r]) => r.forecast !== "none").length;
  const apart = rows.filter(([, r]) => r.discrimination === "high" || r.discrimination === "medium").length,
    withD = rows.filter(([, r]) => r.discrimination !== "n/a").length;
  const l5worse = rows.filter(([, r]) => r.last5_verdict === "season better").length;
  const pv = Object.values(ev.provider ?? {}).filter((p) => p.label !== "not testable");
  const prov = ev.provider ? { same: pv.filter((p) => p.label === "same in Wyscout").length, total: pv.length } : null;
  const cross = ev.cross ?? null;
  const other = (id: string): Grade | null => cross?.statements[id]?.[OTHER] ?? null;
  const moved = cross ? Object.values(cross.statements).filter((c) => c.statsbomb !== c.wyscout).length : 0;
  const untestable = Object.entries(ev.not_testable ?? {});
  const cov = rows.map(([, r]) => r.coverage_80),
    sc = Object.entries(ev.sanity_checks ?? {}),
    dropped = Object.entries(ev.dropped ?? {});

  return (
    <>
      <section aria-labelledby="ev-h">
        <div className="section-head">
          <h2 id="ev-h">Which numbers can you trust?</h2>
          <Explain>{`We checked every number in this report on ${ev.n_teams} teams it had never seen (${BASIS[PROVIDER]}). A number gets a good grade if it really differs between teams and helps you guess what a team will do in its next match.`}</Explain>
        </div>
        <div className="ev-buckets">
          {GRADES.map((g) => (
            <section key={g} className="sticker pad ev-bucket" style={plain} aria-labelledby={`ev-b-${g}`}>
              <div className="ev-bucket-head">
                <GradeMark g={g} />
                <div>
                  <h3 id={`ev-b-${g}`}>{GRADE_TITLE[g]}</h3>
                  <p className="small s-muted">{`${byGrade(g).length} of ${rows.length} numbers`}</p>
                </div>
              </div>
              <p className="ev-bucket-says">{GRADE_SAYS[g]}</p>
              <ul className="ev-items">
                {byGrade(g).map(([id]) => (
                  <li
                    key={id}
                    ref={(el) => {
                      itemRef.current[id] = el;
                    }}
                    className={id === hot ? "sel" : undefined}
                  >
                    {NAME[id]}
                    {ev.shown_in_app?.[id] && <span className="ev-inapp">in this app</span>}
                    {other(id) && other(id) !== g && (
                      <span className="ev-other" title={`Graded ${other(id)} on ${PNAME[OTHER]} data`}>
                        {PNAME[OTHER]} <GradeMark g={other(id)!} />
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        {untestable.length > 0 && (
          <p className="ev-untestable small">
            <b>{`Not in ${PNAME[PROVIDER]} data, so not graded here:`}</b>{" "}
            {untestable.map(([id, why]) => `${NAME[id]} (${WHY_MISSING[why] ?? why})`).join(" · ")}
          </p>
        )}
      </section>

      {cross && (
        <section className="section" aria-labelledby="ev-x">
          <div className="section-head">
            <h2 id="ev-x">Same grade with the other provider?</h2>
            <Explain>
              The same check, with the same rules, was run on a second data provider: StatsBomb 2015/16 (70 teams) and
              Wyscout 2017/18 (96 teams). A grade says how far a type of number can be trusted, not what its value is.
            </Explain>
          </div>
          <div className="ev-cross">
            <div className="ev-cross-fig" aria-label={`${cross.same} of ${cross.of} numbers keep their grade`}>
              <b>{cross.same}</b>
              <span>{`of ${cross.of}`}</span>
            </div>
            <div className="stack">
              <p>{`${cross.same} of ${cross.of} numbers get the same grade on both providers, and none moves by two letters. The ${moved} that change move by one letter, almost all on the line between a weak forecast and none.`}</p>
              <Note kind="caution" tag="Values">
                {ev.provider
                  ? `The grades travel, the values do not: on the same ${ev.provider_matches} Barcelona matches only ${prov?.same} of ${prov?.total} numbers came out the same in both providers. Compare numbers and ranks only within one provider, which is why this app never mixes them.`
                  : "The grades travel, the values do not: each provider defines events in its own way. Compare numbers and ranks only within one provider, which is why this app never mixes them."}
              </Note>
              <p className="small s-muted">
                Provider, season, leagues and teams all change between the two checks: a changed letter cannot be
                pinned on one of them. Protocol written and pushed before the run: docs/protocol_evidence_grade_wyscout.md.
              </p>
            </div>
          </div>
        </section>
      )}

      <section className="section" aria-labelledby="ev-m">
        <div className="section-head">
          <h2 id="ev-m">What this means</h2>
        </div>
        <ol className="ev-steps">
          <li>
            <span className="dot" aria-hidden="true">
              1
            </span>
            <p>{`Most numbers (${apart} of ${withD}) really differ between teams. But only ${helps} of ${rows.length} help you guess the next match, and only ${ev.grades?.A ?? 0} clearly. Knowing a team's season is not the same as knowing what it will do on Saturday.`}</p>
          </li>
          <li>
            <span className="dot" aria-hidden="true">
              2
            </span>
            <p>{`The last 5 matches mislead: the whole season guessed the next match better for ${l5worse} of ${rows.length} numbers. If something changed in the last 5, check it on video before you believe it.`}</p>
          </li>
          <li>
            <span className="dot" aria-hidden="true">
              3
            </span>
            <p>{`The ranges the report shows are honest: a range meant to hold 8 times out of 10 held between ${pc(Math.min(...cov))} and ${pc(Math.max(...cov))} of the time.`}</p>
          </li>
          {prov && !cross && (
            <li>
              <span className="dot" aria-hidden="true">
                4
              </span>
              <p>{`With another data provider (Wyscout, same ${ev.provider_matches} Barcelona matches) only ${prov.same} of ${prov.total} numbers came out the same. Compare numbers only between data from the same provider. One team only, so read this as a warning, not a measure.`}</p>
            </li>
          )}
        </ol>
      </section>

      <section className="section" aria-labelledby="ev-how">
        <div className="section-head">
          <h2 id="ev-how">How we checked</h2>
        </div>
        <ol className="ev-steps">
          <li>
            <span className="dot" aria-hidden="true">
              1
            </span>
            <p>
              Before each match of a team, we wrote down two guesses for the match: the report's guess, from the matches
              played so far (for example "9.5 passes per sequence"), and the guess of someone who knows nothing about
              the team: the league average (for example 8.0).
            </p>
          </li>
          <li>
            <span className="dot" aria-hidden="true">
              2
            </span>
            <p>{`After the match we looked at which guess was closer. We did this about ${(Math.round(Math.max(...rows.filter(([id]) => !id.startsWith("F")).map(([, r]) => r.forecasts)) / 100) * 100).toLocaleString("en")} times, on ${ev.n_teams} teams the report had never seen.`}</p>
          </li>
          <li>
            <span className="dot" aria-hidden="true">
              3
            </span>
            <p>
              We also checked whether the differences between teams are real or just chance. The rules were written down
              and published before the check, and the check was run once.
            </p>
          </li>
        </ol>
        <div style={{ marginTop: 18 }}>
          <Note kind="caution" tag="Limits">
            {PROVIDER === "wyscout"
              ? "One season (2017/18) of Wyscout public data, with possessions rebuilt from the order of events. "
              : "One season (2015/16) of StatsBomb data. "}
            The check does not take the opponent into account, so a good analyst can guess better: the grades are a
            minimum. The grade is for the type of number, not for one team.
          </Note>
        </div>
      </section>

      <details className="more section ev-expert">
        <summary>Details for experts: map, full table, notes</summary>
        <div className="layout-split" style={{ marginTop: 18 }}>
          <figure className="sticker pad ev-fig">
            <span className="no">{`${rows.length} numbers`}</span>
            <EvidenceMap rows={rows} hot={hot} setHot={setHot} />
            <figcaption className="small s-muted">
              Each mark is one type of number with its 95% interval. The grade uses the lower end of the interval: above
              0.10 is a strong forecast, above 0 a weak one. Families (F07, F08) are not on the map: each team has its
              own families, so they have no common value to compare between teams.
            </figcaption>
          </figure>
          <div className="stack">
            <p className="small">
              Skill: 0 = no better than assuming an average team of the league, 1 = perfect; it is computed match by
              match from the 6th match of each team. Tells teams apart: share of the differences between teams that is
              not sampling noise (0.7 or more high, 0.5 medium). Interval held: how often the 80% interval contained the
              next match. Matches needed: to be within half the typical gap between teams.
            </p>
            {!ev.provider && !cross && (
              <Note kind="caution" tag="Provider">
                The check with a second provider has not been run yet: the grades rest on one provider's definitions
                only.
              </Note>
            )}
            <Note kind="caution" tag="Thresholds">
              The thresholds (0.10 for the forecast, 0.5 and 0.7 for telling teams apart) are conventions written down
              before the run, not derived from the data.
            </Note>
            {sc
              .filter(([, ok]) => !ok)
              .map(([k]) => (
                <Note key={k} kind="caution" tag="Expectation failed">
                  {k.startsWith("SC1")
                    ? `Before the run we wrote that the counter-press share would not tell teams apart. It does (${S.T20?.D?.toFixed(2) ?? "–"}): differences between teams are small but real over a season. It still does not forecast the next match. Reported as it came.`
                    : k}
                </Note>
              ))}
            {dropped.length > 0 && (
              <Note
                kind="info"
                tag="Correction"
              >{`${dropped.map(([t, m]) => `${m.length} matches of ${t}`).join(" and ")} were left out: in those event files StatsBomb names the team differently, so its own events were missing (protocol, note 1). The run before this correction is kept unedited in the repository.`}</Note>
            )}
            <p className="small">{`Protocol written and pushed before the run: docs/protocol_evidence_grade.md. Results: ${ev.source}.`}</p>
          </div>
        </div>
        <div className="table-wrap" style={{ marginTop: 24 }}>
          <table className="ev-table">
            <thead>
              <tr>
                <th>Number</th>
                <th>Next match: skill (95%)</th>
                <th>Tells teams apart</th>
                <th>80% interval held</th>
                <th>Matches needed</th>
                <th>Last 5 vs season</th>
                {cross && <th>{`Grade on ${PNAME[OTHER]}`}</th>}
                {ev.provider && <th>Same value in both (Barcelona)</th>}
              </tr>
            </thead>
            {GRADES.map(
              (g) =>
                byGrade(g).length > 0 && (
                  <tbody key={g}>
                    <tr className="grp">
                      <th colSpan={6 + (ev.provider ? 1 : 0) + (cross ? 1 : 0)}>
                        <GradeMark g={g} /> {GRADE_TITLE[g]}
                      </th>
                    </tr>
                    {byGrade(g).map(([id, r]) => (
                      <tr key={id} className={id === hot ? "sel" : undefined} onMouseEnter={() => setHot(id)}>
                        <td>
                          <span className="ev-id">{id}</span>
                          {NAME[id]}
                          {ev.shown_in_app?.[id] && <small>{`In this app: ${ev.shown_in_app[id].join(", ")}`}</small>}
                        </td>
                        <td>
                          <b>{s2(r.skill)}</b>{" "}
                          <small className="inl">{`[${s2(r.skill_ci[0])}, ${s2(r.skill_ci[1])}]`}</small>
                          <small>{r.forecast}</small>
                        </td>
                        <td>
                          {r.D == null ? (
                            "—"
                          ) : (
                            <>
                              <b>{r.D.toFixed(2)}</b>
                              <small>{r.discrimination}</small>
                            </>
                          )}
                        </td>
                        <td>
                          <b>{pc(r.coverage_80)}</b>
                          <small>{r.calibration}</small>
                        </td>
                        <td>{String(r.matches_needed) === "n/a" ? "—" : String(r.matches_needed)}</td>
                        <td>{r.last5_verdict}</td>
                        {cross && (
                          <td>{other(id) ? <GradeMark g={other(id)!} /> : PROVIDER === "statsbomb" ? "not testable" : "—"}</td>
                        )}
                        {ev.provider && (
                          <td>
                            {ev.provider[id]?.label ?? "—"}
                            {ev.provider[id]?.seen_before && <small>seen before</small>}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                ),
            )}
          </table>
        </div>
      </details>
    </>
  );
}
