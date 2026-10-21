/* "Only goals" switch for the replays of a sheet. Hidden while the goal list loads or without event files;
   disabled when none of these clips ended in a goal. */
export default function GoalToggle({
  count,
  on,
  set,
}: {
  count: number | null;
  on: boolean;
  set: (on: boolean) => void;
}) {
  if (count === null) return null;
  return (
    <label className="check no-print" style={{ paddingBottom: 0 }}>
      <input type="checkbox" checked={on && count > 0} disabled={!count} onChange={(e) => set(e.target.checked)} /> Only
      goals · {count}
    </label>
  );
}
