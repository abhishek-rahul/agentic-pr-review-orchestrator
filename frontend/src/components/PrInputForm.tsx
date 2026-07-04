type Props = {
  prUrl: string;
  prGoal: string;
  loading: boolean;
  onPrUrlChange: (value: string) => void;
  onPrGoalChange: (value: string) => void;
  onSubmit: () => void;
};

export function PrInputForm(props: Props) {
  return (
    <div className="card">
      <h2>Review a GitHub PR</h2>
      <label>
        GitHub PR URL
        <input
          className="input"
          placeholder="https://github.com/org/repo/pull/42"
          value={props.prUrl}
          onChange={(event) => props.onPrUrlChange(event.target.value)}
        />
      </label>

      <div style={{ height: 14 }} />

      <label>
        PR Goal / Requirement <span className="muted">optional</span>
        <textarea
          className="textarea"
          placeholder="Example: Add coupon discount support for valid coupons only."
          value={props.prGoal}
          onChange={(event) => props.onPrGoalChange(event.target.value)}
        />
      </label>

      <div style={{ height: 16 }} />

      <button className="button" disabled={props.loading || !props.prUrl} onClick={props.onSubmit}>
        {props.loading ? 'Reviewing...' : 'Review PR'}
      </button>
    </div>
  );
}
