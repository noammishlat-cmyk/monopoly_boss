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

export interface MarketItem {
  name: string;
  price: number;
  base_price: number;
  demand: number;
  supply: number;
}

type PricePoint = {
  price: number;
  time: string;
};

type GameData = {
  market: MarketItem[];
  history: Record<string, PricePoint[]>; 
};

interface LogEntry {
  text: string;
  color: string;
}

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  balance: number;
  net_worth: number;
  inventory_value: number;
  inventory: Record<string, number> | "Hidden";
}

type VoteChoice = {
  id: string;
  label: string;
  votes: number;
};

type ActiveVote = {
  active: boolean;
  vote_id: number | null;
  choices: VoteChoice[];
  expires_at: number;
};


export function useGameState() {
  const BACKEND_ADRESS = "http://192.168.1.246:5000"

  const [userId, setUserId] = useState("test_user321");

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
  const [maxSabotageRisk, setMaxSabotageRisk] = useState(10);
  const [maxSendSabotageRisk, setMaxSendSabotageRisk] = useState(10);

  const [selectedItem, setSelectedItem] = useState("Iron");
  const [tickSecondsRemaining, setTickSecondsRemaining] = useState(0);
  const [voteSecondsRemaining, setVoteSecondsRemaining] = useState(0);
  const [nextCoorprateVote, setNextCoorprateVote] = useState(0);
  const [tickInterval, setTickInterval] = useState(60);
  const [error, setError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  const [selectedTarget, setSelectedTarget] = useState<string | null>('RANDOM');

  const [userLog, setUserLog] = useState<LogEntry[]>()
  const [currentDeploymentTickLength, setCurrentDeploymentTickLength] = useState(1)

  const [currentTax, setCurrentTax] = useState(0.05);

  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>()

  const [activeVote, setActiveVote] = useState<ActiveVote>({
    active: false,
    vote_id: null,
    choices: [],
    expires_at: 0,
  });


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
      const url = `${BACKEND_ADRESS}/api/get_user/${userId}`;
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
      setIsPendingReturn(totalSent > 0);

      setLastDeployment(workers)

      setCurrentTax(data.current_tax)

      setMaxSabotageRisk(data.max_sabotage_precent)
      setMaxSendSabotageRisk(data.max_sabotage_send)

      setUserLog(data.user_logs)

      setCurrentDeploymentTickLength(data.current_deployment_length)

      setNextCoorprateVote(data.next_vote_tick)

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
      const url = `${BACKEND_ADRESS}/api/state/prices`; 
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

  const fetchActiveVote = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_ADRESS}/api/vote/current`);
      if (!res.ok) throw new Error();
      const data = await res.json();

      if (!data.active) {
        setActiveVote({ active: false, vote_id: null, choices: [], expires_at: 0 });
        return;
      }

      // Normalize the 3 options into a choices array so the component
      // doesn't need to know about option_a/b/c naming
      setActiveVote({
        active: true,
        vote_id: data.vote_id,
        expires_at: data.expires_at,
        choices: [
          { id: 'a', label: data.option_a, votes: data.votes_a },
          { id: 'b', label: data.option_b, votes: data.votes_b },
          { id: 'c', label: data.option_c, votes: data.votes_c },
        ],
      });
    } catch {
      setError("Vote sync error");
    }
  }, []);


  const fetchLeaderboard = useCallback(async () => {
    try {
      const url = `${BACKEND_ADRESS}/api/leaderboard`;
      const res = await fetch(url);
      if (!res.ok) throw new Error();
      const data = await res.json();

      // 1. Update the leaderboard state with the array from the response
      if (data.leaderboard) {
        setLeaderboard(data.leaderboard);
      }

    } catch (err) {
      setError("Sync Error");
    } finally {
      setIsHistoryLoading(false);
    }
  }, []);

  useEffect(() =>{
    const loadLeaderboard = async () => {
      await fetchLeaderboard();
    };
    loadLeaderboard();
  }, [fetchLeaderboard])

  // Trading Logic[cite: 1]
  const handleTrade = async (item: string, action: string) => {
    const amount = tradeAmounts[item] || 0;
    if (amount <= 0) return;

    try {
      const response = await fetch(`${BACKEND_ADRESS}/api/${action}`, {
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
      alert(`Trade server unreachable - ${e}`);
    }
  };

  const handleWorkersDeploy = async(userId: string, sentWorkers: WorkerTypes) => {
    try {
      const response = await fetch(`${BACKEND_ADRESS}/api/deploy_workers/${userId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            extraction: sentWorkers.extraction,
            rnd: sentWorkers.rnd,
            espionage: sentWorkers.espionage,
            target: selectedTarget
          })
        });
      if (response.ok) {
        refreshUserData()
      } else {
        const err = await response.json();
        setError(err.error);
      }
    } catch (e) {
      alert(`Trade server unreachable - ${e}`);
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
    setAllocation({ extraction: 0, rnd: 0, espionage: 0 });
  };

  const castVote = useCallback(async (choiceId: string, amount: number) => {
    if (!activeVote.vote_id || amount <= 0) return;

    try {
      const res = await fetch(`${BACKEND_ADRESS}/api/vote/cast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          vote_id: activeVote.vote_id,
          choice: choiceId,
          amount,
        }),
      });

      if (res.ok) {
        const data = await res.json();

        // Update vote tallies directly from the response — no extra fetch needed
        setActiveVote(prev => ({
          ...prev,
          choices: [
            { id: 'a', label: data.option_a, votes: data.votes_a },
            { id: 'b', label: data.option_b, votes: data.votes_b },
            { id: 'c', label: data.option_c, votes: data.votes_c },
          ],
        }));

        // Deduct balance locally for instant feedback before next poll
        setUserData(prev => ({ ...prev, balance: prev.balance - amount }));

      } else {
        const err = await res.json();
        setError(err.error);
      }
    } catch {
      setError("Vote cast failed");
    }
  }, [activeVote.vote_id, userId]);



  // The Heartbeat (Countdown & Polling)[cite: 1]
  useEffect(() => {
    Promise.resolve().then(() => {
      refreshUserData(true);
      refreshPricingData(true);
      fetchActiveVote();
    });

    const heartbeat = setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      if (nextTick > 0) {
        const diff_tick = nextTick - now;
        setTickSecondsRemaining(diff_tick > 0 ? diff_tick : 0);
        const diff_vote = nextCoorprateVote - now;
        setVoteSecondsRemaining(diff_vote > 0 ? diff_vote : 0);
        if (diff_tick <= 0) {
          setTimeout(() => {
            refreshUserData(); 
            refreshPricingData();
            setIsPendingReturn(false);
          }, 1500);
        }
        if (diff_vote <= 0 && nextCoorprateVote > 0) {
          setTimeout(() => fetchActiveVote(), 1500);
        }
      }
      pollCounter.current += 1;
      if (pollCounter.current >= 5) {
        refreshUserData();
        fetchActiveVote();
        pollCounter.current = 0;
      }
    }, 1000);
    return () => clearInterval(heartbeat);
  }, [refreshUserData, nextTick, refreshPricingData]);

  //  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

  return {
    userData,
    gameData,
    selectedItem,
    setSelectedItem,
    tickSecondsRemaining,
    voteSecondsRemaining,
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
    maxSabotageRisk,
    maxSendSabotageRisk,
    handleWorkersDeploy,
    currentTax,
    userLog,
    currentDeploymentTickLength,
    leaderboard,
    fetchLeaderboard,
    userId,
    setUserId,
    nextCoorprateVote,
    selectedTarget,
    setSelectedTarget,
    activeVote,
    castVote,
    fetchActiveVote,
  };
}