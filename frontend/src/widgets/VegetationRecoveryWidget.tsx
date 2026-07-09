import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { MapPin, RefreshCw, Leaf } from 'lucide-react';
import { format } from 'date-fns';

export default function VegetationRecoveryWidget() {
  const [ndvi, setNdvi] = useState(0);
  const [trend, setTrend] = useState(0); // positive for improving
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    const updateData = () => {
      setNdvi(0.2 + Math.random() * 0.6); // 0.2-0.8
      setTrend((Math.random() - 0.5) * 0.02); // -0.01 to 0.01
      setLastUpdated(new Date());
    };

    const interval = setInterval(updateData, 10000);
    updateData();
    return () => clearInterval(interval);
  }, []);

  const getNdviStatus = () => {
    if (ndvi >= 0.6) return { label: 'Healthy', color: 'text-success' };
    if (ndvi >= 0.4) return { label: 'Moderate', color: 'text-warning' };
    return { label: 'Stressed', color: 'text-danger' };
  };

  const getTrendColor = () => {
    if (trend > 0.005) return 'text-success';
    if (trend < -0.005) return 'text-danger';
    return 'text-text-secondary';
  };

  const { label: statusLabel, color: statusColor } = getNdviStatus();
  const trendColor = getTrendColor();

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            Vegetation Recovery Index
          </h3>
          <Badge variant="info" className="text-xs">
            NDVI Trend
          </Badge>
        </div>

        <div className="flex items-center mb-6">
          <div className="p-3 rounded-xl bg-accent/5 dark:bg-accent/5">
            <Leaf className="h-6 w-6 text-accent" />
          </div>
          <div className="ml-4">
            <p className="text-3xl font-bold text-text-primary dark:text-text-primary-dark">
              {ndvi.toFixed(2)}
            </p>
            <p className="text-sm text-text-secondary">NDVI Value</p>
          </div>
        </div>

        <div className="relative h-4 w-full mb-6 bg-background/50 dark:bg-background-dark/50 rounded-full overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r from-green-500 to-yellow-500 transition-all duration-200 ease-in-out`}
            style={{ width: `${ndvi * 100}%` }}
          />
        </div>

        <div className="space-y-3 text-sm mb-6">
          <div className="flex justify-between">
            <span>Status:</span>
            <span className={`font-medium ${statusColor}`}>{statusLabel}</span>
          </div>
          <div className="flex justify-between">
            <span>Trend:</span>
            <span className={`font-medium ${trendColor}`}>
              {trend > 0 ? 'Improving' : trend < 0 ? 'Declining' : 'Stable'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Last Updated:</span>
            <span className="font-medium">{format(lastUpdated, 'HH:mm:ss')}</span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center space-x-2 justify-between">
            <Button variant="outline" size="sm" onClick={() => {
              // Refresh data
              setNdvi(0.2 + Math.random() * 0.6);
              setTrend((Math.random() - 0.5) * 0.02);
              setLastUpdated(new Date());
            }}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
            <MapPin className="h-4 w-4 text-text-secondary" />
            <span className="text-xs text-text-secondary">
              Monitoring: 12 regions
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}