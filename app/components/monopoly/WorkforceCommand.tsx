import React, {useState, useEffect} from 'react';
import { Users, Pickaxe, Cpu, Crosshair, ChevronDown, Skull } from 'lucide-react';
import { DeptInfo } from './DeptInfoHelper';

type WorkerTypes = {
  extraction: number;
  rnd: number;
  espionage: number;
}

// --- NEW: leaderboard entry shape ---
interface LeaderboardEntry {
  rank: number;
  user_id: string;
  balance: number;
  net_worth: number;
  inventory_value: number;
  inventory: Record<string, number> | "Hidden";
}

interface WorkforceCommandProps {
  isPendingReturn: boolean;
  availableUnits: number;
  maxWorkforce: number;
  allocation: WorkerTypes;
  onAllocationChange: (dept: string, value: number) => void;
  onDeploy: (extraction: number, rnd: number, espionage: number, targetId: string | null) => void; // --- CHANGED: added targetId
  lastDeployment: WorkerTypes | null;
  secondsRemaining: number;
  deploymentTickLength: number;
  maxSendSabotage: number;
  maxSabotageRisk: number;
  leaderboard: LeaderboardEntry[];
  currentUserId: string;
  selectedTarget: string | null;
  onTargetChange: (id: string | null) => void;
}

export const WorkforceCommand = ({
  isPendingReturn,
  availableUnits,
  maxWorkforce,
  allocation,
  onAllocationChange,
  onDeploy,
  lastDeployment,
  secondsRemaining,
  deploymentTickLength,
  maxSendSabotage,
  maxSabotageRisk,
  leaderboard,
  currentUserId,
  selectedTarget,
  onTargetChange
}: WorkforceCommandProps) => {

  // --- NEW: target selection state ---
  const [targetDropdownOpen, setTargetDropdownOpen] = useState(false);

  const descriptions: Record<string, string> = {
    extraction: "Send workers to extract materials.\nHigher allocation results in larger resource yields until the end of the deployment cycle.",
    rnd: "Strategic Analytics & Scaling posibilities :\n• RECRUITMENT: Increases maximum available workforce units.\n• SYNERGY: Boosts the probability of finding high-value/rare elements when deployed with Extraction units.\nIf there are less extractors than r&d they will only search for recruits.",
    espionage: "Hostile Disruption Operations.\nAuthorize units to infiltrate rivals to steal materials, money or neutralize personnel.\n\n⚠️ RISK: Detection may lead to permanent loss of deployed workforce units.\nSuccess probability scales with allocation."
  };

  // --- NEW: derived target data ---
  const targets = leaderboard.filter(e => e.user_id !== currentUserId);
  const selectedEntry = targets.find(e => e.user_id === selectedTarget) ?? null;

  if (isPendingReturn) {
    return (
      <div className="bg-slate-900/40 border border-emerald-500/20 h-full p-6 rounded-sm animate-in zoom-in-95 duration-300 flex flex-col items-center justify-center text-center relative overflow-hidden">
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
              {secondsRemaining + (60 * deploymentTickLength) - 60}s
            </span>
          </div>
          <p className="mt-6 text-[8px] text-slate-600 uppercase tracking-widest italic animate-pulse">
            System locked until next market tick...
          </p>
        </div>
      </div>
    );
  }

  const colorClasses: Record<string, string> = {
    extraction: "accent-emerald-500 hover:border-emerald-900/50 text-emerald-500 text-emerald-400",
    rnd: "accent-blue-500 hover:border-blue-900/50 text-blue-500 text-blue-400",
    espionage: "accent-orange-500 hover:border-orange-900/50 text-orange-500 text-orange-400"
  };

  const getRiskStatus = (allocation: number) => {
    const percent = (allocation / maxSendSabotage) * 100;
    if (percent === 0)  return { label: "NOT_ACTIVE", color: "text-emerald-500", bar: "bg-emerald-500" };
    if (percent <= 15)  return { label: "LOW_TRACE",  color: "text-emerald-500", bar: "bg-emerald-500" };
    if (percent <= 40)  return { label: "CAUTION",    color: "text-blue-400",    bar: "bg-blue-400"    };
    if (percent <= 75)  return { label: "ELEVATED",   color: "text-orange-500",  bar: "bg-orange-500"  };
    return               { label: "CRITICAL",   color: "text-red-500",     bar: "bg-red-500"     };
  };

  const getRiskPresentage = (allocation: number) => {
    return Math.min(Math.floor((allocation / maxSendSabotage) * maxSabotageRisk), maxSabotageRisk);
  };

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-left-4 duration-500">
      <div className="flex justify-between items-end mb-2 border-b border-slate-800 pb-2">
        <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-2 uppercase tracking-tighter">
          <Users size={16} className="text-emerald-500" /> HQ_Workforce
        </h2>
        <div className="text-right">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest block">Available Units</span>
          <span className={`text-sm font-bold tabular-nums ${availableUnits === 0 ? 'text-orange-500' : 'text-emerald-400'}`}>
            {availableUnits} / {maxWorkforce}
          </span>
        </div>
      </div>

      {[
        { id: 'extraction', label: 'Extraction',   icon: <Pickaxe size={12} />,   color: 'emerald' },
        { id: 'rnd',        label: 'R&D Analytics', icon: <Cpu size={12} />,       color: 'blue'    },
        { id: 'espionage',  label: 'Sabotage',      icon: <Crosshair size={12} />, color: 'orange'  }
      ].map((dept) => (
        <div key={dept.id} className={`bg-slate-900/50 border border-slate-800 p-3 rounded-sm transition-colors hover:border-${dept.color}-900/50`}>
          <div className="flex justify-between items-center mb-1">
            <div className="flex items-center">
              <span className="text-[11px] font-bold text-slate-300 uppercase flex items-center gap-1.5">
                {React.cloneElement(dept.icon as React.ReactElement<{ className?: string }>, {
                  className: `text-${dept.color}-500`
                })}
                {dept.label}
              </span>
              <DeptInfo label={dept.label} description={descriptions[dept.id]} color={dept.color} />
            </div>

            {dept.id === 'espionage' && (() => {
              const risk = getRiskStatus(allocation.espionage);
              return (
                <div className="p-2 w-3xs bg-black/40 border border-slate-800 rounded-sm animate-in fade-in duration-500">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] text-slate-500 uppercase tracking-tighter">Infiltration_Signature</span>
                    <span className={`text-[10px] font-bold uppercase ${risk.color}`}>{risk.label}</span>
                  </div>
                  <div className="flex gap-1 h-1">
                    {[...Array(10)].map((_, i) => (
                      <div key={i} className={`h-full flex-1 transition-all duration-300 ${
                        (i * 10) < (allocation.espionage / maxSendSabotage * 100) ? risk.bar : 'bg-slate-800'
                      }`} />
                    ))}
                  </div>
                  <div className="mt-2 text-[11px] font-bold text-slate-600 uppercase">
                    Detection Probability: {getRiskPresentage(allocation.espionage)}%
                  </div>
                </div>
              );
            })()}

            <span className={`text-[10px] font-mono text-${dept.color}-400`}>
              {allocation[dept.id as keyof typeof allocation]} Assigned
            </span>
          </div>

          <input
            type="range"
            min="0" max={maxWorkforce}
            value={allocation[dept.id as keyof typeof allocation]}
            onChange={(e) => onAllocationChange(dept.id, parseInt(e.target.value))}
            className={`w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer ${colorClasses[dept.id].split(' ')[0]}`}
          />

          {/* --- NEW: target selector, only shown inside espionage when agents are assigned --- */}
          {dept.id === 'espionage' && allocation.espionage > 0 && (
            <div className="mt-3 border-t border-slate-800 pt-3 space-y-2">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest">Target Designation</span>

              {/* Dropdown trigger */}
              <button
                type="button"
                onClick={() => setTargetDropdownOpen(o => !o)}
                className="w-full flex justify-between items-center px-3 py-2 bg-black/40 border border-orange-900/40 hover:border-orange-500/50 text-[11px] text-left transition-colors"
              >
                <span className={selectedTarget ? 'text-orange-400 font-bold' : 'text-slate-500 italic'}>
                  {selectedTarget === 'RANDOM' 
                    ? '[?] RANDOM_TARGET' 
                    : selectedTarget 
                      ? `[${targets.find(t => t.user_id === selectedTarget)?.rank ?? '?'}] ${selectedTarget}` 
                      : 'Select target...'}
                </span>
                <ChevronDown size={12} className={`text-slate-500 transition-transform ${targetDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown list */}
              {targetDropdownOpen && (
                <div className="border border-slate-800 bg-slate-950 divide-y divide-slate-800/60 max-h-48 overflow-y-auto">
                  {/* RANDOM OPTION */}
                  <button
                    type="button"
                    onClick={() => { onTargetChange('RANDOM'); setTargetDropdownOpen(false); }}
                    className={`w-full px-3 py-2 text-left hover:bg-orange-950/30 transition-colors border-b border-orange-500/20 ${selectedTarget === 'RANDOM' ? 'bg-orange-950/20' : ''}`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-bold text-orange-500 uppercase flex items-center gap-1">
                        <Skull size={10} /> Random Target
                      </span>
                      <span className="text-[9px] text-orange-900 font-mono">LUCK_BASED</span>
                    </div>
                  </button>

                  {targets.length === 0 && (
                    <p className="text-[10px] text-slate-600 italic px-3 py-2">No other players found.</p>
                  )}
                  {targets.map(entry => (
                    <button
                      key={entry.user_id}
                      type="button"
                      onClick={() => { onTargetChange(entry.user_id);; setTargetDropdownOpen(false); }}
                      className={`w-full px-3 py-2 text-left hover:bg-orange-950/30 transition-colors ${selectedTarget === entry.user_id ? 'bg-orange-950/20' : ''}`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] font-bold text-slate-300">{entry.user_id}</span>
                        <span className="text-[10px] text-slate-500">Rank #{entry.rank}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* --- Unified Target Intel Card --- */}
              {(selectedTarget === 'RANDOM' || selectedEntry) && (
                <div className="mt-1 p-2 bg-black/40 border border-orange-900/30 rounded-sm animate-in fade-in duration-300">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Skull size={10} className="text-orange-500" />
                    <span className="text-[10px] text-orange-500 uppercase tracking-widest font-bold">
                      {selectedTarget === 'RANDOM' ? 'Unconfirmed Intel' : 'Target Intel'}
                    </span>
                  </div>

                  <div className="space-y-1">
                    {/* ID Row */}
                    <div className="flex justify-between text-[10px]">
                      <span className="text-slate-500">ID</span>
                      <span className="text-slate-300 font-mono">
                        {selectedTarget === 'RANDOM' ? '?' : selectedEntry?.user_id}
                      </span>
                    </div>

                    {/* Rank Row */}
                    <div className="flex justify-between text-[10px]">
                      <span className="text-slate-500">Rank</span>
                      <span className="text-slate-300">
                        {selectedTarget === 'RANDOM' ? '?' : `#${selectedEntry?.rank}`}
                      </span>
                    </div>

                    {/* Net Worth Row */}
                    <div className="flex justify-between text-[10px]">
                      <span className="text-slate-500">Net Worth</span>
                      <span className="text-orange-400">
                        {selectedTarget === 'RANDOM' ? '?' : `$${selectedEntry?.net_worth.toLocaleString()}`}
                      </span>
                    </div>

                    {/* Assets Row */}
                    <div className="flex justify-between text-[10px]">
                      <span className="text-slate-500">Assets</span>
                      <span className={selectedTarget === 'RANDOM' ? 'text-slate-600' : 'text-slate-300'}>
                        {selectedTarget === 'RANDOM' ? '?' : (selectedEntry?.inventory === "Hidden" ? "Classified" : "Known")}
                      </span>
                    </div>

                    {/* Detailed Assets (Only if real player and inventory is not hidden) */}
                    {selectedTarget !== 'RANDOM' && selectedEntry?.inventory !== "Hidden" && (
                      <div className="mt-1 pt-1 border-t border-slate-800 flex flex-wrap gap-1">
                        {Object.entries(selectedEntry?.inventory || {}).map(([res, amt]) => (
                          <span key={res} className="text-[9px] px-1.5 py-0.5 bg-slate-800 text-slate-400">
                            {amt}x {res}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      <button
        onClick={() => onDeploy(allocation.extraction, allocation.rnd, allocation.espionage, selectedTarget)}
        className="w-full py-3 mt-4 bg-emerald-600/10 hover:bg-emerald-600 border border-emerald-500/50 text-[10px] font-bold uppercase tracking-[0.2em] transition-all active:scale-[0.98] text-emerald-500 hover:text-white"
      >
        Execute Deployment
      </button>
    </div>
  );
};