import math
import sqlite3
import random
import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- CONFIGURATION ---
TICK_INTERVAL = 60.0 
MARKET_DECAY_RATE = 0.05 # How fast the market returns to "Normal" (0.1 = 10% of pressure disappears per tick)
EQUILIBRIUM_LEVEL = 100.0 # The "Neutral" level for Supply and Demand
HISTORY_RETAIN_TIME = 1800  # 30 minutes in seconds

app = Flask(__name__)
CORS(app)

# --- WEB ROUTES ---

@app.route('/api/state/<u_id>')
def get_game_state(u_id):
    # Get the item the user is currently looking at for the graph
    selected_item = request.args.get('item', 'Iron').capitalize()
    
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    
    # 1. FETCH MARKET
    cursor.execute("SELECT name, price, supply, demand, base_price FROM resources")
    market_rows = cursor.fetchall()
    market_data = []
    for row in market_rows:
        name, price, supply, demand, base_price = row
        market_data.append({
            "name": name,
            "price": round(price, 2),
            "supply": supply,
            "demand": demand,
            "base_price": base_price
        })

    # 2. FETCH USER
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
    user_res = cursor.fetchone()
    balance = user_res[0] if user_res else 0
    
    cursor.execute("SELECT resource_name, amount FROM inventory WHERE user_id = ?", (u_id,))
    inv_rows = cursor.fetchall()
    inventory = {row[0]: row[1] for row in inv_rows}

    # 3. FETCH HISTORY (For the selected item only)
    cursor.execute("""
        SELECT price, timestamp FROM price_history 
        WHERE resource_name = ? 
        ORDER BY timestamp DESC LIMIT 30
    """, (selected_item,))
    hist_rows = cursor.fetchall()
    history = []
    for row in reversed(hist_rows):
        history.append({
            "time": time.strftime('%H:%M:%S', time.localtime(row[1])),
            "price": round(row[0], 2)
        })

    # 4. CALCULATE NEXT TICK
    now = time.time()
    next_tick = now + (TICK_INTERVAL - (now % TICK_INTERVAL))

    conn.close()

    # THE BIG JSON
    return jsonify({
        "market": market_data,
        "user": {
            "balance": round(balance, 2),
            "inventory": inventory
        },
        "history": history,
        "next_tick": next_tick,
        "tick_length": TICK_INTERVAL,
        "server_time": now
    })

@app.route('/api/buy', methods=['POST'])
def buy_resource():
    data = request.get_json()
    u_id = data.get('user_id', 'user123')
    item = data.get('item').capitalize()
    qty = int(data.get('amount', 1))

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    try:
        # 1. Get current price (Supply doesn't limit buying anymore, only price does)
        cursor.execute("SELECT price FROM resources WHERE name = ?", (item,))
        res = cursor.fetchone()
        if not res: return jsonify({"error": "Item not found"}), 400
        
        total_cost = res[0] * qty
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        balance = cursor.fetchone()[0]

        if balance < total_cost:
            return jsonify({"error": "Insufficient funds"}), 400

        # 2. TRANSACTION
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_cost, u_id))
        
        # INCREASE DEMAND: Buying adds to the Demand pressure
        cursor.execute("UPDATE resources SET demand = demand + ? WHERE name = ?", (qty, item))
        
        cursor.execute("""
            INSERT INTO inventory (user_id, resource_name, amount) VALUES (?, ?, ?)
            ON CONFLICT(user_id, resource_name) DO UPDATE SET amount = amount + ?
        """, (u_id, item, qty, qty))

        conn.commit()
        return jsonify({"message": "Bought items, demand increased"}), 200
    finally: conn.close()

@app.route('/api/sell', methods=['POST'])
def sell_resource():
    data = request.get_json()
    u_id = data.get('user_id', 'user123')
    item = data.get('item').capitalize()
    qty = int(data.get('amount', 1))

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT amount FROM inventory WHERE user_id = ? AND resource_name = ?", (u_id, item))
        row = cursor.fetchone()
        if not row or row[0] < qty:
            return jsonify({"error": "Not enough items"}), 400

        cursor.execute("SELECT price FROM resources WHERE name = ?", (item,))
        gain = cursor.fetchone()[0] * qty

        # TRANSACTION
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (gain, u_id))
        
        # INCREASE SUPPLY: Selling adds to the Supply pressure
        cursor.execute("UPDATE resources SET supply = supply + ? WHERE name = ?", (qty, item))
        
        cursor.execute("UPDATE inventory SET amount = amount - ? WHERE user_id = ? AND resource_name = ?", (qty, u_id, item))

        conn.commit()
        return jsonify({"message": "Sold items, supply increased"}), 200
    finally: conn.close()


# --- MARKET LOGIC ---

def calculate_market_price(current_price, base_price, supply, demand, last_change):
    """
    Stable Equilibrium Model:
    The price tries to reach (Base Price * Demand/Supply Ratio).
    """
    # 1. Determine the "Fair Market Value" (The Target)
    # If Demand is 2x Supply, target is 2x Base Price.
    # We use max(supply, 1) to avoid division by zero.
    ratio = demand / max(supply, 1)
    target_price = base_price * ratio

    # 2. Calculate the Gap
    # How far is the current price from where it 'should' be?
    # If target is $380 and current is $400,000, diff is -$399,620
    diff = target_price - current_price

    # 3. Move toward the target (Reaction Speed)
    # Move 5% of the way toward the target every tick.
    # This prevents instant teleports but ensures a correction happens.
    reaction_speed = 0.05
    movement = diff * reaction_speed

    # 4. Add Jitter (Noise & Momentum)
    # Keep noise relative to BASE price so it doesn't scale out of control
    momentum = last_change * 0.1
    noise = random.uniform(-0.01, 0.01) * base_price
    
    total_change = movement + momentum + noise

    # 5. Volatility Cap
    # Don't let the price move more than 10% of the CURRENT price in one tick.
    # This keeps the graph readable even during a crash.
    max_move = current_price * 0.10
    total_change = max(min(total_change, max_move), -max_move)

    new_price = current_price + total_change

    # 6. Safety Floor
    # Price can never go below 10% of its base value.
    return max(new_price, base_price * 0.1), total_change

def run_tick():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    now = time.time()

    cursor.execute("SELECT name, price, last_change, supply, demand, base_price FROM resources")
    all_resources = cursor.fetchall()

    for name, price, last_change, supply, demand, base_price in all_resources:
        # 1. Calculate New Price
        new_price, change = calculate_market_price(price, base_price, supply, demand, last_change)

        # 2. MARKET DECAY (Equilibrium Logic)
        # Every tick, Supply and Demand move back toward EQUILIBRIUM_LEVEL
        # This prevents one massive buy from ruining the price forever.
        new_supply = supply + (EQUILIBRIUM_LEVEL - supply) * MARKET_DECAY_RATE
        new_demand = demand + (EQUILIBRIUM_LEVEL - demand) * MARKET_DECAY_RATE

        # Update the DB
        cursor.execute("""
            UPDATE resources 
            SET price = ?, last_change = ?, supply = ?, demand = ?, last_updated = ?
            WHERE name = ?
        """, (new_price, change, new_supply, new_demand, now, name))

        cursor.execute("INSERT INTO price_history VALUES (?, ?, ?)", (name, new_price, now))
        
        print(f"[{name}] ${new_price:.2f} | S:{int(new_supply)} D:{int(new_demand)}")

    cursor.execute("DELETE FROM price_history WHERE timestamp < ?", (now - HISTORY_RETAIN_TIME,))
    conn.commit()
    conn.close()


def market_loop():
    while True:
        run_tick()
        
        now = time.time()
        time_to_next = TICK_INTERVAL - (now % TICK_INTERVAL)
        time.sleep(time_to_next) 
       

# --- INITIALIZATION ---
if __name__ == "__main__":
    conn = sqlite3.connect('market.db')

    # Added base_price column to the schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            name TEXT PRIMARY KEY, 
            price REAL, 
            last_change REAL, 
            supply INTEGER, 
            demand INTEGER, 
            last_updated REAL,
            base_price REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            resource_name TEXT, 
            price REAL, 
            timestamp REAL
        )
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS inventory (user_id TEXT, resource_name TEXT, amount INTEGER, PRIMARY KEY (user_id, resource_name))")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance REAL)")

    materials = [
        #  Name   | Price | Change | Supply | Demand | Updated | Base
        ('Iron'   , 100.0,   0.0,    100,     100,      0,       100.0),
        ('Gold'   , 500.0,   0.0,    100,     100,      0,       500.0),
        ('Oil'    , 300.0,   0.0,    100,     100,      0,       300.0),
        ('Wood'   , 20.0,    0.0,    100,     100,      0,        20.0),
    ]
    
    # Using a dynamic insert to handle the column count
    for m in materials:
        conn.execute("INSERT OR IGNORE INTO resources VALUES (?, ?, ?, ?, ?, ?, ?)", m)

    conn.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", ("user123", 1000.0))
    conn.commit()
    conn.close()

    threading.Thread(target=market_loop, daemon=True).start()
    app.run(port=5000, debug=False, use_reloader=False)