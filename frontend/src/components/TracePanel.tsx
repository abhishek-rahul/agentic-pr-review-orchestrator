import type { TraceStep } from '../types/review';

type Props = {
  trace: TraceStep[];
};

export function TracePanel({ trace }: Props) {
  return (
    <div className="card">
      <h3>Debug Trace</h3>
      {trace.map((step) => (
        <p key={`${step.step_id}-${step.agent_id}`} className="muted">
          <strong>{step.step_id}</strong> / {step.agent_id} / {step.status}: {step.summary}
        </p>
      ))}
    </div>
  );
}
