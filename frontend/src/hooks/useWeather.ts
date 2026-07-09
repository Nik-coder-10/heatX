import { useState, useEffect } from 'react';
import { fetchWeather } from '@/services/weatherApi';

export function useWeather(lat: number, lng: number) {
  const [currentTemp, setCurrentTemp] = useState<number | null>(null);
  const [feelsLike, setFeelsLike] = useState<number | null>(null);
  const [humidity, setHumidity] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    fetchWeather(lat, lng)
      .then((w) => {
        if (cancelled) return;
        setCurrentTemp(w.currentTemp);
        setFeelsLike(w.feelsLike);
        setHumidity(w.humidity);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e.message);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [lat, lng]);

  return { currentTemp, feelsLike, humidity, loading, error };
}
