import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const shouldReduceMotion = useReducedMotion();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      role="switch"
      aria-checked={!isDark}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      onClick={toggleTheme}
      className="relative inline-flex items-center h-7 w-14 rounded-full bg-surface border border-border hover:border-accent transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-1 focus:ring-accent select-none p-0.5"
      title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
    >
      {/* Track ambient icons */}
      <div className="w-full flex items-center justify-between px-1.5 pointer-events-none">
        <Moon className={`w-3 h-3 transition-opacity duration-200 ${isDark ? 'text-accent opacity-100' : 'text-text-tertiary opacity-40'}`} />
        <Sun className={`w-3 h-3 transition-opacity duration-200 ${!isDark ? 'text-accent opacity-100' : 'text-text-tertiary opacity-40'}`} />
      </div>

      {/* Sliding thumb knob with smooth icon crossfade */}
      <motion.div
        className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-canvas border border-border flex items-center justify-center shadow-sm"
        animate={{ x: isDark ? 2 : 28 }}
        transition={shouldReduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 500, damping: 30 }}
      >
        {isDark ? (
          <motion.div
            key="moon"
            initial={shouldReduceMotion ? false : { opacity: 0, rotate: -40, scale: 0.8 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: 40, scale: 0.8 }}
            transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.18 }}
          >
            <Moon className="w-3 h-3 text-accent" />
          </motion.div>
        ) : (
          <motion.div
            key="sun"
            initial={shouldReduceMotion ? false : { opacity: 0, rotate: 40, scale: 0.8 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: -40, scale: 0.8 }}
            transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.18 }}
          >
            <Sun className="w-3 h-3 text-accent" />
          </motion.div>
        )}
      </motion.div>
    </button>
  );
};
