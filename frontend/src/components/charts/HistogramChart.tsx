import { useRef, useEffect } from 'react';
import * as echarts from 'echarts';

interface HistogramChartProps {
  data: number[];
  bins?: number;
  title?: string;
  color?: string;
  className?: string;
}

export function HistogramChart({ data, bins = 20, title, color = '#00C896', className }: HistogramChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts>(null);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    if (!instance.current) instance.current = echarts.init(ref.current);
    const min = Math.min(...data);
    const max = Math.max(...data);
    const binWidth = (max - min) / bins || 1;
    const counts = new Array(bins).fill(0);
    data.forEach((v) => {
      const idx = Math.min(Math.floor((v - min) / binWidth), bins - 1);
      counts[idx]++;
    });
    const labels = counts.map((_, i) => {
      const lo = min + i * binWidth;
      const hi = lo + binWidth;
      return `${lo.toFixed(1)}-${hi.toFixed(1)}`;
    });

    instance.current.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(18,27,47,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
        borderWidth: 1,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
      },
      grid: { left: 56, right: 16, bottom: 52, top: title ? 40 : 16 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: '#94A3B8', fontSize: 9, rotate: 45 },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94A3B8', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)', type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: counts,
        itemStyle: { color, borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 28,
        animationDuration: 600,
        animationEasing: 'cubicOut',
      }],
      ...(title ? { title: { text: title, left: 'center', textStyle: { color: '#F9FAFB', fontSize: 13, fontWeight: 600 } } } : {}),
    });
    const resize = () => instance.current?.resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [data, bins, title, color]);

  return <div ref={ref} className={className || 'h-72 w-full'} />;
}
