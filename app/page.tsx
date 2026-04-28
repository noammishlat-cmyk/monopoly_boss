"use client"

import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, ShieldAlert, BarChart3, Database } from 'lucide-react';

// --- Types ---
type Resource = { 
  name: string; 
  price: number; 
  demand: number; 
  supply: number;
};
type Department = { id: string; name: string; icon: any; workers: number; output: string };

export default function MonopolyBoss() {
  // Game State
  const [netWorth, setNetWorth] = useState(12500.50);
  const [cash, setCash] = useState(10000);
  const [nextTick, setNextTick] = useState(840); // Seconds until next 15-min tick

  const [departments, setDepartments] = useState<Department[]>([
    { id: 'ext', name: 'Extraction', icon: Database, workers: 5, output: '12 Iron / tick' },
    { id: 'rnd', name: 'R&D', icon: TrendingUp, workers: 0, output: '0 Blueprints' },
    { id: 'esp', name: 'Espionage', icon: ShieldAlert, workers: 0, output: 'No Intel' },
  ]);

  const [market, setMarket] = useState<Resource[]>([]);
  const [error, setError] = useState<string | null>(null);


  // Simulate Clock
  useEffect(() => {
    const timer = setInterval(() => {
      setNextTick((prev) => (prev > 0 ? prev - 1 : 900));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const fetchPrice = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/price');
        const data = await response.json(); 

        console.log("Raw Data from API:", data); // Check your console (F12) to see what properties exist

        // Create a Map to ensure uniqueness
        const resourceMap = new Map();

        data.forEach((resource: any) => {
          // This line checks for 'name', then 'item', then 'Unknown'
          const resourceName = resource.name || resource.item || "Unknown";
          
          resourceMap.set(resourceName, {
            name: resourceName,
            price: resource.price,
            demand: resource.demand,
            supply: resource.supply
          });
        });

        const uniqueResources = Array.from(resourceMap.values()) as Resource[];
        
        console.log("Cleaned Data:", uniqueResources);
        setMarket(uniqueResources);
        setError(null);
      } catch (err) {
        console.error("Fetch error:", err);
        setError("Backend Offline");
      }
    };

    fetchPrice();
    const interval = setInterval(fetchPrice, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 font-mono">
      {/* HEADER / STATUS BAR */}
      <header className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-emerald-500 tracking-tighter">MONOPOLY BOSS v1.0</h1>
          <p className="text-xs text-slate-500 italic">User: CEO_PLAYER_01</p>
        </div>
        <div className="flex flex-col items-center border-x border-slate-800 px-4">
          <span className="text-xs text-slate-500 uppercase tracking-widest">Global Net Worth</span>
          <span className="text-3xl font-light text-white tabular-nums">
            {formatCurrency(netWorth)}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-xs text-slate-500">NEXT MARKET TICK</span>
          <span className="text-xl font-bold text-amber-500 tabular-nums">{formatTime(nextTick)}</span>
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: WORKFORCE MANAGEMENT */}
        <section className="lg:col-span-4 space-y-4">
          <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
            <Users size={16} /> DEPARTMENT LOGISTICS
          </h2>
          {departments.map((dept) => (
            <div key={dept.id} className="bg-slate-900 border border-slate-800 p-4 rounded-sm hover:border-emerald-900 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <dept.icon size={20} className="text-emerald-500" />
                <span className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-400">{dept.workers} Workers</span>
              </div>
              <h3 className="font-bold text-lg">{dept.name}</h3>
              <p className="text-xs text-slate-500 mb-4 tracking-tight">{dept.output}</p>
              <div className="grid grid-cols-2 gap-2">
                <button className="bg-slate-800 hover:bg-slate-700 text-xs py-1 rounded border border-slate-700 transition-all active:scale-95">RECALL</button>
                <button className="bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-400 text-xs py-1 rounded border border-emerald-800/50 transition-all active:scale-95">ASSIGN</button>
              </div>
            </div>
          ))}
        </section>

        {/* MIDDLE COLUMN: MARKET DATA */}
        <section className="lg:col-span-5">
          <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-2 mb-4">
            <BarChart3 size={16} /> LIVE COMMODITIES EXCHANGE
          </h2>
          <div className="bg-slate-900 border border-slate-800 rounded-sm overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-800 text-slate-400 text-[10px] uppercase tracking-wider">
                <tr>
                  <th className="p-3">Asset</th>
                  <th className="p-3">Price</th>
                  <th className="p-3 text-right">24h Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {error ? (
                  <tr><td colSpan={3} className="p-4 text-red-500 text-center">{error}</td></tr>
                ) : (
                  market.map((item, index) => (
                    <tr key={`${item.name}-${index}`} className="hover:bg-slate-800/50 transition-colors group">
                      <td className="p-3 font-medium">{item.name}</td>
                      <td className="p-3 tabular-nums font-bold text-white">${item.price}</td>
                      <td className="p-3 text-right text-xs text-slate-400">
                        Supply: {item.supply} / Demand: {item.demand}
                        {item.demand > item.supply ? (
                          <span className="text-orange-500 text-[10px] font-bold">HIGH DEMAND</span>
                          ) : (
                            <span className="text-slate-500 text-[10px]">STABLE</span>
                          )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          <div className="mt-6 bg-slate-900 p-4 border border-slate-800 border-t-4 border-t-amber-600">
            <h3 className="text-xs font-bold text-amber-500 uppercase mb-2">Active Lobbying Policy</h3>
            <p className="text-sm font-bold italic">"The Automation Act"</p>
            <p className="text-xs text-slate-400 mt-1">Status: Voting Open. 64% Support to increase R&D Speed.</p>
          </div>
        </section>

        {/* RIGHT COLUMN: CORPORATE LOG */}
        <section className="lg:col-span-3">
           <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-2 mb-4">
            COMMAND LOG
          </h2>
          <div className="bg-black p-3 rounded border border-slate-800 h-96 overflow-y-auto font-mono text-[10px] space-y-2">
            <p className="text-emerald-500">[08:45:01] LOGIN SUCCESSFUL</p>
            <p className="text-slate-500">[08:45:10] MARKET TICK COMPLETE: Iron +0.02%</p>
            <p className="text-slate-500">[09:00:00] REFINERY ALPHA: 40 units Steel processed.</p>
            <p className="text-red-500">[09:12:44] WARNING: Minor espionage detected in Steel inventory.</p>
            <p className="text-slate-500 text-opacity-50 tracking-widest">_</p>
          </div>
        </section>

      </main>

      {/* FOOTER TICKER */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800 h-8 flex items-center overflow-hidden">
        <div className="animate-marquee whitespace-nowrap flex gap-10 items-center text-[10px] uppercase tracking-widest text-emerald-500/80">
          <span>Global Demand for Steel is rising...</span>
          <span>Player_X33 just liquidated 400 Iron...</span>
          <span>New Policy Proposal: Tax Havens...</span>
          <span>Corporate Espionage attempts up 12% this week...</span>
        </div>
      </footer>

      <style jsx>{`
        @keyframes marquee {
          0% { transform: translateX(100%); }
          100% { transform: translateX(-100%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
      `}</style>
    </div>
  );
}