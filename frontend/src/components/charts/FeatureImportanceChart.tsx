import { useRef, useEffect } from 'react';
import * as echarts from 'echarts';

interface FeatureImportanceChartProps {
  data: Array<{ feature: string; importance: number }>;
  title?: string;
  className?: string;
}

export function FeatureImportanceChart({ data, title, className }: FeatureImportanceChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts>(null);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    if (!instance.current) instance.current = echarts.init(ref.current);
    const sorted = [...data].sort((a, b) => b.importance - a.importance);
    const maxVal = Math.max(...sorted.map((d) => d.importance), 1);
    const accent = '#00C896';

    instance.current.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(18,27,47,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
        borderWidth: 1,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
        formatter: (params: unknown) => {
          const p = (params as Array<{ name: string; value: number }>)[0];
          return `<div style="display:flex;justify-content:space-between;gap:16px">
            <span style="color:#94A3B8">${p.name}</span>
            <span style="color:#F9FAFB;font-weight:600">${(p.value * 100).toFixed(1)}%</span>
          </div>`;
        },
      },
      grid: { left: 100, right: 40, bottom: 16, top: title ? 40 : 16 },
      xAxis: {
        type: 'value',
        max: maxVal * 1.15,
        axisLabel: { color: '#94A3B8', fontSize: 11, formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)', type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: sorted.map((d) => d.feature),
        axisLabel: { color: '#F9FAFB', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: sorted.map((d, i) => ({
          value: d.importance,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: i === 0 ? accent : i <= 2 ? '#14E2A2' : '#00C89680' },
              { offset: 1, color: i === 0 ? '#14E2A2' : i <= 2 ? accent : '#00C89640' },
            ]),
            borderRadius: [0, 6, 6, 0],
          },
        })),
        barMaxWidth: 20,
        label: {
          show: true,
          position: 'right',
          formatter: ({ value }: { value: number }) => `${(value as number * 100).toFixed(1)}%`,
          color: '#94A3B8',
          fontSize: 11,
        },
        animationDuration: 600,
        animationEasing: 'cubicOut',
      }],
      ...(title ? { title: { text: title, left: 'center', textStyle: { color: '#F9FAFB', fontSize: 13, fontWeight: 600 } } } : {}),
    });
    const resize = () => instance.current?.resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [data, title]);

  return <div ref={ref} className={className || 'h-72 w-full'} />;
}
