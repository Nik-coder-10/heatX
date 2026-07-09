import { useState, useCallback, useRef, useEffect } from 'react';

export interface UseAsyncReturn<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: unknown[]) => Promise<T | null>;
  reset: () => void;
}

export function useAsync<T>(
  fn: (...args: unknown[]) => Promise<T>,
  immediate = false
): UseAsyncReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => () => { mounted.current = false; }, []);

  const execute = useCallback(async (...args: unknown[]) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn(...args);
      if (mounted.current) {
        setData(result);
        setLoading(false);
      }
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'An error occurred';
      if (mounted.current) {
        setError(msg);
        setLoading(false);
      }
      return null;
    }
  }, [fn]);

  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  return { data, loading, error, execute, reset };
}
