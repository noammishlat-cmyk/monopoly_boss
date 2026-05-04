import React, { useState } from 'react';

import { FormattedValue } from './FormattedValue';

export interface VoteChoice {
  id: string;
  label: string;
  votes: number;
}

interface VotingPanelProps {
  prompt: string;
  choices: VoteChoice[];
  secondsRemaining: number;
  playerBalance: number;
  onCastVote: (choiceId: string, amount: number) => void;
}

export const VotingPanel = ({
  prompt,
  choices,
  secondsRemaining,
  playerBalance,
  onCastVote,
}: VotingPanelProps) => {
  const [voteAmounts, setVoteAmounts] = useState<Record<string, number>>({});
  const totalVotes = choices.reduce((acc, curr) => acc + curr.votes, 0);

  const handleAmountChange = (choiceId: string, value: string) => {
    const parsed = parseInt(value) || 0;
    setVoteAmounts((prev) => ({ ...prev, [choiceId]: Math.max(0, parsed) }));
  };

  const handleMaxAmount = (choiceId: string) => {
    setVoteAmounts((prev) => ({ ...prev, [choiceId]: Math.floor(playerBalance) }));
  };

  const executeVote = (choiceId: string) => {
    const amount = voteAmounts[choiceId] || 0;
    if (amount <= 0 || amount > playerBalance) return;
    onCastVote(choiceId, amount);
    setVoteAmounts((prev) => ({ ...prev, [choiceId]: 0 }));
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-sm overflow-hidden flex flex-col shadow-2xl font-mono">
      {/* 1. SYSTEM HEADER */}
      <div className="bg-slate-800 p-2 flex justify-between items-center border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Gov_Protocol.exe</span>
        </div>
        <span className={`text-[10px] font-bold tabular-nums text-center ${secondsRemaining <= 10 ? 'text-red-500' : 'text-amber-500'}`}>
          Vote advances in: {<FormattedValue value={secondsRemaining} type="time" />}
        </span>
      </div>

      {/* 2. PROMPT DESCRIPTION */}
      <div className="p-3 bg-slate-950/40 border-b border-slate-800/50">
        <p className="text-[11px] leading-relaxed text-slate-400">
          <span className="text-emerald-500 mr-2 font-bold">{'>'}</span>
          {prompt}
        </p>
      </div>

      {/* 3. VOTING OPTIONS (Vertical Stack for Sidebar) */}
      <div className="p-2 space-y-2">
        {choices.map((choice) => {
          const currentAmount = voteAmounts[choice.id] || 0;
          const voteShare = totalVotes > 0 ? (choice.votes / totalVotes) * 100 : 0;
          const isAffordable = currentAmount <= playerBalance && currentAmount > 0;

          return (
            <div 
              key={choice.id} 
              className="group border border-slate-800 bg-slate-900/50 p-2 rounded-sm transition-all hover:border-slate-700"
            >
              {/* Choice Label & Current Weight */}
              <div className="flex justify-between items-start mb-2">
                <span className="text-[10px] font-bold text-slate-200 uppercase tracking-tight max-w-[70%]">
                  {choice.label}
                </span>
                <span className="text-[9px] text-slate-500 font-bold tabular-nums bg-black px-1 border border-slate-800">
                  {voteShare.toFixed(1)}%
                </span>
              </div>

              {/* Minimal Progress Bar */}
              <div className="w-full bg-black h-1 rounded-full overflow-hidden mb-3">
                <div 
                  className="bg-emerald-500/60 h-full transition-all duration-700" 
                  style={{ width: `${voteShare}%` }} 
                />
              </div>

              {/* Compact Input Area */}
              <div className="flex items-center gap-1.5">
                <div className="relative flex-1">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[9px] text-slate-600">$</span>
                  <input
                    type="number"
                    min="0"
                    placeholder="AMOUNT"
                    className="w-full bg-black border border-slate-800 py-1.5 pl-4 pr-1 text-[10px] text-emerald-400 focus:border-emerald-500 outline-none rounded-sm font-bold transition-all"
                    value={voteAmounts[choice.id] || ''}
                    onChange={(e) => handleAmountChange(choice.id, e.target.value)}
                  />
                </div>
                
                <button
                  onClick={() => handleMaxAmount(choice.id)}
                  className="text-[8px] bg-slate-800 text-slate-400 px-2 py-2 rounded-sm hover:bg-slate-700 uppercase font-bold"
                >
                  MAX
                </button>

                <button
                  onClick={() => executeVote(choice.id)}
                  disabled={!isAffordable}
                  className={`text-[9px] font-bold px-3 py-2 rounded-sm border transition-all ${
                    isAffordable 
                      ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/20' 
                      : 'bg-slate-950 text-slate-700 border-slate-800 cursor-not-allowed'
                  }`}
                >
                  VOTE
                </button>
              </div>

              <div className="flex justify-between mt-1.5 px-0.5">
                <span className="text-[7px] text-slate-600 uppercase">Current Pool</span>
                <span className="text-[8px] text-slate-400 font-bold">
                  <FormattedValue value={choice.votes} type="currency" prefix="$" />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 4. FOOTER STATUS */}
      <div className="p-2 bg-slate-950/80 border-t border-slate-800 flex justify-between items-center">
        <span className="text-[8px] text-slate-500 uppercase tracking-widest font-bold">Capital Reserve:</span>
        <span className="text-[10px] text-emerald-400 font-black tabular-nums">{<FormattedValue value={playerBalance} type="currency" prefix="$" />}</span>
      </div>
    </div>
  );
};