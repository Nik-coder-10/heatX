import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { clsx } from 'clsx';

export function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#030712] text-text-primary">
      <div className="ambient-bg">
        <div className="ambient-blob w-[600px] h-[600px] bg-[#00E5A8] -top-48 -left-48 animate-float" />
        <div className="ambient-blob w-[500px] h-[500px] bg-[#22D3EE] top-1/2 -right-32 animate-float-slow" style={{ animationDelay: '-3s' }} />
        <div className="ambient-blob w-[400px] h-[400px] bg-[#60A5FA] bottom-0 left-1/3 animate-float" style={{ animationDelay: '-5s' }} />
      </div>
      <div className="ambient-grid" />
      <div className="ambient-noise" />

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />

      <div
        className={clsx(
          'transition-all duration-350 ease-premium relative z-10',
          collapsed ? 'lg:ml-[88px]' : 'lg:ml-[236px]',
        )}
      >
        <div className="mx-auto max-w-[1440px]">
          <Header onMenuClick={() => setMobileOpen(!mobileOpen)} />
          <main className="p-5 lg:p-6 animate-fade-in">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
