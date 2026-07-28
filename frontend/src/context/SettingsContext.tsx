import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type ThemeMode = 'dark' | 'light';

interface SettingsContextValue {
  soundEnabled: boolean;
  theme: ThemeMode;
  setSoundEnabled: (value: boolean) => void;
  setTheme: (value: ThemeMode) => void;
  toggleSound: () => void;
  toggleTheme: () => void;
}

const SOUND_KEY = 'namerush.soundEnabled';
const THEME_KEY = 'namerush.theme';

const SettingsContext = createContext<SettingsContextValue | null>(null);

function readBool(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return raw === 'true';
  } catch {
    return fallback;
  }
}

function readTheme(): ThemeMode {
  try {
    const raw = localStorage.getItem(THEME_KEY);
    return raw === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [soundEnabled, setSoundEnabledState] = useState(() => readBool(SOUND_KEY, true));
  const [theme, setThemeState] = useState<ThemeMode>(() => readTheme());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    try {
      localStorage.setItem(SOUND_KEY, String(soundEnabled));
    } catch {
      /* ignore */
    }
  }, [soundEnabled]);

  const setSoundEnabled = useCallback((value: boolean) => {
    setSoundEnabledState(value);
  }, []);

  const setTheme = useCallback((value: ThemeMode) => {
    setThemeState(value);
  }, []);

  const value = useMemo(
    () => ({
      soundEnabled,
      theme,
      setSoundEnabled,
      setTheme,
      toggleSound: () => setSoundEnabledState((prev) => !prev),
      toggleTheme: () => setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark')),
    }),
    [soundEnabled, theme, setSoundEnabled, setTheme],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return ctx;
}
