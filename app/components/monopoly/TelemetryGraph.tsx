"use client";
import React, { useMemo } from 'react';
import { Activity, BarChart3 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';

export type PricePoint = {
  price: number;
  time: string;
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: PricePoint;
  }>;
  label?: string | number;
  currentTax: number;
  basePrice: number;
}

const CustomTooltip = ({ active, payload, label, currentTax, basePrice }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const rawPrice = payload[0].value;
    const sellPrice = rawPrice * (1 - currentTax);
    const diffFromBase = rawPrice - basePrice;
    const diffPercent = ((diffFromBase / basePrice) * 100).toFixed(1);
    const isAbove = diffFromBase >= 0;

    return (
      <div className="bg-slate-950 border border-slate-800 p-2 font-mono shadow-2xl">
        <p className="text-[10px] text-slate-500 mb-1 tracking-widest">{label}</p>
        <div className="space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-[9px] text-emerald-500 uppercase font-bold">Buy Price:</span>
            <span className="text-[10px] text-slate-100 font-bold">${rawPrice.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[9px] text-blue-400 uppercase font-bold">Sell Price:</span>
            <span className="text-[10px] text-slate-100 font-bold">${sellPrice.toFixed(2)}</span>
          </div>
          {/* NEW: Base price row */}
          <div className="flex justify-between gap-4 border-t border-slate-800 pt-1 mt-1">
            <span className="text-[9px] text-slate-400 uppercase font-bold">Base Price:</span>
            <span className="text-[10px] text-slate-300">${basePrice.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[9px] text-slate-400 uppercase font-bold">Vs Base:</span>
            <span className={`text-[10px] font-bold ${isAbove ? 'text-emerald-400' : 'text-red-400'}`}>
              {isAbove ? '+' : ''}{diffPercent}%
            </span>
          </div>
          <div className="text-[8px] text-slate-600 border-t border-slate-800 pt-1 mt-1 uppercase italic">
            Incl. {(currentTax).toFixed(2)}% Corp Tax
          </div>
        </div>
      </div>
    );
  }
  return null;
};

interface TelemetryGraphProps {
  history: PricePoint[];
  selectedItem: string;
  isLoading: boolean;
  currentTax: number;
  basePrice: number;
}

export const TelemetryGraph = ({ history, selectedItem, isLoading, currentTax, basePrice }: TelemetryGraphProps) => {
  const firstPrice = history.length > 0 ? history[0].price : 0.00;

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
              <Tooltip 
                content={<CustomTooltip currentTax={currentTax} basePrice={basePrice} />}
                cursor={{ stroke: '#1e293b', strokeWidth: 1 }}
                isAnimationActive={false}
              />
              
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