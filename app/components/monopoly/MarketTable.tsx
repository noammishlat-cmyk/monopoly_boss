import React from 'react';

type  MarketItem = {
  name: string;
  price: number;
  base_price: number;
  demand: number;
  supply: number;
}

interface MarketTableProps {
  market: MarketItem[];
  selectedItem: string;
  onSelect: (name: string) => void;
  inventory: Record<string, number>;
  tradeAmounts: Record<string, number>;
  setTradeAmounts: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  handleTrade: (item: string, action: string) => void;
  setMax: (item: {name: string, price: number}, action: 'buy' | 'sell') => void;
  currentTax: number;
}

export const MarketTable = ({
  market,
  selectedItem,
  onSelect,
  inventory,
  tradeAmounts,
  setTradeAmounts,
  handleTrade,
  setMax,
  currentTax,
}: MarketTableProps) => {
  return (
    <div className="w-full">
      
      {/* ========================================================= */}
      {/* 1. MOBILE COMPACT SCROLL VIEW                            */}
      {/* ========================================================= */}
      <div className="flex md:hidden flex-col gap-2">
        {/* Fixed height window to prevent pushing down the graph */}
        <div className="max-h-[280px] overflow-y-auto border border-slate-800 bg-slate-950/40 p-2 rounded-sm flex flex-col gap-1.5 custom-scrollbar">
          {market.map((item) => {
            const isSelected = selectedItem === item.name;
            const itemHeld = inventory[item.name] || 0;

            return (
              <div 
                key={item.name} 
                onClick={() => onSelect(item.name)} 
                className={`p-3 rounded-sm border backdrop-blur-md transition-all duration-200 select-none flex flex-col gap-3 ${
                  isSelected 
                    ? 'bg-emerald-950/40 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.05)]' 
                    : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-800/40'
                }`}
              >
                {/* Compact Row: Name (Left), Status (Center), Pricing (Right) */}
                <div className="grid grid-cols-3 items-center text-[10px]">
                  
                  {/* 1. LEFT: Name & Pip */}
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-700'}`} />
                    <span className="font-bold text-slate-200 uppercase tracking-wider truncate">
                      {item.name}
                    </span>
                  </div>

                  {/* 2. CENTER: Status Badge */}
                  <div className="flex justify-center">
                    {(() => {
                      const d = item.demand; const s = item.supply;
                      if (d > s * 1.1) return <span className="text-orange-400 text-[7px] font-black tracking-wider whitespace-nowrap">▲ HIGH DEMAND</span>;
                      if (s > d * 1.1) return <span className="text-blue-400 text-[7px] font-black tracking-wider whitespace-nowrap">▼ SURPLUS</span>;
                      return <span className="text-slate-600 text-[7px] font-bold uppercase whitespace-nowrap">● Stable</span>;
                    })()}
                  </div>

                  {/* 3. RIGHT: Pricing & Balance */}
                  <div className="flex items-center justify-end gap-3 tabular-nums text-right">
                    <div>
                      <span className="font-bold text-white">
                        ${(item.price * (tradeAmounts[item.name] || 1)).toFixed(1)}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 mr-1 text-[8px]">Holding:</span>
                      <span className={`font-bold ${itemHeld > 0 ? 'text-emerald-400' : 'text-slate-600'}`}>
                        {itemHeld}
                      </span>
                    </div>
                  </div>
                </div>

                {/* --- Expandable Drawer (Revealed only when selected) --- */}
                {isSelected && (
                  <div 
                    className="flex flex-col gap-3 pt-2 border-t border-slate-800/80 animate-fadeIn" 
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="grid grid-cols-2 gap-4">
                      {/* Sell price info */}
                      <div className="text-[9px] flex items-center justify-between text-slate-400">
                        <span>Sell Net ({currentTax.toFixed(2)}% Tax):</span>
                        <span className="font-bold text-white tracking-wide">
                          ${(item.price * (1 - currentTax) * (tradeAmounts[item.name] || 1)).toFixed(2)}
                        </span>
                      </div>
                      
                      {/* Status badge /}
                      <div className="flex justify-end items-center">
                        {(() => {
                          const d = item.demand; const s = item.supply;
                          if (d > s * 1.1) return <span className="text-orange-400 text-[7px] font-black tracking-wider">▲ HIGH DEMAND</span>;
                          if (s > d * 1.1) return <span className="text-blue-400 text-[7px] font-black tracking-wider">▼ SURPLUS</span>;
                          return <span className="text-slate-600 text-[7px] font-bold uppercase">● Stable</span>;
                        })()}
                      </div>
                      */}
                    </div>

                    {/* Transaction Control Bar */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <input 
                          type="number" 
                          min="0"
                          className="w-12 bg-black border border-slate-700 p-1.5 text-xs text-center text-slate-200 focus:border-emerald-500 outline-none rounded-sm font-bold"
                          value={tradeAmounts[item.name] || 0}
                          onChange={(e) => setTradeAmounts({...tradeAmounts, [item.name]: parseInt(e.target.value) || 0})}
                        />
                        <div className="flex flex-col gap-0.5">
                          <button 
                            onClick={() => setMax(item, 'buy')} 
                            className="text-[7px] bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-emerald-400 font-bold px-1.5 py-0.5 uppercase transition-colors rounded-sm border border-slate-700/60"
                          >
                            BuyM
                          </button>
                          <button 
                            onClick={() => setMax(item, 'sell')} 
                            className="text-[7px] bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-red-400 font-bold px-1.5 py-0.5 uppercase transition-colors rounded-sm border border-slate-700/60"
                          >
                            SellM
                          </button>
                        </div>
                      </div>

                      {/* Execution */}
                      <div className="flex gap-1 flex-1 max-w-[120px]">
                        <button 
                          onClick={() => handleTrade(item.name, 'buy')} 
                          className="flex-1 bg-emerald-700/20 hover:bg-emerald-600/40 text-emerald-400 py-2 text-[9px] font-bold border border-emerald-900/50 rounded-sm transition-all tracking-wider text-center"
                        >
                          BUY
                        </button>
                        <button 
                          onClick={() => handleTrade(item.name, 'sell')} 
                          className="flex-1 bg-red-700/20 hover:bg-red-600/40 text-red-400 py-2 text-[9px] font-bold border border-red-900/50 rounded-sm transition-all tracking-wider text-center"
                        >
                          SELL
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. DESKTOP LAYOUT (Unchanged)                             */}
      {/* ========================================================= */}
      <div className="hidden md:block bg-slate-900 border border-slate-800 rounded-sm overflow-hidden shadow-2xl">
        <table className="w-full text-left text-[11px] border-collapse">
          <thead className="bg-slate-800 text-slate-500 uppercase text-[9px] tracking-widest">
            <tr>
              <th className="p-3">Resource</th>
              <th className="p-3 text-center">Buy</th>
              <th className="p-3 text-center">Sell - Tax {currentTax.toFixed(2)}%</th>
              <th className="p-3 text-center">Status</th>
              <th className="p-3 text-center">Held</th>
              <th className="p-3 text-center">Execute</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {market.map((item) => (
              <tr 
                key={item.name} 
                onClick={() => onSelect(item.name)} 
                className={`cursor-pointer transition-all duration-200 select-none ${
                  selectedItem === item.name ? 'bg-emerald-900/20 border-l-2 border-emerald-500' : 'hover:bg-slate-800/60 border-l-2 border-transparent'
                }`}
              >
                <td className="p-3 font-bold text-slate-300">{item.name}</td>
                <td className="p-3 text-center tabular-nums font-bold text-white">
                  ${(item.price * (tradeAmounts[item.name] || 1)).toFixed(2)}
                </td>
                <td className="p-3 text-center tabular-nums font-bold text-white">
                  ${(item.price * (1 - currentTax) * (tradeAmounts[item.name] || 1)).toFixed(2)}
                </td>
                <td className="p-3 text-center">
                  <div className="flex justify-center">
                    {(() => {
                      const d = item.demand; const s = item.supply;
                      if (d > s * 1.1) return <span className="text-orange-500 text-[8px] font-black border border-orange-900/50 px-1 bg-orange-900/10">HIGH DEMAND</span>;
                      if (s > d * 1.1) return <span className="text-blue-400 text-[8px] font-black border border-blue-900/50 px-1 bg-blue-900/10">SURPLUS</span>;
                      return <span className="text-slate-600 text-[8px] font-bold uppercase">Stable</span>;
                    })()}
                  </div>
                </td>
                <td className={`p-3 text-center tabular-nums font-bold ${inventory[item.name] > 0 ? 'text-emerald-400' : 'text-slate-700'}`}>
                  {inventory[item.name] || 0}
                </td>
                <td className="p-3"> 
                  <div className="flex items-center justify-center gap-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex flex-col gap-1 items-center">
                      <input 
                        type="number" 
                        min="0"
                        className="w-12 bg-black border border-slate-700 p-1 text-[10px] text-center focus:border-emerald-500 outline-none"
                        value={tradeAmounts[item.name] || 0}
                        onChange={(e) => setTradeAmounts({...tradeAmounts, [item.name]: parseInt(e.target.value) || 0})}
                      />
                      <div className="flex gap-2">
                        <button onClick={() => setMax(item, 'buy')} className="text-[7px] text-slate-500 hover:text-emerald-400 uppercase transition-colors">BuyM</button>
                        <button onClick={() => setMax(item, 'sell')} className="text-[7px] text-slate-500 hover:text-red-400 uppercase transition-colors">SellM</button>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => handleTrade(item.name, 'buy')} className="bg-emerald-700/20 hover:bg-emerald-600/40 text-emerald-400 px-2 py-1.5 text-[9px] font-bold border border-emerald-900/50 rounded-sm transition-all">BUY</button>
                      <button onClick={() => handleTrade(item.name, 'sell')} className="bg-red-700/20 hover:bg-red-600/40 text-red-400 px-2 py-1.5 text-[9px] font-bold border border-red-900/50 rounded-sm transition-all">SELL</button>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};