import { get, post } from './api';
import type { ScenarioTemplate, SimulationResult, ComparisonReport } from '@/types';

export function listTemplates(category?: string): Promise<{ templates: ScenarioTemplate[] }> {
  const qs = category ? `?category=${category}` : '';
  return get(`/scenarios/templates${qs}`);
}

export function getTemplate(name: string): Promise<{ template: ScenarioTemplate }> {
  return get(`/scenarios/templates/${name}`);
}

export function runScenario(
  scenarioName: string,
  X: number[][],
  featureNames: string[],
  y?: number[],
  intensity = 1.0,
  areaHa = 1.0
): Promise<{ result: SimulationResult }> {
  return post('/scenarios/run', {
    scenario_name: scenarioName,
    X, y, feature_names: featureNames,
    intensity, area_ha: areaHa,
  });
}

export function compareScenarios(
  scenarioNames: string[],
  X: number[][],
  featureNames: string[],
  y?: number[],
  areaHa = 1.0
): Promise<{ results: SimulationResult[]; comparison: ComparisonReport }> {
  return post('/scenarios/compare', {
    scenario_names: scenarioNames,
    X, y, feature_names: featureNames, area_ha: areaHa,
  });
}

export function runAllScenarios(
  X: number[][],
  featureNames: string[],
  y?: number[],
  areaHa = 1.0
): Promise<{ results: SimulationResult[]; comparison: ComparisonReport }> {
  return post('/scenarios/run-all', {
    X, y, feature_names: featureNames, area_ha: areaHa,
  });
}
