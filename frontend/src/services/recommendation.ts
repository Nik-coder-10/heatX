import { post } from './api';
import type { RecommendationBundle, ScoredRecommendation } from '@/types';

export function generateRecommendations(
  hotspot: Record<string, unknown>,
  budget?: number,
  generateScenarios = false
): Promise<{
  hotspot_id: string;
  hotspot_severity: string;
  recommendations: ScoredRecommendation[];
  optimization: RecommendationBundle['optimization'];
  scenarios: RecommendationBundle['scenarios'];
}> {
  return post('/recommendations/generate', {
    hotspot,
    budget,
    generate_scenarios: generateScenarios,
  });
}

export function generateBatchRecommendations(
  hotspots: Record<string, unknown>[],
  budget?: number
): Promise<{ results: Array<{ hotspot_id: string; recommendations: ScoredRecommendation[] }> }> {
  return post('/recommendations/generate-batch', { hotspots, budget });
}
