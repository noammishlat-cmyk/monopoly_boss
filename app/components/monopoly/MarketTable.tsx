import React from 'react';

interface MarketTableProps {
  market: any[];
  selectedItem: string;
  onSelect: (name: string) => void;
  inventory: Record<string, number>;
  tradeAmounts: Record<string, number>;
  setTradeAmounts: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  handleTrade: (item: string, action: string) => void;
  setMax: (item: any, action: 'buy' | 'sell') => void;
}

export const MarketTable = ({
  market,
  selectedItem,
  onSelect,
  inventory,
  tradeAmounts,
  setTradeAmounts,
  handleTrade,
  setMax
}: MarketTableProps) => {
  return (
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
          {market.map((item) => (
            <tr 
              key={item.name} 
              onClick={() => onSelect(item.name)} 
              className={`cursor-pointer transition-all duration-200 select-none ${
                selectedItem === item.name ? 'bg-emerald-900/20 border-l-2 border-emerald-500' : 'hover:bg-slate-800/60 border-l-2 border-transparent'
              }`}
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
              <td className={`p-3 text-right tabular-nums font-bold ${inventory[item.name] > 0 ? 'text-emerald-400' : 'text-slate-700'}`}>
                {inventory[item.name] || 0}
              </td>
              <td className="p-3 text-center"> 
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
  );
};