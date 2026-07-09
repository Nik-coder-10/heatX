import { useRef, useEffect } from 'react';
import * as echarts from 'echarts';

interface TemperatureTrendChartProps {
  data: Array<{ date: string; temperature: number }>;
  data2?: Array<{ date: string; temperature: number }>;
  title?: string;
  className?: string;
}

export function TemperatureTrendChart({ data, data2, title, className }: TemperatureTrendChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts>(null);

  useEffect(() => {
    if (!ref.current) return;
    if (!instance.current) {
      instance.current = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    }
    const c = '#00C896';
    const c2 = '#3B82F6';

    instance.current.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(18,27,47,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
        borderWidth: 1,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
        formatter: (params: unknown) => {
          const ps = params as Array<{ seriesName: string; value: number; axisValue: string }>;
          if (!ps) return '';
          return ps.map((p) =>
            `<div style="display:flex;justify-content:space-between;gap:16px">
              <span style="color:#94A3B8">${p.seriesName || ''}</span>
              <span style="color:#F9FAFB;font-weight:600">${p.value?.toFixed(1) ?? ''}°C</span>
            </div>`
          ).join('') +
          `<div style="margin-top:4px;padding-top:4px;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;color:#94A3B8">${ps[0]?.axisValue ?? ''}</div>`;
        },
      },
      grid: { left: 48, right: 16, bottom: 28, top: title ? 40 : 16 },
      xAxis: {
        type: 'category',
        data: data.map((d) => d.date),
        axisLabel: { color: '#94A3B8', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisTick: { show: false },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        min: (value: { min: number }) => Math.floor(value.min - 1),
        axisLabel: { color: '#94A3B8', fontSize: 11, formatter: '{value}°' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)', type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          name: 'Temperature',
          type: 'line',
          data: data.map((d) => d.temperature),
          smooth: true,
          showSymbol: false,
          lineStyle: { color: c, width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0,200,150,0.25)' },
              { offset: 1, color: 'rgba(0,200,150,0.01)' },
            ]),
          },
          animationDuration: 800,
          animationEasing: 'cubicOut',
        },
        ...(data2 ? [{
          name: 'Forecast',
          type: 'line',
          data: data2.map((d) => d.temperature),
          smooth: true,
          showSymbol: false,
          lineStyle: { color: c2, width: 2, type: 'dashed' as const },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(59,130,246,0.2)' },
              { offset: 1, color: 'rgba(59,130,246,0.01)' },
            ]),
          },
          animationDuration: 800,
          animationEasing: 'cubicOut',
        }] : []),
      ],
      ...(title ? { title: { text: title, left: 'center', textStyle: { color: '#F9FAFB', fontSize: 13, fontWeight: 600 } } } : {}),
    });
    const resize = () => instance.current?.resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [data, data2, title]);

  return <div ref={ref} className={className || 'h-72 w-full'} />;
}
