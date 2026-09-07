import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { ArrowRight, Ship } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();

  // Stagger variants for entrance
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.12,
        delayChildren: 0.1,
      },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const },
    },
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#05070D] text-[#F5F5F4] flex flex-col justify-between selection:bg-accent/25 selection:text-accent-glow">
      {/* Background: Nautical Mesh Gradient + Bathymetry Vectors with Ken Burns Drift */}
      <motion.div
        className="absolute inset-0 z-0 pointer-events-none"
        initial={{ scale: 1 }}
        animate={shouldReduceMotion ? {} : { scale: 1.08 }}
        transition={{
          duration: 22,
          repeat: Infinity,
          repeatType: 'reverse',
          ease: 'easeInOut',
        }}
      >
        {/* Deep navy-black gradient base */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#05070D] via-[#08101E] to-[#0E1626]" />

        {/* Ambient Oceanic Glow Orbs */}
        <div className="absolute -top-32 left-1/4 w-[650px] h-[650px] rounded-full bg-[#29B6C2]/[0.07] blur-[140px]" />
        <div className="absolute top-1/3 -right-24 w-[750px] h-[750px] rounded-full bg-[#0D3859]/[0.22] blur-[160px]" />
        <div className="absolute bottom-10 left-10 w-[500px] h-[500px] rounded-full bg-[#1A3A54]/[0.15] blur-[120px]" />

        {/* SVG Maritime Grid & Bathymetric Elevation Contour Pattern */}
        <svg
          className="absolute inset-0 w-full h-full opacity-[0.22] stroke-text-secondary"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <pattern id="maritime-grid" width="80" height="80" patternUnits="userSpaceOnUse">
              <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#26262B" strokeWidth="0.75" />
              <circle cx="80" cy="80" r="1.5" fill="#29B6C2" fillOpacity="0.4" />
              <circle cx="0" cy="0" r="1.5" fill="#29B6C2" fillOpacity="0.4" />
            </pattern>
            <linearGradient id="contour-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#29B6C2" stopOpacity="0.25" />
              <stop offset="50%" stopColor="#1C2E4A" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#05070D" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid overlay */}
          <rect width="100%" height="100%" fill="url(#maritime-grid)" />

          {/* Bathymetric depth wave contours */}
          <g fill="none" stroke="url(#contour-grad)" strokeWidth="1.2">
            <path d="M -100 280 C 300 180, 700 390, 1300 240 C 1700 120, 2100 320, 2500 220" />
            <path d="M -100 360 C 350 250, 750 480, 1350 330 C 1750 200, 2150 420, 2550 300" strokeDasharray="4 6" />
            <path d="M -100 450 C 400 340, 800 580, 1400 420 C 1800 300, 2200 510, 2600 390" />
            <path d="M -100 540 C 450 430, 850 670, 1450 510 C 1850 400, 2250 600, 2650 480" strokeDasharray="3 8" />
            <path d="M -100 630 C 500 520, 900 750, 1500 600 C 1900 500, 2300 690, 2700 570" />
          </g>

          {/* Stylized dry-bulk shipping coordinate markers */}
          <g fill="#29B6C2" fillOpacity="0.6" fontSize="10" fontFamily="'JetBrains Mono', monospace">
            <text x="8%" y="24%">19° 18' N, 84° 51' E [Gopalpur]</text>
            <text x="28%" y="16%">20° 15' N, 86° 40' E [Paradip]</text>
            <text x="56%" y="22%">20° 47' N, 86° 58' E [Dhamra]</text>
            <text x="75%" y="18%">17° 41' N, 83° 17' E [Vizag]</text>
            <text x="88%" y="30%">22° 01' N, 88° 03' E [Haldia]</text>
          </g>
        </svg>

        {/* Bottom Scrim gradient fading down to #050708 for maximum legibility */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#05070D]/60 to-[#050708]" />
      </motion.div>

      {/* Top Navigation Bar */}
      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#131316] border border-[#26262B] flex items-center justify-center text-accent">
            <Ship className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight text-[#F5F5F4] flex items-center gap-2">
              <span>NAV-STEEL DSS</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-[#131316] border border-[#26262B] text-accent">
                SIH 2026
              </span>
            </div>
            <div className="text-xs text-text-secondary">Ministry of Steel • PS SIH26006</div>
          </div>
        </div>

        <nav className="hidden md:flex items-center gap-6 text-sm text-text-secondary">
          <span className="hover:text-text-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard')}>
            Cockpit
          </span>
          <span className="hover:text-text-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard')}>
            Market Watch
          </span>
          <span className="hover:text-text-primary transition-colors cursor-pointer" onClick={() => navigate('/dashboard')}>
            Transparency
          </span>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-1.5 text-xs font-mono text-[#22A97A]">
            <span className="w-2 h-2 rounded-full bg-[#22A97A] animate-pulse" />
            <span>NEON CONNECTED</span>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 w-full max-w-5xl mx-auto px-6 pt-12 pb-16 my-auto flex flex-col items-center text-center">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center max-w-4xl"
        >
          {/* Badge Pill Above Headline */}
          <motion.div variants={itemVariants} className="mb-6">
            <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-[#131316]/90 border border-[#26262B] text-xs font-medium text-text-secondary backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-accent animate-ping" />
              <span className="text-text-primary font-semibold">SIH 2026</span>
              <span className="text-text-tertiary">•</span>
              <span>Problem Statement SIH26006</span>
              <span className="text-text-tertiary">•</span>
              <span className="text-accent">East Coast India</span>
            </div>
          </motion.div>

          {/* Large Tight-Tracked Headline */}
          <motion.h1
            variants={itemVariants}
            className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-[-0.035em] leading-[1.08] text-[#F5F5F4] mb-6 max-w-4xl text-balance"
          >
            Intelligent Freight Forecasting &amp; Vessel Chartering Decision Support
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            variants={itemVariants}
            className="text-base sm:text-lg md:text-xl text-text-secondary leading-relaxed max-w-3xl mb-10 font-normal"
          >
            Quantified, backtested procurement optimization for India&apos;s steel manufacturing sector.
            Evaluates walk-forward P10/P50/P90 price trajectories, dynamic port draft limits,
            and JIT speed advisories to deliver an explainable <span className="text-[#22A97A] font-medium">FIX NOW</span> vs{' '}
            <span className="text-[#E8A33D] font-medium">WAIT</span> expected-value recommendation.
          </motion.p>

          {/* Hydraoo Reference CTA Button: Solid White Pill, Black Text, Circular Arrow that slides right */}
          <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="group relative inline-flex items-center gap-3 px-8 py-4 rounded-full bg-white text-black font-semibold text-base transition-all duration-300 hover:bg-[#F4F4F5] hover:shadow-[0_0_30px_rgba(255,255,255,0.25)] active:scale-[0.98]"
            >
              <span>Get Started</span>
              <div className="w-8 h-8 rounded-full bg-black text-white flex items-center justify-center transition-transform duration-300 ease-out group-hover:translate-x-1.5">
                <ArrowRight className="w-4 h-4 text-white" />
              </div>
            </button>
          </motion.div>

          {/* Trust & Scope Summary Pills */}
          <motion.div
            variants={itemVariants}
            className="mt-14 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-3xl"
          >
            <div className="p-3.5 rounded-2xl bg-[#131316]/80 border border-[#26262B] backdrop-blur-sm flex flex-col items-center">
              <span className="text-xs text-text-tertiary font-medium">PORTS IN SCOPE</span>
              <span className="text-sm font-semibold font-mono text-text-primary mt-1">6 Ports (7 Berths/SPM)</span>
            </div>
            <div className="p-3.5 rounded-2xl bg-[#131316]/80 border border-[#26262B] backdrop-blur-sm flex flex-col items-center">
              <span className="text-xs text-text-tertiary font-medium">VESSEL CLASSES</span>
              <span className="text-sm font-semibold font-mono text-text-primary mt-1">4 Bulkers</span>
            </div>
            <div className="p-3.5 rounded-2xl bg-[#131316]/80 border border-[#26262B] backdrop-blur-sm flex flex-col items-center">
              <span className="text-xs text-text-tertiary font-medium">SUPPLY CORRIDORS</span>
              <span className="text-sm font-semibold font-mono text-text-primary mt-1">8 Overseas</span>
            </div>
            <div className="p-3.5 rounded-2xl bg-[#131316]/80 border border-[#26262B] backdrop-blur-sm flex flex-col items-center">
              <span className="text-xs text-text-tertiary font-medium">VALIDATION</span>
              <span className="text-sm font-semibold font-mono text-[#22A97A] mt-1">Walk-Forward CV</span>
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Landing Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 border-t border-[#26262B]/60 flex flex-col sm:flex-row items-center justify-between text-xs text-text-tertiary gap-3">
        <div className="flex items-center gap-4">
          <span>Ministry of Steel • Smart Automation</span>
          <span>•</span>
          <span className="font-mono">BDRY Proxy Sourced</span>
        </div>
        <div>
          <span>SIH 2026 Candidate Solution • Problem Statement SIH26006</span>
        </div>
      </footer>
    </div>
  );
};
