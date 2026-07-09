import { post } from './api';
import type { ExplainResult } from '@/types';

export function explain(
  X: number[][],
  y?: number[],
  featureNames?: string[],
  method = 'shap'
): Promise<{ status: string; data: ExplainResult }> {
  return post('/ml/inference/explain', {
    X, y, feature_names: featureNames, method,
    compute_global: true,
    compute_local: true,
    compute_counterfactual: true,
    compute_confidence: true,
    compute_uncertainty: true,
  });
}

export function explainHotspot(
  hotspot: Record<string, unknown>,
  X: number[][],
  featureNames: string[],
  targetReduction = 2.0
): Promise<{ status: string; data: ExplainResult }> {
  return post('/ml/inference/explain-hotspot', {
    hotspot, X, feature_names: featureNames,
    target_reduction: targetReduction,
  });
}
