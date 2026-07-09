import { clsx } from 'clsx';
import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}

const variants = {
  default: 'bg-white/[0.04] text-text-secondary border-white/5',
  success: 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/10',
  warning: 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/10',
  danger: 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/10',
  info: 'bg-[#60A5FA]/10 text-[#60A5FA] border-[#60A5FA]/10',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center rounded-lg px-2 py-0.5 text-2xs font-medium border',
      variants[variant], className,
    )}>
      {children}
    </span>
  );
}
