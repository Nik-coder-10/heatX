import { clsx } from 'clsx';

interface LayerItem {
  id: string;
  label: string;
  visible: boolean;
  color?: string;
}

interface LayerControlProps {
  layers: LayerItem[];
  onToggle: (id: string) => void;
  className?: string;
}

export function LayerControl({ layers, onToggle, className }: LayerControlProps) {
  return (
    <div className={clsx(
      'rounded-xl border border-surface-200 dark:border-surface-700',
      'bg-white/90 dark:bg-surface-800/90 backdrop-blur-sm',
      'p-3 shadow-lg min-w-[180px]', className,
    )}>
      <h4 className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400 mb-2">
        Layers
      </h4>
      <div className="space-y-1.5">
        {layers.map((layer) => (
          <label
            key={layer.id}
            className="flex items-center gap-2.5 px-1 py-1 rounded hover:bg-surface-100 dark:hover:bg-surface-700/50 cursor-pointer transition-colors"
          >
            <input
              type="checkbox"
              checked={layer.visible}
              onChange={() => onToggle(layer.id)}
              className="rounded border-surface-300 dark:border-surface-600 text-primary-600 focus:ring-primary-500 cursor-pointer"
            />
            {layer.color && (
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: layer.color }}
              />
            )}
            <span className="text-sm text-surface-700 dark:text-surface-300 select-none">
              {layer.label}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
