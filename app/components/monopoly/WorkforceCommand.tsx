import React, {useState} from 'react';
import { Users, Pickaxe, Cpu, Crosshair, Info } from 'lucide-react';
import { DeptInfo } from './DeptInfoHelper';

type WorkerTpes = {
  extraction: number;
  rnd: number;
  espionage: number
}

interface WorkforceCommandProps {
  isPendingReturn: boolean;
  availableUnits: number;
  maxWorkforce: number;
  allocation: WorkerTpes;
  onAllocationChange: (dept: string, value: number) => void;
  onDeploy: (extraction: number, rnd: number, espionage: number) => void;
  lastDeployment: WorkerTpes;
  secondsRemaining: number;
  maxSabotageRisk: number;
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
  maxSabotageRisk,
}: WorkforceCommandProps) => {

  // Define your descriptions here or pass them in as props
  const descriptions: Record<string, string> = {
    extraction: "Send workers to extract materials.\nHigher allocation results in larger resource yields until the end of the deployment cycle.",
    
    rnd: "Strategic Analytics & Scaling posibilities :\n• RECRUITMENT: Increases maximum available workforce units.\n• SYNERGY: Boosts the probability of finding high-value/rare elements when deployed with Extraction units.\nIf there are less extractors than r&d they will only search for recruits.",
    
    espionage: "Hostile Disruption Operations.\nAuthorize units to infiltrate rivals to steal materials or neutralize personnel.\n\n⚠️ RISK: Detection may lead to permanent loss of deployed workforce units.\nSuccess probability scales with allocation."
  };

  if (isPendingReturn) {
    return (
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
    );
  }

  const colorClasses: Record<string, string> = {
    extraction: "accent-emerald-500 hover:border-emerald-900/50 text-emerald-500 text-emerald-400",
    rnd: "accent-blue-500 hover:border-blue-900/50 text-blue-500 text-blue-400",
    espionage: "accent-orange-500 hover:border-orange-900/50 text-orange-500 text-orange-400"
  };

  const getRiskStatus = (allocation: number) => {
    const percent = (allocation / maxSabotageRisk) * 100;
    
    if (percent === 0) return { label: "NOT_ACTIVE", color: "text-emerald-500", bar: "bg-emerald-500", level: "SAFE" };;
    if (percent <= 15) return { label: "LOW_TRACE", color: "text-emerald-500", bar: "bg-emerald-500", level: "SAFE" };
    if (percent <= 40) return { label: "CAUTION", color: "text-blue-400", bar: "bg-blue-400", level: "MODERATE" };
    if (percent <= 75) return { label: "ELEVATED", color: "text-orange-500", bar: "bg-orange-500", level: "HIGH" };
    return { label: "CRITICAL", color: "text-red-500", bar: "bg-red-500", level: "EXTREME" };
  };

  const getRiskPresentage = (allocation: number) => {
    let amount = Math.floor((allocation / maxSabotageRisk) * 70);
    amount = Math.min(amount, 70)
    return amount
  }

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

      {/* Map through sliders */}
      {[
        { id: 'extraction', label: 'Extraction', icon: <Pickaxe size={12} />, color: 'emerald' },
        { id: 'rnd', label: 'R&D Analytics', icon: <Cpu size={12} />, color: 'blue' },
        { id: 'espionage', label: 'Sabotage', icon: <Crosshair size={12} />, color: 'orange' }
      ].map((dept) => (
        <div key={dept.id} className={`bg-slate-900/50 border border-slate-800 p-3 rounded-sm transition-colors hover:border-${dept.color}-900/50`}>
          <div className="flex justify-between items-center mb-1">
            <div className="flex items-center">
              <span className={`text-[11px] font-bold text-slate-300 uppercase flex items-center gap-1.5`}>
                {React.cloneElement(dept.icon as React.ReactElement<{ className?: string }>, { 
                  className: `text-${dept.color}-500` 
                })} 
                {dept.label}
              </span>
              
              {/* INDIVIDUAL INFO BUTTON */}
              <DeptInfo 
                label={dept.label} 
                description={descriptions[dept.id]} 
                color={dept.color} 
              />
            </div>

            {dept.id === 'espionage' && (() => {
              const risk = getRiskStatus(allocation.espionage);
              if (!risk) return null;

              return (
                <div className="p-2 w-3xs bg-black/40 border border-slate-800 rounded-sm animate-in fade-in duration-500">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] text-slate-500 uppercase tracking-tighter">Infiltration_Signature</span>
                    <span className={`text-[10px] font-bold uppercase ${risk.color}`}>{risk.label}</span>
                  </div>
                  
                  {/* Segmented Progress Bar */}
                  <div className="flex gap-1 h-1">
                    {[...Array(10)].map((_, i) => (
                      <div 
                        key={i}
                        className={`h-full flex-1 transition-all duration-300 ${
                          (i * 10) < (allocation.espionage / maxSabotageRisk * 100) 
                            ? risk.bar 
                            : 'bg-slate-800'
                        }`}
                      />
                    ))}
                  </div>

                  <div className="mt-2 flex justify-between text-[11px] font-bold text-slate-600 uppercase">
                    <span>Detection Probability: {getRiskPresentage(allocation.espionage)}%</span>
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
        </div>
      ))}

      <button 
        onClick={() => onDeploy(allocation.extraction, allocation.rnd, allocation.espionage)}
        className="w-full py-3 mt-4 bg-emerald-600/10 hover:bg-emerald-600 border border-emerald-500/50 text-[10px] font-bold uppercase tracking-[0.2em] transition-all active:scale-[0.98] text-emerald-500 hover:text-white"
      >
        Execute Deployment
      </button>
    </div>
  );
};