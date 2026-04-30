"use client";
import { motion, AnimatePresence } from 'framer-motion';
import { Info, X } from 'lucide-react';
import { useState } from 'react';

interface DeptInfoProps {
  label: string;
  description: string;
  color: string;
}

export const DeptInfo = ({ label, description, color }: DeptInfoProps) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative inline-block ml-1">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`p-0.5 hover:bg-slate-800 rounded transition-colors text-slate-500 hover:text-${color}-400`}
      >
        <Info size={10} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Transparent click-away overlay */}
            <div className="fixed inset-0 z-[60]" onClick={() => setIsOpen(false)} />
            
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 5 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 5 }}
              className="absolute left-0 top-6 w-128 p-3 bg-slate-950 border border-slate-700 shadow-xl z-[70] rounded-sm pointer-events-auto"
            >
              <div className="flex justify-between items-start mb-2">
                <span className={`text-[14px] font-bold uppercase tracking-tighter text-${color}-400`}>
                  Subsystem: {label}
                </span>
                <button onClick={() => setIsOpen(false)}>
                  <X size={14} className="text-slate-600 hover:text-white" />
                </button>
              </div>
              <p className="text-[10px] leading-relaxed text-slate-400 whitespace-pre-line">
                {description}
              </p>
              <div className={`absolute -top-1 left-2 w-2 h-2 bg-slate-950 border-l border-t border-slate-700 rotate-45`} />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};