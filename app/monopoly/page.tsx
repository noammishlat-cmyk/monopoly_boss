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

export default function MonopolyBoss() {
  const UserID = "user123";

  // Destructure EVERYTHING needed from the "brain" hook
  const { 
    userData,
    gameData, 
    selectedItem, 
    setSelectedItem,
    secondsRemaining, 
    tickInterval, 
    formatCurrency,
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
  } = useGameState(UserID);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 font-mono">
      {/* 1. TOP NAVIGATION & STATUS */}
      <Header 
        userId={UserID}
        balance={userData.balance}
        tickInterval={tickInterval}
        secondsRemaining={secondsRemaining}
        formatCurrency={formatCurrency}
      />

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* 2. LEFT COLUMN: UNIT MANAGEMENT */}
        <section className="lg:col-span-4 h-full">
          <WorkforceCommand 
            isPendingReturn={isPendingReturn}
            availableUnits={availableUnits}
            maxWorkforce={userData.max_workforce}
            allocation={allocation}
            onAllocationChange={handleAllocationChange}
            onDeploy={deployWorkforce}
            lastDeployment={lastDeployment}
            secondsRemaining={secondsRemaining}
            maxSabotageRisk={maxSabotageRisk}
          />
        </section>
        
        {/* 3. MIDDLE COLUMN: MARKET DATA & VISUALS */}
        <section className="lg:col-span-5 space-y-6">
          <MarketTable 
            market={gameData.market} 
            selectedItem={selectedItem}
            onSelect={setSelectedItem}
            inventory={userData.inventory}
            tradeAmounts={tradeAmounts}
            setTradeAmounts={setTradeAmounts}
            handleTrade={handleTrade}
            setMax={setMax}
          />
          
          <TelemetryGraph 
            history={gameData.history[selectedItem] || []} 
            selectedItem={selectedItem}
            isLoading={isHistoryLoading}
          />
        </section>

        {/* 4. RIGHT COLUMN: SYSTEM MESSAGES */}
        <section className="lg:col-span-3">
          <CommandLog 
            marketLength={gameData.market.length}
            selectedItem={selectedItem}
            error={error}
          />
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