import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard, Satellite, Thermometer, BarChart3, Flame,
  TrendingUp, Lightbulb, Beaker, Brain, FileText, Shield,
  PanelRightClose, PanelRightOpen,
} from 'lucide-react';
import { useState } from 'react';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/satellite', icon: Satellite, label: 'Satellite Upload' },
  { to: '/lst', icon: Thermometer, label: 'LST Viewer' },
  { to: '/indices', icon: BarChart3, label: 'Spectral Indices' },
  { to: '/uhi', icon: Flame, label: 'Urban Heat' },
  { to: '/forecasting', icon: TrendingUp, label: 'Forecasting' },
  { to: '/recommendations', icon: Lightbulb, label: 'Recommendations' },
  { to: '/scenarios', icon: Beaker, label: 'Scenario Simulator' },
  { to: '/xai', icon: Brain, label: 'Explainability' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/admin', icon: Shield, label: 'Admin' },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const [hovered, setHovered] = useState(false);
  const effectiveCollapsed = collapsed && !hovered;

  return (
    <aside
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={clsx(
        'fixed left-3 top-3 bottom-3 z-50 flex flex-col rounded-2xl glass-strong',
        'transition-all duration-350 ease-premium overflow-hidden',
        effectiveCollapsed ? 'w-[64px]' : 'w-56',
      )}
    >
      <div className="flex items-center h-14 px-3.5 gap-2.5 border-b border-white/5">
        <div className={clsx(
          'flex items-center justify-center flex-shrink-0 rounded-xl transition-all duration-350',
          effectiveCollapsed ? 'w-8 h-8' : 'w-8 h-8',
        )}>
          <svg viewBox="0 0 32 32" className="w-full h-full" fill="none">
            <rect width="32" height="32" rx="8" fill="#00E5A8" />
            <path d="M8 22V10l8 6-8 6z" fill="#030712" />
            <path d="M16 22V10l8 6-8 6z" fill="#030712" opacity="0.6" />
            <path d="M24 22V10" stroke="#030712" strokeWidth="2" strokeLinecap="round" opacity="0.4" />
          </svg>
        </div>
        {!effectiveCollapsed && (
          <span className="text-sm font-semibold text-text-primary tracking-tight whitespace-nowrap">
            <span className="text-[#00E5A8]">Heat</span>X
          </span>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-2.5 px-2 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => clsx(
              'nav-pill rounded-xl text-xs',
              isActive ? 'nav-pill-active' : 'nav-pill-inactive',
              effectiveCollapsed && 'justify-center px-0 py-2.5',
            )}
            title={effectiveCollapsed ? label : undefined}
          >
            <Icon className="h-[17px] w-[17px] flex-shrink-0" />
            {!effectiveCollapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/5 p-2 space-y-1">
        <button
          onClick={onToggle}
          className={clsx(
            'flex items-center w-full rounded-xl text-xs font-medium transition-all duration-300 ease-premium',
            'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]',
            effectiveCollapsed ? 'justify-center p-2.5' : 'gap-3 px-3 py-2.5',
          )}
        >
          {effectiveCollapsed ? (
            <PanelRightOpen className="h-[17px] w-[17px]" />
          ) : (
            <>
              <PanelRightClose className="h-[17px] w-[17px]" />
              <span>Collapse</span>
            </>
          )}
        </button>
        <div className={clsx(
          'flex items-center rounded-xl transition-all duration-300',
          effectiveCollapsed ? 'justify-center p-2' : 'gap-2.5 px-3 py-2',
        )}>
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#00E5A8]/30 to-[#22D3EE]/20 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-semibold text-[#00E5A8]">JD</span>
          </div>
          {!effectiveCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-text-primary truncate">Jane Doe</p>
              <p className="text-2xs text-text-secondary">Administrator</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
