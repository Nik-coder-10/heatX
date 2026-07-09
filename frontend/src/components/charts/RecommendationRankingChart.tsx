import { useRef, useEffect } from 'react';
import * as echarts from 'echarts';

interface RecRankData {
  label: string;
  overallScore: number;
  cost: number;
}

interface RecommendationRankingChartProps {
  data: RecRankData[];
  title?: string;
  className?: string;
}

export function RecommendationRankingChart({ data, title, className }: RecommendationRankingChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts>(null);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    if (!instance.current) instance.current = echarts.init(ref.current);
    const sorted = [...data].sort((a, b) => b.overallScore - a.overallScore);
    const maxScore = Math.max(...sorted.map((d) => d.overallScore), 1);

    instance.current.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(18,27,47,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
        borderWidth: 1,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
        formatter: (params: unknown) => {
          const p = (params as Array<{ name: string; value: number; data: { cost: number } }>)[0];
          const item = sorted.find((d) => d.label === p.name);
          return `<div style="font-size:12px">
            <div style="color:#F9FAFB;font-weight:600;margin-bottom:4px">${p.name}</div>
            <div style="display:flex;justify-content:space-between;color:#94A3B8">
              <span>Score</span><span style="color:#F9FAFB">${p.value.toFixed(2)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;color:#94A3B8">
              <span>Cost</span><span style="color:#F9FAFB">$${(item?.cost || 0).toLocaleString()}</span>
            </div>
          </div>`;
        },
      },
      grid: { left: 120, right: 40, bottom: 16, top: title ? 40 : 16 },
      xAxis: {
        type: 'value',
        max: maxScore * 1.15,
        axisLabel: { color: '#94A3B8', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)', type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: sorted.map((d) => d.label),
        axisLabel: { color: '#F9FAFB', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: sorted.map((d, i) => ({
          value: d.overallScore,
          cost: d.cost,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: i === 0 ? '#00C896' : '#00C89660' },
              { offset: 1, color: i === 0 ? '#14E2A2' : '#00C89630' },
            ]),
            borderRadius: [0, 6, 6, 0],
          },
        })),
        barMaxWidth: 22,
        label: {
          show: true,
          position: 'right',
          formatter: ({ value }: { value: number }) => (value as number).toFixed(2),
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
