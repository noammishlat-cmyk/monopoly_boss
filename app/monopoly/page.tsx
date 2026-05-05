"use client";

import React, { useState, useEffect } from 'react';
import { useGameState } from '../hooks/useGameState';
import Header from '../components/monopoly/Header';
import { MarketTable } from '../components/monopoly/MarketTable';
import { WorkforceCommand } from '../components/monopoly/WorkforceCommand';
import { TelemetryGraph } from '../components/monopoly/TelemetryGraph';
import { CommandLog } from '../components/monopoly/CommandLog';
import { FooterTicker } from '../components/monopoly/FooterTicker';
import { Notification } from '../components/monopoly/Notification';
import { VotingPanel, VoteChoice } from '../components/monopoly/VotingPanel';

export default function MonopolyBoss() {
  const { 
    userId,
    userData,
    gameData, 
    selectedItem, 
    setSelectedItem,
    tickSecondsRemaining, 
    voteSecondsRemaining,
    tickInterval, 
    handleTrade,
    tradeAmounts,
    setTradeAmounts,
    setMax,
    isHistoryLoading,
    allocation,
    availableUnits,
    handleAllocationChange,
    deployWorkforce,
    isPendingReturn,
    lastDeployment,
    error,
    clearError,
    maxSabotageRisk,
    maxSendSabotageRisk,
    currentTax,
    userLog,
    currentDeploymentTickLength,
    leaderboard,
    fetchLeaderboard,
    selectedTarget,
    setSelectedTarget,
    activeVote,
    castVote
  } = useGameState();

  const [activeTab, setActiveTab] = useState('workforce');

  const tabs = [
    { id: 'workforce', label: 'Workforce' },
    { id: 'market', label: 'Market' },
    { id: 'system', label: 'System' },
  ];

  // --- VOTING STATE ---
  const [choices, setChoices] = useState<VoteChoice[]>([ 
    { id: 'tax_up', label: 'Ratify Emergency Tax Hike (+5%)', votes: 12000 },
    { id: 'tax_down', label: 'Approve Subsidies & Cut Taxes (-3%)', votes: 18500 },
    { id: 'stable', label: 'Maintain Present Regulations', votes: 4500 }
  ]);

  const handleCastVote = (choiceId: string, amount: number) => {
    // Logic to update state locally for immediate feedback
    setChoices(prevChoices => 
      prevChoices.map(c => c.id === choiceId ? { ...c, votes: c.votes + amount } : c)
    );
    // Note: Actual balance deduction would happen inside useGameState or a dedicated handleVote hook
  };


  const netWorth = Object.entries(userData.inventory).reduce((total, [itemName, amount]) => {
    const marketItem = gameData.market.find(m => m.name === itemName);
    const price = marketItem ? marketItem.price : 0;
    return total + (price * (amount as number));
  }, userData.balance);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 font-mono pb-32 lg:pb-4">
      {/* 1. TOP NAVIGATION & STATUS */}
      <Header 
        leaderboard={leaderboard ?? []}
        userId={userId}
        balance={userData.balance}
        totalAssets={netWorth}
        tickInterval={tickInterval}
        secondsRemaining={tickSecondsRemaining}
        loadLeaderboard={fetchLeaderboard}
      />

      {/* --- MOBILE TAB NAVIGATION --- */}
      <nav className="lg:hidden fixed bottom-16 left-4 right-4 z-50 flex gap-2 p-2 bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-3 rounded-xl text-[10px] font-bold transition-all ${
              activeTab === tab.id 
                ? "bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.3)]" 
                : "text-slate-500 border border-transparent"
            }`}
          >
            {tab.label.toUpperCase()}
          </button>
        ))}
      </nav>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* 2. LEFT COLUMN: UNIT MANAGEMENT */}
        <section className={`lg:col-span-4 ${activeTab === 'workforce' ? 'block' : 'hidden lg:block'}`}>
          <WorkforceCommand 
            currentUserId={userId}
            isPendingReturn={isPendingReturn}
            availableUnits={availableUnits}
            maxWorkforce={userData.max_workforce}
            allocation={allocation}
            onAllocationChange={handleAllocationChange}
            
            selectedTarget={selectedTarget}
            onTargetChange={setSelectedTarget}
            
            onDeploy={deployWorkforce}
            deploymentTickLength={currentDeploymentTickLength}
            lastDeployment={lastDeployment}
            secondsRemaining={tickSecondsRemaining}
            maxSendSabotage={maxSendSabotageRisk}
            maxSabotageRisk={maxSabotageRisk}
            leaderboard={leaderboard ?? []}
          />
        </section>
        
        {/* 3. MIDDLE COLUMN: MARKET DATA & VISUALS */}
        <section className={`lg:col-span-5 space-y-6 ${activeTab === 'market' ? 'block' : 'hidden lg:block'}`}>
          <MarketTable 
            market={gameData.market} 
            selectedItem={selectedItem}
            onSelect={setSelectedItem}
            inventory={userData.inventory}
            tradeAmounts={tradeAmounts}
            setTradeAmounts={setTradeAmounts}
            handleTrade={handleTrade}
            setMax={setMax}
            currentTax={currentTax}
          />
          
          <TelemetryGraph 
            history={gameData.history[selectedItem] || []} 
            selectedItem={selectedItem}
            isLoading={isHistoryLoading}
            currentTax={currentTax}
            basePrice={gameData.market.find(m => m.name === selectedItem)?.base_price ?? 0}
          />
        </section>

        {/* 4. RIGHT COLUMN: SYSTEM (Voting & Logs) */}
        <section className={`lg:col-span-3 space-y-6 ${activeTab === 'system' ? 'block' : 'hidden lg:block'}`}>
          {/* Voting Panel Integrated Here */}
          <VotingPanel 
            prompt="Corporate governance vote — select a policy directive:"
            choices={activeVote.choices}
            secondsRemaining={voteSecondsRemaining}
            playerBalance={userData.balance}
            onCastVote={castVote}
          />

          <div className="flex-1">
            <CommandLog 
              marketLength={gameData.market.length}
              selectedItem={selectedItem}
              current_log={userLog}
              error={error}
            />
          </div>
        </section>
      </main>

      {/* 5. BOTTOM TICKER */}
      <FooterTicker />

      <Notification 
        message={error} 
        isVisible={!!error} 
        onClose={clearError}
      />
    </div>
  );
}