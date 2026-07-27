import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '@/api/client';
import type { CareerSaveDetail } from '@/types';

interface CareerContextValue {
  activeCareer: CareerSaveDetail | null;
  loading: boolean;
  error: string | null;
  refreshCareer: () => Promise<void>;
  setActiveCareer: (career: CareerSaveDetail | null) => void;
}

const CareerContext = createContext<CareerContextValue | undefined>(undefined);

export function CareerProvider({ children }: { children: ReactNode }) {
  const [activeCareer, setActiveCareer] = useState<CareerSaveDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshCareer = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const career = await api.getActiveCareer();
      setActiveCareer(career);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load career');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshCareer();
  }, [refreshCareer]);

  return (
    <CareerContext.Provider
      value={{ activeCareer, loading, error, refreshCareer, setActiveCareer }}
    >
      {children}
    </CareerContext.Provider>
  );
}

export function useCareer() {
  const context = useContext(CareerContext);
  if (!context) {
    throw new Error('useCareer must be used within CareerProvider');
  }
  return context;
}
