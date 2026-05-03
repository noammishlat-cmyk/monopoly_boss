import math
import sqlite3
import random
import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# --- CONFIGURATION ---
TICK_INTERVAL = 60.0 
MARKET_DECAY_RATE = 0.05 # How fast the market returns to "Normal" (0.1 = 10% of pressure disappears per tick)
EQUILIBRIUM_LEVEL = 200.0 # The "Neutral" level for Supply and Demand
HISTORY_RETAIN_TIME = 1800  # 30 minutes in seconds
CURRENT_TAX = 0.05 # 5%
RECRUITING_CHANCE = 15 # 15%
SABOTAGE_MAX_DETECTION_PRECENT = 40
SABOTAGE_MAX_DETECTION_SEND = 10
SABOTAGE_CHANCE_OF_DEATH = 20 # Minimum chance for dying during sabotage
WORKFORCE_RETURN_TIME = 1 # In Ticks
SHOW_INVENTORY_IN_LEADERBOARD = 1


CORPORATE_CHANGES_OPTIONS = [
    "Corporate Tax Policy + 0.05% to tax during selling. (Capped at 3%)",
    "Corporate Tax Policy - 0.05% to tax during selling. (Capped at 0.03%)",
    "Corporate Tax Policy + 0.07% to tax during selling. (Capped at 3%)",
    "Corporate Tax Policy -  0.07% to tax during selling. (Capped at 0.03%)",
    "Corporate Tax Policy + 0.02% to tax during selling. (Capped at 3%)",
    "Corporate Tax Policy - 0.02% to tax during selling. (Capped at 0.03%)",

    "Recruiting Overahall - Uneployment - Increase chance for recruiting.", # RECRUITING_CHANCE
    "Recruiting Overahall - Tough Market - Decrease chance for recruiting.", # RECRUITING_CHANCE

    "Global Security Crisis - Increase success chance for sabotage.", # Either SABOTAGE_MAX_DETECTION_PRECENT or SABOTAGE_MAX_DETECTION_SEND
    "Global Security Upgrades - Decrease success chance for sabotage.", # Either SABOTAGE_MAX_DETECTION_PRECENT or SABOTAGE_MAX_DETECTION_SEND
    "Global Security Crisis - Decrease chance of death during sabotage.", # SABOTAGE_CHANCE_OF_DEATH
    "Global Security Upgrades - Increase chance of death during sabotage.", # SABOTAGE_CHANCE_OF_DEATH

    "Area Contaminated - Global return time for workers has increased.", # WORKFORCE_RETURN_TIME
    "New Area Found - Global return time for workers has decreased.", # WORKFORCE_RETURN_TIME

    "Value Crisis - Element $element_name has increased in value.", # update_resource_base_price()
    "Value Overhall - Element $element_name has decreased in value.", # update_resource_base_price()

    "Value Crisis - Element $element_name has increased in demand.", # update_resource_base_price()
    "Value Overhall - Element $element_name has decreased in demand.", # update_resource_base_price()
]


MATERIALS = [
    #  Name   | Price | Change | Supply | Demand | Updated |  Base  | Rarity Index (Higher = Rarer)
    ('Wood'   , 20.0,    0.0,    2000,    2000,     0,        20.0,        1),
    ('Iron'   , 100.0,   0.0,    1000,    1000,     0,       100.0,        2),
    ('Gold'   , 500.0,   0.0,    660,     660,      0,       500.0,        3),
    ('Oil'    , 300.0,   0.0,    500,     500,      0,       300.0,        4),
]

app = Flask(__name__)
CORS(app)

# --- WEB ROUTES ---

@app.route('/api/get_user/<u_id>')
def get_game_state(u_id):
    global CURRENT_TAX
    global SABOTAGE_MAX_DETECTION_PRECENT
    global SABOTAGE_MAX_DETECTION_SEND
    global WORKFORCE_RETURN_TIME

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # 1. FETCH USER DATA (Including Workforce)
    cursor.execute("""
        SELECT balance, max_workforce, workers_extraction, workers_rnd, workers_espionage, workforce_deployment_length
        FROM users WHERE user_id = ?
    """, (u_id,))
    
    user_res = cursor.fetchone()
    
    if user_res:
        balance, max_total, w_ext, w_rnd, w_esp, workforce_deployment_length = user_res
    else:
        # Default fallback if user doesn't exist
        balance, max_total, w_ext, w_rnd, w_esp, workforce_deployment_length = 0, 0, 0, 0, 0, 0

    # 2. FETCH INVENTORY
    cursor.execute("SELECT resource_name, amount FROM inventory WHERE user_id = ?", (u_id,))
    inv_rows = cursor.fetchall()
    inventory = {row[0]: row[1] for row in inv_rows}

    # 3. FORMAT THE WORKFORCE DATA
    deployed_workers = {
        "extraction": w_ext,
        "rnd": w_rnd,
        "espionage": w_esp
    }

    now = time.time()
    next_tick = now + (TICK_INTERVAL - (now % TICK_INTERVAL))

    return jsonify({
        "balance": round(balance, 2),
        "inventory": inventory,
        "max_workforce": max_total,
        "deployed_workers": deployed_workers,
        "next_tick": next_tick,
        "server_time": now,
        "tick_length": TICK_INTERVAL,
        "current_tax": CURRENT_TAX,
        "max_sabotage_send": SABOTAGE_MAX_DETECTION_SEND,
        "max_sabotage_precent": SABOTAGE_MAX_DETECTION_PRECENT,
        "user_logs": get_user_logs(u_id),
        "workforce_deployment_length": WORKFORCE_RETURN_TIME,
        "current_deployment_length": workforce_deployment_length
    })

@app.route('/api/leaderboard')
def get_leaderboard():
    global SHOW_INVENTORY_IN_LEADERBOARD

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    try:
        # 1. Get current market prices
        cursor.execute("SELECT name, price FROM resources")
        prices = {row[0]: row[1] for row in cursor.fetchall()}

        # 2. Get users and inventories
        cursor.execute("SELECT user_id, balance FROM users")
        users = cursor.fetchall()
        cursor.execute("SELECT user_id, resource_name, amount FROM inventory")
        inventory_rows = cursor.fetchall()

        # Group inventory by user
        inventories = {}
        for u_id, res_name, amount in inventory_rows:
            if u_id not in inventories: inventories[u_id] = {}
            inventories[u_id][res_name] = amount

        # 3. Build RAW leaderboard (with all data)
        leaderboard = []
        for u_id, balance in users:
            user_inv = inventories.get(u_id, {})
            
            # Calculate real value
            inv_value = sum(prices.get(res, 0) * amt for res, amt in user_inv.items())
            net_worth = balance + inv_value

            leaderboard.append({
                "user_id": u_id,
                "balance": round(balance, 2),
                "inventory_value": round(inv_value, 2),
                "net_worth": round(net_worth, 2),
                "raw_inventory": user_inv # Keep this temporary for now
            })

        # 4. SORT FIRST to determine Rank
        leaderboard.sort(key=lambda x: x["net_worth"], reverse=True)

        # 5. MASK inventory based on Rank
        for i, entry in enumerate(leaderboard):
            rank = i + 1
            entry["rank"] = rank
            
            # Logic: If rank is within the limit, show it; otherwise, hide it
            if rank <= SHOW_INVENTORY_IN_LEADERBOARD:
                entry["inventory"] = {res: amt for res, amt in entry["raw_inventory"].items() if amt > 0}
            else:
                entry["inventory"] = "Hidden"
            
            # Remove the raw helper data before sending to frontend
            del entry["raw_inventory"]

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/state/prices')
def get_prices():
    return fetch_market_state()

@app.route('/api/deploy_workers/<u_id>', methods=['POST'])
def deploy_workers(u_id):
    global WORKFORCE_RETURN_TIME

    data = request.get_json()
    u_id = data.get('user_id', '')

    if u_id == '':
        return jsonify({
                "error": "user_id does not exist",
            }), 400

    # Get values from the request, default to 0 if missing
    # We use abs(int()) to ensure we don't get decimals or negative numbers
    try:
        ext = abs(int(data.get('extraction', 0)))
        rnd = abs(int(data.get('rnd', 0)))
        esp = abs(int(data.get('espionage', 0)))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid worker counts provided"}), 400

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    try:
        # 1. FETCH MAX WORKFORCE
        cursor.execute("SELECT max_workforce FROM users WHERE user_id = ?", (u_id,))
        res = cursor.fetchone()
        
        if not res:
            return jsonify({"error": "User not found"}), 404
        
        max_limit = res[0]
        total_requested = ext + rnd + esp

        # 2. SAFETY MECHANISM
        if total_requested > max_limit:
            return jsonify({
                "error": "Workforce limit exceeded",
                "requested": total_requested,
                "max": max_limit
            }), 400

        # 3. UPDATE DATABASE
        cursor.execute("""
            UPDATE users SET 
            workers_extraction = ?, 
            workers_rnd = ?, 
            workers_espionage = ? ,
            workforce_deployment_length = ?
            WHERE user_id = ?
        """, (ext, rnd, esp, WORKFORCE_RETURN_TIME, u_id))

        add_log(cursor=cursor, log_msg=f"Sent {ext + rnd + esp} workers.", u_id=u_id, log_type="HQ")

        conn.commit()
        return jsonify({
            "message": "Workers reassigned successfully",
            "distribution": {"extraction": ext, "rnd": rnd, "espionage": esp}
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/buy', methods=['POST'])
def buy_resource():
    data = request.get_json()
    u_id = data.get('user_id', 'user123')
    item = data.get('item').capitalize()
    qty = int(data.get('amount', 1))

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    try:
        # --- PRE-TRANSACTION SNAPSHOT ---
        cursor.execute("SELECT price, supply, demand FROM resources WHERE name = ?", (item,))
        res = cursor.fetchone()
        if not res: return jsonify({"error": "Item not found"}), 400
        
        old_price, old_supply, old_demand = res
        total_cost = old_price * qty
        
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        balance = cursor.fetchone()[0]

        if balance < total_cost:
            return jsonify({"error": "Insufficient funds"}), 400

        # 1. Update User Balance
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_cost, u_id))
        
        # 2. Apply Inverse Reaction
        cursor.execute("""
            UPDATE resources 
            SET demand = demand + ?, 
                supply = MAX(supply - ?, 1) 
            WHERE name = ?
        """, (qty, qty, item))
        
        # 3. Add to inventory
        cursor.execute("""
            INSERT INTO inventory (user_id, resource_name, amount) VALUES (?, ?, ?)
            ON CONFLICT(user_id, resource_name) DO UPDATE SET amount = amount + ?
        """, (u_id, item, qty, qty))

        # --- POST-TRANSACTION SNAPSHOT ---
        cursor.execute("SELECT supply, demand FROM resources WHERE name = ?", (item,))
        new_supply, new_demand = cursor.fetchone()

        print(f"\n[🛒 BUY EVENT] User: {u_id} | Item: {item} | Qty: {qty}")
        print(f"  💰 Price Per: ${old_price:,.2f} | Total: ${total_cost:,.2f}")
        print(f"  📉 Supply: {old_supply} -> {new_supply} (Diff: -{qty})")
        print(f"  📈 Demand: {old_demand} -> {new_demand} (Diff: +{qty})")
        print("-" * 40)

        add_log(cursor=cursor, log_msg=f"Purchased {qty}x {item} for ${total_cost:,.2f}.", u_id=u_id, log_type="BUY")

        conn.commit()
        conn.close()
        return fetch_market_state()
    except Exception as e:
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/sell', methods=['POST'])
def sell_resource():
    data = request.get_json()
    u_id = data.get('user_id', 'user123')
    item = data.get('item').capitalize()
    qty = int(data.get('amount', 1))

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    try:
        # Check Inventory
        cursor.execute("SELECT amount FROM inventory WHERE user_id = ? AND resource_name = ?", (u_id, item))
        row = cursor.fetchone()
        if not row or row[0] < qty:
            return jsonify({"error": "Not enough items"}), 400

        # --- PRE-TRANSACTION SNAPSHOT ---
        cursor.execute("SELECT price, supply, demand FROM resources WHERE name = ?", (item,))
        res = cursor.fetchone()
        current_price, old_supply, old_demand = res
        
        # Apply tax
        tax_rate = CURRENT_TAX
        gain = (current_price * qty) * (1.0 - tax_rate)

        # 1. Update Balance
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (gain, u_id))
        
        # 2. Apply Inverse Reaction
        cursor.execute("""
            UPDATE resources 
            SET supply = supply + ?, 
                demand = MAX(demand - ?, 1) 
            WHERE name = ?
        """, (qty, qty, item))
        
        # 3. Update Inventory
        cursor.execute("UPDATE inventory SET amount = amount - ? WHERE user_id = ? AND resource_name = ?", (qty, u_id, item))

        # --- POST-TRANSACTION SNAPSHOT ---
        cursor.execute("SELECT supply, demand FROM resources WHERE name = ?", (item,))
        new_supply, new_demand = cursor.fetchone()

        print(f"\n[💰 SELL EVENT] User: {u_id} | Item: {item} | Qty: {qty}")
        print(f"  💵 Market Price: ${current_price:,.2f} | Player Gained (Post-Tax): ${gain:,.2f}")
        print(f"  📈 Supply: {old_supply} -> {new_supply} (Diff: +{qty})")
        print(f"  📉 Demand: {old_demand} -> {new_demand} (Diff: -{qty})")
        print("-" * 40)

        add_log(cursor=cursor, log_msg=f"Sold {qty}x {item} for ${current_price*qty:,.2f}.", u_id=u_id, log_type="SELL")

        conn.commit()
        conn.close()
        return fetch_market_state()
    except Exception as e:
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500

def add_log(cursor: sqlite3.Cursor, log_msg:str, u_id: str, log_type: str):
    cursor.execute("""
        INSERT INTO activity_logs (user_id, action_type, message) 
        VALUES (?, ?, ?)
    """, (u_id, log_type, log_msg))

# --- MARKET LOGIC ---

def fetch_market_state():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    
    # 1. FETCH MARKET
    cursor.execute("SELECT name, price, supply, demand, base_price FROM resources")
    market_rows = cursor.fetchall()
    market_data = []
    resource_names = []
    for row in market_rows:
        name, price, supply, demand, base_price = row
        resource_names.append(name)
        market_data.append({
            "name": name,
            "price": round(price, 2),
            "supply": supply,
            "demand": demand,
            "base_price": base_price
        })

    all_histories = {}
    
    for name in resource_names:
        cursor.execute("""
            SELECT price, timestamp FROM price_history 
            WHERE resource_name = ? 
            ORDER BY timestamp DESC LIMIT 30
        """, (name,))
        hist_rows = cursor.fetchall()
        
        item_history = []
        for row in reversed(hist_rows):
            item_history.append({
                "time": time.strftime('%H:%M:%S', time.localtime(row[1])),
                "price": round(row[0], 2)
            })
        all_histories[name] = item_history

    # 3. CALCULATE NEXT TICK
    now = time.time()
    next_tick = now + (TICK_INTERVAL - (now % TICK_INTERVAL))

    conn.close()

    return jsonify({
        "market": market_data,
        "history": all_histories,
        "next_tick": next_tick,
        "tick_length": TICK_INTERVAL,
        "server_time": now
    })

def calculate_market_price(current_price, base_price, supply, demand, last_change, rarity_index):
    """
    Elastic Equilibrium Model:
    Scales non-linearly to prevent hyperinflation and uses rarity 
    to dictate how aggressively the market reacts to shortages.
    """
    # 1. Non-linear Target Price (Incorporating Rarity)
    # Higher rarity makes the price MORE sensitive to shortages (inelastic)
    # Rarity 1 (Common) -> Elasticity 0.5 (Prices rise slowly during shortages)
    # Rarity 5 (Legendary) -> Elasticity 1.15 (Prices spike aggressively)
    elasticity = 0.35 + (rarity_index * 0.15) 
    
    ratio = max(demand, 1) / max(supply, 1)
    
    # Apply elasticity exponent to prevent absurd linear scaling
    adjusted_ratio = math.pow(ratio, elasticity) 
    
    # Hard cap the multiplier to protect game balance (e.g., max 50x base price)
    adjusted_ratio = min(adjusted_ratio, 50.0)
    target_price = base_price * adjusted_ratio

    # 2. Calculate the Gap
    diff = target_price - current_price

    # 3. Dynamic Reaction Speed
    # React faster when the gap is huge (panic buying/selling)
    # React slower when the gap is small (soft landing)
    distance_ratio = abs(diff) / max(current_price, 1)
    reaction_speed = 0.03 * (1 + distance_ratio) 
    # Cap reaction speed so it doesn't instantly snap
    reaction_speed = min(reaction_speed, 0.15)
    
    movement = diff * reaction_speed

    # 4. Dampened Momentum & Noise
    # Only apply strong momentum if we are far from the target to prevent jitter
    momentum_dampener = min(abs(diff) / base_price, 1.0)
    momentum = last_change * 0.1 * momentum_dampener 
    
    # Noise scales with base price, so hyper-inflated goods don't swing wildly
    noise = random.uniform(-0.01, 0.01) * base_price
    
    total_change = movement + momentum + noise

    # 5. Dynamic Volatility Cap
    # Rarer items have looser volatility limits (more volatile markets)
    volatility_limit = 0.08 + (rarity_index * 0.02) 
    max_move = current_price * volatility_limit
    total_change = max(min(total_change, max_move), -max_move)

    new_price = current_price + total_change

    # 6. Safety Floor
    # Ensure it never drops below 10% of base
    floor_price = base_price * 0.1
    return max(new_price, floor_price), total_change

def run_tick():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    now = time.time()

    cursor.execute("SELECT name, price, last_change, supply, demand, base_price, rarity_index FROM resources")
    all_resources = cursor.fetchall()

    for name, price, last_change, supply, demand, base_price, rarity_index in all_resources:
        # 1. Calculate New Price
        new_price, change = calculate_market_price(price, base_price, supply, demand, last_change, rarity_index)

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

    handle_workers_done()

def get_user_logs(user_id, limit=15):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    # Fetch action_type so we know what color to use
    cursor.execute("""
        SELECT 
            message, 
            datetime(timestamp, 'localtime') as local_ts, 
            action_type 
        FROM activity_logs 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (user_id, limit))
    
    raw_logs = cursor.fetchall()
    conn.close()

    # Define your color mapping
    # These strings will be used as Tailwind classes in React
    color_map = {
        'BUY': 'text-emerald-400',
        'SELL': 'text-blue-400',
        'SABOTAGE': 'text-orange-400',
        'ERROR': 'text-red-500',
        'SYSTEM': 'text-slate-500',
        'HQ': 'text-amber-400',
        'FAIL': 'text-red-600',
        'KILLED': 'text-red-600',
    }

    formatted_logs = []
    for message, ts_string, action_type in raw_logs:
        dt_obj = datetime.strptime(ts_string, '%Y-%m-%d %H:%M:%S')
        time_str = dt_obj.strftime('%H:%M:%S')

        formatted_logs.append({
            "text": f"[{time_str}] {message}",
            "color": color_map.get(action_type, 'text-white') # Default to white
        })

    return formatted_logs


def market_loop():
    while True:
        now = time.time()
        time_to_next = TICK_INTERVAL - (now % TICK_INTERVAL)
        time.sleep(time_to_next) 

        run_tick()


def sync_table_schema(conn, table_name, schema_definition):
    """
    Ensures the table exists and has all columns defined in the schema_definition.
    Note: schema_definition should be the content inside the CREATE TABLE (...)
    """
    cursor = conn.cursor()
    
    # 1. Create the table if it doesn't exist at all
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_definition})")
    
    # 2. Get existing columns from the DB
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # 3. Parse the schema_definition to find column names and types
    # This is a simple parser that looks for lines starting with column names
    for line in schema_definition.strip().split(','):
        parts = line.strip().split()
        if not parts: continue
        
        column_name = parts[0].replace('"', '').replace('`', '')
        
        # If the column name isn't in the DB and isn't a table constraint (like PRIMARY KEY)
        if column_name not in existing_columns and column_name.upper() not in ("PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE"):
            # Construct the ALTER TABLE command
            # We join the rest of the line back together to get the type and defaults
            column_def = " ".join(parts[1:])
            try:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
                print(f"Migration: Added column '{column_name}' to table '{table_name}'")
            except sqlite3.OperationalError as e:
                print(f"Migration Error on '{column_name}': {e}")

def handle_workers_done():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Decreases deployment timers for all active users by 1
    cursor.execute("""
        UPDATE users 
        SET workforce_deployment_length = workforce_deployment_length - 1 
        WHERE workforce_deployment_length > 0
    """)

    cursor.execute("""
        SELECT user_id, workers_extraction, workers_rnd, workers_espionage, max_workforce
        FROM users 
        WHERE workforce_deployment_length = 0 
        AND (workers_extraction + workers_rnd + workers_espionage) > 0
    """)
    finished_users = cursor.fetchall()

    for user_data in finished_users:
        u_id, ext, rnd, esp, max_wf = user_data
        
        # Call your existing reward logic for this specific user
        # Note: You'll need to update handle_workers_reward to accept these values
        handle_workers_reward(cursor, finished_users)

        # RESET workers ONLY for this specific user
        cursor.execute("""
            UPDATE users SET 
                workers_extraction = 0, 
                workers_rnd = 0, 
                workers_espionage = 0
            WHERE user_id = ?
        """, (u_id,))

    print(f"Tick Event: Processed {len(finished_users)} completed deployments.")

    conn.commit()
    conn.close()

def handle_workers_reward(cursor: sqlite3.Cursor, active_users: list[tuple]):
    global RECRUITING_CHANCE

    # Calculate success chance for gathering materials
    cursor.execute("SELECT name, rarity_index FROM resources")
    rarity_map = {row[0]: row[1] for row in cursor.fetchall()}

    for u_id, ext_count, rnd_count, sabo_count, max_wf in active_users:
        # Start with the random split
        rnd_splitter = random.randint(0, rnd_count)
        # Apply 25% / 75% "Safety Zone"
        floor = int(rnd_count / 4)
        ceiling = int(rnd_count / 4 * 3)
        # Clamp the value between floor and ceiling
        rnd_splitter = max(floor, min(rnd_splitter, ceiling))
        # Apply the Efficiency Cap (Cannot have more enhancers than extractors)
        # This ensures research doesn't exceed the actual workforce capability.
        enhancers = min(rnd_splitter, ext_count)
        # Give the remainder to recruiters
        recruiters = rnd_count - enhancers

        print(f"Split the workers for User {u_id} into - {enhancers} enhancers and - {recruiters} recruiters.")

        overall_recruted = 0

        # Calculate success chance for each recruiting
        success_threshold = RECRUITING_CHANCE

        for _ in range(recruiters):
            roll = random.uniform(0, 100)
            
            if roll <= success_threshold:
                # SUCCESS
                overall_recruted += 1
                print(f"User {u_id}-{_} recruted Someone (Chance: {success_threshold:.1f}%)")
            else:
                print(f"User {u_id}-{_} recruting failed (Rolled {roll:.1f} vs {success_threshold:.1f}%)")

        overall_rewards = extraction_reward(rarity_map, enhancers, max_wf, u_id, ext_count)

        if sabo_count > 0:
            # 1. Find a random target who is NOT the current user
            cursor.execute("""
                SELECT user_id FROM users 
                WHERE user_id != ? 
                ORDER BY RANDOM() LIMIT 1
            """, (u_id,))
            
            target_row = cursor.fetchone()

            if sabo_count > 0:
                # Pick a target that isn't the current user
                cursor.execute("SELECT user_id FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (u_id,))
                target_res = cursor.fetchone()

                if target_res:
                    target_id = target_res[0]
                    # Run the logic
                    rewards = sabotage_reward(cursor, u_id, target_id, sabo_count)

                    if rewards["user_eliminated"] > 0 and rewards["failed"]:
                        count = rewards['user_eliminated']
                        msg = f"Failed sabotage with casualties - {count} worker{'s' if count != 1 else ''} have been killed."
                        add_log(cursor=cursor, log_msg=msg, u_id=u_id, log_type='FAIL')
                    elif rewards["target_eliminated"] > 0:
                        count = rewards['target_eliminated']
                        msg = f"Completed sabotage - {count} worker{'s' if count != 1 else ''} have been killed for {target_id}."
                        add_log(cursor=cursor, log_msg=msg, u_id=u_id, log_type='SABOTAGE')
                    else:
                        add_log(cursor=cursor, log_msg=f"Sabotage failed, no casualties", u_id=u_id, log_type='SABOTAGE')


        if overall_recruted > 0:
            cursor.execute("""
                UPDATE users 
                SET max_workforce = max_workforce + ? 
                WHERE user_id = ?
            """, (overall_recruted, u_id))
            print(f"User {u_id} expanded workforce capacity by {overall_recruted}!")
            add_log(cursor=cursor, log_msg=f"R&D Team managed to recruit {overall_recruted} workers.", u_id=u_id, log_type="HQ")
        else:
            print(f"User {u_id} recruiting failed completely")

        if overall_rewards:
            for res_name, amount in overall_rewards.items():
                # 1. Update Player Inventory (You already have this)
                cursor.execute("""
                    INSERT INTO inventory (user_id, resource_name, amount) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, resource_name) 
                    DO UPDATE SET amount = amount + ?
                """, (u_id, res_name, amount, amount))
                
                # 2. UPDATE GLOBAL MARKET SUPPLY
                # This ensures that as players find more, the global price drops.
                cursor.execute("""
                    UPDATE resources 
                    SET supply = supply + ? 
                    WHERE name = ?
                """, (amount, res_name))
                
                # Debugging prints
                print(f"User {u_id} gathered {amount}x {res_name}")
                print(f"  [🌍 MARKET] Global supply of {res_name} increased by {amount}.")
            
            # Summary print
            summary = ", ".join([f"{amt}x {name}" for name, amt in overall_rewards.items()])
            print(f"✅ Total harvest for User {u_id}: {summary}")
            add_log(cursor=cursor, log_msg=f"Extraction Team managed to harvest: {summary}.", u_id=u_id, log_type="HQ")
        else:
            print(f"User {u_id} mining failed completely")

def extraction_reward(rarity_map: dict, enhancers: int, max_wf: int, u_id: str, workers: int):
    resources = list(rarity_map.keys())
    overall_rewards = {}
    
    for _ in range(workers):
        rnd_ratio = enhancers / max(max_wf, 1)
        weights = []
        for res_name in resources:
            rarity = rarity_map[res_name]
            target_weight = (rnd_ratio * rarity) + (1 - rnd_ratio) * (1 / rarity)
            weights.append(target_weight)

        # Pick the target based on weights
        resource_to_mine = random.choices(resources, weights=weights, k=1)[0]
        rarity = rarity_map[resource_to_mine]

        # --- SUCCESS CALCULATION ---
        # base_potential is your "skill" (25% to 100%) - This isn't actually a 100% success, only if they managed to find anything at all
        base_potential = 25 + (rnd_ratio * 75) 
        # Flatten the rarity impact
        stability_factor = 0.6 
        dampened_rarity = math.pow(rarity, stability_factor)
        # Calculate final threshold
        final_success_threshold = base_potential / dampened_rarity
        # Clamp a minimum success floor so it's never 0%
        final_success_threshold = max(final_success_threshold, 5.0)

        roll = random.uniform(0, 100)
        
        if roll <= final_success_threshold:
            # SUCCESS: Track which specific resource was found
            overall_rewards[resource_to_mine] = overall_rewards.get(resource_to_mine, 0) + 1
            print(f"User {u_id}-{_} mined {resource_to_mine} (Chance: {final_success_threshold:.1f}%)")
        else:
            # FAILED
            print(f"User {u_id}-{_} mining failed to mine {resource_to_mine} (Rolled {roll:.1f} vs {final_success_threshold:.1f}%)")
            pass
    return overall_rewards

def sabotage_reward(cursor, user_id, target_id, sabo_count):
    global SABOTAGE_MAX_DETECTION_SEND
    global SABOTAGE_MAX_DETECTION_PRECENT
    global SABOTAGE_CHANCE_OF_DEATH

    # Calculate success rate
    precent_for_caught = min((sabo_count / SABOTAGE_MAX_DETECTION_SEND) * SABOTAGE_MAX_DETECTION_PRECENT, SABOTAGE_MAX_DETECTION_PRECENT)
    print(f"Getting caught precent - {precent_for_caught}")
    success_chance = 5 
    user_eliminated_total = 0
    target_eliminated_total = 0
    failed = False

    if (precent_for_caught > SABOTAGE_CHANCE_OF_DEATH): # Chance for death of own workers is only if risk is above SABOTAGE_CHANCE_OF_DEATH
        for _ in range(sabo_count):
            roll = random.uniform(0, 100)
            if roll <= precent_for_caught:
                user_eliminated_total += 1
                failed = True
    if not failed:
        for _ in range(sabo_count):
            roll = random.uniform(0, 100)
            if roll <= success_chance:
                target_eliminated_total += 1

    if user_eliminated_total > 0:
        # Decrease the user's workforce, but keep it at a minimum of 5
        cursor.execute("""
            UPDATE users 
            SET max_workforce = MAX(5, max_workforce - ?) 
            WHERE user_id = ?
        """, (user_eliminated_total, user_id))
        print(f"🎯 User {user_id} lost {user_eliminated_total} workers.")

    if target_eliminated_total > 0:
        # Decrease the target's workforce, but keep it at a minimum of 5
        cursor.execute("""
            UPDATE users 
            SET max_workforce = MAX(5, max_workforce - ?) 
            WHERE user_id = ?
        """, (target_eliminated_total, target_id))
        add_log(cursor=cursor, log_msg=f"User {user_id} killed {target_eliminated_total} of your workers", u_id=target_id, log_type='KILLED')
        print(f"🎯 User {user_id} successfully eliminated {target_eliminated_total} workers from User {target_id}!")

    return {"user_eliminated": user_eliminated_total, "target_eliminated": target_eliminated_total, "failed": failed}

def update_resource_base_price(cursor, resource_name, new_base_price):
    try:
        cursor.execute("""
            UPDATE resources 
            SET 
                last_change = ? - base_price,
                base_price = ?,
                price = (price - base_price) + ?
            WHERE name = ?
        """, (new_base_price, new_base_price, new_base_price, resource_name.capitalize()))
        
        return True
    except Exception as e:
        print(f"Error updating base price: {e}")
        return False
    
def update_resource_demand(cursor: sqlite3.Cursor, resource_name: str, add_demand: float):
    try:
        cursor.execute("""
            UPDATE resources 
            SET 
                demand = demand + ?
            WHERE name = ?
        """, (add_demand, resource_name.capitalize()))
        
        print(f"Added {add_demand} demand")
        return True
    except Exception as e:
        print(f"Error updating base price: {e}")
        return False

# --- INITIALIZATION ---
if __name__ == "__main__":
    conn = sqlite3.connect('market.db')

    # Define Schemas
    RESOURCES_SCHEMA = """
        name TEXT PRIMARY KEY, 
        price REAL, 
        last_change REAL, 
        supply INTEGER, 
        demand INTEGER, 
        last_updated REAL,
        base_price REAL,
        rarity_index INTEGER
    """
    
    USERS_SCHEMA = """
        user_id TEXT PRIMARY KEY, 
        balance REAL,
        max_workforce INTEGER DEFAULT 10,
        workers_extraction INTEGER DEFAULT 0,
        workers_rnd INTEGER DEFAULT 0,
        workers_espionage INTEGER DEFAULT 0,
        workforce_deployment_length INTEGER DEFAULT 0
    """

    INVENTORY_SCHEMA = """
        user_id TEXT, 
        resource_name TEXT,
        amount INTEGER,
        PRIMARY KEY (user_id, resource_name)
    """

    ACTIVITY_LOGS = """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action_type TEXT, -- e.g., 'BUY', 'SELL', 'SABOTAGE'
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    """

    # Sync them!
    sync_table_schema(conn, "resources", RESOURCES_SCHEMA)
    sync_table_schema(conn, "users", USERS_SCHEMA)
    sync_table_schema(conn, "inventory", INVENTORY_SCHEMA)
    sync_table_schema(conn, "activity_logs", ACTIVITY_LOGS)

    # Standard Price History (doesn't change often, but keep it simple)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            resource_name TEXT, price REAL, timestamp REAL
        )
    """)

    # --- UPSERT DATA ---
    # Use INSERT OR IGNORE so we don't duplicate data on every restart
    conn.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, balance, max_workforce, workers_extraction, workers_rnd, workers_espionage) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("user123", 1000.0, 10, 0, 0, 0))

    conn.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, balance, max_workforce, workers_extraction, workers_rnd, workers_espionage) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("test_user321", 1000.0, 10, 0, 0, 0))

    for m in MATERIALS:
        conn.execute("INSERT OR IGNORE INTO resources VALUES (?, ?, ?, ?, ?, ?, ?, ?)", m)

    update_resource_demand(cursor=conn.cursor(), resource_name="Iron", add_demand=100)

    conn.commit()
    conn.close()

    threading.Thread(target=market_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)