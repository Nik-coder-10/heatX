import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

const sizes = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-3.5 py-2 text-sm gap-2',
  lg: 'px-5 py-2.5 text-sm gap-2',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        variant === 'primary' ? 'btn-primary ' + sizes[size] :
        variant === 'secondary' ? 'btn-secondary ' + sizes[size] :
        variant === 'outline' ? 'btn-secondary ' + sizes[size] :
        variant === 'ghost' ? 'btn-ghost ' + sizes[size] :
        'bg-[#EF4444] text-white hover:bg-[#EF4444]/90 ' + sizes[size],
        'rounded-xl',
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  ),
);

Button.displayName = 'Button';
