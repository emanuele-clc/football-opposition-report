import { useEffect, useMemo, useState } from "react";
import { api, type ClipRef, type ClipRow, type ReviewData, type TeamData } from "../api";
import { FamilyLanes, Note, PlayIcon, Replay, rib } from "../charts";
import { clock, pc } from "../format";
import { clipId, useClips } from "../useClips";
import { famLine } from "./Overview";

const VERDICTS = ["yes", "partly", "no"] as const;
const famIdx = (f: string) => {
  const m = /^[AB](\d+)$/.exec(f);
  return m ? Number(m[1]) - 1 : 0;
};
const setAt = <T,>(arr: T[], i: number, v: T) => arr.map((x, j) => (j === i ? v : x));
const N_LEARN = 5;
/* Examples shown before judging: other sequences of the same family (never the ones to judge, which are its most
   typical ones), spread evenly over the season so the reviewer sees the family's range, not only its centre. */
function learnSet(all: ClipRow[] | null, fam: string, judged: Set<string>): ClipRef[] {
  const pool = (all ?? [])
    .filter((r) => r.family === fam && !judged.has(clipId(r)))
    .sort((a, b) => a.date.localeCompare(b.date) || a.half - b.half || a.minute - b.minute);
  const n = Math.min(N_LEARN, pool.length);
  return Array.from({ length: n }, (_, k) => pool[Math.floor(((k + 0.5) * pool.length) / n)]).map((r, k) => ({
    match: r.match,
    half: r.half,
    minute: r.minute,
    second: r.second,
    title: `${fam} example ${k + 1}`,
    detail: `${fam} example ${k + 1} of ${n} · vs ${r.opponent}, ${r.date}, half ${r.half} ${clock(r.minute, r.second)} · ${r.start_type}`,
  }));
}

export default function Review({ d, events }: { d: TeamData; events: boolean }) {
  const [data, setData] = useState<ReviewData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [verdicts, setVerdicts] = useState<string[]>([]);
  const [comments, setComments] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [reviewer, setReviewer] = useState("");
  const [role, setRole] = useState("");
  const [sel, setSel] = useState(0);
  const [saved, setSaved] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [learning, setLearning] = useState(true);
  const [learnIdx, setLearnIdx] = useState(0);
  const [seen, setSeen] = useState<Set<string>>(() => new Set());
  const { rows: all } = useClips(d.key, "sequences");

  useEffect(() => {
    api
      .review(d.key)
      .then((r) => {
        setData(r);
        setVerdicts(r.rows.map((x) => x.coherent_with_family ?? ""));
        setComments(r.rows.map((x) => x.comment ?? ""));
        setAnswers(r.questions.map((q) => r.answers?.questions.find((a) => a.question === q)?.answer ?? ""));
        setReviewer(r.answers?.reviewer ?? "");
        setRole(r.answers?.role ?? "");
        if (r.filled_file)
          setSaved(`Loaded the saved review (${r.filled_file}${r.answers?.saved ? `, ${r.answers.saved}` : ""}).`);
      })
      .catch((e) => setErr(e.message));
  }, [d.key]);

  const refs: ClipRef[] = useMemo(
    () =>
      (data?.rows ?? []).map((r) => ({
        match: Number(r.match ?? 0),
        half: Number(r.half),
        minute: Number(r.minute),
        second: Number(r.second),
        title: r.family,
        detail: `${r.family} · vs ${r.opponent}, ${r.date}, half ${r.half} ${clock(Number(r.minute), Number(r.second))} · ${r.start_type}`,
      })),
    [data],
  );
  const summary = useMemo(() => {
    const by: Record<string, Record<string, number>> = {};
    (data?.rows ?? []).forEach((r, i) => {
      const v = verdicts[i];
      if (!v) return;
      by[r.family] ??= { yes: 0, partly: 0, no: 0 };
      by[r.family][v]++;
    });
    return by;
  }, [data, verdicts]);
  const done = verdicts.filter(Boolean).length;
  const fam = data?.rows[sel]?.family ?? "";
  const judged = useMemo(() => new Set(refs.map(clipId)), [refs]);
  const learn = useMemo(() => learnSet(all, fam, judged), [all, fam, judged]);
  const phase = fam.startsWith("A") ? "advanced" : "build-up";
  const famData = d.report.phases[phase].families.find((f) => f.fam === fam);
  /* Choosing a sequence of a family not seen yet shows that family's examples first; afterwards the sequence itself. */
  const pick = (i: number, judge = false) => {
    const f = data?.rows[i]?.family ?? "";
    setSel(i);
    setLearnIdx(0);
    setLearning(!judge && !seen.has(f));
  };
  const showing = learning && learn.length > 0;

  if (err)
    return (
      <div className="state">
        <h2>No review sheet</h2>
        <p>{err}</p>
      </div>
    );
  if (!data)
    return (
      <div aria-busy="true">
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  const save = async () => {
    setSaving(true);
    setSaved(null);
    try {
      const r = await api.saveReview(d.key, { verdicts, comments, answers, reviewer, role });
      setSaved(
        `Saved ${r.answered} of ${verdicts.length} answers to ${r.saved} in the data folder. To summarise: python -X utf8 src/report/summarize_review.py followed by that file's path.`,
      );
    } catch (e) {
      setSaved((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="section-head">
        <h2>Analyst review</h2>
      </div>
      <p className="measure" style={{ marginBottom: 18 }}>
        This page is for a person with football experience (video analyst, coach), not for match preparation. The
        families were made by the computer and no football expert has checked them yet: here one person checks them, in
        about 30 minutes, with you running the app.
      </p>
      <ol className="ev-steps review-steps">
        <li>
          <span className="dot" aria-hidden="true">
            1
          </span>
          <p>
            <b>Write who is reviewing</b> (role and years of experience are enough) in the two fields below.
          </p>
        </li>
        <li>
          <span className="dot" aria-hidden="true">
            2
          </span>
          <p>
            <b>First the examples, then the judgement.</b> Click a row: on the right, the box says what its family is
            and the replay shows {N_LEARN} other sequences of that family. Then switch to the sequence to judge and ask:
            does it fit its family? Click yes, partly or no; for partly and no, write what does not fit.
          </p>
        </li>
        <li>
          <span className="dot" aria-hidden="true">
            3
          </span>
          <p>
            <b>Answer the five questions</b> at the bottom of the page in the reviewer's own words, then click Save
            review. The answers are saved in the data folder; the report does not change.
          </p>
        </li>
      </ol>
      <div className="filters">
        <label className="field">
          Reviewer
          <input
            className="text-in"
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            placeholder="Name"
          />
        </label>
        <label className="field">
          Role and experience
          <input
            className="text-in"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. video analyst, 3 years"
          />
        </label>
        <span style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <span className="small">
            {done} of {verdicts.length} sequences marked
          </span>
          <button className="btn" type="button" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save review"}
          </button>
        </span>
      </div>
      {saved && (
        <div style={{ marginBottom: 14 }}>
          <Note kind="info" tag="Review">
            {saved}
          </Note>
        </div>
      )}

      <div className="layout-split layout-clips">
        <div className="table-wrap">
          <table className="clip-table">
            <thead>
              <tr>
                <th></th>
                <th className="l">Family</th>
                <th className="l">Match</th>
                <th>Half, time</th>
                <th>Passes</th>
                <th>Shot</th>
                <th className="l">Fits the family?</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r, i) => (
                <tr key={i} className={`clickable${i === sel ? " sel" : ""}`} onClick={() => pick(i)}>
                  <td>
                    <button
                      type="button"
                      className="play-btn"
                      aria-label={`Replay sequence ${i + 1}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        pick(i);
                      }}
                    >
                      {PlayIcon}
                    </button>
                  </td>
                  <td className="l">
                    <span className="chip" style={rib(famIdx(r.family), r.family)}>
                      {r.family}
                    </span>
                  </td>
                  <td className="l">
                    {r.opponent}
                    <small>
                      {r.date} · {r.start_type}
                    </small>
                  </td>
                  <td>
                    {r.half}, {clock(Number(r.minute), Number(r.second))}
                  </td>
                  <td>{r.passes}</td>
                  <td>{r.ended_in_shot === "1" ? "yes" : ""}</td>
                  <td className="l" onClick={(e) => e.stopPropagation()}>
                    <div className="verdict" role="group" aria-label={`Sequence ${i + 1}: fits ${r.family}?`}>
                      {VERDICTS.map((v) => (
                        <button
                          key={v}
                          type="button"
                          data-v={v}
                          aria-pressed={verdicts[i] === v}
                          onClick={() => setVerdicts(setAt(verdicts, i, verdicts[i] === v ? "" : v))}
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                    {verdicts[i] && verdicts[i] !== "yes" && (
                      <input
                        className="text-in small-in"
                        value={comments[i]}
                        onChange={(e) => setComments(setAt(comments, i, e.target.value))}
                        placeholder="What does not fit?"
                        aria-label={`Comment on sequence ${i + 1}`}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <aside style={{ position: "sticky", top: 84 }}>
          {famData && (
            <div className="sticker pad fam-guide" style={{ marginBottom: 22 }}>
              <h3>What {fam} is</h3>
              <p>
                {famLine(famData)}. {pc(famData.share)} of {phase} sequences ({famData.n}).
              </p>
              <div className="pitch-wrap">
                <FamilyLanes families={d.report.phases[phase].families} pick={fam} />
              </div>
              <p className="s-muted" style={{ fontSize: 12.5 }}>
                Average of all {famData.n} sequences of {fam}, computed by the program; the bars show where each family
                starts and ends.
              </p>
            </div>
          )}
          <div className="sticker" style={rib(famIdx(fam), fam)}>
            <span className="no">{fam}</span>
            <div className="sticker-top no-print">
              <div className="seg-toggle" role="group" aria-label="What to replay">
                <button
                  type="button"
                  aria-pressed={showing}
                  disabled={!learn.length}
                  onClick={() => {
                    setLearning(true);
                    setLearnIdx(0);
                  }}
                >
                  1 · Examples of {fam}
                </button>
                <button
                  type="button"
                  aria-pressed={!showing}
                  onClick={() => {
                    setLearning(false);
                    setSeen(new Set(seen).add(fam));
                  }}
                >
                  2 · Sequence to judge
                </button>
              </div>
            </div>
            {showing && events ? (
              <>
                <Replay teamKey={d.key} clips={learn} index={learnIdx} onIndex={setLearnIdx} />
                <div className="replay-cap">
                  <div>
                    <p>
                      {learn[learnIdx]?.detail}. Other sequences of {fam}, not the ones you judge: watch a few to see
                      what the family looks like.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="ctl primary"
                    onClick={() => {
                      setLearning(false);
                      setSeen(new Set(seen).add(fam));
                    }}
                  >
                    Now judge the sequence
                  </button>
                </div>
              </>
            ) : events && refs[sel]?.match ? (
              <Replay teamKey={d.key} clips={refs} index={sel} onIndex={(i) => pick(i, true)} />
            ) : (
              <div className="note info" style={{ margin: 14 }}>
                <span className="tag">Replays</span>Replays need the raw event files; use the video with the times in
                the table.
              </div>
            )}
            {!showing && refs[sel] && (
              <div className="replay-cap">
                <p>
                  {refs[sel].detail}. Check it on video too: the replay shows the events, not the players off the ball.
                </p>
              </div>
            )}
          </div>
          {Object.keys(summary).length > 0 && (
            <div className="sticker pad" style={{ marginTop: 16 }}>
              <h3>So far</h3>
              <table style={{ marginTop: 8 }}>
                <thead>
                  <tr>
                    <th>Family</th>
                    <th>yes</th>
                    <th>partly</th>
                    <th>no</th>
                    <th>yes or partly</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary)
                    .sort()
                    .map(([f, c]) => {
                      const n = c.yes + c.partly + c.no;
                      return (
                        <tr key={f}>
                          <td>
                            <span className="chip" style={rib(famIdx(f), f)}>
                              {f}
                            </span>
                          </td>
                          <td>{c.yes}</td>
                          <td>{c.partly}</td>
                          <td>{c.no}</td>
                          <td>
                            <b>{pc((c.yes + c.partly) / n)}</b>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
              <p className="s-muted" style={{ fontSize: 12.5, marginTop: 8 }}>
                Descriptive: with 3 sequences per family it is not a precise estimate.
              </p>
            </div>
          )}
        </aside>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Part 2: five questions</h2>
        </div>
        <div className="layout-2">
          {data.questions.map((q, i) => (
            <label key={i} className="sticker pad q-card">
              <span className="q-no">{i + 1}</span>
              <span className="q-text">{q}</span>
              <textarea
                value={answers[i] ?? ""}
                onChange={(e) => setAnswers(setAt(answers, i, e.target.value))}
                rows={4}
              />
            </label>
          ))}
        </div>
        <p style={{ marginTop: 18 }}>
          <button className="btn" type="button" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save review"}
          </button>
        </p>
      </section>
    </>
  );
}
