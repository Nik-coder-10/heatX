import { useRef, useEffect, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchWeather } from '@/services/weatherApi';
import { getHeatspotData, type HeatspotData } from '@/services/heatspotModel';
import { clsx } from 'clsx';
import { Maximize2, Minimize2, Thermometer, CloudSun } from 'lucide-react';

interface CanvasHeatmapProps {
  lat?: number;
  lng?: number;
  cityName?: string;
  className?: string;
}

const TILE_PROVIDERS = [
  {
    name: 'OpenStreetMap',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  {
    name: 'CartoDB Positron',
    url: 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    attr: '&copy; <a href="https://carto.com/">CARTO</a>',
  },
  {
    name: 'CartoDB Dark Matter',
    url: 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    attr: '&copy; <a href="https://carto.com/">CARTO</a>',
  },
];

let tileIndex = 0;

function heatColor(t: number, min: number, max: number): string {
  const ratio = Math.max(0, Math.min(1, (t - min) / (max - min)));
  return `rgb(${ratio < 0.5 ? 255 : Math.round(255 - (ratio - 0.5) * 510)},${Math.round(Math.min(255, (1 - ratio) * 260))},${Math.round(Math.max(0, 80 - ratio * 160))})`;
}

export function CanvasHeatmap({ lat = 20.59, lng = 78.96, cityName = '', className }: CanvasHeatmapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [tileFailed, setTileFailed] = useState(false);
  const [weather, setWeather] = useState<{ current: number; feelsLike: number; humidity: number; label: string } | null>(null);
  const [modelData, setModelData] = useState<HeatspotData | null>(null);
  const [loading, setLoading] = useState(true);
  const [modelLoading, setModelLoading] = useState(false);

  // weather fetch
  useEffect(() => {
    let dead = false;
    setLoading(true);
    fetchWeather(lat, lng)
      .then((w) => {
        if (dead) return;
        setWeather({ current: w.currentTemp, feelsLike: w.feelsLike, humidity: w.humidity, label: `${w.currentTemp.toFixed(1)}°C` });
        setLoading(false);
      })
      .catch((e) => {
        if (dead) return;
        console.warn('Weather fetch failed:', e.message);
        setWeather({ current: 30, feelsLike: 30, humidity: 50, label: '30.0°C (est.)' });
        setLoading(false);
      });
    return () => { dead = true; };
  }, [lat, lng]);

  // heatspot model — runs when weather data is available
  useEffect(() => {
    if (!weather || loading) return;
    let dead = false;
    setModelLoading(true);
    getHeatspotData(lat, lng, weather.current)
      .then((data) => { if (!dead) { setModelData(data); setModelLoading(false); } })
      .catch((e) => {
        if (dead) return;
        console.warn('Heatspot model failed:', e.message);
        setModelLoading(false);
      });
    return () => { dead = true; };
  }, [lat, lng, weather, loading]);

  // init leaflet map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = L.map(mapContainer.current, {
      center: [lat, lng],
      zoom: 10,
      zoomControl: false,
      attributionControl: false,
    });
    L.control.zoom({ position: 'topright' }).addTo(map);
    L.control.attribution({ position: 'bottomright', prefix: false }).addTo(map);

    function addTiles(idx: number) {
      if (tileLayerRef.current) map.removeLayer(tileLayerRef.current);
      const provider = TILE_PROVIDERS[idx % TILE_PROVIDERS.length];
      const layer = L.tileLayer(provider.url, {
        maxZoom: 19,
        attribution: provider.attr,
        errorTileUrl: '',
      });
      layer.on('tileerror', () => {
        console.warn(`Tile provider "${provider.name}" failed, trying next...`);
        tileIndex = (idx + 1) % TILE_PROVIDERS.length;
        setTileFailed(true);
        addTiles(tileIndex);
      });
      layer.addTo(map);
      tileLayerRef.current = layer;
    }

    addTiles(tileIndex);

    const check = () => { setMapReady(true); map.invalidateSize(); };
    map.once('load', check);
    const fallbackTimer = setTimeout(() => { if (!mapReady) { setMapReady(true); map.invalidateSize(); } }, 5000);
    map.on('load', () => clearTimeout(fallbackTimer));

    mapRef.current = map;
    return () => { clearTimeout(fallbackTimer); map.remove(); mapRef.current = null; tileLayerRef.current = null; };
  }, []);

  // fly to location on lat/lng change
  useEffect(() => {
    const map = mapRef.current;
    if (map && mapReady) {
      map.flyTo([lat, lng], 10, { duration: 1.2 });
    }
  }, [lat, lng, mapReady]);

  // draw canvas heatmap overlay
  useEffect(() => {
    if (!modelData || modelLoading || !mapReady) return;
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;

    const render = () => {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const rect = wrapper.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.scale(dpr, dpr);
      const w = rect.width;
      const h = rect.height;

      ctx.clearRect(0, 0, w, h);

      const temps = modelData.temps;
      const minT = modelData.minTemp;
      const maxT = modelData.maxTemp;
      const range = maxT - minT || 1;
      const rows = temps.length;
      const cols = temps[0].length;
      const cellW = w / cols;
      const cellH = h / rows;

      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const t = temps[row][col];
          const ratio = (t - minT) / range;
          const r = Math.min(255, Math.round(ratio * 360));
          const g = Math.min(255, Math.round((1 - ratio) * 260));
          const b = Math.max(0, Math.round(80 - ratio * 160));
          ctx.fillStyle = `rgba(${r},${g},${b},0.35)`;
          ctx.fillRect(col * cellW, row * cellH, cellW + 0.5, cellH + 0.5);
        }
      }

      // hotspot radial glows
      modelData.hotspots.forEach((hs) => {
        const cx = (hs.x / cols) * w;
        const cy = (hs.y / rows) * h;
        const radius = 28 + hs.intensity * 30;
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
        g.addColorStop(0, `rgba(255, 50, 70, ${hs.intensity * 0.55})`);
        g.addColorStop(0.35, `rgba(255, 100, 50, ${hs.intensity * 0.25})`);
        g.addColorStop(1, 'rgba(255, 92, 114, 0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // city label
      ctx.save();
      ctx.shadowColor = 'rgba(0,0,0,0.85)';
      ctx.shadowBlur = 8;
      ctx.font = 'bold 15px Inter, system-ui, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#fff';
      ctx.fillText(cityName || `${lat.toFixed(2)}, ${lng.toFixed(2)}`, 14, 14);
      ctx.font = '11px Inter, system-ui, sans-serif';
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.fillText(`${modelData.avgTemp.toFixed(2)}°C avg · ${modelData.hotspots.length} hotspots`, 14, 34);
      ctx.restore();

      // color bar
      const barY = h - 34;
      const barW = Math.min(140, w * 0.32);
      const barH = 8;
      const barX = w - barW - 14;
      for (let i = 0; i < barW; i++) {
        ctx.fillStyle = heatColor(minT + (i / barW) * range, minT, maxT);
        ctx.fillRect(barX + i, barY, 1, barH);
      }
      ctx.font = '9px Inter, system-ui, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      ctx.fillText(`${minT.toFixed(2)}°C`, barX, barY + barH + 3);
      ctx.textAlign = 'right';
      ctx.fillText(`${maxT.toFixed(2)}°C`, barX + barW, barY + barH + 3);
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(wrapper);
    return () => ro.disconnect();
  }, [modelData, modelLoading, mapReady, cityName, lat, lng]);

  const toggleFullscreen = () => {
    const el = wrapperRef.current;
    if (!el) return;
    if (!document.fullscreenElement) { el.requestFullscreen?.().catch(() => {}); }
    else { document.exitFullscreen?.().catch(() => {}); }
  };

  useEffect(() => {
    const fn = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', fn);
    return () => document.removeEventListener('fullscreenchange', fn);
  }, []);

  return (
    <div
      ref={wrapperRef}
      className={clsx(
        'relative rounded-xl overflow-hidden border border-border',
        fullscreen && 'fixed inset-0 z-[9999] rounded-none border-0',
        className,
      )}
    >
      <div ref={mapContainer} className="absolute inset-0 z-0" />

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-30 gap-2 pointer-events-none">
          <CloudSun className="h-5 w-5 text-accent animate-pulse" />
          <span className="text-sm text-text-secondary">Loading weather data...</span>
        </div>
      )}

      {modelLoading && weather && (
        <div className="absolute inset-0 flex items-center justify-center z-30 gap-2 pointer-events-none">
          <CloudSun className="h-5 w-5 text-accent animate-pulse" />
          <span className="text-sm text-text-secondary">Analyzing environmental factors...</span>
        </div>
      )}

      {!modelLoading && modelData && mapReady && (
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full z-10 pointer-events-none block" />
      )}

      {weather && !loading && (
        <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-black/60 backdrop-blur-sm border border-white/10 text-xs text-white shadow-lg pointer-events-none">
          <Thermometer className="h-3.5 w-3.5 text-danger" />
          {weather.label}
          {weather.feelsLike !== weather.current && (
            <span className="text-text-secondary">(feels {weather.feelsLike.toFixed(1)})</span>
          )}
          {weather.humidity && (
            <span className="text-text-secondary">{weather.humidity}% RH</span>
          )}
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span className="text-text-secondary">Live</span>
        </div>
      )}

      {tileFailed && (
        <div className="absolute bottom-10 right-3 z-20 px-2 py-1 rounded bg-amber-900/70 text-amber-200 text-[9px]">
          Retrying tile source...
        </div>
      )}

      <button
        onClick={toggleFullscreen}
        className="absolute bottom-3 right-3 z-20 w-8 h-8 rounded-lg bg-black/60 backdrop-blur-sm border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors text-white/70 hover:text-white shadow-lg"
        title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
      >
        {fullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
      </button>
    </div>
  );
}
