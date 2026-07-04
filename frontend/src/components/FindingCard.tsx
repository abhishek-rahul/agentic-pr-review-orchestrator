import type { Finding } from '../types/review';

type Props = {
  finding: Finding;
};

export function FindingCard({ finding }: Props) {
  return (
    <div className="finding">
      <strong>{finding.severity.toUpperCase()}</strong>
      <p>{finding.issue}</p>
      <p>
        <strong>File:</strong> {finding.file_path}
      </p>
      <p>
        <strong>Suggestion:</strong> {finding.suggestion}
      </p>
      <p className="muted">
        <strong>Why PR-related:</strong> {finding.pr_relevance_reason}
      </p>
      <p className="muted">
        <strong>Evidence:</strong> {finding.evidence}
      </p>
    </div>
  );
}
