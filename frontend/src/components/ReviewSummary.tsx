import type { DiffSummary } from '../types/review';

type Props = {
  summary: DiffSummary;
  finalSummary: string;
  requestId: string;
};

export function ReviewSummary({ summary, finalSummary, requestId }: Props) {
  return (
    <div className="card">
      <h3>Review Summary</h3>
      <p>{finalSummary}</p>
      <p className="muted">Request ID: {requestId}</p>
      <p>
        <strong>Main area:</strong> {summary.main_area}
      </p>
      <p>
        <strong>Change type:</strong> {summary.main_change_type}
      </p>
      <p>
        <strong>Mode:</strong> {summary.review_mode}
      </p>
    </div>
  );
}
