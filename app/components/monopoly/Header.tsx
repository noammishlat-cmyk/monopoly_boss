"use client";

import React from 'react';

// Define what this component needs to work
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
  return (
    <header className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 border-b border-slate-800 pb-4">
      {/* 1. Identity Section */}
      <div>
        <h1 className="text-xl font-bold text-emerald-500 tracking-tighter italic uppercase">
          Monopoly Boss
        </h1>
        <p className="text-[10px] text-slate-500 uppercase tracking-widest italic">
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
        <div className="flex flex-col items-end justify-center relative w-16 h-16 group">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="32" cy="32" r="28"
              stroke="currentColor" strokeWidth="2" fill="transparent"
              className="text-slate-800"
            />
            <circle
              cx="32" cy="32" r="28"
              stroke="currentColor" strokeWidth="3" fill="transparent"
              strokeDasharray={176}
              strokeDashoffset={176 - (176 * (tickInterval - secondsRemaining)) / tickInterval}
              className={`transition-all duration-1000 ease-linear ${
                secondsRemaining === 0 ? "text-white scale-0 rotate-180" : "text-emerald-500"
              }`}
              style={{ transformOrigin: 'center' }}
            />
          </svg>

          <div className="absolute inset-0 flex items-center justify-center">
            {secondsRemaining === 0 ? (
              <div className="w-2 h-2 bg-white rounded-full animate-ping" />
            ) : (
              <span className="text-[10px] font-bold text-slate-500 tabular-nums">
                {secondsRemaining}s
              </span>
            )}
          </div>
          
          <span className="absolute -bottom-4 right-0 text-[8px] uppercase tracking-tighter text-slate-600">
            Syncing...
          </span>
        </div>
      </div>
    </header>
  );
}