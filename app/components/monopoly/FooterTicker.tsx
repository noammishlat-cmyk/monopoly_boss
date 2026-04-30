"use client";
import React from 'react';

export const FooterTicker = () => {
  return (
    <>
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800 h-6 flex items-center overflow-hidden">
        <div className="animate-marquee whitespace-nowrap flex gap-10 items-center text-[9px] uppercase tracking-tighter text-slate-600">
          <span>Global Demand for Steel is rising...</span>
          <span>CEO Player_X liquidated 400 Iron...</span>
          <span>New Policy Proposal: Tax Havens...</span>
          <span>Market Volatility Index: Stable...</span>
        </div>
      </footer>

      <style jsx>{`
        @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
        .animate-marquee { animation: marquee 60s linear infinite; }
      `}</style>
    </>
  );
};