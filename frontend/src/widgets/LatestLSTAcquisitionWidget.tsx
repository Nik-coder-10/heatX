import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Thermometer, MapPin, Clock } from 'lucide-react';
import { format } from 'date-fns';

export default function LatestLSTAcquisitionWidget() {
  const [lstValue, setLstValue] = useState(0);
  const [acquisitionTime, setAcquisitionTime] = useState(new Date());
  const [satellite, setSatellite] = useState('Landsat 9');
  const [cloudCover, setCloudCover] = useState(0);

  useEffect(() => {
    const updateData = () => {
      setLstValue(30 + Math.random() * 20); // 30-50°C
      setAcquisitionTime(new Date());
      setSatellite(Math.random() > 0.5 ? 'Landsat 9' : 'Sentinel-2');
      setCloudCover(Math.floor(Math.random() * 100));
    };

    const interval = setInterval(updateData, 15000);
    updateData();
    return () => clearInterval(interval);
  }, []);

  const getCloudCoverClass = () => {
    if (cloudCover < 20) return 'text-success';
    if (cloudCover < 50) return 'text-warning';
    return 'text-danger';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">
            Latest LST Acquisition
          </h3>
          <label className="flex items-center space-x-2 text-sm text-text-secondary">
            <MapPin className="h-4 w-4" />
            Live Feed
          </label>
        </div>

        <div className="flex items-center mb-4">
          <div className="p-3 rounded-xl bg-accent/5 dark:bg-accent/5">
            <Thermometer className="h-6 w-6 text-danger" />
          </div>
          <div className="ml-4">
            <p className="text-3xl font-bold text-text-primary dark:text-text-primary-dark">
              {lstValue.toFixed(1)}°C
            </p>
            <p className="text-sm text-text-secondary">Land Surface Temperature</p>
          </div>
        </div>

        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span>Satellite:</span>
            <span className="font-medium">{satellite}</span>
          </div>
          <div className="flex justify-between">
            <span>Acquisition Time:</span>
            <span className="font-medium">{format(acquisitionTime, 'HH:mm:ss')}</span>
          </div>
          <div className="flex justify-between">
            <span>Cloud Cover:</span>
            <span className={`font-medium ${getCloudCoverClass()}`}>
              {cloudCover}%
            </span>
          </div>
          <div className="flex justify-between">
            <span>Resolution:</span>
            <span className="font-medium">30m</span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4 text-text-secondary" />
            <span className="text-xs text-text-secondary">Last Updated: </span>
            <span className="font-medium text-text-primary dark:text-text-primary-dark">
              {new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}