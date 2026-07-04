type Props = {
  label: string;
  value: string | number;
};

export function ScoreCard({ label, value }: Props) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <h2>{value}</h2>
    </div>
  );
}
