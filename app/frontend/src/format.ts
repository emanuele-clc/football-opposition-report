// Same rounding as the pipeline sheets: percentages to whole points (one decimal under 1%), counts to one decimal.
export const pc = (x: number) => (x > 0 && x < 0.01 ? `${(100 * x).toFixed(1)}%` : `${Math.round(100 * x)}%`);
export const n1 = (x: number) => x.toFixed(1);
export const fmt = (x: number, unit: "pct" | "num") => (unit === "pct" ? pc(x) : n1(x));
export const ciText = (c: [number, number] | null | undefined, unit: "pct" | "num") =>
  c ? (unit === "pct" ? `${Math.round(100 * c[0])}–${Math.round(100 * c[1])}%` : `${n1(c[0])}–${n1(c[1])}`) : "";
export const ordinal = (n: number) => {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};
export const clock = (m: number, s: number) => `${m}:${String(s).padStart(2, "0")}`;
