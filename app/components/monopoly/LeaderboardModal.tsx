import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  balance: number;
  net_worth: number;
  inventory_value: number;
  inventory: Record<string, number> | "Hidden";
}

interface LeaderboardModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: LeaderboardEntry[];
  formatCurrency: (val: number) => string;
}

export const LeaderboardModal = ({ isOpen, onClose, data, formatCurrency }: LeaderboardModalProps) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
          />

          {/* Modal Content */}
          <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 shadow-2xl rounded-sm overflow-hidden font-mono"
          >
            {/* Header */}
            <div className="bg-slate-800 p-4 border-b border-slate-700 flex justify-between items-center">
              <div>
                <h2 className="text-emerald-400 font-black tracking-tighter uppercase text-lg">Global_Ranking</h2>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest">End of Cycle: Sunday 23:59</p>
              </div>
              <button 
                onClick={onClose}
                className="text-slate-500 hover:text-white transition-colors text-xl"
              >
                ✕
              </button>
            </div>

            {/* Table Header */}
            <div className="grid grid-cols-12 gap-2 p-3 bg-slate-950/50 text-[10px] font-bold text-slate-500 uppercase border-b border-slate-800">
              <div className="col-span-1 text-center">Rk</div>
              <div className="col-span-4">Entity_ID</div>
              <div className="col-span-3 text-right">Liquidity</div>
              <div className="col-span-4 text-right">Net_Worth</div>
            </div>

            {/* List */}
            <div className="max-h-[60vh] overflow-y-auto custom-scrollbar">
              {data.map((player) => (
                <div 
                  key={player.user_id} 
                  className={`grid grid-cols-12 gap-2 p-3 border-b border-slate-800/50 items-center transition-colors hover:bg-slate-800/30 ${player.rank === 1 ? 'bg-emerald-500/5' : ''}`}
                >
                  <div className="col-span-1 text-center font-black text-slate-500 text-xs">
                    {player.rank}
                  </div>
                  
                  <div className="col-span-4">
                    <div className="text-[11px] font-bold text-slate-200 truncate uppercase">
                      {player.user_id}
                    </div>
                    {/* Inventory Mini-View */}
                    <div className="flex gap-1 mt-1">
                      {typeof player.inventory === 'object' ? (
                        Object.entries(player.inventory).map(([res, amt]) => (
                          <span key={res} className="text-[8px] bg-slate-950 px-1 border border-slate-800 text-slate-500 rounded-xs">
                            {res[0]}:{amt}
                          </span>
                        ))
                      ) : (
                        <span className="text-[8px] text-slate-700 italic tracking-widest uppercase">Inventory_Encrypted</span>
                      )}
                    </div>
                  </div>

                  <div className="col-span-3 text-right tabular-nums text-[11px] text-slate-400">
                    {formatCurrency(player.balance)}
                  </div>

                  <div className="col-span-4 text-right tabular-nums text-[12px] font-bold text-emerald-400">
                    {formatCurrency(player.net_worth)}
                  </div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="p-3 bg-slate-950/80 text-center">
              <p className="text-[9px] text-slate-600 uppercase tracking-widest">
                System sync successful. All values updated to current market prices.
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};