"use client";
import React from 'react';

interface CommandLogProps {
  marketLength: number;
  selectedItem: string;
  error: string | null;
}

export const CommandLog = ({ marketLength, selectedItem, error }: CommandLogProps) => {
  const time = new Date().toLocaleTimeString();
  
  return (
    <div className="h-full">
      <h2 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-tighter">Command Log</h2>
      <div className="bg-black p-3 rounded border border-slate-800 h-[500px] overflow-y-auto font-mono text-[9px] space-y-1">
         <p className="text-emerald-900 font-bold mb-2">SYSTEM_BOOT_SUCCESSFUL...</p>
         <p className="text-slate-600">[{time}] Market sync: {marketLength} resources active.</p>
         <p className="text-blue-500">[{time}] Monitoring focus: {selectedItem}</p>
         {/*error && <p className="text-red-500">[{time}] WARNING: {error}</p>*/}
         <p className="animate-pulse text-emerald-500">_</p>
      </div>
    </div>
  );
};