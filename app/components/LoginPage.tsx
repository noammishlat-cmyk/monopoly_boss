import React, { useState } from 'react';
import { motion } from 'framer-motion';

export const LoginPage = (
  { onLogin, isLoading }: { onLogin: (id: string) => void, isLoading: boolean }) => {
  const [inputId, setInputId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputId.trim()) {
      onLogin(inputId.trim());
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 font-mono">
      {/* Animated Background scanline effect */}
      <div className="fixed inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-10 bg-[length:100%_2px,3px_100%]" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-20 w-full max-w-md"
      >
        {/* Decorative Corner Brackets */}
        <div className="absolute -top-2 -left-2 w-8 h-8 border-t-2 border-l-2 border-emerald-500/50" />
        <div className="absolute -bottom-2 -right-2 w-8 h-8 border-b-2 border-r-2 border-emerald-500/50" />

        <div className="bg-black/60 backdrop-blur-xl border border-slate-800 p-8 shadow-2xl shadow-emerald-500/10">
          <header className="mb-8">
            <h1 className="text-2xl font-black text-emerald-500 italic tracking-tighter uppercase mb-1">
              Monopoly_Boss
            </h1>
            <div className="flex items-center gap-2">
              <span className="h-[1px] w-8 bg-emerald-500/30" />
              <p className="text-[10px] text-slate-500 uppercase tracking-[0.3em]">
                Secure_Gateway_V3
              </p>
            </div>
          </header>


          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-[10px] uppercase text-slate-500 font-bold mb-2 tracking-widest">
                Identity_Token (User_ID)
              </label>
              <input 
                type="text"
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
                disabled={isLoading} // Disable while loading
                placeholder={isLoading ? "AUTHENTICATING..." : "ENTER_AUTH_ID..."}
                className={`w-full bg-slate-900/50 border border-slate-800 p-3 text-emerald-400 placeholder:text-slate-700 focus:outline-none focus:border-emerald-500/50 transition-all text-sm ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                required
              />
            </div>

            <button 
              type="submit"
              disabled={isLoading} // Disable while loading
              className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-black font-black py-3 uppercase text-xs tracking-widest transition-all active:scale-95 shadow-[0_0_20px_rgba(16,185,129,0.2)]"
            >
              {isLoading ? 'Signing In...' : 'Initialize_Session'}
            </button>
          </form>

          <footer className="mt-8 pt-6 border-t border-slate-800/50">
            <div className="flex justify-between items-center text-[8px] text-slate-600 uppercase tracking-tighter">
              <span>Status: Waiting_For_Auth</span>
              <span className="animate-pulse">System_Online</span>
            </div>
          </footer>
        </div>

        <p className="text-center mt-6 text-[9px] text-slate-700 uppercase tracking-widest">
          Unauthorized access is logged and prosecuted by the <span className="text-slate-500">Corporate Council</span>.
        </p>
      </motion.div>
    </div>
  );
};