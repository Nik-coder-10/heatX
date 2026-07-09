import { useState, type ReactNode } from 'react';
import { clsx } from 'clsx';

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  className?: string;
}

export function Tabs({ tabs, defaultTab, className }: TabsProps) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.id);
  const activeTab = tabs.find((t) => t.id === active);

  return (
    <div className={className}>
      <div className="flex gap-0.5 p-0.5 rounded-lg bg-surface-200/50 border border-border w-fit" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            onClick={() => setActive(tab.id)}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200',
              active === tab.id
                ? 'bg-surface-300 text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="pt-4 animate-fade-in" role="tabpanel">
        {activeTab?.content}
      </div>
    </div>
  );
}
