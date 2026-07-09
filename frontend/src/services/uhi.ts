import { post } from './api';
import type { UHIResult, Hotspot } from '@/types';

export function detectHotspots(
  lst: number[][],
  ndvi?: number[][],
  ndbi?: number[][],
  method = 'adaptive_threshold'
): Promise<UHIResult> {
  return post('/heat/detect', { lst, ndvi, ndbi, method });
}

export function getHotspotDetail(id: string): Promise<Hotspot> {
  return post('/heat/hotspot', { id });
}

export function getUHISummary(): Promise<{
  total_hotspots: number;
  avg_severity: number;
  total_area: number;
}> {
  return post('/heat/summary', {});
}
