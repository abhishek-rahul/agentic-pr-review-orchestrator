import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { reviewPr } from '../api/reviewApi';
import { FindingCard } from '../components/FindingCard';
import { GuardrailStatus } from '../components/GuardrailStatus';
import { PrInputForm } from '../components/PrInputForm';
import { ReviewStatus } from '../components/ReviewStatus';
import { ReviewSummary } from '../components/ReviewSummary';
import { ScoreCard } from '../components/ScoreCard';
import { TracePanel } from '../components/TracePanel';

export function ReviewPage() {
  const [prUrl, setPrUrl] = useState('');
  const [prGoal, setPrGoal] = useState('');

  const mutation = useMutation({
    mutationFn: () => reviewPr(prUrl, prGoal),
  });

  const result = mutation.data;

  return (
    <main className="page">
      <h1>Agentic PR Review & Code Quality Orchestrator</h1>
      <p className="muted">
        PR-diff-focused review with percentage score, guardrails, and eval skeleton.
      </p>

      <PrInputForm
        prUrl={prUrl}
        prGoal={prGoal}
        loading={mutation.isPending}
        onPrUrlChange={setPrUrl}
        onPrGoalChange={setPrGoal}
        onSubmit={() => mutation.mutate()}
      />

      {mutation.isError && (
        <ReviewStatus message="Review failed. Check PR URL, repo visibility, backend logs, or GitHub token." />
      )}

      {result && (
        <div style={{ marginTop: 20 }}>
          <div className="grid">
            <ScoreCard label="Merge Readiness" value={`${result.overall_score}%`} />
            <ScoreCard label="Confidence" value={`${result.confidence}%`} />
            <ScoreCard label="Risk Level" value={result.risk_level} />
            <ScoreCard label="Eval Score" value={`${result.eval_result.score}%`} />
          </div>

          <div style={{ height: 16 }} />
          <ReviewSummary summary={result.diff_summary} finalSummary={result.final_summary} requestId={result.request_id} />

          <div style={{ height: 16 }} />
          <GuardrailStatus guardrails={result.guardrails} />

          <div className="card" style={{ marginTop: 16 }}>
            <h3>Findings</h3>
            {result.findings.length === 0 && <p>No findings generated for this initial MVP run.</p>}
            {result.findings.map((finding, index) => (
              <FindingCard key={`${finding.file_path}-${index}`} finding={finding} />
            ))}
          </div>

          <div style={{ height: 16 }} />
          <TracePanel trace={result.trace} />
        </div>
      )}
    </main>
  );
}
