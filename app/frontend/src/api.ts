// Shapes of the pipeline files (src/report/*.py) as served by app/backend/server.py.
export type CI = [number, number];

export interface Example { date: string; opponent: string; half: number; minute: number; second: number; video: string; start: string; passes: number; dur: number; shot: boolean; match?: number | null }
export interface Family {
  fam: string; n: number; share: number; share_ci: CI; passes: number; dur: number; long: number; x0: number; x1: number; directness: number;
  shot: number; shot_ci: CI; shot_share: number; per_match_p10_p90: CI; examples: Example[]; jaccard: number; reliability: string;
}
export interface Phase { k: number; n: number; jaccard_mean: number; null_shuffle: number; null_gauss: number; margin: number; verdict: string; families: Family[]; by_start: { start: string; n: number; shares: Record<string, number> }[] }
export interface Style { passes: number; long: number; dur: number; shot: number; buildup_share: number }
export interface Report {
  team: string; matches: number; period: string; sequences: number;
  phases: Record<"build-up" | "advanced", Phase>;
  reliability: Record<string, { passes: number; long: number; shot: number; build_up: number; advanced: number }>;
  style: { team: Style; team_ci: Record<keyof Style, CI>; references: Record<string, Style> };
}
export interface RestartMetric { season: number; ci: CI; last5: number | null; last5_ci: CI | null }
export interface RestartKind {
  n: number; per_match: number; n_last5: number; passes: number; metrics: Record<string, RestartMetric>;
  receivers: Record<string, { n: number; share: number }>; by_length: Record<string, { n: number; opp_half: number; lost_own_half: number; shot: number }>;
}
export interface Restarts { team: string; matches: number; kinds: Record<string, RestartKind> }
export interface SetPieceKind {
  n: number; per_match: number; shot: number; shot_ci: CI; goals: number; xg: number | null;
  zones: Record<string, { n: number; share: number; ci: CI; shot: number; xg: number | null }>;
  by_side: Record<string, { n: number; zones: Record<string, number> }>;
  takers: Record<string, number>; receivers: Record<string, number>;
}
export interface SetPieces { team: string; matches: number; kinds: Record<string, SetPieceKind> }
export interface Third { n: number; per_match: number; per_match_ci?: CI; regain5?: number; conceded10?: number; shot10?: number; shot?: number; final_third?: number }
export interface Transitions {
  team: string; matches: number;
  losses: { n: number; per_match: number; regain5: number; regain5_ci: CI; conceded10: number; conceded10_ci: CI; by_third: Record<string, Third> };
  recoveries: { n: number; per_match: number; shot10: number; shot10_ci: CI; by_third: Record<string, Third> };
  last5: { losses_per_match: number; regain5: number; recoveries_final_third_per_match: number };
}
export interface Defending {
  team: string; matches: number;
  ppda: { value: number; ci: CI; last5: number; opp_passes: number; actions: number };
  pressures: { per_match: number; ci: CI; last5: number; by_third: Record<string, { share: number; per_match: number }>; counterpress_share: number; counterpress_ci: CI; grid_per_match: number[][] };
  height: { mean_x: number; ci: CI; median_x: number | null; last5: number; actions_per_match: number };
  conceded: { shots_per_match: number; shots_ci: CI; xg_per_match: number; xg_ci: CI; last5_shots: number; last5_xg: number };
}
export interface MatchupMetric { id: string; label: string; unit: string; direction: string; linked: boolean; a: number; b: number; diff: number; ci: CI; verdict: "clear" | "uncertain" | "small group" }
export interface Matchups {
  team: string; matches: number; note: string; min_group: number; median_opp_ppda: number; formations_used: string[];
  splits: Record<string, { label: string; n_a: number; n_b: number; groups: [string, string]; rule: string; metrics: MatchupMetric[] }>;
  per_match: { match: number; date: string; opponent: string; venue: string; score: string; formation: string; opp_formation: string; opp_back_line: string; opp_press: string; opp_ppda: number; xg_for: number; xg_against: number; lost_own_half: number }[];
}
export interface GPEvidence { id: string; label: string; value: number; unit: string; rank: number; of: number; team?: "you" | "opponent" }
export interface GPFormations { most_used: { formation: string; raw: string; matches: number }[]; last5: { formation: string; raw: string; opponent: string; date: string }[]; matches: number }
export interface GPPlayer { player: string; full: string; shirt: number | null; keeper: boolean; total: number; matches: number; per_match: number }
export interface GPEvents {
  matches: number;
  players: { id: string; role: string; unit: string; note: string; top: GPPlayer[] }[];
  timeline: { slot: string; goals_for: number; goals_against: number; xg_for: number; xg_against: number }[];
}
export interface GPWatch { rule: string; matches: { match: number; date: string; opponent: string; venue: string; score: string; opp_formation: string; opp_ppda: number; xg_for: number; xg_against: number; distance: number | null }[] }
export interface GamePlan {
  opponent: string; mine: string | null; teams_in_folder: number; k: number;
  brief: { intro: string; priorities: string[]; phases: Record<"with_ball" | "without_ball" | "transitions" | "set_pieces", { title: string; lines: string[] }> };
  formations: { opponent: GPFormations | null; mine: GPFormations | null };
  profile: GPEvidence[];
  watch_first: GPWatch | null;
  hints: { id: string; side: "opp" | "both"; title: string; why: string; look: string; tab: string; evidence: GPEvidence[] }[];
  opp_past: { split: string; label: string; unit: string; a: number; b: number; ga: string; gb: string; n_a: number; n_b: number }[];
  my_vs_press: { groups: [string, string]; n_a: number; n_b: number; metrics: MatchupMetric[] } | null;
}
export interface Rank {
  id: string; group: string; label: string; sheet: string; unit: "pct" | "num" | "num2"; caution: string | null; value: number; ci: CI | null;
  rank: number; of: number; teams: { key: string; team: string; value: number }[];
}
export interface TeamSummary { key: string; team: string; matches: number; period: string; sequences: number; sheets: string[]; clips: string[] }
export interface TeamData extends TeamSummary {
  report: Report; restarts: Restarts | null; setpieces: SetPieces | null; transitions: Transitions | null; defending: Defending | null; matchups: Matchups | null; ranks: Rank[]; references: string[];
}
export interface Info { data_dir: string; is_examples: boolean; can_generate: boolean; has_events: boolean }
export interface ClipRow { family: string; match: number; date: string; opponent: string; half: number; minute: number; second: number; start_type: string; passes: number; duration_s: number; ended_in_shot: number; video_time?: string }
export interface Source { file: string; competition: string; season: string; teams: { team: string; matches: number }[] }
export interface Action { t: number; type: string; us: boolean; player: string; x: number; y: number; ex?: number; ey?: number; ok?: boolean; to?: string; long?: boolean; kind?: string; outcome?: string; xg?: number | null }
export interface Replay { match: number; half: number; minute: number; second: number; play_pattern: string; actions: Action[] }
/* One clip to replay: where it is in the events, plus what to say about it. */
export interface ClipRef { match: number; half: number; minute: number; second: number; window?: boolean; title: string; detail: string }
export interface PathsData { team: string; n: number; of: number; paths: { family: string; shot: number; pts: [number, number][] }[] }
export interface ReviewRow { family: string; date: string; opponent: string; half: string; minute: string; second: string; start_type: string; passes: string; duration_s: string; ended_in_shot: string; coherent_with_family: string; comment: string; match: string | null }
export interface ReviewData { rows: ReviewRow[]; questions: string[]; answers: { reviewer: string; role: string; saved: string; questions: { question: string; answer: string }[] } | null; filled_file: string | null }
export interface RestartPass { kind: string; match: number; half: number; minute: number; second: number; x: number; y: number; ex: number; ey: number; short: number; receiver: string; complete: number; opp_half: number; shot: number; lost_own_half: number }
export interface NetworkData { team: string; families: Record<string, { sequences: number; nodes: { player: string; shirt: number | null; touches: number; x: number; y: number }[]; edges: { a: string; b: string; passes: number }[] }> }
export interface StyleMapData { metrics: string[]; axes: { explained: number; loadings: { id: string; label: string; weight: number }[] }[]; teams: { key: string; team: string; period: string; x: number; y: number; nearest: { team: string; distance: number }[] }[] }
export interface SimilarData { of: Record<string, string>; similar: (Record<string, string> & { distance: number; pts: [number, number][] })[]; typical_nn_distance: number }
export interface Job { id: string; team: string; key: string; source: string; status: "running" | "done" | "failed"; log: string[] }

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { msg = (await r.json()).detail ?? msg; } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

export const api = {
  info: () => get<Info>("/api/info"),
  teams: () => get<TeamSummary[]>("/api/teams"),
  team: (key: string) => get<TeamData>(`/api/teams/${encodeURIComponent(key)}`),
  clips: (key: string, kind: string) => get<{ columns: string[]; rows: ClipRow[] }>(`/api/teams/${encodeURIComponent(key)}/clips/${kind}`),
  replay: (key: string, c: ClipRef) =>
    get<Replay>(`/api/teams/${encodeURIComponent(key)}/replay?match=${c.match}&half=${c.half}&minute=${c.minute}&second=${c.second}${c.window ? "&window=true" : ""}`),
  paths: (key: string) => get<PathsData>(`/api/teams/${encodeURIComponent(key)}/paths`),
  review: (key: string) => get<ReviewData>(`/api/teams/${encodeURIComponent(key)}/review`),
  saveReview: async (key: string, body: { verdicts: string[]; comments: string[]; answers: string[]; reviewer: string; role: string }) => {
    const r = await fetch(`/api/teams/${encodeURIComponent(key)}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail ?? "Could not save the review.");
    return j as { saved: string; answered: number };
  },
  pressing: (key: string) => get<{ team: string; restarts: RestartPass[] }>(`/api/teams/${encodeURIComponent(key)}/pressing`),
  network: (key: string) => get<NetworkData>(`/api/teams/${encodeURIComponent(key)}/network`),
  gifUrl: (key: string, c: ClipRef) =>
    `/api/teams/${encodeURIComponent(key)}/replay.gif?match=${c.match}&half=${c.half}&minute=${c.minute}&second=${c.second}${c.window ? "&window=true" : ""}&title=${encodeURIComponent(c.title)}`,
  stylemap: () => get<StyleMapData>("/api/stylemap"),
  gameplanEvents: (key: string) => get<GPEvents>(`/api/teams/${encodeURIComponent(key)}/gameplan/events`),
  gameplan: (key: string, mine: string) => get<GamePlan>(`/api/teams/${encodeURIComponent(key)}/gameplan${mine ? `?mine=${encodeURIComponent(mine)}` : ""}`),
  similar: (key: string, r: { match: number; half: number; minute: number; second: number }) =>
    get<SimilarData>(`/api/teams/${encodeURIComponent(key)}/similar?match=${r.match}&half=${r.half}&minute=${r.minute}&second=${r.second}`),
  sources: () => get<Source[]>("/api/sources"),
  job: (id: string) => get<Job>(`/api/jobs/${id}`),
  startJob: async (source: string, team: string): Promise<Job> => {
    const r = await fetch("/api/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source, team }) });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail ?? "Could not start the pipeline.");
    return body;
  },
  exportUrl: (key: string, kind: string, ext: "csv" | "zip", f: { family?: string; opponent?: string; shot?: boolean; half?: number }) => {
    const q = new URLSearchParams();
    if (f.family) q.set("family", f.family);
    if (f.opponent) q.set("opponent", f.opponent);
    if (f.shot) q.set("shot", "true");
    if (f.half) q.set("half", String(f.half));
    return `/api/teams/${encodeURIComponent(key)}/export/${kind}.${ext}?${q}`;
  },
};
