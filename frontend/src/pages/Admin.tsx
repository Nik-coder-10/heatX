import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { useAppState } from '@/store/AppState';
import { Users, Database, Activity, Settings, RefreshCw, Trash2, BarChart3, HardDrive, CheckCircle, X } from 'lucide-react';
import { clsx } from 'clsx';

interface SystemMetric {
  label: string; value: string; status: 'healthy' | 'warning' | 'critical';
}

interface Toast {
  id: number; message: string; type: 'success' | 'error' | 'info';
}

let toastId = 0;

export default function Admin() {
  const { state } = useAppState();
  const navigate = useNavigate();
  const [refreshing, setRefreshing] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const addToast = useCallback((message: string, type: Toast['type'] = 'success') => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  }, []);

  const handleAction = async (label: string) => {
    setActionLoading(label);
    await new Promise((r) => setTimeout(r, 800));
    setActionLoading(null);
    if (label === 'Clear Cache') addToast('Cache cleared successfully');
    else if (label === 'Run Diagnostics') addToast('Diagnostics complete — all systems operational');
    else if (label === 'System Logs') navigate('/admin');
    else if (label === 'View Storage') addToast(`Storage: ${(state.uploadedFiles.reduce((a, f) => a + f.size, 0) / (1024 * 1024)).toFixed(2)} MB used`);
  };

  const metrics: SystemMetric[] = [
    { label: 'API Status', value: 'Operational', status: 'healthy' },
    { label: 'Database', value: 'Connected', status: 'healthy' },
    { label: 'ML Engine', value: 'Ready', status: 'healthy' },
    { label: 'Storage', value: `${(state.uploadedFiles.reduce((a, f) => a + f.size, 0) / (1024 * 1024)).toFixed(2)} MB used`, status: 'healthy' },
    { label: 'Cache Hit Rate', value: '87%', status: 'healthy' },
    { label: 'Queue Depth', value: `${state.uploadedFiles.length} items`, status: 'warning' },
  ];

  const refresh = async () => {
    setRefreshing(true);
    await new Promise((r) => setTimeout(r, 1000));
    setRefreshing(false);
    addToast('Dashboard refreshed');
  };

  const columns: Column<{ name: string; email: string; role: string; status: string; lastActive: string }>[] = [
    { key: 'name', header: 'Name' },
    { key: 'email', header: 'Email' },
    { key: 'role', header: 'Role' },
    { key: 'status', header: 'Status' },
    { key: 'lastActive', header: 'Last Active' },
  ];

  const users = [
    { name: 'Admin User', email: 'admin@platform.org', role: 'Administrator', status: 'active', lastActive: '5 min ago' },
    { name: 'Dr. Sarah Chen', email: 'sarah.chen@university.edu', role: 'Researcher', status: 'active', lastActive: '2 min ago' },
    { name: 'James Rodriguez', email: 'james.r@cityplanning.gov', role: 'Planner', status: 'active', lastActive: '1 hour ago' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Admin Dashboard</h1>
          <p className="text-sm text-text-secondary mt-0.5">System administration and monitoring</p>
        </div>
        <Button size="sm" variant="secondary" onClick={refresh} loading={refreshing}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Activity, label: 'Uptime', value: '99.97%', color: '#00C896' },
          { icon: Users, label: 'Active Users', value: '3', color: '#3B82F6' },
          { icon: Database, label: 'Datasets', value: String(state.uploadedFiles.length), color: '#F6C343' },
          { icon: BarChart3, label: 'Total Rows', value: state.uploadedFiles.reduce((a, f) => a + f.rows, 0).toLocaleString(), color: '#FF5C72' },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15` }}>
                <s.icon className="h-4 w-4" style={{ color: s.color }} />
              </div>
              <div>
                <p className="text-xl font-bold text-text-primary">{s.value}</p>
                <p className="text-xs text-text-secondary">{s.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card padding="lg">
          <CardTitle className="mb-4">System Health</CardTitle>
          <div className="space-y-2">
            {metrics.map((m) => (
              <div key={m.label} className="flex items-center justify-between p-2.5 rounded-lg hover:bg-white/[0.02] transition-colors">
                <span className="text-sm text-text-primary">{m.label}</span>
                <div className="flex items-center gap-2">
                  <Badge variant={m.status === 'healthy' ? 'success' : m.status === 'warning' ? 'warning' : 'danger'}>
                    {m.status}
                  </Badge>
                  <span className="text-xs text-text-secondary">{m.value}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card padding="lg">
          <CardTitle className="mb-4">Quick Actions</CardTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { label: 'Clear Cache', icon: Trash2 },
              { label: 'Run Diagnostics', icon: Activity },
              { label: 'System Logs', icon: Settings },
              { label: 'View Storage', icon: HardDrive },
            ].map(({ label, icon: Icon }) => (
              <Button
                key={label}
                variant="secondary"
                className="justify-start gap-3"
                loading={actionLoading === label}
                onClick={() => handleAction(label)}
              >
                <Icon className="h-4 w-4" /> {label}
              </Button>
            ))}
          </div>
        </Card>
      </div>

      <Card padding="none">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <CardTitle>User Management</CardTitle>
          <Button size="sm" onClick={() => addToast('User invitation feature coming soon')}>
            <Users className="h-3.5 w-3.5" /> Add User
          </Button>
        </div>
        <DataTable columns={columns} data={users} pageSize={10} />
      </Card>

      <div className="fixed bottom-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={clsx(
              'flex items-center gap-2.5 px-4 py-2.5 rounded-lg shadow-elevated border text-sm animate-slide-up',
              'bg-surface-200 text-text-primary',
              t.type === 'success' && 'border-success/30',
              t.type === 'error' && 'border-danger/30',
              t.type === 'info' && 'border-accent/30',
            )}
          >
            {t.type === 'success' && <CheckCircle className="h-4 w-4 text-success" />}
            <span>{t.message}</span>
            <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} className="ml-2 text-text-secondary hover:text-text-primary">
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
