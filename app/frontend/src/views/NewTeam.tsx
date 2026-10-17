import { useEffect, useRef, useState } from "react";
import { api, type Info, type Job, type Source } from "../api";
import { Note } from "../charts";

export default function NewTeam({ info, known, done }: { info: Info | null; known: string[]; done: (key: string) => void }) {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [file, setFile] = useState("");
  const [team, setTeam] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.sources().then((s) => { setSources(s); if (s[0]) setFile(s[0].file); }).catch((e) => setError(e.message)); }, []);
  useEffect(() => {
    if (!job || job.status !== "running") return;
    const t = setInterval(() => api.job(job.id).then(setJob).catch(() => undefined), 1500);
    return () => clearInterval(t);
  }, [job]);
  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [job?.log.length]);

  const src = sources?.find((s) => s.file === file);
  const start = async () => {
    setError(null);
    try { setJob(await api.startJob(file, team)); } catch (e) { setError((e as Error).message); }
  };

  if (sources && sources.length === 0) {
    return (
      <div className="state">
        <h2>No match data in this folder</h2>
        <p>The app is reading <b>{info?.data_dir}</b>. To make a report for a new team it needs StatsBomb match lists in <code>matches/</code> and the event files in <code>ev/</code>, as written by <code>src/week1/download_data.py</code>.</p>
        <p>Start the app on that folder instead:</p>
        <div className="log">python -X utf8 app\run.py --data-dir C:\Users\ecole\sbdata</div>
      </div>
    );
  }
  return (
    <>
      <div className="section-head">
        <h2>Add a team</h2>
        <p>Runs src/oppreport.py on the match data in {info?.data_dir}. It takes a few minutes (resampling for the reliability estimates); you can keep using the app.</p>
      </div>
      {!sources && !error && <div aria-busy="true"><div className="skeleton" /><div className="skeleton" /></div>}
      {sources && (
        <div className="filters">
          <label className="field">Competition and season
            <select value={file} onChange={(e) => { setFile(e.target.value); setTeam(""); }} disabled={job?.status === "running"}>
              {sources.map((s) => <option key={s.file} value={s.file}>{s.competition} {s.season}</option>)}
            </select>
          </label>
          <label className="field">Team
            <select value={team} onChange={(e) => setTeam(e.target.value)} disabled={job?.status === "running"}>
              <option value="">Choose a team</option>
              {src?.teams.map((t) => <option key={t.team} value={t.team}>{t.team} · {t.matches} matches{known.includes(t.team) ? " · report exists" : ""}</option>)}
            </select>
          </label>
          <button className="btn" type="button" disabled={!team || job?.status === "running"} onClick={start}>{known.includes(team) ? "Generate again" : "Generate report"}</button>
        </div>
      )}
      <div className="stack" style={{ marginTop: 16, maxWidth: 900 }}>
        {team && known.includes(team) && !job && <Note kind="info" tag="Exists">A report for {team} is already in the folder. Generating again overwrites its files with a fresh run.</Note>}
        {error && <Note kind="caution" tag="Not started">{error}</Note>}
        {job && (
          <>
            <Note kind={job.status === "failed" ? "caution" : job.status === "done" ? "ok" : "info"} tag={job.status === "running" ? "Running" : job.status === "done" ? "Done" : "Failed"}>
              {job.status === "running" && <>Generating the report for <b>{job.team}</b>.</>}
              {job.status === "done" && <>The report for <b>{job.team}</b> is ready. <button className="btn" type="button" style={{ marginLeft: 8 }} onClick={() => done(job.key)}>Open it</button></>}
              {job.status === "failed" && <>The pipeline stopped. The last lines of its output are below; they name the problem.</>}
            </Note>
            <div className="log" ref={logRef} aria-live="polite">{job.log.join("\n") || "Starting…"}</div>
          </>
        )}
      </div>
    </>
  );
}
