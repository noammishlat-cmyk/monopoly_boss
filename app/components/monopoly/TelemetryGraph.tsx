"use client";
import React, { useMemo } from 'react';
import { Activity, BarChart3 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';

interface TelemetryGraphProps {
  history: any[];
  selectedItem: string;
  isLoading: boolean;
}

export const TelemetryGraph = ({ history, selectedItem, isLoading }: TelemetryGraphProps) => {
  const firstPrice = history.length > 0 ? history[0].price : 0;

  const gradientStops = useMemo(() => {
    if (history.length < 2) return null;
    
    const totalPoints = history.length - 1;
    const buffer = 0.5; // higher = sharper color change

    return history.map((entry, i) => {
      const current = entry;
      const prev = i > 0 ? history[i - 1] : history[i];
      
      const isRising = current.price >= prev.price;
      const color = isRising ? "#10b981" : "#ef4444";
      const percentage = (i / totalPoints) * 100;

      // We use two stops per point to "tighten" the color change area
      return (
        <React.Fragment key={`${i}-point`}>
          <stop 
            offset={`${Math.max(0, percentage - buffer)}%`} 
            stopColor={color} 
          />
          <stop 
            offset={`${Math.min(100, percentage + buffer)}%`} 
            stopColor={color} 
          />
        </React.Fragment>
      );
    });
  }, [history]);

  return (
    <div className="bg-slate-900 border border-slate-800 p-4 rounded-sm relative overflow-hidden min-h-[200px]">
      <h3 className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest flex items-center gap-2 mb-4">
        <Activity size={12} className={isLoading ? "animate-spin" : "animate-pulse"} />
        Telemetry Feed: {selectedItem}
      </h3>

      <div className="h-40 w-full relative">
        {isLoading && (
          <div className="absolute inset-0 z-10 bg-slate-900/80 backdrop-blur-sm flex flex-col items-center justify-center border border-emerald-900/30">
            <p className="text-[9px] text-emerald-500 font-bold tracking-[0.2em] animate-pulse">
              SYNCING_DATA...
            </p>
          </div>
        )}
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <defs>
                {/* x1=0 x2=1 makes this a horizontal gradient */}
                <linearGradient id="horizontalSegmentGradient" x1="0" y1="0" x2="1" y2="0">
                  {gradientStops}
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} opacity={0.2} />
              <XAxis dataKey="time" hide />
              <YAxis hide domain={['auto', 'auto']} />
              <ReferenceLine y={firstPrice} stroke="#475569" strokeDasharray="3 3" />
              <Tooltip contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', fontSize: '10px' }} />
              
              <Line 
                type="monotone" 
                dataKey="price" 
                stroke="url(#horizontalSegmentGradient)" 
                strokeWidth={2} 
                dot={false} 
                isAnimationActive={false} 
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full w-full flex items-center justify-center opacity-20"><BarChart3 size={40} /></div>
        )}
      </div>
    </div>
  );
};