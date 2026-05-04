"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LeaderboardModal } from './LeaderboardModal';
import { FormattedValue } from './FormattedValue';

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  balance: number;
  net_worth: number;
  inventory_value: number;
  inventory: Record<string, number> | "Hidden";
}

interface HeaderProps {
  userId: string;
  balance: number;
  totalAssets: number;
  tickInterval: number;
  secondsRemaining: number;
  leaderboard: LeaderboardEntry[] | undefined
  loadLeaderboard: () => void;
}

export default function Header({ 
  userId, 
  balance, 
  totalAssets,
  tickInterval, 
  secondsRemaining, 
  leaderboard,
  loadLeaderboard
}: HeaderProps) {
  
  // Track if we are currently "filling" the circle or "eating" it
  const [isFilling, setIsFilling] = useState(false);
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

  
  // Inside your MonopolyBoss component:
  const [isLeaderboardOpen, setIsLeaderboardOpen] = useState(false);

  // Assuming your backend data is stored in gameData.leaderboard
  const leaderboardData = leaderboard || [];

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
      
      {/* 2. Balance Section (Expanded for Total Assets) */}
      <div className="flex items-center justify-around border-x border-slate-800 px-4">
        <div className="flex flex-col items-center">
          <span className="text-[8px] text-slate-500 uppercase tracking-[0.2em] font-bold mb-1">
            Liquid Cash
          </span>
          <span className="text-xl font-light text-emerald-400 tabular-nums">
            <FormattedValue value={balance} type="currency" prefix="$" />
          </span>
        </div>

        {/* Divider line between the two values */}
        <div className="h-8 w-[1px] bg-slate-800 mx-2" />

        <div className="flex flex-col items-center">
          <span className="text-[8px] text-slate-500 uppercase tracking-[0.2em] font-bold mb-1">
            Total Net Worth
          </span>
          <span className="text-xl font-light text-blue-400 tabular-nums">
            <FormattedValue value={totalAssets} type="currency" prefix="$" />
          </span>
        </div>
      </div>

      {/* 3. Timer Section */}
      <div className="flex flex-row items-center justify-end gap-6">
        
        {/* NEW: Leaderboard Trigger (Now a Circle) */}
        <div className="relative group">
          <button 
            onClick={() => {loadLeaderboard(); setIsLeaderboardOpen(true);}}
            className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center transition-all hover:border-emerald-500 hover:shadow-[0_0_15px_rgba(16,185,129,0.2)] active:scale-95"
          >
            <span className="text-[8px] font-black text-slate-500 group-hover:text-emerald-400 text-center leading-none uppercase tracking-tighter">
              Rank<br/>CSV
            </span>
          </button>
          
          {/* Tooltip hint */}
          <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[7px] text-slate-700 opacity-0 group-hover:opacity-100 transition-opacity uppercase font-bold whitespace-nowrap">
            View Leaderboard
          </span>
        </div>

        {/* Existing Timer Circle */}
        <div className="relative w-16 h-16">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 64 64">
            <circle
              cx="32" cy="32" r="28"
              stroke="currentColor" strokeWidth="2" fill="transparent"
              className="text-slate-800/40"
            />
            <motion.circle
              cx="32" cy="32" r="28"
              stroke="currentColor" strokeWidth="3" fill="transparent"
              strokeLinecap="round"
              className="text-emerald-500 shadow-glow"
              initial={false}
              animate={{ 
                pathLength: isFilling ? (1 - progress) : progress,
                pathOffset: isFilling ? 0 : (1 - progress)
              }}
              transition={{ duration: 1, ease: "linear" }}
            />
          </svg>

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

        {/* Modal remains at the bottom of the JSX tree so it doesn't break layout */}
        <LeaderboardModal 
          isOpen={isLeaderboardOpen}
          onClose={() => setIsLeaderboardOpen(false)}
          data={leaderboardData}
          updateLeaderboard={loadLeaderboard}
        />
      </div>
    </header>
  );
}