// Shapes of the pipeline files (src/report/*.py) as served by app/backend/server.py.
export type CI = [number, number];

export interface Example {
  date: string;
  opponent: string;
  half: number;
  minute: number;
  second: number;
  video: string;
  start: string;
  passes: number;
  dur: number;
  shot: boolean;
  match?: number | null;
}
export interface Family {
  fam: string;
  n: number;
  share: number;
  share_ci: CI;
  passes: number;
  dur: number;
  long: number;
  x0: number;
  x1: number;
  directness: number;
  shot: number;
  shot_ci: CI;
  shot_share: number;
  per_match_p10_p90: CI;
  examples: Example[];
  jaccard: number;
  reliability: string;
}
export interface Phase {
  k: number;
  n: number;
  jaccard_mean: number;
  null_shuffle: number;
  null_gauss: number;
  margin: number;
  verdict: string;
  families: Family[];
  by_start: { start: string; n: number; shares: Record<string, number> }[];
}
export interface Style {
  passes: number;
  long: number;
  dur: number;
  shot: number;
  buildup_share: number;
}
export interface Report {
  team: string;
  matches: number;
  period: string;
  sequences: number;
  phases: Record<"build-up" | "advanced", Phase>;
  reliability: Record<string, { passes: number; long: number; shot: number; build_up: number; advanced: number }>;
  style: { team: Style; team_ci: Record<keyof Style, CI>; references: Record<string, Style> };
}
export interface RestartMetric {
  season: number;
  ci: CI;
  last5: number | null;
  last5_ci: CI | null;
}
export interface RestartKind {
  n: number;
  per_match: number;
  n_last5: number;
  passes: number;
  metrics: Record<string, RestartMetric>;
  receivers: Record<string, { n: number; share: number }>;
  by_length: Record<string, { n: number; opp_half: number; lost_own_half: number; shot: number }>;
}
export interface Restarts {
  team: string;
  matches: number;
  kinds: Record<string, RestartKind>;
}
export interface SetPieceKind {
  n: number;
  per_match: number;
  shot: number;
  shot_ci: CI;
  goals: number;
  xg: number | null;
  zones: Record<string, { n: number; share: number; ci: CI; shot: number; xg: number | null }>;
  by_side: Record<string, { n: number; zones: Record<string, number> }>;
  takers: Record<string, number>;
  receivers: Record<string, number>;
}
export interface SetPieces {
  team: string;
  matches: number;
  kinds: Record<string, SetPieceKind>;
}
export interface Third {
  n: number;
  per_match: number;
  per_match_ci?: CI;
  regain5?: number;
  conceded10?: number;
  shot10?: number;
  shot?: number;
  final_third?: number;
}
export interface Transitions {
  team: string;
  matches: number;
  losses: {
    n: number;
    per_match: number;
    regain5: number;
    regain5_ci: CI;
    conceded10: number;
    conceded10_ci: CI;
    by_third: Record<string, Third>;
  };
  recoveries: { n: number; per_match: number; shot10: number; shot10_ci: CI; by_third: Record<string, Third> };
  last5: { losses_per_match: number; regain5: number; recoveries_final_third_per_match: number };
}
export interface Defending {
  team: string;
  matches: number;
  ppda: { value: number; ci: CI; last5: number; opp_passes: number; actions: number };
  pressures: {
    per_match: number;
    ci: CI;
    last5: number;
    by_third: Record<string, { share: number; per_match: number }>;
    counterpress_share: number;
    counterpress_ci: CI;
    grid_per_match: number[][];
  };
  height: { mean_x: number; ci: CI; median_x: number | null; last5: number; actions_per_match: number };
  conceded: {
    shots_per_match: number;
    shots_ci: CI;
    xg_per_match: number;
    xg_ci: CI;
    last5_shots: number;
    last5_xg: number;
    xg_per_shot?: number;
    xg_per_shot_ci?: CI;
    last5_xg_per_shot?: number;
  };
}
export interface PerMatch {
  per_match: number;
  ci: CI;
  last5: number;
}
export interface Threat {
  team: string;
  matches: number;
  period: string;
  grid: { nx: number; ny: number; matches: number; moves: number; shots: number; goals: number };
  xt: PerMatch;
  xt_pass: PerMatch;
  xt_carry: PerMatch;
  given_up: PerMatch;
  conceded: PerMatch;
  origin_per_match: Record<string, number>;
  map_per_match: number[][];
  players: { player: string; xt: number; per_match: number; matches: number; share: number | null }[];
}
export interface MatchupMetric {
  id: string;
  label: string;
  unit: string;
  direction: string;
  linked: boolean;
  a: number;
  b: number;
  diff: number;
  ci: CI;
  verdict: "clear" | "uncertain" | "small group";
}
export interface Matchups {
  team: string;
  matches: number;
  note: string;
  min_group: number;
  median_opp_ppda: number;
  formations_used: string[];
  splits: Record<
    string,
    { label: string; n_a: number; n_b: number; groups: [string, string]; rule: string; metrics: MatchupMetric[] }
  >;
  per_match: {
    match: number;
    date: string;
    opponent: string;
    venue: string;
    score: string;
    formation: string;
    opp_formation: string;
    opp_back_line: string;
    opp_press: string;
    opp_ppda: number;
    xg_for: number;
    xg_against: number;
    lost_own_half: number;
  }[];
}
export interface GPEvidence {
  id: string;
  label: string;
  value: number;
  unit: string;
  rank: number;
  of: number;
  provisional?: boolean;
  team?: "you" | "opponent";
  grade?: Grade | null;
}
export interface GPFormations {
  most_used: { formation: string; raw: string; matches: number }[];
  last5: { formation: string; raw: string; opponent: string; date: string }[];
  matches: number;
}
export interface GPPlayer {
  player: string;
  full: string;
  shirt: number | null;
  keeper: boolean;
  total: number;
  matches: number;
  per_match: number;
}
export interface GPEvents {
  matches: number;
  players: { id: string; role: string; unit: string; note: string; top: GPPlayer[] }[];
  goals: {
    side: "for" | "against";
    match: number;
    date: string | null;
    opponent: string;
    half: number;
    minute: number;
    second: number;
    start_minute: number;
    start_second: number;
    possession: number | null;
    scorer: string;
    xg: number | null;
    origin: string;
    body: string | null;
    x: number | null;
    y: number | null;
  }[];
  goals_by_origin: { for: Record<string, number>; against: Record<string, number> };
  timeline: { slot: string; goals_for: number; goals_against: number; xg_for: number; xg_against: number }[];
}
export interface GPWatch {
  rule: string;
  matches: {
    match: number;
    date: string;
    opponent: string;
    venue: string;
    score: string;
    opp_formation: string;
    opp_ppda: number;
    xg_for: number;
    xg_against: number;
    distance: number | null;
  }[];
}
export interface PZone {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  passes: number;
  under_pressure: number;
  up_share: number;
  up_completion: number;
  free_completion: number;
  up_long_share: number;
  few: boolean;
  ref_completion: number | null;
  ref_long_share: number | null;
  diff: number | null;
  weaker: boolean;
}
export interface WithoutData {
  players: { player: string; starts: number; not_started: number; usable: boolean }[];
  player?: string;
  n_with?: number;
  n_without?: number;
  metrics?: {
    id: string;
    label: string;
    unit: string;
    a: number | null;
    b: number | null;
    diff: number | null;
    ci: [number, number] | null;
    verdict: "clear" | "uncertain" | "small group";
  }[];
  without_matches?: { date: string; opponent: string; score: string }[];
}
export interface GamePlan {
  opponent: string;
  mine: string | null;
  teams_in_folder: number;
  k: number;
  brief: {
    intro: string;
    priorities: string[];
    priority_grades?: (Grade | null)[];
    phases: Record<"with_ball" | "without_ball" | "transitions" | "set_pieces", { title: string; lines: string[] }>;
  };
  formations: { opponent: GPFormations | null; mine: GPFormations | null };
  profile: GPEvidence[];
  watch_first: GPWatch | null;
  foul_zones: {
    zones: {
      x0: number;
      x1: number;
      y0: number;
      y1: number;
      fouls: number;
      cards: number;
      per_match: number;
      ref_per_match: number | null;
    }[];
    matches: number;
    teams_in_reference: number;
    total_per_match: number;
    ref_total_per_match: number | null;
  } | null;
  breaks: {
    zones: { x0: number; x1: number; y0: number; y1: number; n: number; shot10: number }[];
    shots: {
      match: number;
      date: string;
      opponent: string;
      half: number;
      minute: number;
      second: number;
      x: number;
      y: number;
    }[];
    rate: number;
    n: number;
    matches: number;
  } | null;
  pressure_zones: {
    zones: PZone[];
    total: { passes: number; completion: number; free_completion: number };
    teams_in_reference: number;
    matches: number;
  } | null;
  hints: {
    id: string;
    side: "opp" | "both";
    title: string;
    why: string;
    look: string;
    tab: string;
    evidence: GPEvidence[];
    grade?: Grade | null;
  }[];
  opp_past: {
    split: string;
    label: string;
    unit: string;
    a: number;
    b: number;
    ga: string;
    gb: string;
    n_a: number;
    n_b: number;
  }[];
  my_vs_press: { groups: [string, string]; n_a: number; n_b: number; metrics: MatchupMetric[] } | null;
}
export interface Rank {
  id: string;
  group: string;
  label: string;
  sheet: string;
  unit: "pct" | "num" | "num2";
  caution: string | null;
  value: number;
  ci: CI | null;
  rank: number;
  of: number;
  /* Fewer matches than the minimum: placed among the teams but not ranked (server MIN_MATCHES). */
  provisional?: boolean;
  teams: { key: string; team: string; value: number }[];
  statement?: string | null;
  grade?: Grade | null;
}
// Evidence grade of the statement types (results/evidence_grade_corrected.json, protocol docs/protocol_evidence_grade.md).
export type Grade = "A" | "B" | "C" | "D";
export interface EvStatement {
  statement: string;
  forecasts: number;
  teams: number;
  grade: Grade;
  skill: number;
  skill_ci: CI;
  forecast: "strong" | "weak" | "none";
  D?: number | null;
  D_ci?: CI;
  discrimination: "high" | "medium" | "low" | "n/a";
  coverage_80: number;
  coverage_ci: CI;
  calibration: string;
  last5_vs_season: number;
  last5_ci: CI;
  last5_verdict: string;
  matches_needed: string | number;
  items?: number;
}
export interface Evidence {
  available: boolean;
  source?: string;
  set?: string;
  n_teams?: number;
  grades?: Record<Grade, number>;
  sanity_checks?: Record<string, boolean>;
  statements?: Record<string, EvStatement>;
  dropped?: Record<string, number[]>;
  provider?: Record<string, { label: string; seen_before?: boolean; why?: string }> | null;
  shown_in_app?: Record<string, string[]>;
  provider_matches?: number | null;
}
export interface TeamSummary {
  key: string;
  team: string;
  matches: number;
  period: string;
  sequences: number;
  provisional?: boolean;
  sheets: string[];
  clips: string[];
}
export interface TeamData extends TeamSummary {
  report: Report;
  restarts: Restarts | null;
  setpieces: SetPieces | null;
  transitions: Transitions | null;
  defending: Defending | null;
  xthreat: Threat | null;
  matchups: Matchups | null;
  ranks: Rank[];
  references: string[];
  min_matches?: number;
}
export interface Info {
  data_dir: string;
  is_examples: boolean;
  can_generate: boolean;
  has_events: boolean;
  has_tracking?: boolean;
}
export interface TrackGoal {
  half: number;
  frame: number;
  team: string;
  side: "home" | "guest";
  player: string;
  clock: string;
  xg: number | null;
}
export interface TrackMatch {
  match: string;
  date: string;
  competition: string;
  home: string;
  guest: string;
  result: string;
  goals: TrackGoal[];
}
type Est = { mean: number; ci: CI };
export interface TrackResults {
  pitch_control: null | {
    A_pass_check: {
      passes: number;
      completed_share: number;
      auc: Record<"pc" | "margin" | "length" | "pc_minus_margin" | "pc_minus_length", { value: number; ci: CI }>;
      pc_adds_over_margin: boolean;
      pc_adds_over_length: boolean;
      brier_pc: number;
      brier_base_rate: number;
    };
    B_space: {
      match: string;
      team: string;
      frames: number;
      opp_half_controlled: number;
      own_half_controlled_when_defending: number;
    }[];
  };
  ghosting: null | {
    horizon_s: number;
    samples: { train: number; test: number };
    position_error_m: Record<string, Est>;
    line_height_error_m: Record<string, Est>;
    position_diff: Record<string, Est & { lstm_beats: boolean }>;
    line_diff: Record<string, Est & { lstm_beats: boolean }>;
    test_mean_displacement_m: number;
  };
}
export interface TrackFrame {
  t: number;
  alive: number;
  ball: [number, number] | null;
  p: ([number, number] | null)[];
  pc: number[];
}
export interface TrackClip {
  match: string;
  half: number;
  clock: string;
  home: string;
  guest: string;
  home_attacks: "left" | "right";
  grid: [number, number];
  players: { name: string; side: "home" | "guest"; gk: boolean }[];
  frames: TrackFrame[];
}
export interface ClipRow {
  family: string;
  match: number;
  date: string;
  opponent: string;
  half: number;
  minute: number;
  second: number;
  start_type: string;
  passes: number;
  duration_s: number;
  ended_in_shot: number;
  video_time?: string;
}
export interface Source {
  file: string;
  competition: string;
  season: string;
  teams: { team: string; matches: number; with_events: number }[];
}
export interface Action {
  t: number;
  type: string;
  us: boolean;
  player: string;
  x: number;
  y: number;
  ex?: number;
  ey?: number;
  ok?: boolean;
  to?: string;
  long?: boolean;
  kind?: string;
  outcome?: string;
  xg?: number | null;
}
export interface Replay {
  match: number;
  half: number;
  minute: number;
  second: number;
  play_pattern: string;
  actions: Action[];
}
/* One clip to replay: where it is in the events, plus what to say about it. */
export interface ClipRef {
  match: number;
  half: number;
  minute: number;
  second: number;
  window?: boolean;
  possession?: number;
  title: string;
  detail: string;
}
export interface PathsData {
  team: string;
  n: number;
  of: number;
  paths: { family: string; shot: number; pts: [number, number][] }[];
}
export interface ReviewRow {
  family: string;
  date: string;
  opponent: string;
  half: string;
  minute: string;
  second: string;
  start_type: string;
  passes: string;
  duration_s: string;
  ended_in_shot: string;
  coherent_with_family: string;
  comment: string;
  match: string | null;
}
export interface ReviewData {
  rows: ReviewRow[];
  questions: string[];
  answers: { reviewer: string; role: string; saved: string; questions: { question: string; answer: string }[] } | null;
  filled_file: string | null;
}
export interface RestartPass {
  kind: string;
  match: number;
  half: number;
  minute: number;
  second: number;
  x: number;
  y: number;
  ex: number;
  ey: number;
  short: number;
  receiver: string;
  complete: number;
  opp_half: number;
  shot: number;
  lost_own_half: number;
}
export interface NetworkData {
  team: string;
  families: Record<
    string,
    {
      sequences: number;
      nodes: { player: string; shirt: number | null; touches: number; x: number; y: number }[];
      edges: { a: string; b: string; passes: number }[];
    }
  >;
}
export interface StyleMapData {
  metrics: string[];
  left_out?: { team: string; matches: number }[];
  min_matches?: number;
  axes: { explained: number; loadings: { id: string; label: string; weight: number }[] }[];
  teams: {
    key: string;
    team: string;
    period: string;
    x: number;
    y: number;
    nearest: { team: string; distance: number }[];
  }[];
}
export interface SimilarData {
  of: Record<string, string>;
  similar: (Record<string, string> & { distance: number; pts: [number, number][] })[];
  typical_nn_distance: number;
}
export interface Job {
  id: string;
  team: string;
  key: string;
  source: string;
  status: "running" | "done" | "failed";
  log: string[];
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      msg = (await r.json()).detail ?? msg;
    } catch {
      /* not JSON */
    }
    throw new Error(msg);
  }
  return r.json();
}

export const api = {
  info: () => get<Info>("/api/info"),
  trackResults: () => get<TrackResults>("/api/tracking/results"),
  trackMatches: () => get<TrackMatch[]>("/api/tracking/matches"),
  trackClip: (match: string, half: number, frame: number) =>
    get<TrackClip>(`/api/tracking/clip?match=${encodeURIComponent(match)}&half=${half}&frame=${frame}`),
  teams: () => get<TeamSummary[]>("/api/teams"),
  evidence: () => get<Evidence>("/api/evidence"),
  team: (key: string) => get<TeamData>(`/api/teams/${encodeURIComponent(key)}`),
  clips: (key: string, kind: string) =>
    get<{ columns: string[]; rows: ClipRow[] }>(`/api/teams/${encodeURIComponent(key)}/clips/${kind}`),
  clipGoals: (key: string, kind: string) =>
    get<{ goals: [number, number, number, number][] }>(`/api/teams/${encodeURIComponent(key)}/clips/${kind}/goals`),
  replay: (key: string, c: ClipRef) =>
    get<Replay>(
      `/api/teams/${encodeURIComponent(key)}/replay?match=${c.match}&half=${c.half}&minute=${c.minute}&second=${c.second}${c.window ? "&window=true" : ""}${c.possession ? `&possession=${c.possession}` : ""}`,
    ),
  paths: (key: string) => get<PathsData>(`/api/teams/${encodeURIComponent(key)}/paths`),
  review: (key: string) => get<ReviewData>(`/api/teams/${encodeURIComponent(key)}/review`),
  saveReview: async (
    key: string,
    body: { verdicts: string[]; comments: string[]; answers: string[]; reviewer: string; role: string },
  ) => {
    const r = await fetch(`/api/teams/${encodeURIComponent(key)}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail ?? "Could not save the review.");
    return j as { saved: string; answered: number };
  },
  pressing: (key: string) =>
    get<{ team: string; restarts: RestartPass[] }>(`/api/teams/${encodeURIComponent(key)}/pressing`),
  network: (key: string) => get<NetworkData>(`/api/teams/${encodeURIComponent(key)}/network`),
  gifUrl: (key: string, c: ClipRef) =>
    `/api/teams/${encodeURIComponent(key)}/replay.gif?match=${c.match}&half=${c.half}&minute=${c.minute}&second=${c.second}${c.window ? "&window=true" : ""}${c.possession ? `&possession=${c.possession}` : ""}&title=${encodeURIComponent(c.title)}`,
  stylemap: () => get<StyleMapData>("/api/stylemap"),
  without: (key: string, player: string) =>
    get<WithoutData>(
      `/api/teams/${encodeURIComponent(key)}/without${player ? `?player=${encodeURIComponent(player)}` : ""}`,
    ),
  gameplanEvents: (key: string) => get<GPEvents>(`/api/teams/${encodeURIComponent(key)}/gameplan/events`),
  gameplan: (key: string, mine: string) =>
    get<GamePlan>(`/api/teams/${encodeURIComponent(key)}/gameplan${mine ? `?mine=${encodeURIComponent(mine)}` : ""}`),
  similar: (key: string, r: { match: number; half: number; minute: number; second: number }) =>
    get<SimilarData>(
      `/api/teams/${encodeURIComponent(key)}/similar?match=${r.match}&half=${r.half}&minute=${r.minute}&second=${r.second}`,
    ),
  sources: () => get<Source[]>("/api/sources"),
  job: (id: string) => get<Job>(`/api/jobs/${id}`),
  startJob: async (source: string, team: string): Promise<Job> => {
    const r = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, team }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail ?? "Could not start the pipeline.");
    return body;
  },
  exportUrl: (
    key: string,
    kind: string,
    ext: "csv" | "zip",
    f: { family?: string; opponent?: string; shot?: boolean; goal?: boolean; half?: number },
  ) => {
    const q = new URLSearchParams();
    if (f.family) q.set("family", f.family);
    if (f.opponent) q.set("opponent", f.opponent);
    if (f.shot) q.set("shot", "true");
    if (f.goal) q.set("goal", "true");
    if (f.half) q.set("half", String(f.half));
    return `/api/teams/${encodeURIComponent(key)}/export/${kind}.${ext}?${q}`;
  },
};
