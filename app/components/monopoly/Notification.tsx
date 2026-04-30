"use client";
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle } from 'lucide-react';

interface NotificationProps {
  message: string | null;
  isVisible: boolean;
  onClose: () => void;
}

export const Notification = ({ message, isVisible, onClose }: NotificationProps) => {
  
  // Handle auto-dismiss logic here to keep the main page clean
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ y: 50, opacity: 0, x: "-50%" }}
          animate={{ y: 0, opacity: 1, x: "-50%" }}
          exit={{ y: 20, opacity: 0, x: "-50%" }}
          className="fixed bottom-10 left-1/2 z-[100]"
        >
          <div 
            onClick={onClose}
            className="bg-red-950 border border-red-500 text-red-200 px-6 py-3 rounded-md shadow-[0_0_15px_rgba(239,68,68,0.3)] flex items-center gap-3 font-mono cursor-pointer hover:bg-red-900 transition-colors"
          >
            <AlertCircle size={18} className="text-red-500" />
            <span>{message}</span>
            <div className="ml-4 text-[10px] opacity-50 text-red-400 font-bold uppercase tracking-widest border-l border-red-500/30 pl-4">
              Dismiss
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};