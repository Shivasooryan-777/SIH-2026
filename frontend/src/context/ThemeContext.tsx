import React, { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';

export interface ChartThemeConfig {
  grid: string;
  axis: string;
  tick: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipText: string;
  p50Line: string;
  p50Dot: string;
  p50DotStroke: string;
  p50ActiveDot: string;
  quantileGradientStop: string;
  quantileMask: string;
  baselineLine: string;
  baselineText: string;
  shapUp: string;
  shapDown: string;
  shapZeroLine: string;
  shapYTick: string;
}

const darkChartTheme: ChartThemeConfig = {
  grid: '#26262B',
  axis: '#26262B',
  tick: '#A1A1AA',
  tooltipBg: '#09090B',
  tooltipBorder: '#26262B',
  tooltipText: '#F4F4F5',
  p50Line: '#29B6C2',
  p50Dot: '#29B6C2',
  p50DotStroke: '#131316',
  p50ActiveDot: '#6EE7E0',
  quantileGradientStop: '#29B6C2',
  quantileMask: '#131316',
  baselineLine: '#71717A',
  baselineText: '#A1A1AA',
  shapUp: '#29B6C2',
  shapDown: '#E4574C',
  shapZeroLine: '#3F3F46',
  shapYTick: '#F4F4F5',
};

const lightChartTheme: ChartThemeConfig = {
  grid: '#E4E4E7',
  axis: '#E4E4E7',
  tick: '#52525B',
  tooltipBg: '#FFFFFF',
  tooltipBorder: '#E4E4E7',
  tooltipText: '#18181B',
  p50Line: '#0E7C88',
  p50Dot: '#0E7C88',
  p50DotStroke: '#FFFFFF',
  p50ActiveDot: '#29B6C2',
  quantileGradientStop: '#0E7C88',
  quantileMask: '#FFFFFF',
  baselineLine: '#A1A1AA',
  baselineText: '#52525B',
  shapUp: '#0E7C88',
  shapDown: '#B91C1C',
  shapZeroLine: '#D4D4D8',
  shapYTick: '#18181B',
};

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  chartTheme: ChartThemeConfig;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = 'navsteel_theme';

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') {
        return stored;
      }
    }
    // Default to dark for first-time visitors per requirements (not OS preference)
    return 'dark';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'light') {
      root.classList.add('light');
      root.classList.remove('dark');
    } else {
      root.classList.add('dark');
      root.classList.remove('light');
    }
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Ignore localStorage write failures in private/restricted environments
    }
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const setTheme = (nextTheme: Theme) => {
    setThemeState(nextTheme);
  };

  const chartTheme = theme === 'light' ? lightChartTheme : darkChartTheme;

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme, chartTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
