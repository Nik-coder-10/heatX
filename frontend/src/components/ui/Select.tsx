import { forwardRef, type SelectHTMLAttributes } from 'react';
import { clsx } from 'clsx';
import { ChevronDown } from 'lucide-react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Array<{ value: string; label: string }>;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, ...props }, ref) => (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-xs font-medium text-text-secondary">{label}</label>
      )}
      <div className="relative">
        <select
          ref={ref}
          className={clsx(
            'input-field appearance-none pr-9',
            className,
          )}
          {...props}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-secondary" />
      </div>
    </div>
  ),
);

Select.displayName = 'Select';
