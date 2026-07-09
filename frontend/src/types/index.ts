
export interface Hotspot {
  id: string;
  severity: string;
  severity_score: number;
  confidence: number;
  geometry: GeoJSON.Polygon;
  area_sq_km: number;
  perimeter_km: number;
  centroid: [number, number];
  bbox: [number, number, number, number];
  mean_temperature_c: number;
  max_temperature_c: number;
  min_temperature_c: number;
  mean_ndvi: number;
  mean_ndbi: number;
  mean_ndwi: number;
  detection_method: string;
  dominant_landcover: string;
  vegetation_fraction: number;
  builtup_fraction: number;
  compactness: number;
  elongation: number;
  nearest_hotspot_distance_km: number | null;
  recommended_actions: string[];
  pixel_count: number;
  quality_metrics: Record<string, number>;
}

export interface UHIResult {
  hotspots: Hotspot[];
  metadata: Record<string, unknown>;
  statistics: Record<string, unknown>;
  detection_mask?: number[][];
  severity_map?: number[][];
  quality_report?: Record<string, unknown>;
}

export interface PredictionResult {
  values: number[];
  confidence: number | number[] | null;
  uncertainty: Record<string, number> | null;
  feature_importance: Record<string, number> | null;
  model_type: string;
  task: string;
}

export interface ForecastResult {
  current_intensity: number | null;
  future_lst: number[] | null;
  hotspot_probability: number | null;
  future_severity: string | null;
  hotspot_growth: number | null;
  risk_map: number[] | null;
}

export interface ScenarioTemplate {
  name: string;
  description: string;
  category: string;
  cost_per_hectare: number;
  co2_reduction_factor: number;
  features_affected: string[];
  default_parameters: Record<string, number>;
  feature_modifiers?: Record<string, Record<string, number | string>>;
}

export interface SimulationResult {
  scenario_name: string;
  mean_lst_baseline: number;
  mean_lst_simulated: number;
  mean_lst_change: number;
  max_lst_change: number;
  pct_improvement: number;
  total_area_ha: number;
  estimated_cost: number;
  estimated_co2_reduction: number;
  cost_effectiveness: number;
  parameters: Record<string, unknown>;
}

export interface ScoredRecommendation {
  recommendation_type: string;
  label: string;
  description: string;
  estimated_cost: number;
  expected_temperature_reduction: number;
  carbon_reduction: number;
  priority: number;
  cost_effectiveness: number;
  feasibility_score: number;
  overall_score: number;
  area_hectares: number;
  current_temperature_c: number;
  rationale: string;
  feature_attribution: Record<string, number>;
}

export interface RecommendationBundle {
  hotspot_id: string;
  hotspot_severity: string;
  recommendations: ScoredRecommendation[];
  optimization: {
    total_cost: number;
    total_temperature_reduction: number;
    total_carbon_reduction: number;
    budget_utilization: number;
    selected_recommendations: ScoredRecommendation[];
  } | null;
  scenarios: Array<{
    total_cost: number;
    total_temperature_reduction: number;
    budget_utilization: number;
  }> | null;
}

export interface ExplainResult {
  global_explanation?: {
    feature_importance: Record<string, number>;
    top_features: Array<{ name: string; importance: number }>;
  };
  local_explanations?: Array<{
    instance_id: number;
    shap_values: Record<string, number>;
    top_features: Array<{ name: string; value: number; impact: 'positive' | 'negative' }>;
  }>;
  counterfactuals?: Array<{
    original: Record<string, number>;
    counterfactual: Record<string, number>;
    changes: Record<string, { from: number; to: number }>;
  }>;
  confidence?: { overall: number; prediction: number; explanation: number };
  uncertainty?: { overall: number; aleatoric: number; epistemic: number };
}

export interface FeatureImportance {
  feature: string;
  importance: number;
  category?: string;
}

export interface TrainMetrics {
  mae: number;
  rmse: number;
  r2: number;
  mape?: number;
}

export interface SatelliteScene {
  id: string;
  provider: string;
  capture_date: string;
  cloud_cover: number;
  resolution: number;
  bounds: [number, number, number, number];
  thumbnail_url?: string;
  status: string;
}

export interface ComparisonReport {
  best_scenario: string;
  rankings: Array<{
    scenario: string;
    temp_reduction: number;
    cost: number;
    cost_effectiveness: number;
    co2_reduction: number;
    improvement_pct: number;
  }>;
  temperature_range: { min: number; max: number; mean: number };
  cost_range: { min: number; max: number; mean: number };
}

export interface UploadedFile {
  id: string;
  name: string;
  type: 'csv' | 'xlsx' | 'geojson';
  size: number;
  rows: number;
  columns: string[];
  data: Record<string, unknown>[];
  uploadedAt: string;
  preview?: Record<string, unknown>[];
}

export interface AppState {
  uploadedFiles: UploadedFile[];
  selectedFileId: string | null;
  selectedLocation: { lat: number; lng: number; name: string } | null;
}

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export interface ApiError {
  status: string;
  message: string;
  detail?: string;
}
