// hooks/useGameState.ts
import { useState, useEffect, useCallback, useRef } from 'react';

type WorkerTypes = {
  extraction: number,
  rnd: number,
  espionage: number,
};

type UserData = {
  balance: number;
  inventory: Record<string, number>;
  max_workforce: number;
  deployed_workers: WorkerTypes
};

type PricePoint = {
  price: number;
  time: string;
};

type GameData = {
  market: any[];
  history: Record<string, PricePoint[]>; 
};

export function useGameState(userId: string) {
  // 1. Core State
  const [userData, setUserData] = useState<UserData>({
    balance: 0,
    inventory: {},
    max_workforce: 0,
    deployed_workers: {extraction:0, rnd:0, espionage:0}
  });
  const [gameData, setGameData] = useState<GameData>({
    market: [],
    history: {},
  });
  const [nextTick, setNextTick] = useState(0);
  const [maxSabotageRisk, setMaxSabotageRisk] = useState(25);

  const [selectedItem, setSelectedItem] = useState("Iron");
  const [secondsRemaining, setSecondsRemaining] = useState(0);
  const [tickInterval, setTickInterval] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  const [currentTax, setCurrentTax] = useState(0.05);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [error]);

  const clearError = () => setError(null);

  // 2. Trading State
  const [tradeAmounts, setTradeAmounts] = useState<Record<string, number>>({});

  // 3. Workforce State
  const [allocation, setAllocation] = useState({
    extraction: 0,
    rnd: 0,
    espionage: 0
  });
  const [lastDeployment, setLastDeployment] = useState<typeof allocation | null>(null);
  const [isPendingReturn, setIsPendingReturn] = useState(true);

  // Derived Workforce values
  const deployedUnits = allocation.extraction + allocation.rnd + allocation.espionage;
  const availableUnits = userData.max_workforce - deployedUnits;

  const pollCounter = useRef(0);

  // --- LOGIC FUNCTIONS ---

  // Data Fetching[cite: 1]
  const refreshUserData = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) setIsHistoryLoading(true);
      const url = `http://localhost:5000/api/get_user/${userId}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error();
      const data = await res.json();

      setUserData({
        balance: data.balance,
        inventory: data.inventory,
        max_workforce: data.max_workforce,
        deployed_workers: data.deployed_workers,
      });

      const workers = data.deployed_workers
      const totalSent = (workers.extraction || 0) + (workers.rnd || 0) + (workers.espionage || 0);
      console.log(totalSent)
      setIsPendingReturn(totalSent > 0);

      setLastDeployment(workers)

      setCurrentTax(data.current_tax)

      setNextTick(data.next_tick)
      setTickInterval(data.tick_length);
    } catch (err) {
      setError("Sync Error");
    } finally {
      setIsHistoryLoading(false);
    }
  }, [userId]);

  const refreshPricingData = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) setIsHistoryLoading(true);
      
      // Note: Removed the extra '}' from the end of your URL string
      const url = `http://localhost:5000/api/state/prices`; 
      const res = await fetch(url);
      if (!res.ok) throw new Error("Fetch failed");
      
      const data = await res.json();

      // Update your main game state with the new market and history object
      setGameData({
        market: data.market,
        history: data.history // This is now the { Gold: [], Iron: [] } object
      });
      
      setNextTick(data.next_tick)
      setTickInterval(data.tick_length);
      setError(null);
    } catch (err) {
      setError("Sync Error");
    } finally {
      setIsHistoryLoading(false);
    }
  }, []);

  // Trading Logic[cite: 1]
  const handleTrade = async (item: string, action: string) => {
    const amount = tradeAmounts[item] || 0;
    if (amount <= 0) return;

    try {
      const response = await fetch(`http://127.0.0.1:5000/api/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, item: item, amount: amount }),
      });
      
      if (response.ok) {
        refreshUserData();
        setTradeAmounts(prev => ({ ...prev, [item]: 0 }));

        const data = await response.json();

        setGameData({
          market: data.market,
          history: data.history // This is now the { Gold: [], Iron: [] } object
        });
        
        setNextTick(data.next_tick)
        setTickInterval(data.tick_length);
        setError(null);
      } else {
        const err = await response.json();
        setError(err.error);
      }
    } catch (e) {
      alert("Trade server unreachable");
    }
  };

  const handleWorkersDeploy = async(userId: string, sentWorkers: WorkerTypes) => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/deploy_workers/${userId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'user123',
            extraction: sentWorkers.extraction,
            rnd: sentWorkers.rnd,
            espionage: sentWorkers.espionage,
          })
        });
      if (response.ok) {
        // LOGIC FOR HANDELING WORKERS IN BACKEND
      } else {
        const err = await response.json();
        setError(err.error);
      }
    } catch (e) {
      alert("Trade server unreachable");
    }
  }

  const setMax = (item: {name: string, price: number}, action: 'buy' | 'sell') => {
    let amount = 0;
    if (action === 'buy') {
      amount = Math.floor(userData.balance / item.price);
    } else {
      amount = userData.inventory[item.name] || 0;
    }
    setTradeAmounts(prev => ({ ...prev, [item.name]: amount }));
  };

  // Workforce Logic[cite: 1]
  const handleAllocationChange = (dept: string, value: number) => {
    setAllocation(prev => {
      const otherUnits = Object.keys(prev).reduce(
        (sum, key) => (key !== dept ? sum + prev[key as keyof typeof prev] : sum), 
        0
      );
      const maxAllowed = userData.max_workforce - otherUnits;
      return { ...prev, [dept]: Math.min(value, maxAllowed) };
    });
  };

  const deployWorkforce = (extraction: number, rnd: number, espionage: number) => {
    setLastDeployment({ ...allocation });
    handleWorkersDeploy(userId, {extraction, rnd, espionage})
    setIsPendingReturn(true);
    // Add your API deployment call here if needed[cite: 1]
  };

  // The Heartbeat (Countdown & Polling)[cite: 1]
  useEffect(() => {
    refreshUserData(true); 
    refreshPricingData(true);
    const heartbeat = setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      if (nextTick > 0) {
        const diff = nextTick - now;
        setSecondsRemaining(diff > 0 ? diff : 0);
        if (diff <= 0) {
          setTimeout(() => {
            refreshUserData(); 
            refreshPricingData();
            setIsPendingReturn(false);
          }, 500);
        }
      }
      pollCounter.current += 1;
      if (pollCounter.current >= 5) {
        refreshUserData();
        pollCounter.current = 0;
      }
    }, 1000);
    return () => clearInterval(heartbeat);
  }, [refreshUserData, nextTick]);

  // Helper[cite: 1]
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

  return {
    userData,
    gameData,
    selectedItem,
    setSelectedItem,
    secondsRemaining,
    tickInterval,
    error,
    clearError,
    isHistoryLoading,
    tradeAmounts,
    setTradeAmounts,
    handleTrade,
    setMax,
    allocation,
    availableUnits,
    handleAllocationChange,
    deployWorkforce,
    isPendingReturn,
    lastDeployment,
    formatCurrency,
    maxSabotageRisk,
    handleWorkersDeploy,
    currentTax
  };
}