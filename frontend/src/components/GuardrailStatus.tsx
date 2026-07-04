type Props = {
  guardrails: {
    pr_scope_passed: boolean;
    evidence_passed: boolean;
    hallucination_passed: boolean;
    score_passed: boolean;
  };
};

function mark(value: boolean) {
  return value ? '✅' : '❌';
}

export function GuardrailStatus({ guardrails }: Props) {
  return (
    <div className="card">
      <h3>Guardrails</h3>
      <p>{mark(guardrails.pr_scope_passed)} PR scope validation</p>
      <p>{mark(guardrails.evidence_passed)} Evidence validation</p>
      <p>{mark(guardrails.hallucination_passed)} No fake file/path validation</p>
      <p>{mark(guardrails.score_passed)} Score validation</p>
    </div>
  );
}
