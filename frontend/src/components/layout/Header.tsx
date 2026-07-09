import { useState, useRef, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Menu, Search, Bell, Settings, ChevronDown, Sun, MapPin } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { clsx } from 'clsx';
import { LOCATIONS } from '@/services/locations';

interface HeaderProps {
  onMenuClick: () => void;
}

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/satellite': 'Satellite Upload',
  '/lst': 'LST Viewer',
  '/indices': 'Spectral Indices',
  '/uhi': 'Urban Heat Viewer',
  '/forecasting': 'Forecasting',
  '/recommendations': 'Recommendations',
  '/scenarios': 'Scenario Simulator',
  '/xai': 'Model Explainability',
  '/reports': 'Reports',
  '/admin': 'Admin',
};

export function Header({ onMenuClick }: HeaderProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { toggle } = useTheme();
  const title = pageTitles[location.pathname] || 'Urban Climate Intelligence Platform';

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<typeof LOCATIONS>([]);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    const q = query.toLowerCase();
    setSearchResults(
      LOCATIONS.filter((l) => l.name.toLowerCase().includes(q)).slice(0, 5)
    );
  }, []);

  const selectLocation = (loc: typeof LOCATIONS[0]) => {
    setSearchQuery('');
    setSearchResults([]);
    setSearchOpen(false);
    const currentPath = location.pathname === '/' ? '/lst' : location.pathname;
    navigate(`${currentPath}?lat=${loc.lat}&lng=${loc.lng}&name=${encodeURIComponent(loc.name)}`);
  };

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setSearchOpen(true);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        inputRef.current?.blur();
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, []);

  return (
    <header className="sticky top-0 z-40 h-14 flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 rounded-xl hover:bg-white/[0.04] transition-colors"
          aria-label="Toggle menu"
        >
          <Menu className="h-4 w-4 text-text-secondary" />
        </button>
        <h1 className="text-sm font-semibold text-text-primary tracking-tight">{title}</h1>
      </div>

      <div className="flex items-center gap-1.5">
        <div ref={searchRef} className="relative hidden md:block">
          <div
            className={clsx(
              'flex items-center gap-2 rounded-xl px-3 py-1.5 border min-w-[220px] transition-all duration-250',
              searchOpen
                ? 'border-[#00E5A8]/40 bg-[rgba(12,24,44,0.75)] shadow-[0_0_20px_rgba(0,229,168,0.06)]'
                : 'border-white/5 bg-[rgba(7,17,32,0.5)]',
            )}
          >
            <Search className="h-3.5 w-3.5 text-text-secondary" />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => { handleSearch(e.target.value); setSearchOpen(true); }}
              onFocus={() => setSearchOpen(true)}
              placeholder="Search cities..."
              className="bg-transparent text-xs text-text-primary placeholder:text-text-secondary/40 outline-none border-none w-full"
            />
            <kbd className="text-2xs text-text-secondary/40 px-1 py-0.5 rounded bg-white/[0.04] flex items-center gap-0.5 flex-shrink-0">
              <span className="text-[10px]">⌘</span>K
            </kbd>
          </div>
          {searchOpen && searchResults.length > 0 && (
            <div className="absolute top-full mt-1.5 left-0 right-0 rounded-xl border border-white/[0.06] bg-[rgba(12,24,44,0.9)] backdrop-blur-xl shadow-modal overflow-hidden animate-scale-in">
              {searchResults.map((loc) => (
                <button
                  key={loc.name}
                  onClick={() => selectLocation(loc)}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs text-text-primary hover:bg-white/[0.04] transition-colors text-left"
                >
                  <MapPin className="h-3.5 w-3.5 text-[#00E5A8] flex-shrink-0" />
                  <span>{loc.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={toggle}
          className="p-2 rounded-xl hover:bg-white/[0.04] transition-colors text-text-secondary hover:text-text-primary"
          aria-label="Toggle theme"
        >
          <Sun className="h-4 w-4" />
        </button>

        <button
          onClick={() => navigate('/admin')}
          className="relative p-2 rounded-xl hover:bg-white/[0.04] transition-colors text-text-secondary hover:text-text-primary"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[#EF4444]" />
        </button>

        <button
          onClick={() => navigate('/admin')}
          className="p-2 rounded-xl hover:bg-white/[0.04] transition-colors text-text-secondary hover:text-text-primary"
          aria-label="Settings"
        >
          <Settings className="h-4 w-4" />
        </button>

        <button
          onClick={() => navigate('/admin')}
          className="flex items-center gap-2.5 pl-2.5 ml-1.5 border-l border-white/[0.06]"
        >
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#00E5A8]/30 to-[#22D3EE]/20 flex items-center justify-center">
            <span className="text-xs font-semibold text-[#00E5A8]">AD</span>
          </div>
          <div className="hidden md:flex items-center gap-1">
            <span className="text-xs font-medium text-text-primary">Admin</span>
            <ChevronDown className="h-3 w-3 text-text-secondary" />
          </div>
        </button>
      </div>
    </header>
  );
}
