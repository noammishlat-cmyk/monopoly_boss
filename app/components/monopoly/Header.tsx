"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface HeaderProps {
  userId: string;
  balance: number;
  tickInterval: number;
  secondsRemaining: number;
  formatCurrency: (val: number) => string;
}

export default function Header({ 
  userId, 
  balance, 
  tickInterval, 
  secondsRemaining, 
  formatCurrency 
}: HeaderProps) {
  
  // Track if we are currently "filling" the circle or "eating" it
  const [isFilling, setIsFilling] = useState(true);
  const prevSecondsRef = useRef(secondsRemaining);

  // Detect when the timer resets to toggle the phase
  useEffect(() => {
    // If the new seconds are significantly higher than the old seconds, 
    // it means the backend reset the timer for a new tick.
    if (secondsRemaining > prevSecondsRef.current) {
      setIsFilling((prev) => !prev);
    }
    prevSecondsRef.current = secondsRemaining;
  }, [secondsRemaining]);

  // Normalize progress (1.0 at start of countdown, 0.0 at 0 seconds)
  const progress = tickInterval > 0 ? Math.max(0, secondsRemaining / tickInterval) : 0;

  return (
    <header className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 border-b border-slate-800 pb-4">
      {/* 1. Identity Section */}
      <div>
        <h1 className="text-xl font-bold text-emerald-500 tracking-tighter italic uppercase">
          Monopoly Boss
        </h1>
        <p className="text-[10px] text-slate-500 uppercase tracking-widest italic leading-none">
          Auth_ID: {userId}
        </p>
      </div>
      
      {/* 2. Balance Section */}
      <div className="flex flex-col items-center border-x border-slate-800 px-4">
        <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
          Liquid Balance
        </span>
        <span className="text-2xl font-light text-emerald-400 tabular-nums">
          {formatCurrency(balance)}
        </span>
      </div>

      {/* 3. Timer Section */}
      <div className="flex flex-col items-end justify-center">
        <div className="relative w-16 h-16">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 64 64">
            {/* Background Track */}
            <circle
              cx="32" cy="32" r="28"
              stroke="currentColor" strokeWidth="2" fill="transparent"
              className="text-slate-800/40"
            />
            
            {/* Animated "Snake" Circle */}
            <motion.circle
              cx="32" cy="32" r="28"
              stroke="currentColor" strokeWidth="3" fill="transparent"
              strokeLinecap="round"
              className="text-emerald-500 shadow-glow"
              initial={false}
              animate={{ 
                // Phase 1 (Filling): Length grows from 0 to 1
                // Phase 2 (Eating): Length shrinks from 1 to 0 AND moves forward
                pathLength: isFilling ? (1 - progress) : progress,
                pathOffset: isFilling ? 0 : (1 - progress)
              }}
              transition={{ 
                duration: 1, 
                ease: "linear"
              }}
            />
          </svg>

          {/* Center Content */}
          <div className="absolute inset-0 flex items-center justify-center">
            <AnimatePresence mode="wait">
              {secondsRemaining === 0 ? (
                <motion.div
                  key="ping"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  className="w-2 h-2 bg-emerald-400 rounded-full animate-ping"
                />
              ) : (
                <motion.div
                  key="count"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.2 }}
                  className="flex flex-col items-center"
                >
                  <span className="text-[12px] font-black text-slate-100 tabular-nums leading-none">
                    {secondsRemaining}
                  </span>
                  <span className="text-[7px] text-emerald-500/60 font-bold uppercase tracking-tighter">
                    {isFilling ? "Filling" : "Eating"}
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          <span className="absolute -bottom-4 right-0 text-[8px] uppercase tracking-tighter text-slate-600 font-bold">
            Synced
          </span>
        </div>
      </div>
    </header>
  );
}