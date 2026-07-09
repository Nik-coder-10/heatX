import { useState } from 'react';
import { clsx } from 'clsx';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  onRowClick?: (item: T) => void;
  className?: string;
}

export function DataTable<T extends object = Record<string, unknown>>({
  columns, data, pageSize = 20, onRowClick, className,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(0);

  const sorted = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const aVal = (a as Record<string, unknown>)[sortKey];
    const bVal = (b as Record<string, unknown>)[sortKey];
    if (aVal == null || bVal == null) return 0;
    const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const totalPages = Math.ceil(sorted.length / pageSize);
  const visibleData = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div className={clsx('glass-card overflow-hidden p-0', className)}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && handleSort(col.key)}
                  className={clsx(
                    'px-4 py-3.5 text-left text-2xs font-semibold uppercase tracking-wider text-text-secondary',
                    col.sortable && 'cursor-pointer hover:text-text-primary select-none',
                    col.className,
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    {col.header}
                    {col.sortable && (
                      sortKey === col.key ? (
                        sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronsUpDown className="h-3 w-3 opacity-30" />
                      )
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {visibleData.map((item, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(item)}
                className={clsx(
                  'transition-colors duration-150',
                  onRowClick && 'cursor-pointer hover:bg-white/[0.02]',
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      'px-4 py-3 text-sm text-text-primary/90 whitespace-nowrap',
                      col.className,
                    )}
                  >
                    {col.render ? col.render(item) : String((item as Record<string, unknown>)[col.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.length === 0 && (
        <div className="px-4 py-12 text-center text-sm text-text-secondary">No data available</div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-white/[0.06]">
          <span className="text-xs text-text-secondary">
            Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div className="flex gap-1">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={clsx(
                  'w-7 h-7 rounded-lg text-xs font-medium transition-colors',
                  page === i ? 'bg-[#00E5A8]/10 text-[#00E5A8]' : 'text-text-secondary hover:bg-white/[0.04]',
                )}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
