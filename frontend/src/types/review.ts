export type Finding = {
  file_path: string;
  line_number?: number | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  issue: string;
  suggestion: string;
  pr_relevance_reason: string;
  relation_to_pr: string;
  evidence: string;
};

export type DiffSummary = {
  review_mode: string;
  main_change_type: string;
  main_area: string;
  goal_detected: boolean;
  requires_rag: boolean;
  required_review_types: string[];
};

export type TraceStep = {
  request_id: string;
  step_id: string;
  agent_id: string;
  status: string;
  summary: string;
};

export type ReviewResult = {
  request_id: string;
  review_mode: string;
  pr_url: string;
  diff_summary: DiffSummary;
  overall_score: number;
  confidence: number;
  risk_level: string;
  recommendation: string;
  final_summary: string;
  findings: Finding[];
  guardrails: {
    pr_scope_passed: boolean;
    evidence_passed: boolean;
    hallucination_passed: boolean;
    score_passed: boolean;
  };
  eval_result: {
    score: number;
    passed: boolean;
    reason: string;
  };
  trace: TraceStep[];
};
