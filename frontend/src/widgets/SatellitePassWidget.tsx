import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Satellite, RefreshCw } from 'lucide-react';

export default function SatellitePassWidget() {
  const [nextPass, setNextPass] = useState('');
  const [status, setStatus] = useState<'idle' | 'pending' | 'processing' | 'complete'>('idle');

  useEffect(() => {
    // Simulate checking for next satellite pass
    const updatePass = () => {
      const hours = Math.floor(Math.random() * 3) + 1;
      const minutes = Math.floor(Math.random() * 60);
      const time = new Date();
      time.setHours(time.getHours() + hours);
      time.setMinutes(minutes);
      setNextPass(time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));

      // Simulate status changes
      const statuses: ('idle' | 'pending' | 'processing' | 'complete')[] =
        ['idle', 'pending', 'processing', 'complete'];
      setStatus(statuses[Math.floor(Math.random() * statuses.length)]);
    };

    const interval = setInterval(updatePass, 10000);
    updatePass(); // Initial call
    return () => clearInterval(interval);
  }, []);

  const statusLabels: Record<typeof status, { label: string; variant: 'default' | 'success' | 'warning' | 'danger' | 'info' }> = {
    idle: { label: 'Idle', variant: 'default' },
    pending: { label: 'Pending', variant: 'warning' },
    processing: { label: 'Processing', variant: 'info' },
    complete: { label: 'Complete', variant: 'success' }
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            Next Satellite Pass
          </h3>
          <Button variant="outline" size="sm" onClick={() => {
            // Trigger refresh
            setStatus('processing');
            setTimeout(() => setStatus('complete'), 2000);
          }} className="p-1">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <Satellite className="h-5 w-5 text-accent" />
            <span className="font-medium">Next Pass: </span>
            <span className="text-text-primary dark:text-text-primary-dark">{nextPass}</span>
          </div>
          <Badge variant={statusLabels[status].variant} className="ml-2">
            {statusLabels[status].label}
          </Badge>
        </div>

        <div className="space-y-2 text-sm text-text-secondary">
          <div className="flex justify-between">
            <span>Satellite:</span>
            <span>Landsat 9</span>
          </div>
          <div className="flex justify-between">
            <span>Pass Type:</span>
            <span>Descending</span>
          </div>
          <div className="flex justify-between">
            <span>Resolution:</span>
            <span>30m</span>
          </div>
          <div className="flex justify-between">
            <span>Cloud Cover:</span>
            <span className={`${Math.random() < 0.3 ? 'text-success' : Math.random() < 0.7 ? 'text-warning' : 'text-danger'}`}>
              {Math.floor(Math.random() * 100)}%
            </span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-text-secondary">Data Freshness: </span>
            <span className="font-medium text-text-primary dark:text-text-primary-dark">
              12 min ago
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}