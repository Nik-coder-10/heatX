import { useEffect, type ReactNode } from 'react';
import { clsx } from 'clsx';
import { X } from 'lucide-react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const sizes = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
};

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
      const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
      window.addEventListener('keydown', handler);
      return () => {
        document.body.style.overflow = '';
        window.removeEventListener('keydown', handler);
      };
    }
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className={clsx(
        'relative w-full rounded-xl bg-surface-200 border border-border shadow-modal',
        'animate-scale-in',
        sizes[size],
      )}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-white/5 transition-colors" aria-label="Close modal">
            <X className="h-4 w-4 text-text-secondary" />
          </button>
        </div>
        <div className="px-5 py-4 max-h-[70vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
