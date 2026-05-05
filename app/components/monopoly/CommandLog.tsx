import React, { useState, useEffect } from 'react';

interface LogEntry {
  text: string;
  color: string;
}

interface CommandLogProps {
  marketLength: number;
  selectedItem: string;
  current_log: LogEntry[] | undefined;
  error: string | null;
}

export const CommandLog = ({ marketLength, selectedItem, current_log, error }: CommandLogProps) => {
  
  const [mountedTime, setMountedTime] = useState<string>("--:--:--");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMountedTime(new Date().toLocaleTimeString());
  }, []);

  return (
    <div className="h-full">
      <h2 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-tighter">Command Log</h2>
      {/* Fixed small height, no scrolling, and reversed stack */}
      <div className="bg-black p-3 rounded border border-slate-800 h-[230px] overflow-hidden font-mono text-[9px] space-y-1 flex flex-col-reverse justify-end">
          
          <p className="animate-pulse text-emerald-500">_</p>
          <p className="text-slate-600">Market sync: {marketLength} resources active.</p>

          {/* Newest logs appear here at the top of the stack */}
          {Array.isArray(current_log) && [...current_log].reverse().map((log, index) => (
            <p key={index} className={log.color}>
              {log.text}
            </p>
          ))}

          <p className="text-emerald-900 font-bold mb-2">SYSTEM_BOOT_SUCCESSFUL...</p>
      </div>
    </div>
  );
};