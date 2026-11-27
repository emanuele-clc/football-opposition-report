/* The A-D grades: how much each number of the report can be trusted, and why. */
import { useEffect, useRef, useState } from "react";
import { api, type Evidence as EvData, type EvStatement, type Grade, type TeamData, type TrustN } from "../api";
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

/* Why a number got its grade, and after how many matches it can be trusted (exploratory, docs/protocol_trust_n.md).
   Each sentence comes from one number, with the rules of the protocol: D for "teams differ", the lower end of the skill
   interval for "predicts", the matches needed for the last part. No language model. */
function why(r: EvStatement, t?: TrustN): string[] {
  const out: string[] = [];
  const D = r.D ?? null;
  if (D != null)
    out.push(
      D >= 0.7
        ? "Teams differ a lot in this number."
        : D >= 0.5
          ? "Teams differ somewhat in this number."
          : "Teams differ little in this number: it is mostly chance.",
    );
  const lo = r.skill_ci[0];
  out.push(
    lo >= 0.1
      ? "The season so far predicts the next match much better than the league average."
      : lo > 0
        ? "The season so far predicts the next match a little better than the league average."
        : "The season so far does not predict the next match better than the league average.",
  );
  if (t?.flag_uncertain) out.push("This estimate is uncertain on the first matches of a season.");
  if (t?.curve === "below") out.push("It predicts worse than its spread suggests: it may change during the season.");
  return out;
}

function TrustSection({ ev, seen }: { ev: EvData; seen: number }) {
  const T = ev.trust!;
  const S = ev.statements!;
  const order: Grade[] = ["A", "B", "C", "D"];
  const rows = Object.entries(T.statements)
    .filter(([id]) => S[id])
    .sort(
      (a, b) =>
        order.indexOf(S[a[0]].grade) - order.indexOf(S[b[0]].grade) ||
        (a[1].matches_starts ?? 999) - (b[1].matches_starts ?? 999),
    );
  const status = (t: TrustN) =>
    t.matches_reliable != null && seen >= t.matches_reliable
      ? "reliable now"
      : t.matches_starts != null && seen >= t.matches_starts
        ? "use as a hint"
        : "not enough yet";
  const n = (x: number | null) => (x == null ? "not within a season" : `${x} matches`);
  return (
    <section className="section" aria-labelledby="ev-n">
      <div className="section-head">
        <h2 id="ev-n">How many matches do you need?</h2>
        <Explain>{`A number needs enough matches before it says more about the team than about chance. This team has ${seen} matches here.`}</Explain>
      </div>
      <div className="table-wrap">
        <table className="ev-table ev-trust">
          <thead>
            <tr>
              <th>Number</th>
              <th>Says something after</th>
              <th>Reliable after</th>
              <th>With the matches here</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([id, t]) => (
              <tr key={id}>
                <td>
                  <GradeMark g={S[id].grade} /> {NAME[id]}
                  {why(S[id], t).map((s) => (
                    <small key={s}>{s}</small>
                  ))}
                </td>
                <td>{n(t.matches_starts)}</td>
                <td>{n(t.matches_reliable)}</td>
                <td>
                  <b>{status(t)}</b>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 18 }}>
        <Note kind="info" tag="Exploratory">
          {`Not part of the graded check. "Says something" means that half of the difference between teams is style and half is chance; "reliable" means three quarters is style. The numbers come from how much each number differs between teams, and the rule was checked on the first ${T.grid[0]} to ${T.grid[T.grid.length - 1]} matches of the ${T.n_teams} teams (docs/protocol_trust_n.md). One number per type of statement, not per team.`}
        </Note>
      </div>
    </section>
  );
}

/* Does a number change with the style of the next opponent? (exploratory, docs/protocol_opponent_model.md)
   Teams grouped in three per league by how they attack or defend (k-means on the whole season). "Changes" = the model with
   the opponent's group forecast the second half of the season better than the season so far. Group effects: how far the
   league's teams moved, on average, against each group. Nothing is recomputed here. */
const SHARE = new Set(["S03", "S04", "S05", "R09", "R10", "R11", "R12", "R13", "P15", "P16", "P17", "T19", "T20", "T21", "T22", "D25", "A32"]);
const TWO = new Set(["D28", "A30", "A31"]);
const eff = (id: string, x: number) =>
  SHARE.has(id)
    ? `${x >= 0 ? "+" : "−"}${Math.abs(x * 100).toFixed(1)} pts`
    : `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(TWO.has(id) ? 2 : 1)}`;

function StyleSection({ ev, team, period }: { ev: EvData; team: string; period: string }) {
  const T = ev.style!;
  const S = ev.statements!;
  // groups are from the 2015/16 season: only a team of that season is placed in one
  const season1516 = period.startsWith("2015-") && period.includes("2016-");
  const league = season1516
    ? Object.entries(T.leagues).find(([, l]) => l.attack.some((g) => g.teams.includes(team)))
    : undefined;
  const blocks = [
    { style: "attack" as const, title: "Without the ball: against how the opponent attacks", by: "passes per sequence" },
    { style: "defence" as const, title: "With the ball: against how the opponent defends", by: "PPDA" },
  ];
  return (
    <section className="section" aria-labelledby="ev-s">
      <div className="section-head">
        <h2 id="ev-s">Does it change with the opponent's style?</h2>
        <Explain>
          In each league the teams were put in three groups by how they attack, and in three groups by how they defend.
          For each number: does knowing the group of the next opponent forecast the match better than the season so
          far? If yes, read the number together with the next opponent.
        </Explain>
      </div>
      {blocks.map(({ style, title, by }) => {
        const groups = league?.[1][style];
        const rows = Object.entries(T.statements)
          .filter(([id, r]) => r.style === style && S[id])
          .sort((a, b) => Number(b[1].changes) - Number(a[1].changes) || b[1].improvement - a[1].improvement);
        return (
          <div key={style} style={{ marginTop: 18 }}>
            <h3>{title}</h3>
            <div className="table-wrap">
              <table className="ev-table ev-style">
                <thead>
                  <tr>
                    <th>Number</th>
                    <th>Answer</th>
                    {groups?.map((g) => (
                      <th key={g.label}>{`vs ${g.label}`}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(([id, r]) => (
                    <tr key={id}>
                      <td>
                        <GradeMark g={S[id].grade} /> {NAME[id]}
                      </td>
                      <td>
                        <b>{r.changes ? "changes with the style" : "stable"}</b>
                        {r.changes && <small>{`forecast error ${Math.round(r.improvement * 100)}% lower`}</small>}
                        {T.wyscout && (
                          <small>
                            {r.wyscout_changes == null
                              ? "not checked on Wyscout"
                              : r.wyscout_changes === r.changes
                                ? "same on Wyscout 2017/18"
                                : "different on Wyscout 2017/18"}
                          </small>
                        )}
                      </td>
                      {groups?.map((g) => (
                        <td key={g.label}>{r.changes ? eff(id, g.effects[id]) : "·"}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {groups && (
              <ul className="ev-style-groups small">
                {groups.map((g) => (
                  <li key={g.label}>
                    <b>{`${g.label}:`}</b>{" "}
                    {g.teams.map((t, i) => (
                      <span key={t}>
                        {t === team ? <b>{t}</b> : t}
                        {i < g.teams.length - 1 ? ", " : ""}
                      </span>
                    ))}
                  </li>
                ))}
              </ul>
            )}
            {groups && (
              <p className="small s-muted">{`${league![0]} 2015/16, whole season. Groups named by ${by}. Columns: how far the teams of the league moved, on average, against each group.`}</p>
            )}
          </div>
        );
      })}
      <div style={{ marginTop: 18 }}>
        <Note kind="info" tag="Exploratory">
          {`Not part of the graded check. Groups: k-means with 3 groups per league, remade at every date with past matches only; ${T.n_teams} teams, StatsBomb 2015/16, compared on the second half of the season (docs/protocol_opponent_model.md). The groups help to read a number, not to forecast it: the forecast on the Game plan keeps the single opponent, because the groups were worse than it for ${T.worse_than_single_opponent} of ${T.n_statements} numbers. PPDA changes most, partly by construction: it counts the opponent's passes.${T.wyscout ? ` Repeated with the same method on Wyscout 2017/18 (${T.wyscout.n_teams} teams, docs/protocol_opponent_model_wyscout.md): same answer for ${T.wyscout.same} of ${T.wyscout.of} numbers, just at the threshold fixed in advance; the numbers that differ are mostly restarts and corners.` : ""}`}
        </Note>
      </div>
    </section>
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
          Run <code>src/analysis/evidence_grade.py</code> (StatsBomb) or <code>src/analysis/evidence_grade_wyscout.py</code>{" "}
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

      <details className="more section">
        <summary>More detail: how many matches you need, the opponent's style, the other provider, how we checked</summary>
      {ev.trust && <TrustSection ev={ev} seen={d.matches} />}
      {ev.style && <StyleSection ev={ev} team={d.team} period={d.period} />}

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

      </details>

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
