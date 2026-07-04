import axios from 'axios';
import type { ReviewResult } from '../types/review';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api',
});

export async function reviewPr(prUrl: string, prGoal?: string): Promise<ReviewResult> {
  const response = await api.post<ReviewResult>('/review-pr', {
    pr_url: prUrl,
    pr_goal: prGoal || null,
  });
  return response.data;
}
