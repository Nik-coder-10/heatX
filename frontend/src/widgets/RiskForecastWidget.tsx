import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { RefreshCw } from 'lucide-react';

interface ForecastDay {
  day: string;
  risk: number; // 0-100
  confidence: number; // 0-100
}

export default function RiskForecastWidget() {
  const [forecast, setForecast] = useState<ForecastDay[]>([]);

  const generateForecast = useCallback(() => {
    const days = ['Today', 'Tomorrow', 'Day 3', 'Day 4', 'Day 5'];
    return days.map((day) => ({
      day,
      risk: 30 + Math.random() * 60,
      confidence: 70 + Math.random() * 25,
    }));
  }, []);

  useEffect(() => {
    setForecast(generateForecast());
  }, [generateForecast]);

  const getRiskColor = (risk: number) => {
    if (risk >= 80) return 'text-danger';
    if (risk >= 60) return 'text-warning';
    return 'text-success';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            3-Day Risk Forecast
          </h3>
          <Badge variant="info" className="text-xs">
            Prediction Confidence
          </Badge>
        </div>

        <div className="space-y-4">
          {forecast.map((day, index) => (
            <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-background/50 dark:bg-background-dark/50">
              <div className="flex items-center space-x-3">
                <div className={`w-2 h-2 rounded-full ${index === 0 ? 'bg-accent' : 'bg-background/50'}`} />
                <span className="font-medium">{day.day}</span>
              </div>
              <div className="flex-1 space-x-4 text-center">
                <div className="flex flex-col items-center">
                  <span className="text-sm font-medium text-text-secondary">Risk Level</span>
                  <span className={`block text-2xl font-bold ${getRiskColor(day.risk)}`}>
                    {Math.round(day.risk)}%
                  </span>
                </div>
                <div className="flex flex-col items-center">
                  <span className="text-sm font-medium text-text-secondary">Confidence</span>
                  <span className="block text-lg font-medium text-text-primary dark:text-text-primary-dark">
                    {Math.round(day.confidence)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {day.risk > 70 ? (
                  <Badge variant="danger">
                    High Risk
                  </Badge>
                ) : day.risk > 40 ? (
                  <Badge variant="warning">
                    Moderate
                  </Badge>
                ) : (
                  <Badge variant="success">
                    Low Risk
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex justify-between">
            <Button variant="outline" size="sm" onClick={() => {
              // Update forecast
              setForecast(generateForecast());
            }}>
              <RefreshCw className="h-4 w-4" />
              Update Forecast
            </Button>
            <span className="text-xs text-text-secondary">
              Updated: {new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}