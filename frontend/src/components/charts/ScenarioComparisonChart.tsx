import { useRef, useEffect } from 'react';
import * as echarts from 'echarts';

interface ScenarioData {
  name: string;
  tempReduction: number;
  cost: number;
  costEffectiveness: number;
}

interface ScenarioComparisonChartProps {
  data: ScenarioData[];
  metric?: 'temp' | 'cost' | 'cost_effectiveness';
  title?: string;
  className?: string;
}

const metricConfig = {
  temp: { label: 'Temperature Reduction (°C)', color: '#00C896' },
  cost: { label: 'Cost (USD)', color: '#F6C343' },
  cost_effectiveness: { label: 'Cost Effectiveness (°C/$M)', color: '#3B82F6' },
};

export function ScenarioComparisonChart({ data, metric = 'temp', title, className }: ScenarioComparisonChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts>(null);
  const cfg = metricConfig[metric];

  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    if (!instance.current) instance.current = echarts.init(ref.current);
    const values = data.map((d) => {
      if (metric === 'temp') return d.tempReduction;
      if (metric === 'cost') return d.cost / 1_000_000;
      return d.costEffectiveness;
    });
    const maxVal = Math.max(...values.map(Math.abs), 1);

    instance.current.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(18,27,47,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
        borderWidth: 1,
        textStyle: { color: '#F9FAFB', fontSize: 12 },
      },
      grid: { left: 120, right: 40, bottom: 24, top: title ? 40 : 16 },
      xAxis: {
        type: 'value',
        max: maxVal * 1.2,
        axisLabel: { color: '#94A3B8', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)', type: 'dashed' } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: data.map((d) => d.name),
        axisLabel: { color: '#F9FAFB', fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar',
        data: values.map((v) => ({
          value: Math.abs(v),
          itemStyle: {
            color: cfg.color,
            borderRadius: [0, 6, 6, 0],
          },
        })),
        barMaxWidth: 24,
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
  }, [data, metric, title]);

  return <div ref={ref} className={className || 'h-72 w-full'} />;
}
