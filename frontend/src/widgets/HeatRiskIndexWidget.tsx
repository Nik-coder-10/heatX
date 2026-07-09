import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';

export default function HeatRiskIndexWidget() {
  const [value, setValue] = useState(0);
  const [trend, setTrend] = useState(0); // positive for up, negative for down

  useEffect(() => {
    // Simulate fetching data
    const timer = setInterval(() => {
      const newValue = 75 + Math.random() * 20; // Between 75-95
      const newTrend = (Math.random() - 0.5) * 2; // Between -1 and 1
      setValue(newValue);
      setTrend(newTrend);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const trendDirection = trend > 0 ? 'up' : trend < 0 ? 'down' : 'neutral';
  const trendIcon = trendDirection === 'up' ? <TrendingUp className="h-4 w-4" /> :
                   trendDirection === 'down' ? <TrendingDown className="h-4 w-4" /> :
                   <Activity className="h-4 w-4" />;
  const trendColor = trendDirection === 'up' ? 'text-danger' :
                    trendDirection === 'down' ? 'text-success' :
                    'text-text-secondary';

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            Active Heat Risk Index
          </h3>
          <Button variant="outline" size="sm" className="p-1">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h3m8 0v3m-3-3h3m-3 3H9m8 0v3m-3-3H9m8 0V9a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2z" />
            </svg>
          </Button>
        </div>

        <div className="text-4xl font-bold text-text-primary dark:text-text-primary-dark mb-2">
          {value.toFixed(0)}
        </div>
        <div className="flex items-center space-x-2 mb-4">
          <span className="text-sm text-text-secondary">Risk Level: </span>
          <span className={`font-medium ${value > 90 ? 'text-danger' : value > 80 ? 'text-warning' : 'text-success'}`}>
            {value > 90 ? 'Extreme' : value > 80 ? 'High' : 'Moderate'}
          </span>
        </div>

        <div className="flex items-center space-x-2 mb-4">
          <span className="text-sm text-text-secondary">Trend: </span>
          <span className={`${trendColor} font-medium`}>
            {trendDirection === 'up' ? '↑' : trendDirection === 'down' ? '↓' : '→'}
            {Math.abs(trend).toFixed(1)}
          </span>
          {trendIcon}
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm text-text-secondary">Last Updated: </span>
          <span className="font-medium">{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </Card>
  );
}