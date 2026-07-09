import { useState } from 'react';
import { FileText, Trash2, Edit3, Check, X, Download } from 'lucide-react';
import { clsx } from 'clsx';
import type { UploadedFile } from '@/types';

interface FileListProps {
  files: UploadedFile[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, name: string) => void;
  onExport: (file: UploadedFile) => void;
}

export function FileList({ files, selectedId, onSelect, onDelete, onRename, onExport }: FileListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  if (files.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
        <p className="text-sm">No files uploaded</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {files.map((file) => (
        <div
          key={file.id}
          className={clsx(
            'flex items-center justify-between p-3 rounded-lg border transition-all duration-200 cursor-pointer',
            selectedId === file.id
              ? 'bg-accent/5 border-accent/30'
              : 'bg-surface-200/50 border-border hover:border-white/10 hover:bg-surface-200/80',
          )}
          onClick={() => onSelect(file.id === selectedId ? null : file.id)}
        >
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
              <FileText className="h-4 w-4 text-accent" />
            </div>
            <div className="min-w-0 flex-1">
              {editingId === file.id ? (
                <form
                  onSubmit={(e) => { e.preventDefault(); onRename(file.id, editName); setEditingId(null); }}
                  className="flex items-center gap-1"
                >
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="input-field py-1 text-xs"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                  <button type="submit" className="p-1 hover:text-accent cursor-pointer" onClick={(e) => e.stopPropagation()}>
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button type="button" className="p-1 hover:text-danger cursor-pointer" onClick={(e) => { e.stopPropagation(); setEditingId(null); }}>
                    <X className="h-3.5 w-3.5" />
                  </button>
                </form>
              ) : (
                <p className="text-sm font-medium text-text-primary truncate">{file.name}</p>
              )}
              <p className="text-xs text-text-secondary">
                {file.type.toUpperCase()} &middot; {file.rows} rows &middot; {(file.size / 1024).toFixed(0)} KB
              </p>
            </div>
          </div>

          <div className="flex items-center gap-0.5 flex-shrink-0 ml-2">
            <button
              onClick={(e) => { e.stopPropagation(); setEditingId(file.id); setEditName(file.name); }}
              className="p-1.5 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors"
              title="Rename"
            >
              <Edit3 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onExport(file); }}
              className="p-1.5 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors"
              title="Export"
            >
              <Download className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(file.id); }}
              className="p-1.5 rounded-lg hover:bg-danger/10 text-text-secondary hover:text-danger transition-colors"
              title="Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
