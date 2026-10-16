import { usageLevel } from "../usage";

export function UsageMeter({ caption, percent }: { caption: string; percent: number | null }) {
  if (percent === null) return <span>—</span>;
  return (
    <div className="meter">
      <div className="meter-label"><span>{caption}</span><span>{percent}%</span></div>
      <div className="meter-track"><i className={`meter-bar ${usageLevel(percent)}`} style={{ width: `${percent}%` }} /></div>
    </div>
  );
}
