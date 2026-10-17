import { useEffect, useMemo, useState } from "react";
import { api, type ClipRef, type ReviewData, type TeamData } from "../api";
import { Note, PlayIcon, Replay, rib } from "../charts";
import { clock, pc } from "../format";

const VERDICTS = ["yes", "partly", "no"] as const;
const famIdx = (f: string) => { const m = /^[AB](\d+)$/.exec(f); return m ? Number(m[1]) - 1 : 0; };
const setAt = <T,>(arr: T[], i: number, v: T) => arr.map((x, j) => (j === i ? v : x));

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

  useEffect(() => {
    api.review(d.key).then((r) => {
      setData(r);
      setVerdicts(r.rows.map((x) => x.coherent_with_family ?? ""));
      setComments(r.rows.map((x) => x.comment ?? ""));
      setAnswers(r.questions.map((q) => r.answers?.questions.find((a) => a.question === q)?.answer ?? ""));
      setReviewer(r.answers?.reviewer ?? ""); setRole(r.answers?.role ?? "");
      if (r.filled_file) setSaved(`Loaded the saved review (${r.filled_file}${r.answers?.saved ? `, ${r.answers.saved}` : ""}).`);
    }).catch((e) => setErr(e.message));
  }, [d.key]);

  const refs: ClipRef[] = useMemo(() => (data?.rows ?? []).map((r) => ({
    match: Number(r.match ?? 0), half: Number(r.half), minute: Number(r.minute), second: Number(r.second),
    title: r.family, detail: `${r.family} · vs ${r.opponent}, ${r.date}, half ${r.half} ${clock(Number(r.minute), Number(r.second))} · ${r.start_type}`,
  })), [data]);
  const summary = useMemo(() => {
    const by: Record<string, Record<string, number>> = {};
    (data?.rows ?? []).forEach((r, i) => { const v = verdicts[i]; if (!v) return; by[r.family] ??= { yes: 0, partly: 0, no: 0 }; by[r.family][v]++; });
    return by;
  }, [data, verdicts]);
  const done = verdicts.filter(Boolean).length;

  if (err) return <div className="state"><h2>No review sheet</h2><p>{err}</p></div>;
  if (!data) return <div aria-busy="true"><div className="skeleton" style={{ height: 300 }} /></div>;
  const save = async () => {
    setSaving(true); setSaved(null);
    try {
      const r = await api.saveReview(d.key, { verdicts, comments, answers, reviewer, role });
      setSaved(`Saved ${r.answered} of ${verdicts.length} answers to ${r.saved} in the data folder. To summarise: python -X utf8 src/report/summarize_review.py followed by that file's path.`);
    } catch (e) { setSaved((e as Error).message); } finally { setSaving(false); }
  };

  return (
    <>
      <div className="section-head">
        <h2>Analyst review</h2>
        <p>Part 1: watch each sequence and mark whether it fits the family it was assigned to (yes / partly / no). Part 2: answer the five questions. The same questions are used for every reviewer. Nothing here is evidence that the report is useful until someone with football experience has answered.</p>
      </div>
      <div className="filters">
        <label className="field">Reviewer<input className="text-in" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Name" /></label>
        <label className="field">Role and experience<input className="text-in" value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. video analyst, 3 years" /></label>
        <span style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <span className="small">{done} of {verdicts.length} sequences marked</span>
          <button className="btn" type="button" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save review"}</button>
        </span>
      </div>
      {saved && <div style={{ marginBottom: 14 }}><Note kind="info" tag="Review">{saved}</Note></div>}

      <div className="layout-split layout-clips">
        <div className="table-wrap">
          <table className="clip-table">
            <thead><tr><th></th><th className="l">Family</th><th className="l">Match</th><th>Half, time</th><th>Passes</th><th>Shot</th><th className="l">Fits the family?</th></tr></thead>
            <tbody>
              {data.rows.map((r, i) => (
                <tr key={i} className={`clickable${i === sel ? " sel" : ""}`} onClick={() => setSel(i)}>
                  <td><button type="button" className="play-btn" aria-label={`Replay sequence ${i + 1}`} onClick={(e) => { e.stopPropagation(); setSel(i); }}>{PlayIcon}</button></td>
                  <td className="l"><span className="chip" style={rib(famIdx(r.family))}>{r.family}</span></td>
                  <td className="l">{r.opponent}<small>{r.date} · {r.start_type}</small></td>
                  <td>{r.half}, {clock(Number(r.minute), Number(r.second))}</td><td>{r.passes}</td><td>{r.ended_in_shot === "1" ? "yes" : ""}</td>
                  <td className="l" onClick={(e) => e.stopPropagation()}>
                    <div className="verdict" role="group" aria-label={`Sequence ${i + 1}: fits ${r.family}?`}>
                      {VERDICTS.map((v) => <button key={v} type="button" data-v={v} aria-pressed={verdicts[i] === v} onClick={() => setVerdicts(setAt(verdicts, i, verdicts[i] === v ? "" : v))}>{v}</button>)}
                    </div>
                    {verdicts[i] && verdicts[i] !== "yes" && <input className="text-in small-in" value={comments[i]} onChange={(e) => setComments(setAt(comments, i, e.target.value))} placeholder="What does not fit?" aria-label={`Comment on sequence ${i + 1}`} />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <aside style={{ position: "sticky", top: 84 }}>
          <div className="sticker" style={rib(famIdx(data.rows[sel]?.family ?? ""))}>
            <span className="no">{data.rows[sel]?.family}</span>
            {events && refs[sel]?.match ? <Replay teamKey={d.key} clips={refs} index={sel} onIndex={setSel} /> : <div className="note info" style={{ margin: 14 }}><span className="tag">Replays</span>Replays need the raw event files; use the video with the times in the table.</div>}
            {refs[sel] && <div className="replay-cap"><p>{refs[sel].detail}. Check it on video too: the replay shows the events, not the players off the ball.</p></div>}
          </div>
          {Object.keys(summary).length > 0 && (
            <div className="sticker pad" style={{ marginTop: 16 }}>
              <h3>So far</h3>
              <table style={{ marginTop: 8 }}>
                <thead><tr><th>Family</th><th>yes</th><th>partly</th><th>no</th><th>yes or partly</th></tr></thead>
                <tbody>{Object.entries(summary).sort().map(([f, c]) => { const n = c.yes + c.partly + c.no; return <tr key={f}><td><span className="chip" style={rib(famIdx(f))}>{f}</span></td><td>{c.yes}</td><td>{c.partly}</td><td>{c.no}</td><td><b>{pc((c.yes + c.partly) / n)}</b></td></tr>; })}</tbody>
              </table>
              <p className="s-muted" style={{ fontSize: 12.5, marginTop: 8 }}>Descriptive: with 3 sequences per family it is not a precise estimate.</p>
            </div>
          )}
        </aside>
      </div>

      <section className="section">
        <div className="section-head"><h2>Part 2: five questions</h2></div>
        <div className="layout-2">
          {data.questions.map((q, i) => (
            <label key={i} className="sticker pad q-card">
              <span className="q-no">{i + 1}</span>
              <span className="q-text">{q}</span>
              <textarea value={answers[i] ?? ""} onChange={(e) => setAnswers(setAt(answers, i, e.target.value))} rows={4} />
            </label>
          ))}
        </div>
        <p style={{ marginTop: 18 }}><button className="btn" type="button" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save review"}</button></p>
      </section>
    </>
  );
}
