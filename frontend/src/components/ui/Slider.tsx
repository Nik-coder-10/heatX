import { clsx } from 'clsx';

interface SliderProps {
  label?: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (v: number) => void;
  formatValue?: (v: number) => string;
  className?: string;
}

export function Slider({
  label, value, min = 0, max = 1, step = 0.1,
  onChange, formatValue, className,
}: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className={clsx('space-y-2', className)}>
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-text-secondary">{label}</label>
          <span className="text-xs text-text-primary font-mono">
            {formatValue ? formatValue(value) : value.toFixed(2)}
          </span>
        </div>
      )}
      <div className="relative h-1.5 rounded-full bg-white/[0.06]">
        <div
          className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-[#00E5A8] to-[#22D3EE] transition-all duration-200"
          style={{ width: `${pct}%` }}
        />
        <input
          type="range"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          aria-label={label}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-[#00E5A8] border-2 border-[#030712] shadow-[0_0_12px_rgba(0,229,168,0.3)] transition-all duration-200 pointer-events-none"
          style={{ left: `calc(${pct}% - 8px)` }}
        />
      </div>
    </div>
  );
}
