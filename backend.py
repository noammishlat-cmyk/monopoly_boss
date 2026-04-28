import sqlite3
import random
import time
import threading
from flask import Flask, jsonify
from flask_cors import CORS

# --- CONFIGURATION ---
BASE_VALUE = 100.0
TICK_INTERVAL = 1.0  # Increased for readability
MOMENTUM_STRENGTH = 0.4
NOISE_MAX = 0.02

app = Flask(__name__)
CORS(app)

MARKET_DATA = {}

# --- WEB ROUTES ---

@app.route('/')
def index():
    return "Market API is running. Go to /api/price to see data."

@app.route('/api/price')
def get_all_prices():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, supply, demand FROM resources")
    rows = cursor.fetchall()
    conn.close()
    
    # Transform rows into a list of dictionaries
    market_snapshot = []
    for row in rows:
        market_snapshot.append({
            "item": row[0],
            "price": round(row[1], 2),
            "supply": row[2],
            "demand": row[3]
        })
    return jsonify(market_snapshot)

# --- MARKET LOGIC ---

def update_functions():
    global MARKET_DATA  # Tell the function to use the global dict
    temp_data = {}
    try:
        with open(r"C:\Users\danmi\Desktop\price.txt", "r", encoding='utf-8') as file:
            for line in file:
                line = line.strip() 
                if "=" in line:
                    key, value = line.split("=")
                    # Store everything in uppercase for easy lookup (e.g., IRON_SUPPLY)
                    temp_data[key.strip().upper()] = int(value.strip())
        
        # Update the global dict with the new file contents
        MARKET_DATA = temp_data
    except Exception as e:
        print(f"File Read Error: {e}")

def run_tick():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # 1. Get all materials currently in the DB
    cursor.execute("SELECT name, price, last_change, supply, demand FROM resources")
    all_resources = cursor.fetchall()

    for name, price, last_change, old_supply, old_demand in all_resources:
        # 2. Get the new Supply/Demand from the text file data (default to old if not in file)
        # We assume 'data' is the global dict populated by update_functions()
        new_supply = MARKET_DATA.get(f"{name}_SUPPLY", old_supply)
        new_demand = MARKET_DATA.get(f"{name}_DEMAND", old_demand)

        # 3. Calculate new price
        sd_ratio = (new_demand / new_supply) if new_supply > 0 else 1.0
        noise = random.uniform(-NOISE_MAX, NOISE_MAX) * price
        momentum = last_change * MOMENTUM_STRENGTH
        
        change = noise + momentum
        # You might want a different BASE_VALUE for different items!
        new_price = max((BASE_VALUE * sd_ratio) + change, 1.0)
        
        # 4. Update this specific material
        cursor.execute("""
            UPDATE resources 
            SET price = ?, last_change = ?, supply = ?, demand = ?, last_updated = ?
            WHERE name = ?
        """, (new_price, change, new_supply, new_demand, time.time(), name))

        print(f"Price Update for {name}: ${new_price:.2f} | S:{new_supply} D:{new_demand}")
    
    conn.commit()
    conn.close()

def market_loop():
    """The background task that runs the market"""
    while True:
        update_functions()
        run_tick()
        time.sleep(TICK_INTERVAL)

# --- INITIALIZATION ---
if __name__ == "__main__":
    # Setup DB
    conn = sqlite3.connect('market.db')
    conn.execute("CREATE TABLE IF NOT EXISTS resources (name TEXT PRIMARY KEY, price REAL, last_change REAL, supply INTEGER, demand INTEGER, last_updated REAL)")
    materials = [
        ('Iron', 100.0, 0.0, 500, 550, 0),
        ('Gold', 500.0, 0.0, 50, 60, 0),
        ('Wood', 20.0, 0.0, 1000, 800, 0)
    ]
    conn.executemany("INSERT OR IGNORE INTO resources VALUES (?, ?, ?, ?, ?, ?)", materials)
    conn.commit()
    conn.close()

    # Start Market in Background Thread
    threading.Thread(target=market_loop, daemon=True).start()

    # Start Flask on Port 5000
    print("Web Server starting on http://127.0.0.1:5000")
    app.run(port=5000, debug=False, use_reloader=False)