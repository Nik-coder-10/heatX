import { clsx } from 'clsx';

export function Spinner({ className, size = 'md' }: { className?: string; size?: 'sm' | 'md' | 'lg' }) {
  const dims = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-10 w-10' };
  return (
    <div className={clsx('flex items-center justify-center', className)} role="status" aria-label="Loading">
      <svg className={clsx('animate-spin text-accent', dims[size])} viewBox="0 0 24 24" fill="none">
        <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-100" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span className="sr-only">Loading...</span>
    </div>
  );
}
