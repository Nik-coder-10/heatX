import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import type { UploadedFile } from '@/types';

interface DataPreviewProps {
  file: UploadedFile;
}

export function DataPreview({ file }: DataPreviewProps) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const filtered = useMemo(() => {
    if (!search.trim()) return file.data;
    const q = search.toLowerCase();
    return file.data.filter((row) =>
      Object.values(row).some((v) => String(v).toLowerCase().includes(q))
    );
  }, [file.data, search]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-text-secondary">{filtered.length} of {file.data.length} rows</p>
        <div className="relative w-56">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-secondary" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search data..."
            className="input-field pl-8 text-xs"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="px-3 py-2 text-left text-2xs font-semibold text-text-secondary uppercase">#</th>
              {file.columns.map((col) => (
                <th key={col} className="px-3 py-2 text-left text-2xs font-semibold text-text-secondary uppercase whitespace-nowrap">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {pageData.map((row, i) => (
              <tr key={page * pageSize + i} className="hover:bg-white/[0.02]">
                <td className="px-3 py-2 text-xs text-text-secondary">{page * pageSize + i + 1}</td>
                {file.columns.map((col) => (
                  <td key={col} className="px-3 py-2 text-sm text-text-primary/90 whitespace-nowrap">
                    {String(row[col] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3">
          <p className="text-xs text-text-secondary">Page {page + 1} of {totalPages}</p>
          <div className="flex gap-1">
            <button
              disabled={page === 0}
              onClick={() => setPage(Math.max(0, page - 1))}
              className="px-3 py-1 text-xs rounded-lg border border-border disabled:opacity-40 hover:bg-white/5 cursor-pointer text-text-secondary"
            >
              Prev
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              className="px-3 py-1 text-xs rounded-lg border border-border disabled:opacity-40 hover:bg-white/5 cursor-pointer text-text-secondary"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
