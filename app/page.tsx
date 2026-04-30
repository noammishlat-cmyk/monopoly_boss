"use client"

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Pickaxe, Cpu, Crosshair, Users, BarChart3, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine  } from 'recharts';

// --- Types ---
type GameState = {
  market: any[];
  user: {
    balance: number;
    inventory: Record<string, number>;
  };
  history: any[];
  nextTick: number;
};

export default function MonopolyBoss() {
  // 1. Unified Game State
  const [gameState, setGameState] = useState<GameState>({
    market: [],
    user: { balance: 0, inventory: {} },
    history: [],
    nextTick: 0,
  });

  const [selectedItem, setSelectedItem] = useState("Iron");
  const [tradeAmounts, setTradeAmounts] = useState<Record<string, number>>({});
  const [lastDeployment, setLastDeployment] = useState<typeof allocation | null>(null);
  
  // Refs for background logic
  const userId = "user123";


  // --- Workforce Allocation State ---
  const [MAX_WORKFORCE, SET_MAX_WORKFORCE] = useState(5); // Total units available to the player
  const [allocation, setAllocation] = useState({
    extraction: 0,
    rnd: 0,
    espionage: 0
  });

  // Calculate used and available units
  const deployedUnits = allocation.extraction + allocation.rnd + allocation.espionage;
  const availableUnits = MAX_WORKFORCE - deployedUnits;

  const handleAllocationChange = (dept: string, value: number) => {
    setAllocation(prev => {
      // Calculate how many units are used by OTHER departments
      const otherUnits = Object.keys(prev).reduce(
        (sum, key) => (key !== dept ? sum + prev[key as keyof typeof prev] : sum), 
        0
      );
      
      // Prevent allocating more than the max limit
      const maxAllowed = MAX_WORKFORCE - otherUnits;
      const newValue = Math.min(value, maxAllowed);

      return { ...prev, [dept]: newValue };
    });
  };

  // Mock function to "send" orders to the server
  const deployWorkforce = () => {
    setLastDeployment({ ...allocation });
    setIsPendingReturn(true);

    // Logic for the backend would go here

  };



  const refreshData = useCallback(async (isInitial = false) => {
    try {
      // Only show the loading screen if we are intentionally switching items
      if (isInitial) setIsHistoryLoading(true);

      const url = `http://localhost:5000/api/state/${userId}?item=${selectedItem || 'Iron'}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error();
      const data = await res.json();

      setGameState({
        market: data.market,
        user: data.user,
        history: data.history,
        nextTick: data.next_tick
      });

      setTickInterval(data.tick_length)

    } catch (err) {
      setError("Sync Error");
    } finally {
      setIsHistoryLoading(false); // Turn off loader
    }
  }, [selectedItem, userId]);

  const handleSelect = (name: string) => {
    if (name === selectedItem) return;
    setSelectedItem(name);
    setIsHistoryLoading(true);
    // Clear the history immediately so the old graph disappears
    setGameState(prev => ({ ...prev, history: [] })); 
  };



  // 3. The Single Heartbeat (Visual countdown + Data Polling)
  

  // 4. Trade Execution
  const handleTrade = async (item: string, action: string) => {
    const amount = tradeAmounts[item] || 0;
    if (amount <= 0) return;

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, item: item, amount: amount }),
      });
      
      if (response.ok) {
        refreshData();
        setTradeAmounts(prev => ({ ...prev, [item]: 0 })); // Reset input
      } else {
        const err = await response.json();
        alert(err.error);
      }
    } catch (e) {
      alert("Trade server unreachable");
    }
  };

  const setMax = (item: any, action: 'buy' | 'sell') => {
    let amount = 0;
    if (action === 'buy') {
      amount = Math.floor(gameState.user.balance / item.price);
    } else {
      amount = gameState.user.inventory[item.name] || 0;
    }
    setTradeAmounts(prev => ({ ...prev, [item.name]: amount }));
  };
  
  const history = gameState.history;
  const prices = history.map(h => h.price);
  
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const firstPrice = history.length > 0 ? history[0].price : 0;

  let offset = 0;
  if (maxPrice !== minPrice) {
    // This calculates the percentage of the height where the starting price sits
    // We use (max - first) because SVG coordinates start from the top (0)
    offset = ((maxPrice - firstPrice) / (maxPrice - minPrice)) * 100;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 font-mono">
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT: WORKFORCE COMMAND DIRECTIVE (4 cols) */}
        <section className="lg:col-span-4 h-full">
          {!isPendingReturn ? (
            /* --- STATE 1: MANAGEMENT (Available) --- */
            <div className="space-y-4 animate-in fade-in slide-in-from-left-4 duration-500">
              <div className="flex justify-between items-end mb-2 border-b border-slate-800 pb-2">
                <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-2 uppercase tracking-tighter">
                  <Users size={16} className="text-emerald-500" /> HQ_Workforce
                </h2>
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest block">Available Units</span>
                  <span className={`text-sm font-bold tabular-nums ${availableUnits === 0 ? 'text-orange-500' : 'text-emerald-400'}`}>
                    {availableUnits} / {MAX_WORKFORCE}
                  </span>
                </div>
              </div>

              {/* Slider Blocks */}
              {[
                { id: 'extraction', label: 'Extraction', icon: <Pickaxe size={12} />, color: 'emerald', desc: 'Yield' },
                { id: 'rnd', label: 'R&D Analytics', icon: <Cpu size={12} />, color: 'blue', desc: 'Efficiency' },
                { id: 'espionage', label: 'Sabotage', icon: <Crosshair size={12} />, color: 'orange', desc: 'Volatility' }
              ].map((dept) => (
                <div key={dept.id} className={`bg-slate-900/50 border border-slate-800 p-3 rounded-sm transition-colors hover:border-${dept.color}-900/50`}>
                  <div className="flex justify-between items-center mb-1">
                    <span className={`text-[11px] font-bold text-slate-300 uppercase flex items-center gap-1.5`}>
                      {React.cloneElement(dept.icon as React.ReactElement<{ className?: string }>, { 
                          className: `text-${dept.color}-500` 
                        })} {dept.label}
                    </span>
                    <span className={`text-[10px] font-mono text-${dept.color}-400`}>{allocation[dept.id as keyof typeof allocation]} Assigned</span>
                  </div>
                  <input 
                    type="range" 
                    min="0" max={MAX_WORKFORCE}
                    value={allocation[dept.id as keyof typeof allocation]}
                    onChange={(e) => handleAllocationChange(dept.id, parseInt(e.target.value))}
                    className={`w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-${dept.color}-500`}
                  />
                </div>
              ))}

              <button 
                onClick={deployWorkforce}
                disabled={deployedUnits === 0}
                className="w-full py-3 mt-4 bg-emerald-600/10 hover:bg-emerald-600 border border-emerald-500/50 text-[10px] font-bold uppercase tracking-[0.2em] transition-all active:scale-[0.98] text-emerald-500 hover:text-white"
              >
                Execute Deployment
              </button>
            </div>
          ) : (
            /* --- STATE 2: MONITORING (Deployed) --- */
            <div className="bg-slate-900/40 border border-emerald-500/20 h-full p-6 rounded-sm animate-in zoom-in-95 duration-300 flex flex-col items-center justify-center text-center relative overflow-hidden">
              {/* Background scanning effect */}
              <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/5 to-transparent pointer-events-none animate-pulse" />
              
              <div className="relative z-10">
                <div className="relative mb-6">
                   <div className="w-16 h-16 border-2 border-emerald-500/20 rounded-full border-t-emerald-500 animate-spin mx-auto" />
                   <Users className="absolute inset-0 m-auto text-emerald-500 animate-pulse" size={24} />
                </div>

                <h2 className="text-emerald-500 font-bold uppercase tracking-[0.3em] text-xs mb-1">Field Ops Active</h2>
                <p className="text-[10px] text-slate-500 uppercase mb-8">Personnel currently out of range</p>
                
                <div className="w-48 space-y-3 mb-8">
                  {[
                    { label: 'EXTRACTION', val: lastDeployment?.extraction, color: 'text-emerald-400' },
                    { label: 'R&D_TEAMS', val: lastDeployment?.rnd, color: 'text-blue-400' },
                    { label: 'SABOTEURS', val: lastDeployment?.espionage, color: 'text-orange-400' }
                  ].map(stat => (
                    <div key={stat.label} className="flex justify-between border-b border-slate-800 pb-1 font-mono text-[10px]">
                      <span className="text-slate-500">{stat.label}</span>
                      <span className={stat.color}>{stat.val}</span>
                    </div>
                  ))}
                </div>

                <div className="p-3 bg-black border border-slate-800 inline-block w-full">
                   <span className="text-[9px] text-slate-500 uppercase block mb-1">Estimated Return In</span>
                   <span className="text-xl font-light text-white tabular-nums tracking-widest">
                     {secondsRemaining}s
                   </span>
                </div>
                
                <p className="mt-6 text-[8px] text-slate-600 uppercase tracking-widest italic animate-pulse">
                  System locked until next market tick...
                </p>
              </div>
            </div>
          )}
        </section>

        {/* MIDDLE: MARKET & GRAPH (5 cols) */}
        <section className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-sm overflow-hidden shadow-2xl">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-800 text-slate-500 uppercase text-[9px] tracking-widest">
                <tr>
                  <th className="p-3">Resource</th>
                  <th className="p-3 text-right">Price</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Held</th>
                  <th className="p-3 text-center">Execute</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {gameState.market.map((item) => (
                  <tr 
                    key={item.name} 
                    onClick={() => handleSelect(item.name)} 
                    className={`
                      cursor-pointer transition-all duration-200 select-none
                      ${selectedItem === item.name ? 'bg-emerald-900/20 border-l-2 border-emerald-500' : 'hover:bg-slate-800/60 border-l-2 border-transparent'}
                    `}
                  >
                    <td className="p-3 font-bold text-slate-300">{item.name}</td>
                    <td className="p-3 text-right tabular-nums font-bold text-white">${item.price.toFixed(2)}</td>
                    <td className="p-3 text-center">
                      {(() => {
                        const d = item.demand; const s = item.supply;
                        if (d > s * 1.1) return <span className="text-orange-500 text-[8px] font-black border border-orange-900/50 px-1 bg-orange-900/10">HIGH DEMAND</span>;
                        if (s > d * 1.1) return <span className="text-blue-400 text-[8px] font-black border border-blue-900/50 px-1 bg-blue-900/10">SURPLUS</span>;
                        return <span className="text-slate-600 text-[8px] font-bold uppercase">Stable</span>;
                      })()}
                    </td>
                    <td className={`p-3 text-right tabular-nums font-bold ${gameState.user.inventory[item.name] > 0 ? 'text-emerald-400' : 'text-slate-700'}`}>
                      {gameState.user.inventory[item.name] || 0}
                    </td>
                    
                    {/* FIXED COLUMN BELOW */}
                    <td className="p-3 text-center"> 
                        {/* REMOVED stopPropagation from TD and put it on the DIV instead */}
                        <div className="inline-flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <div className="flex flex-col gap-1 items-center">
                                <input 
                                  type="number" 
                                  className="w-10 bg-black border border-slate-700 p-1 text-[9px] text-center"
                                  value={tradeAmounts[item.name] || 0}
                                  onChange={(e) => setTradeAmounts({...tradeAmounts, [item.name]: parseInt(e.target.value) || 0})}
                                />
                                <div className="flex gap-1">
                                    <button onClick={() => setMax(item, 'buy')} className="text-[7px] text-slate-500 hover:text-white uppercase">BuyM</button>
                                    <button onClick={() => setMax(item, 'sell')} className="text-[7px] text-slate-500 hover:text-white uppercase">SellM</button>
                                </div>
                            </div>
                            <button onClick={() => handleTrade(item.name, 'buy')} className="bg-emerald-700/40 hover:bg-emerald-600 px-2 py-1 text-[9px] font-bold border border-emerald-900">BUY</button>
                            <button onClick={() => handleTrade(item.name, 'sell')} className="bg-red-700/40 hover:bg-red-600 px-2 py-1 text-[9px] font-bold border border-red-900">SELL</button>
                        </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Integrated Performance Graph */}
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-sm relative overflow-hidden min-h-[200px]">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest flex items-center gap-2">
                <Activity size={12} className={isHistoryLoading ? "animate-spin" : "animate-pulse"} />
                Telemetry Feed: {selectedItem}
              </h3>
            </div>

            {/* LOADING OVERLAY */}
            {isHistoryLoading && (
              <div className="absolute inset-0 z-10 bg-slate-900/80 backdrop-blur-sm flex flex-col items-center justify-center border border-emerald-900/30">
                <div className="flex gap-1 mb-2">
                  <div className="w-1 h-4 bg-emerald-500 animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-1 h-4 bg-emerald-500 animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-1 h-4 bg-emerald-500 animate-bounce"></div>
                </div>
                <p className="text-[9px] text-emerald-500 font-bold tracking-[0.2em] animate-pulse">
                  SYNCING_DATA_PACKETS...
                </p>
              </div>
            )}

            <div className="h-40 w-full relative">
              {!isHistoryLoading && gameState.history.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={gameState.history}>
                    <defs>
                      {/* This gradient handles the color switch */}
                      <linearGradient id="lineColor" x1="0" y1="0" x2="0" y2="1">
                        <stop offset={`${offset}%`} stopColor="#10b981" stopOpacity={1} /> {/* Green above offset */}
                        <stop offset={`${offset}%`} stopColor="#ef4444" stopOpacity={1} /> {/* Red below offset */}
                      </linearGradient>
                      
                      {/* Optional: Add a subtle glow/fill that also respects the offset */}
                      <linearGradient id="fillColor" x1="0" y1="0" x2="0" y2="1">
                        <stop offset={`${offset}%`} stopColor="#10b981" stopOpacity={0.1} />
                        <stop offset={`${offset}%`} stopColor="#ef4444" stopOpacity={0.1} />
                      </linearGradient>
                    </defs>

                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} opacity={0.2} />
                    
                    <XAxis dataKey="time" hide />
                    <YAxis hide domain={['auto', 'auto']} />
                    
                    {/* The Baseline: Shows the starting price level */}
                    <ReferenceLine 
                      y={firstPrice} 
                      stroke="#475569" 
                      strokeDasharray="3 3" 
                      label={{ position: 'right', value: 'START', fill: '#475569', fontSize: 8 }} 
                    />

                    <Tooltip 
                      contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', fontSize: '10px' }} 
                      labelStyle={{ display: 'none' }}
                    />

                    {/* The Main Line using the gradient */}
                    <Line 
                      type="monotone" 
                      dataKey="price" 
                      stroke="url(#lineColor)" 
                      strokeWidth={2} 
                      dot={false} 
                      isAnimationActive={false} 
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full w-full flex items-center justify-center opacity-20">
                  <BarChart3 size={40} />
                </div>
              )}
            </div>
          </div>
        </section>

        {/* RIGHT: LOG (3 cols) */}
        <section className="lg:col-span-3">
          <h2 className="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-tighter">Command Log</h2>
          <div className="bg-black p-3 rounded border border-slate-800 h-[500px] overflow-y-auto font-mono text-[9px] space-y-1">
             <p className="text-emerald-900 font-bold mb-2">SYSTEM_BOOT_SUCCESSFUL...</p>
             <p className="text-slate-600">[{new Date().toLocaleTimeString()}] Establishing uplink...</p>
             <p className="text-slate-600">[{new Date().toLocaleTimeString()}] Market sync: {gameState.market.length} resources active.</p>
             <p className="text-blue-500">[{new Date().toLocaleTimeString()}] Monitoring focus: {selectedItem}</p>
             {error && <p className="text-red-500">[{new Date().toLocaleTimeString()}] WARNING: {error}</p>}
             <p className="animate-pulse text-emerald-500">_</p>
          </div>
        </section>

      </main>

      {/* FOOTER TICKER */}
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
    </div>
  );
}