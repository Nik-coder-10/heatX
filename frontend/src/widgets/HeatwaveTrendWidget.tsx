import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Clock, RefreshCw, Thermometer } from 'lucide-react';
import { format } from 'date-fns';

interface HeatwaveData {
  date: string;
  temperature: number;
  anomaly: number;
}

export default function HeatwaveTrendWidget() {
  const [data, setData] = useState<HeatwaveData[]>([]);

  const generateData = useCallback(() => {
    const days = 7;
    const baseTemp = 35;
    return Array.from({ length: days }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - i);
      return {
        date: format(date, 'EEE'),
        temperature: baseTemp + Math.random() * 5,
        anomaly: (Math.random() - 0.5) * 4,
      };
    }).reverse();
  }, []);

  useEffect(() => {
    setData(generateData());
  }, [generateData]);

  const latestAnomaly = data[data.length - 1]?.anomaly || 0;
  const anomalyTrend = latestAnomaly > 0.5 ? 'up' : latestAnomaly < -0.5 ? 'down' : 'stable';

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            Heatwave Trend Analysis
          </h3>
          <Badge variant={anomalyTrend === 'up' ? 'danger' : anomalyTrend === 'down' ? 'success' : 'info'}
                 className="text-xs">
            {anomalyTrend === 'up' ? 'Increasing' : anomalyTrend === 'down' ? 'Decreasing' : 'Stable'}
          </Badge>
        </div>

        <div className="space-y-4">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-xl bg-accent/5 dark:bg-accent/5">
              <Thermometer className="h-6 w-6 text-danger" />
            </div>
            <div className="ml-4">
              <p className="text-2xl font-bold text-text-primary dark:text-text-primary-dark">
                {data[data.length - 1]?.temperature.toFixed(1)}°C
              </p>
              <p className="text-sm text-text-secondary">Current Temperature</p>
            </div>
          </div>

          <div className="h-4 w-full bg-background/50 dark:bg-background-dark/50 rounded-full overflow-hidden mb-4">
            <div
              className="h-full bg-gradient-to-r from-accent to-accent/20"
              style={{ width: `${Math.min(Math.max((latestAnomaly + 2) / 4 * 100, 0), 100)}%` }}
            />
          </div>

          <div className="flex justify-between text-sm">
            <span>Temperature Anomaly:</span>
            <span className={`font-medium ${latestAnomaly > 0 ? 'text-danger' : latestAnomaly < 0 ? 'text-success' : 'text-text-secondary'}`}>
              {latestAnomaly.toFixed(1)}°C
            </span>
          </div>

          <div className="h-2 w-full bg-background/50 dark:bg-background-dark/50 rounded-full overflow-hidden mb-4">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-red-500"
              style={{ width: `${(latestAnomaly + 2) / 4 * 100}%` }}
            />
          </div>

          <div className="space-y-2 text-sm">
            {data.map((day, index) => (
              <div key={index} className="flex items-center justify-between">
                <span className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    index === data.length - 1 ? 'bg-accent' : 'bg-background/50'
                  }`} />
                  <span className="font-medium">{day.date}</span>
                </span>
                <span className={`font-mono text-right ${
                  day.anomaly > 0 ? 'text-danger' : day.anomaly < 0 ? 'text-success' : 'text-text-secondary'
                } w-16`}>
                  {day.anomaly.toFixed(1)}°
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center space-x-2 justify-between">
            <Button variant="outline" size="sm" onClick={() => {
              // Refresh data
              setData(generateData());
            }}>
              <RefreshCw className="h-4 w-4" />
              Refresh Data
            </Button>
            <Clock className="h-4 w-4 text-text-secondary" />
            <span className="text-xs text-text-secondary">
              Updated: {new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}