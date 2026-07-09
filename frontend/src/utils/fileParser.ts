import Papa from 'papaparse';
import type { UploadedFile } from '@/types';

function generateId(): string {
  return `file_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

async function parseCSV(file: File): Promise<UploadedFile> {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (results.errors.length > 0 && results.data.length === 0) {
          reject(new Error(`CSV parse error: ${results.errors[0].message}`));
          return;
        }
        const columns = results.meta.fields || [];
        const data = results.data as Record<string, unknown>[];
        resolve({
          id: generateId(),
          name: file.name,
          type: 'csv',
          size: file.size,
          rows: data.length,
          columns,
          data,
          uploadedAt: new Date().toISOString(),
          preview: data.slice(0, 10),
        });
      },
      error: (err) => reject(new Error(err.message)),
    });
  });
}

async function parseExcel(file: File): Promise<UploadedFile> {
  const XLSX = await import('xlsx');
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: 'array' });
  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const json = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: '' });
  const columns = json.length > 0 ? Object.keys(json[0]) : [];
  return {
    id: generateId(),
    name: file.name,
    type: 'xlsx',
    size: file.size,
    rows: json.length,
    columns,
    data: json,
    uploadedAt: new Date().toISOString(),
    preview: json.slice(0, 10),
  };
}

async function parseGeoJSON(file: File): Promise<UploadedFile> {
  const text = await file.text();
  const geojson = JSON.parse(text);
  const features = geojson.features || [];
  const props = features.length > 0 ? Object.keys(features[0].properties || {}) : [];
  return {
    id: generateId(),
    name: file.name,
    type: 'geojson',
    size: file.size,
    rows: features.length,
    columns: ['type', 'geometry.type', ...props],
    data: features,
    uploadedAt: new Date().toISOString(),
    preview: features.slice(0, 10),
  };
}

export async function parseFile(file: File): Promise<UploadedFile> {
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (ext === 'csv') return parseCSV(file);
  if (ext === 'xlsx' || ext === 'xls') return parseExcel(file);
  if (ext === 'geojson' || ext === 'json') return parseGeoJSON(file);
  throw new Error(`Unsupported file type: .${ext}. Supported: CSV, XLSX, GeoJSON`);
}

export function validateFile(file: File): string | null {
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (!['csv', 'xlsx', 'xls', 'geojson', 'json'].includes(ext || '')) {
    return `Unsupported file type .${ext}`;
  }
  if (file.size > 100 * 1024 * 1024) {
    return 'File exceeds 100MB size limit';
  }
  return null;
}
