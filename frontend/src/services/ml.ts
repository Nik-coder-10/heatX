import { post } from './api';
import type { PredictionResult, ForecastResult, TrainMetrics } from '@/types';

export function trainModel(
  X: number[][],
  y: number[],
  modelType = 'random_forest',
  task = 'regression'
): Promise<{ status: string; model_type: string; metrics: TrainMetrics | null }> {
  return post('/ml/training/train', { X, y, model_type: modelType, task });
}

export function predict(
  X: number[][],
  featureNames?: string[]
): Promise<PredictionResult> {
  return post('/ml/inference/predict', { X, feature_names: featureNames });
}

export function forecast(
  X: number[][],
  deltaYears = 10,
  featureNames?: string[]
): Promise<ForecastResult> {
  return post('/ml/inference/forecast', { X, delta_years: deltaYears, feature_names: featureNames });
}

export function crossValidate(
  X: number[][],
  y: number[],
  strategy = 'kfold',
  nFolds = 5
): Promise<{ mean_score: number; std_score: number; n_folds: number }> {
  return post('/ml/training/cross-validate', { X, y, strategy, n_folds: nFolds });
}

export function hyperparameterOptimize(
  X: number[][],
  y: number[],
  method = 'grid',
  nTrials = 20
): Promise<{ best_params: Record<string, unknown>; best_score: number }> {
  return post('/ml/training/hyperparameter-optimization', {
    X, y, method, n_trials: nTrials,
  });
}
