// =============================================================================
// Urban Heat Mitigation Platform - K6 Load Test
// Run: docker run --rm -i grafana/k6 run - < deploy/tests/load-test.js
// =============================================================================

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ===== Configuration =====
const BASE_URL = __ENV.BASE_URL || 'http://localhost/api/v1';
const STAGES = [
  { duration: '2m', target: 50 },   // Ramp up to 50 users
  { duration: '5m', target: 100 },  // Hold at 100 users
  { duration: '2m', target: 200 },  // Ramp up to 200 users
  { duration: '5m', target: 200 },  // Hold at 200 users
  { duration: '2m', target: 0 },    // Ramp down
];

// ===== Custom Metrics =====
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const successCount = new Counter('successful_requests');

// ===== Options =====
export const options = {
  stages: STAGES,
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests must complete within 2s
    http_req_failed: ['rate<0.05'],     // Error rate must be < 5%
    errors: ['rate<0.05'],
  },
  userAgent: 'UrbanHeat-K6-LoadTest/1.0',
};

// ===== Setup =====
export function setup() {
  // Health check before starting
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check passed': (r) => r.status === 200,
  });
  return { baseUrl: BASE_URL };
}

// ===== Main Test =====
export default function (data) {
  const baseUrl = data.baseUrl;

  group('Health Checks', () => {
    const res = http.get(`${baseUrl}/health`);
    apiLatency.add(res.timings.duration);
    errorRate.add(res.status >= 400);
    check(res, {
      'health endpoint OK': (r) => r.status === 200,
      'health response time < 500ms': (r) => r.timings.duration < 500,
    });
    if (res.status < 400) successCount.add(1);
    sleep(1);
  });

  group('UHI Detection', () => {
    const payload = JSON.stringify({
      lat: 12.9716 + (Math.random() - 0.5) * 0.1,
      lon: 77.5946 + (Math.random() - 0.5) * 0.1,
      radius_km: 10,
    });
    const res = http.post(`${baseUrl}/heat/detect`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    apiLatency.add(res.timings.duration);
    errorRate.add(res.status >= 400);
    check(res, {
      'UHI detection OK': (r) => r.status === 200 || r.status === 422,
    });
    if (res.status < 400) successCount.add(1);
    sleep(2);
  });

  group('Spectral Indices', () => {
    const payload = JSON.stringify({
      lat: 12.9716,
      lon: 77.5946,
      indices: ['ndvi', 'ndwi', 'nbri'],
    });
    const res = http.post(`${baseUrl}/gis/indices`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    apiLatency.add(res.timings.duration);
    errorRate.add(res.status >= 400);
    check(res, {
      'indices endpoint OK': (r) => r.status === 200 || r.status === 422,
    });
    if (res.status < 400) successCount.add(1);
    sleep(2);
  });

  group('Recommendations', () => {
    const payload = JSON.stringify({
      lat: 12.9716,
      lon: 77.5946,
      budget: 1000000,
      area_hectares: 100,
    });
    const res = http.post(`${baseUrl}/recommendations/generate`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    apiLatency.add(res.timings.duration);
    errorRate.add(res.status >= 400);
    check(res, {
      'recommendations endpoint OK': (r) => r.status === 200 || r.status === 422,
    });
    if (res.status < 400) successCount.add(1);
    sleep(3);
  });

  group('Scenario Templates', () => {
    const res = http.get(`${baseUrl}/scenarios/templates`);
    apiLatency.add(res.timings.duration);
    errorRate.add(res.status >= 400);
    check(res, {
      'scenario templates OK': (r) => r.status === 200,
    });
    if (res.status < 400) successCount.add(1);
    sleep(1);
  });

  // 50% chance to hit ML endpoints
  if (Math.random() < 0.5) {
    group('ML Predict', () => {
      const payload = JSON.stringify({
        features: [
          [12.97, 77.59, 540, 0.45, 0.32, 0.23, 0.12, 298.5, 305.2, 0.15, 0.08, 0.22],
        ],
        model_type: 'random_forest',
        model_kwargs: { n_estimators: 100, max_depth: 10 },
      });
      const res = http.post(`${baseUrl}/ml/inference/predict`, payload, {
        headers: { 'Content-Type': 'application/json' },
      });
      apiLatency.add(res.timings.duration);
      errorRate.add(res.status >= 400);
      if (res.status < 400) successCount.add(1);
      sleep(2);
    });
  }
}

// ===== Teardown =====
export function teardown(data) {
  const res = http.get(`${data.baseUrl}/health`);
  check(res, { 'final health check OK': (r) => r.status === 200 });
}
