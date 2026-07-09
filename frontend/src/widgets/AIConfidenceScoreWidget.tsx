import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Zap, Brain } from 'lucide-react';

export default function AIConfidenceScoreWidget() {
  const [confidence, setConfidence] = useState(0);
  const [modelStatus, setModelStatus] = useState('idle');
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    const updateConfidence = () => {
      setConfidence(75 + Math.random() * 20); // 75-95
      const statuses = ['idle', 'training', 'predicting', 'ready'] as const;
      setModelStatus(statuses[Math.floor(Math.random() * statuses.length)]);
      setLastUpdated(new Date());
    };

    const interval = setInterval(updateConfidence, 8000);
    updateConfidence();
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    switch (modelStatus) {
      case 'idle': return 'text-text-secondary';
      case 'training': return 'text-warning';
      case 'predicting': return 'text-info';
      case 'ready': return 'text-success';
      default: return 'text-text-secondary';
    }
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            AI Model Confidence
          </h3>
          <Badge variant="info" className="text-xs">
            Prediction Engine
          </Badge>
        </div>

        <div className="flex items-center mb-6">
          <div className="p-3 rounded-xl bg-accent/5 dark:bg-accent/5">
            <Brain className="h-6 w-6 text-accent" />
          </div>
          <div className="ml-4">
            <p className="text-4xl font-bold text-text-primary dark:text-text-primary-dark">
              {confidence.toFixed(0)}%
            </p>
            <p className="text-sm text-text-secondary">Model Accuracy</p>
          </div>
        </div>

        <div className="relative h-4 w-full mb-6 bg-background/50 dark:bg-background-dark/50 rounded-full overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r from-green-500 to-red-500 transition-all duration-500 ease-in-out`}
            style={{ width: `${confidence}%` }}
          />
          <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 flex items-center w-px bg-white/20" />
        </div>

        <div className="space-y-3 text-sm mb-6">
          <div className="flex justify-between">
            <span>Confidence Level:</span>
            <span className="font-medium">
              {confidence >= 90 ? 'Excellent' : confidence >= 80 ? 'Good' : confidence >= 70 ? 'Fair' : 'Poor'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Model Status:</span>
            <span className={`font-medium ${getStatusColor()}`}>
              {modelStatus.charAt(0).toUpperCase() + modelStatus.slice(1)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Last Updated:</span>
            <span className="font-medium">{lastUpdated.toLocaleTimeString()}</span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center space-x-2 justify-between">
            <div className="flex items-center space-x-2">
              <Badge variant={confidence > 85 ? 'success' : confidence > 70 ? 'warning' : 'danger'}>
                Reliable
              </Badge>
              <Badge variant={confidence > 85 ? 'success' : confidence > 70 ? 'warning' : 'danger'} className="ml-2">
                Actionable
              </Badge>
            </div>
            <Button variant="outline" size="sm" onClick={() => {
              // Retrain model simulation
              setModelStatus('training');
              setTimeout(() => {
                setModelStatus('predicting');
                setTimeout(() => {
                  setModelStatus('ready');
                  setConfidence(80 + Math.random() * 15);
                }, 2000);
              }, 2000);
            }}>
              <Zap className="h-4 w-4" />
              Retrain Model
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}