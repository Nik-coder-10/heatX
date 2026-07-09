import { clsx } from 'clsx';

interface LegendItem {
  label: string;
  color: string;
  type?: 'fill' | 'line' | 'circle';
}

interface MapLegendProps {
  items: LegendItem[];
  title?: string;
  className?: string;
}

export function MapLegend({ items, title, className }: MapLegendProps) {
  if (items.length === 0) return null;
  return (
    <div className={clsx(
      'rounded-lg border border-surface-200 dark:border-surface-700',
      'bg-white/90 dark:bg-surface-800/90 backdrop-blur-sm',
      'px-3 py-2 shadow-lg', className,
    )}>
      {title && (
        <h4 className="text-xs font-semibold uppercase tracking-wider text-surface-500 mb-1.5">
          {title}
        </h4>
      )}
      <div className="space-y-1">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            {item.type === 'circle' ? (
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
            ) : item.type === 'line' ? (
              <span className="w-4 h-0.5 flex-shrink-0" style={{ backgroundColor: item.color }} />
            ) : (
              <span className="w-4 h-3 rounded flex-shrink-0" style={{ backgroundColor: item.color }} />
            )}
            <span className="text-xs text-surface-600 dark:text-surface-400">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
