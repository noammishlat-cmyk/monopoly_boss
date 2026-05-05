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
VOTE_INTERVAL = 60.0 * 60 # An hour

MARKET_DECAY_RATE = 0.05
HISTORY_RETAIN_TIME = 1800  # 30 minutes in seconds
CURRENT_TAX = 0.05          # 5%
RECRUITING_CHANCE = 15      # 15%
SABOTAGE_MAX_DETECTION_PRECENT = 40
SABOTAGE_MAX_DETECTION_SEND = 10
SABOTAGE_CHANCE_OF_DEATH = 20
WORKFORCE_RETURN_TIME = 1   # In Ticks
SHOW_INVENTORY_IN_LEADERBOARD = 0
COORPRATE_VOTE_LENGTH = 30

MATERIALS = [
    #  Name    | Price | Change | Supply | Demand | Updated |  Base   | Rarity Index
    ('Wood'    , 20.0,    0.0,    60000,   60000,      0,        20.0,        1),
    ('Iron'    , 100.0,   0.0,    30000,   30000,      0,       100.0,        2),
    ('Copper'  , 300.0,   0.0,    30000,   30000,      0,       300.0,        2),
    ('Gold'    , 500.0,   0.0,    12000,   12000,      0,       500.0,        3),
    ('Oil'     , 700.0,   0.0,     5000,    5000,      0,       700.0,        4),
    ('Lithium' , 1200.0,  0.0,     5000,    5000,      0,      1200.0,        4),
    ('Silicon' , 2500.0,  0.0,     5000,    5000,      0,      2500.0,        4),
    ('Diamond' , 20000.0, 0.0,      800,     800,      0,     20000.0,        5),
]
# Instead of one global EQUILIBRIUM_LEVEL = 200 for all resources,
# each rarity tier has its own natural resting supply/demand.
# This prevents Diamond (1000 units) from being pulled toward the same
# equilibrium as Wood (90000 units), which would make all markets feel the same.
EQUILIBRIUM_BY_RARITY = {
    1: 60000,   # Common    (Wood)
    2: 30000,   # Uncommon  (Iron, Copper)
    3: 12000,   # Rare      (Gold)
    4: 5000,    # Epic      (Oil, Lithium, Silicon)
    5: 800,     # Legendary (Diamond)
}

# --- FIX 2: Momentum window length ---
# Price momentum now looks at the last N ticks instead of just 1.
# This smooths out chart lines and makes trends more readable.
MOMENTUM_WINDOW = 5


CORPORATE_CHANGES_OPTIONS = [
    "Corporate Tax Policy | +0.05% to tax during selling. (Capped at 3%)",
    "Corporate Tax Policy | -0.05% to tax during selling. (Capped at 0.03%)",
    "Corporate Tax Policy | +0.07% to tax during selling. (Capped at 3%)",
    "Corporate Tax Policy | -0.07% to tax during selling. (Capped at 0.03%)",
    "Corporate Tax Policy | +0.02% to tax during selling. (Capped at 3%)",
    "Corporate Tax Policy | -0.02% to tax during selling. (Capped at 0.03%)",

    "Recruiting Overhaul | Unemployment - Increase chance for recruiting.",
    "Recruiting Overhaul | Tough Market - Decrease chance for recruiting.",

    "Global Security Crisis | Increase success chance for sabotage.",
    "Global Security Upgrades | Decrease success chance for sabotage.",
    "Global Security Crisis | Decrease chance of death during sabotage.",
    "Global Security Upgrades | Increase chance of death during sabotage.",

    "Area Contaminated | Global return time for workers has increased.",
    "New Area Found | Global return time for workers has decreased.",

    "Value Crisis | Elements `$element_name1, $element_name2, $element_name3` has increased in value.",
    "Value Overhaul | Elements `$element_name1, $element_name2, $element_name3` has decreased in value.",

    "Value Crisis | Elements `$element_name1, $element_name2, $element_name3` has increased in demand.",
    "Value Overhaul | Elements `$element_name1, $element_name2, $element_name3` has decreased in demand.",

    "Public Report | See the resources of top 10 players in leaderboard",
]

app = Flask(__name__)
CORS(app)

# --- WEB ROUTES ---

@app.route('/api/get_user/<u_id>')
def get_game_state(u_id):
    global CURRENT_TAX, SABOTAGE_MAX_DETECTION_PRECENT, SABOTAGE_MAX_DETECTION_SEND, WORKFORCE_RETURN_TIME

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT balance, max_workforce, workers_extraction, workers_rnd, workers_espionage, workforce_deployment_length
        FROM users WHERE user_id = ?
    """, (u_id,))
    user_res = cursor.fetchone()

    cursor.execute("SELECT current_vote_length FROM system")
    row = cursor.fetchone()
    current_coorprate_vote = row[0] if row else 30

    if user_res:
        balance, max_total, w_ext, w_rnd, w_esp, workforce_deployment_length = user_res
    else:
        balance, max_total, w_ext, w_rnd, w_esp, workforce_deployment_length = 0, 0, 0, 0, 0, 0

    cursor.execute("SELECT resource_name, amount FROM inventory WHERE user_id = ?", (u_id,))
    inventory = {row[0]: row[1] for row in cursor.fetchall()}

    deployed_workers = {"extraction": w_ext, "rnd": w_rnd, "espionage": w_esp}

    now = time.time()
    next_tick = now + (TICK_INTERVAL - (now % TICK_INTERVAL))
    next_vote = now + (VOTE_INTERVAL - (now % VOTE_INTERVAL))

    conn.close()

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
        "current_deployment_length": workforce_deployment_length,
        "next_vote_tick": next_vote,
    })


@app.route('/api/leaderboard')
def get_leaderboard():
    global SHOW_INVENTORY_IN_LEADERBOARD

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name, price FROM resources")
        prices = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT user_id, balance FROM users")
        users = cursor.fetchall()
        cursor.execute("SELECT user_id, resource_name, amount FROM inventory")
        inventory_rows = cursor.fetchall()

        inventories = {}
        for u_id, res_name, amount in inventory_rows:
            if u_id not in inventories:
                inventories[u_id] = {}
            inventories[u_id][res_name] = amount

        leaderboard = []
        for u_id, balance in users:
            user_inv = inventories.get(u_id, {})
            inv_value = sum(prices.get(res, 0) * amt for res, amt in user_inv.items())
            net_worth = balance + inv_value
            leaderboard.append({
                "user_id": u_id,
                "balance": round(balance, 2),
                "inventory_value": round(inv_value, 2),
                "net_worth": round(net_worth, 2),
                "raw_inventory": user_inv
            })

        leaderboard.sort(key=lambda x: x["net_worth"], reverse=True)

        for i, entry in enumerate(leaderboard):
            rank = i + 1
            entry["rank"] = rank
            if rank <= SHOW_INVENTORY_IN_LEADERBOARD:
                entry["inventory"] = {res: amt for res, amt in entry["raw_inventory"].items() if amt > 0}
            else:
                entry["inventory"] = "Hidden"
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
        return jsonify({"error": "user_id does not exist"}), 400

    try:
        ext = abs(int(data.get('extraction', 0)))
        rnd = abs(int(data.get('rnd', 0)))
        esp = abs(int(data.get('espionage', 0)))
        target = data.get('target', "RANDOM")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid worker counts provided"}), 400

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT max_workforce FROM users WHERE user_id = ?", (u_id,))
        res = cursor.fetchone()

        if not res:
            return jsonify({"error": "User not found"}), 404

        max_limit = res[0]
        total_requested = ext + rnd + esp

        if total_requested > max_limit:
            return jsonify({
                "error": "Workforce limit exceeded",
                "requested": total_requested,
                "max": max_limit
            }), 400

        cursor.execute("""
            UPDATE users SET 
            workers_extraction = ?, 
            workers_rnd = ?, 
            workers_espionage = ?,
            espionage_taget = ?,
            workforce_deployment_length = ?
            WHERE user_id = ?
        """, (ext, rnd, esp, target, WORKFORCE_RETURN_TIME, u_id))

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
        cursor.execute("SELECT price, supply, demand FROM resources WHERE name = ?", (item,))
        res = cursor.fetchone()
        if not res:
            return jsonify({"error": "Item not found"}), 400

        old_price, old_supply, old_demand = res
        total_cost = old_price * qty

        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        balance = cursor.fetchone()[0]

        if balance < total_cost:
            return jsonify({"error": "Insufficient funds"}), 400

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_cost, u_id))
        cursor.execute("""
            UPDATE resources 
            SET demand = demand + ?, supply = MAX(supply - ?, 1) 
            WHERE name = ?
        """, (qty, qty, item))
        cursor.execute("""
            INSERT INTO inventory (user_id, resource_name, amount) VALUES (?, ?, ?)
            ON CONFLICT(user_id, resource_name) DO UPDATE SET amount = amount + ?
        """, (u_id, item, qty, qty))

        cursor.execute("SELECT supply, demand FROM resources WHERE name = ?", (item,))
        new_supply, new_demand = cursor.fetchone()

        print(f"\n[BUY] User: {u_id} | Item: {item} | Qty: {qty}")
        print(f"  Price: ${old_price:,.2f} | Total: ${total_cost:,.2f}")
        print(f"  Supply: {old_supply} -> {new_supply} | Demand: {old_demand} -> {new_demand}")

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
        cursor.execute("SELECT amount FROM inventory WHERE user_id = ? AND resource_name = ?", (u_id, item))
        row = cursor.fetchone()
        if not row or row[0] < qty:
            return jsonify({"error": "Not enough items"}), 400

        cursor.execute("SELECT price, supply, demand FROM resources WHERE name = ?", (item,))
        res = cursor.fetchone()
        current_price, old_supply, old_demand = res

        tax_rate = CURRENT_TAX
        gain = (current_price * qty) * (1.0 - tax_rate)

        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (gain, u_id))
        cursor.execute("""
            UPDATE resources 
            SET supply = supply + ?, demand = MAX(demand - ?, 1) 
            WHERE name = ?
        """, (qty, qty, item))
        cursor.execute("""
            UPDATE inventory SET amount = amount - ? 
            WHERE user_id = ? AND resource_name = ?
        """, (qty, u_id, item))

        cursor.execute("SELECT supply, demand FROM resources WHERE name = ?", (item,))
        new_supply, new_demand = cursor.fetchone()

        print(f"\n[SELL] User: {u_id} | Item: {item} | Qty: {qty}")
        print(f"  Market Price: ${current_price:,.2f} | Player Gained (Post-Tax): ${gain:,.2f}")
        print(f"  Supply: {old_supply} -> {new_supply} | Demand: {old_demand} -> {new_demand}")

        add_log(cursor=cursor, log_msg=f"Sold {qty}x {item} for ${current_price*qty:,.2f}.", u_id=u_id, log_type="SELL")

        conn.commit()
        conn.close()
        return fetch_market_state()
    except Exception as e:
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500


# --- VOTING ROUTES ---

@app.route('/api/vote/current')
def get_current_vote():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, option_a, option_b, option_c, votes_a, votes_b, votes_c, expires_at
            FROM corporate_votes
            WHERE expires_at > ?
            ORDER BY expires_at DESC LIMIT 1
        """, (time.time(),))
        row = cursor.fetchone()
        if not row:
            return jsonify({"active": False}), 200

        vote_id, opt_a, opt_b, opt_c, votes_a, votes_b, votes_c, expires_at = row
        return jsonify({
            "active": True,
            "vote_id": vote_id,
            "option_a": opt_a, "option_b": opt_b, "option_c": opt_c,
            "votes_a": votes_a, "votes_b": votes_b, "votes_c": votes_c,
            "expires_at": expires_at,
            "server_time": time.time()
        }), 200
    finally:
        conn.close()


@app.route('/api/vote/cast', methods=['POST'])
def cast_vote():
    data = request.get_json()
    u_id = data.get('user_id', '')
    vote_id = data.get('vote_id')
    choice = data.get('choice', '').lower()
    amount = float(data.get('amount', 0))

    if not u_id or not vote_id or choice not in ('a', 'b', 'c') or amount <= 0:
        return jsonify({"error": "Invalid request"}), 400

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    try:
        # Check vote is still active
        cursor.execute("SELECT expires_at FROM corporate_votes WHERE id = ?", (vote_id,))
        row = cursor.fetchone()
        if not row or row[0] < time.time():
            return jsonify({"error": "Vote has expired or does not exist"}), 400

        # Check user has enough balance
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
        balance_row = cursor.fetchone()
        if not balance_row or balance_row[0] < amount:
            return jsonify({"error": "Insufficient funds"}), 400

        # Deduct from user balance
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, u_id))

        # Add amount to the chosen option's pool
        col = {"a": "votes_a", "b": "votes_b", "c": "votes_c"}[choice]
        cursor.execute(f"UPDATE corporate_votes SET {col} = {col} + ? WHERE id = ?", (amount, vote_id))

        # Record the contribution (no uniqueness constraint — same user can top up)
        cursor.execute("""
            INSERT INTO vote_records (vote_id, user_id, choice, amount)
            VALUES (?, ?, ?, ?)
        """, (vote_id, u_id, choice, amount))

        conn.commit()

        # Return updated vote state so frontend can refresh immediately
        cursor.execute("""
            SELECT option_a, option_b, option_c, votes_a, votes_b, votes_c, expires_at
            FROM corporate_votes WHERE id = ?
        """, (vote_id,))
        v = cursor.fetchone()
        return jsonify({
            "message": "Vote cast successfully",
            "vote_id": vote_id,
            "option_a": v[0], "option_b": v[1], "option_c": v[2],
            "votes_a": v[3], "votes_b": v[4], "votes_c": v[5],
            "expires_at": v[6],
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# --- HELPER ---

def add_log(cursor: sqlite3.Cursor, log_msg: str, u_id: str, log_type: str):
    cursor.execute("""
        INSERT INTO activity_logs (user_id, action_type, message) 
        VALUES (?, ?, ?)
    """, (u_id, log_type, log_msg))


# --- MARKET LOGIC ---

def fetch_market_state():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

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
        all_histories[name] = [
            {"time": time.strftime('%H:%M:%S', time.localtime(r[1])), "price": round(r[0], 2)}
            for r in reversed(hist_rows)
        ]

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


def get_price_momentum(cursor: sqlite3.Cursor, resource_name: str, window: int = MOMENTUM_WINDOW) -> float:
    """
    FIX 2: Rolling momentum window.
    Returns the average price *change* over the last N ticks.
    Previously the code only used last_change (1 tick), which caused
    jittery, erratic charts. Averaging over 5 ticks smooths trends out.
    """
    cursor.execute("""
        SELECT price FROM price_history
        WHERE resource_name = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (resource_name, window + 1))
    rows = cursor.fetchall()

    if len(rows) < 2:
        return 0.0

    prices = [r[0] for r in rows]
    changes = [prices[i] - prices[i + 1] for i in range(len(prices) - 1)]
    return sum(changes) / len(changes)


def calculate_market_price(current_price, base_price, supply, demand, momentum, rarity_index):
    """
    FIX 1 + FIX 2: Elastic Equilibrium Model — improved.

    Changes vs original:
    - `momentum` is now a rolling average (5 ticks) instead of last_change (1 tick)
    - Price cap changed: instead of hard-capping the ratio at 50x, we cap the
      *final price* at 20x base_price. This allows rare items to be volatile
      but prevents Diamond from hitting astronomic numbers during low-pop play.
    - Noise now scales with rarity so common goods are stable, rare goods are spicy.
    """
    # 1. Non-linear target price
    elasticity = 0.35 + (rarity_index * 0.15)
    ratio = max(demand, 1) / max(supply, 1)
    adjusted_ratio = math.pow(ratio, elasticity)

    # Cap the ratio — not the final price — to keep math sane
    adjusted_ratio = min(adjusted_ratio, 15.0)
    target_price = base_price * adjusted_ratio

    # FIX: Absolute price ceiling at 20x base to prevent hyperinflation
    # in low-population games where nobody can push prices back down
    price_ceiling = base_price * 20.0
    target_price = min(target_price, price_ceiling)

    # 2. Gap and reaction speed
    diff = target_price - current_price
    distance_ratio = abs(diff) / max(current_price, 1)
    reaction_speed = 0.03 * (1 + distance_ratio)
    reaction_speed = min(reaction_speed, 0.15)
    movement = diff * reaction_speed

    # 3. Smoothed momentum (rolling average, dampened near target)
    momentum_dampener = min(abs(diff) / base_price, 1.0)
    momentum_force = momentum * 0.1 * momentum_dampener

    # FIX: Noise scales with rarity so Wood is stable and Diamond is spicy
    # Common (rarity 1) -> ±0.5% noise
    # Legendary (rarity 5) -> ±2.5% noise
    noise_scale = rarity_index * 0.005
    noise = random.uniform(-noise_scale, noise_scale) * base_price

    total_change = movement + momentum_force + noise

    # 4. Volatility cap (rarer = looser cap, more volatile)
    volatility_limit = 0.08 + (rarity_index * 0.02)
    max_move = current_price * volatility_limit
    total_change = max(min(total_change, max_move), -max_move)

    new_price = current_price + total_change

    # 5. Safety floor: never below 10% of base
    floor_price = base_price * 0.1
    return max(new_price, floor_price), total_change


def run_tick():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    now = time.time()

    cursor.execute("SELECT name, price, last_change, supply, demand, base_price, rarity_index FROM resources")
    all_resources = cursor.fetchall()

    for name, price, last_change, supply, demand, base_price, rarity_index in all_resources:
        # FIX 2: Use rolling momentum instead of single last_change
        momentum = get_price_momentum(cursor, name)

        new_price, change = calculate_market_price(
            price, base_price, supply, demand, momentum, rarity_index
        )

        # FIX 1: Per-rarity equilibrium — each resource decays toward its
        # own natural level rather than a single EQUILIBRIUM_LEVEL = 200
        equilibrium = EQUILIBRIUM_BY_RARITY.get(rarity_index, 5000)
        new_supply = supply + (equilibrium - supply) * MARKET_DECAY_RATE
        new_demand = demand + (equilibrium - demand) * MARKET_DECAY_RATE

        cursor.execute("""
            UPDATE resources 
            SET price = ?, last_change = ?, supply = ?, demand = ?, last_updated = ?
            WHERE name = ?
        """, (new_price, change, new_supply, new_demand, now, name))

        cursor.execute("INSERT INTO price_history VALUES (?, ?, ?)", (name, new_price, now))

        print(f"[{name}] ${new_price:.2f} | S:{int(new_supply)} D:{int(new_demand)} | EQ:{equilibrium}")

    cursor.execute("DELETE FROM price_history WHERE timestamp < ?", (now - HISTORY_RETAIN_TIME,))

    handle_workers_done(cursor)

    conn.commit()
    conn.close()


def get_user_logs(user_id, limit=15):
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message, datetime(timestamp, 'localtime'), action_type
        FROM activity_logs 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (user_id, limit))
    raw_logs = cursor.fetchall()
    conn.close()

    color_map = {
        'BUY': 'text-emerald-400',
        'SELL': 'text-blue-400',
        'SABOTAGE': 'text-orange-400',
        'ERROR': 'text-red-500',
        'SYSTEM': 'text-slate-500',
        'HQ': 'text-amber-400',
        'FAIL': 'text-red-600',
        'KILLED': 'text-red-600',
        'VOTE': 'text-purple-400',
    }

    formatted_logs = []
    for message, ts_string, action_type in raw_logs:
        dt_obj = datetime.strptime(ts_string, '%Y-%m-%d %H:%M:%S')
        formatted_logs.append({
            "text": f"[{dt_obj.strftime('%H:%M:%S')}] {message}",
            "color": color_map.get(action_type, 'text-white')
        })
    return formatted_logs


# --- WORKER LOGIC ---

def handle_workers_done(cursor: sqlite3.Cursor):
    cursor.execute("""
        UPDATE users 
        SET workforce_deployment_length = workforce_deployment_length - 1 
        WHERE workforce_deployment_length > 0
    """)

    cursor.execute("""
        SELECT user_id, workers_extraction, workers_rnd, workers_espionage, espionage_taget, max_workforce
        FROM users 
        WHERE workforce_deployment_length = 0 
        AND (workers_extraction + workers_rnd + workers_espionage) > 0
    """)
    finished_users = cursor.fetchall()

    for user_data in finished_users:
        u_id = user_data[0]
        handle_workers_reward(cursor, [user_data])
        cursor.execute("""
            UPDATE users SET 
                workers_extraction = 0, 
                workers_rnd = 0, 
                workers_espionage = 0,
                espionage_taget = 'RANDOM'
            WHERE user_id = ?
        """, (u_id,))

    print(f"Tick: Processed {len(finished_users)} completed deployments.")


def handle_workers_reward(cursor: sqlite3.Cursor, active_users: list):
    global RECRUITING_CHANCE

    cursor.execute("SELECT name, rarity_index FROM resources")
    rarity_map = {row[0]: row[1] for row in cursor.fetchall()}

    for u_id, ext_count, rnd_count, sabo_count, espionage_taget, max_wf in active_users:
        # Split R&D workers between enhancers and recruiters
        rnd_splitter = random.randint(0, rnd_count)
        floor = int(rnd_count / 4)
        ceiling = int(rnd_count / 4 * 3)
        rnd_splitter = max(floor, min(rnd_splitter, ceiling))
        enhancers = min(rnd_splitter, ext_count)
        recruiters = rnd_count - enhancers

        print(f"User {u_id}: {enhancers} enhancers, {recruiters} recruiters")

        # --- RECRUITING ---
        overall_recruited = 0
        for _ in range(recruiters):
            if random.uniform(0, 100) <= RECRUITING_CHANCE:
                overall_recruited += 1

        # --- EXTRACTION ---
        # FIX 3: Diminishing returns on large extraction armies.
        # Without this, sending 100 workers is strictly 100x better than sending 1.
        # Now, effective_extractors grows sub-linearly: doubling workers gives ~1.4x output.
        # The sqrt scale means small teams are efficient, large teams face coordination overhead.
        if ext_count > 0:
            effective_extractors = math.sqrt(ext_count) * math.sqrt(ext_count + 1) / 2
            effective_extractors = max(1, int(effective_extractors))
        else:
            effective_extractors = 0

        overall_rewards = extraction_reward(rarity_map, enhancers, max_wf, u_id, effective_extractors)

        # --- SABOTAGE ---
        if sabo_count > 0:
            if (espionage_taget != "RANDOM"):
                cursor.execute("SELECT user_id FROM users WHERE user_id == ? LIMIT 1", (espionage_taget,))
            else:
                cursor.execute("SELECT user_id FROM users WHERE user_id != ? ORDER BY RANDOM() LIMIT 1", (u_id,))
            
            target_res = cursor.fetchone()

            if target_res:
                target_id = target_res[0]
                rewards = sabotage_reward(cursor, u_id, target_id, sabo_count)

                if rewards["failed"]:
                    count = rewards['user_eliminated']
                    msg = f"Sabotage failed — {count} of your worker{'s were' if count != 1 else ' was'} killed."
                else:
                    parts = []

                    if rewards["target_eliminated"] > 0:
                        count = rewards['target_eliminated']
                        parts.append(f"{count} worker{'s' if count != 1 else ''} neutralized")

                    if rewards["money_stolen"] > 0:
                        parts.append(f"${rewards['money_stolen']:,.2f} stolen")

                    if rewards["materials_stolen"]:
                        summary = ", ".join(f"{amt}x {res}" for res, amt in rewards["materials_stolen"].items())
                        parts.append(f"{summary} stolen")

                    if parts:
                        msg = f"Sabotage success — {', '.join(parts)}."
                    else:
                        msg = "Sabotage mission returned empty handed."

                add_log(cursor, msg, u_id, 'FAIL' if rewards["failed"] else 'SABOTAGE')

        # --- APPLY RESULTS ---
        if overall_recruited > 0:
            cursor.execute("""
                UPDATE users SET max_workforce = max_workforce + ? WHERE user_id = ?
            """, (overall_recruited, u_id))
            add_log(cursor, f"R&D recruited {overall_recruited} new worker{'s' if overall_recruited != 1 else ''}.", u_id, "HQ")

        if overall_rewards:
            for res_name, amount in overall_rewards.items():
                cursor.execute("""
                    INSERT INTO inventory (user_id, resource_name, amount) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, resource_name) DO UPDATE SET amount = amount + ?
                """, (u_id, res_name, amount, amount))
                cursor.execute("UPDATE resources SET supply = supply + ? WHERE name = ?", (amount, res_name))

            summary = ", ".join([f"{amt}x {name}" for name, amt in overall_rewards.items()])
            print(f"Harvest for {u_id}: {summary}")
            add_log(cursor, f"Extraction harvested: {summary}.", u_id, "HQ")
        else:
            print(f"User {u_id} extraction came up empty.")


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

        resource_to_mine = random.choices(resources, weights=weights, k=1)[0]
        rarity = rarity_map[resource_to_mine]

        base_potential = 25 + (rnd_ratio * 75)
        stability_factor = 0.6
        dampened_rarity = math.pow(rarity, stability_factor)
        final_success_threshold = max(base_potential / dampened_rarity, 5.0)

        roll = random.uniform(0, 100)
        if roll <= final_success_threshold:
            overall_rewards[resource_to_mine] = overall_rewards.get(resource_to_mine, 0) + 1
        # else: no reward, worker came up empty

    return overall_rewards


def sabotage_reward(cursor, user_id, target_id, sabo_count):
    global SABOTAGE_MAX_DETECTION_SEND, SABOTAGE_MAX_DETECTION_PRECENT, SABOTAGE_CHANCE_OF_DEATH

    ACTIONS = ["steal_materials", "steal_money", "neutralize"]

    # Detection risk scales with how many agents you send
    precent_for_caught = min(
        (sabo_count / SABOTAGE_MAX_DETECTION_SEND) * SABOTAGE_MAX_DETECTION_PRECENT,
        SABOTAGE_MAX_DETECTION_PRECENT
    )

    # Success chance scales with squad size, capped at 25%
    base_success = 5.0
    bonus_per_agent = 2.0
    success_chance = min(base_success + (sabo_count * bonus_per_agent), 25.0)

    print(f"Sabotage: catch={precent_for_caught:.1f}% success={success_chance:.1f}%")

    user_eliminated_total = 0
    target_eliminated_total = 0
    materials_stolen = {}   # { resource_name: amount }
    money_stolen = 0.0
    failed = False

    # --- PHASE 1: Detection check (only risks death if risk exceeds the death threshold) ---
    if precent_for_caught > SABOTAGE_CHANCE_OF_DEATH:
        for _ in range(sabo_count):
            if random.uniform(0, 100) <= precent_for_caught:
                user_eliminated_total += 1
                failed = True

    # --- PHASE 2: Each surviving agent independently picks and attempts an action ---
    if not failed:
        surviving_agents = sabo_count - user_eliminated_total

        # Fetch target's inventory for steal_materials rolls
        cursor.execute("""
            SELECT resource_name, amount FROM inventory
            WHERE user_id = ? AND amount > 0
        """, (target_id,))
        target_inventory = {row[0]: row[1] for row in cursor.fetchall()}

        # Fetch target's balance for steal_money rolls
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
        target_balance_row = cursor.fetchone()
        target_balance = target_balance_row[0] if target_balance_row else 0.0

        for _ in range(surviving_agents):
            if random.uniform(0, 100) > success_chance:
                continue  # This agent failed silently

            action = random.choice(ACTIONS)

            if action == "neutralize":
                target_eliminated_total += 1

            elif action == "steal_money":
                # Steal between 1% and 5% of target's current balance per agent
                if target_balance > 0:
                    stolen = target_balance * random.uniform(0.01, 0.05)
                    stolen = round(stolen, 2)
                    money_stolen += stolen
                    target_balance -= stolen  # Track locally so agents don't over-steal

            elif action == "steal_materials":
                # Pick a random resource the target actually owns
                available = [(r, a) for r, a in target_inventory.items() if a > 0]
                if available:
                    resource, amount = random.choice(available)
                    # Steal 1 unit per agent (keeps it meaningful but not devastating)
                    materials_stolen[resource] = materials_stolen.get(resource, 0) + 1
                    target_inventory[resource] = max(0, target_inventory[resource] - 1)

    # --- PHASE 3: Apply all results to the database ---

    if user_eliminated_total > 0:
        cursor.execute("""
            UPDATE users SET max_workforce = MAX(5, max_workforce - ?) WHERE user_id = ?
        """, (user_eliminated_total, user_id))
        print(f"User {user_id} lost {user_eliminated_total} agents.")

    if target_eliminated_total > 0:
        cursor.execute("""
            UPDATE users SET max_workforce = MAX(5, max_workforce - ?) WHERE user_id = ?
        """, (target_eliminated_total, target_id))
        add_log(cursor, f"User {user_id} eliminated {target_eliminated_total} of your workers.", target_id, "KILLED")

    if money_stolen > 0:
        cursor.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (money_stolen, target_id))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (money_stolen, user_id))
        add_log(cursor, f"User {user_id} stole ${money_stolen:,.2f} from you.", target_id, "KILLED")
        print(f"User {user_id} stole ${money_stolen:,.2f} from {target_id}.")

    if materials_stolen:
        for resource, amount in materials_stolen.items():
            # Remove from target
            cursor.execute("""
                UPDATE inventory SET amount = MAX(0, amount - ?)
                WHERE user_id = ? AND resource_name = ?
            """, (amount, target_id, resource))
            # Add to attacker
            cursor.execute("""
                INSERT INTO inventory (user_id, resource_name, amount) VALUES (?, ?, ?)
                ON CONFLICT(user_id, resource_name) DO UPDATE SET amount = amount + ?
            """, (user_id, resource, amount, amount))
        summary = ", ".join(f"{amt}x {res}" for res, amt in materials_stolen.items())
        add_log(cursor, f"User {user_id} stole {summary} from you.", target_id, "KILLED")
        print(f"User {user_id} stole {summary} from {target_id}.")

    return {
        "user_eliminated": user_eliminated_total,
        "target_eliminated": target_eliminated_total,
        "money_stolen": money_stolen,
        "materials_stolen": materials_stolen,
        "failed": failed,
    }


# --- CORPORATE VOTE LOGIC ---

def create_new_vote(cursor: sqlite3.Cursor):
    options = random.sample(CORPORATE_CHANGES_OPTIONS, 3)

    cursor.execute("SELECT name FROM resources ORDER BY RANDOM()")
    all_resources = [row[0] for row in cursor.fetchall()]
    resource_pool = iter(all_resources)

    resolved_options = []
    for opt in options:
        import re
        placeholders = re.findall(r'\$element_name\d*', opt)
        for placeholder in placeholders:
            resource = next(resource_pool, "Unknown")
            opt = opt.replace(placeholder, resource, 1)
        resolved_options.append(opt)

    # Align expiry to the next clock boundary so the vote loop resolves it
    # exactly on time instead of one full interval late
    now = time.time()
    expires_at = now + (VOTE_INTERVAL - (now % VOTE_INTERVAL))

    cursor.execute("""
        INSERT INTO corporate_votes (option_a, option_b, option_c, votes_a, votes_b, votes_c, expires_at)
        VALUES (?, ?, ?, 0, 0, 0, ?)
    """, (resolved_options[0], resolved_options[1], resolved_options[2], expires_at))
    vote_id = cursor.lastrowid
    print(f"[VOTE] New corporate vote #{vote_id} created. Expires at {time.strftime('%H:%M:%S', time.localtime(expires_at))}")
    print(f"  A: {resolved_options[0]}\n  B: {resolved_options[1]}\n  C: {resolved_options[2]}")
    return vote_id


def apply_vote_result(cursor: sqlite3.Cursor, vote_id: int):
    global CURRENT_TAX, RECRUITING_CHANCE, SABOTAGE_MAX_DETECTION_PRECENT
    global SABOTAGE_MAX_DETECTION_SEND, SABOTAGE_CHANCE_OF_DEATH, WORKFORCE_RETURN_TIME
    global SHOW_INVENTORY_IN_LEADERBOARD

    cursor.execute("""
        SELECT option_a, option_b, option_c, votes_a, votes_b, votes_c
        FROM corporate_votes WHERE id = ?
    """, (vote_id,))
    row = cursor.fetchone()
    if not row:
        return

    opt_a, opt_b, opt_c, votes_a, votes_b, votes_c = row

    winner = max(
        [("a", opt_a, votes_a), ("b", opt_b, votes_b), ("c", opt_c, votes_c)],
        key=lambda x: (x[2], random.random())
    )[1]

    print(f"[VOTE] Vote #{vote_id} resolved. Winner: '{winner}'")

    # Reset leaderboard visibility every cycle — only Public Report turns it on
    SHOW_INVENTORY_IN_LEADERBOARD = 1

    if "Tax Policy | +0.05" in winner:
        CURRENT_TAX = min(CURRENT_TAX + 0.05, 0.3)
    elif "Tax Policy | -0.05" in winner:
        CURRENT_TAX = max(CURRENT_TAX - 0.05, 0.03)
    elif "Tax Policy | +0.07" in winner:
        CURRENT_TAX = min(CURRENT_TAX + 0.07, 0.3)
    elif "Tax Policy | -0.07" in winner:
        CURRENT_TAX = max(CURRENT_TAX - 0.07, 0.03)
    elif "Tax Policy | +0.02" in winner:
        CURRENT_TAX = min(CURRENT_TAX + 0.02, 0.3)
    elif "Tax Policy | -0.02" in winner:
        CURRENT_TAX = max(CURRENT_TAX - 0.02, 0.03)

    elif "Unemployment" in winner:
        RECRUITING_CHANCE = min(RECRUITING_CHANCE + 5, 50)
    elif "Tough Market" in winner:
        RECRUITING_CHANCE = max(RECRUITING_CHANCE - 5, 5)

    elif "Global Security Crisis" in winner and "success chance" in winner:
        SABOTAGE_MAX_DETECTION_PRECENT = max(SABOTAGE_MAX_DETECTION_PRECENT - 10, 5)
    elif "Global Security Upgrades" in winner and "success chance" in winner:
        SABOTAGE_MAX_DETECTION_PRECENT = min(SABOTAGE_MAX_DETECTION_PRECENT + 10, 80)
    elif "Global Security Crisis" in winner and "death" in winner:
        SABOTAGE_CHANCE_OF_DEATH = max(SABOTAGE_CHANCE_OF_DEATH - 5, 5)
    elif "Global Security Upgrades" in winner and "death" in winner:
        SABOTAGE_CHANCE_OF_DEATH = min(SABOTAGE_CHANCE_OF_DEATH + 5, 60)

    elif "Area Contaminated" in winner:
        WORKFORCE_RETURN_TIME = min(WORKFORCE_RETURN_TIME + 1, 5)
    elif "New Area Found" in winner:
        WORKFORCE_RETURN_TIME = max(WORKFORCE_RETURN_TIME - 1, 1)

    elif "Public Report" in winner:
        SHOW_INVENTORY_IN_LEADERBOARD = 10

    elif "increased in value" in winner or "decreased in value" in winner or \
         "increased in demand" in winner or "decreased in demand" in winner:
        cursor.execute("SELECT name, base_price FROM resources")
        all_res = {row[0]: row[1] for row in cursor.fetchall()}
        res_names = [name for name in all_res if name in winner]
        for res_name in res_names:
            base_price = all_res[res_name]
            if "increased in value" in winner:
                update_resource_base_price(cursor, res_name, base_price * random.uniform(0.7, 1.3))
            elif "decreased in value" in winner:
                update_resource_base_price(cursor, res_name, base_price * random.uniform(0.7, 1.3))
            elif "increased in demand" in winner:
                update_resource_demand(cursor, res_name, +random.uniform(0.5, 1.0))
            elif "decreased in demand" in winner:
                update_resource_demand(cursor, res_name, -random.uniform(0.5, 1.0))

    # Broadcast result to all users
    cursor.execute("SELECT user_id FROM users")
    for (uid,) in cursor.fetchall():
        add_log(cursor, f"[Corporate] New policy enacted: {winner}", uid, "SYSTEM")

    print(f"[VOTE] Effect applied. TAX={CURRENT_TAX:.4f} RECRUITING={RECRUITING_CHANCE}")


# --- RESOURCE HELPERS ---

def update_resource_base_price(cursor, resource_name, new_base_price):
    try:
        cursor.execute("""
            UPDATE resources 
            SET base_price = ?,
                price = ?,
                last_change = 0
            WHERE name = ?
        """, (new_base_price, new_base_price, resource_name.capitalize()))
        print(f"Base price for {resource_name} set to {new_base_price:.2f}")
        return True
    except Exception as e:
        print(f"Error updating base price: {e}")
        return False



def update_resource_demand(cursor: sqlite3.Cursor, resource_name: str, direction: float):
    try:
        cursor.execute("SELECT rarity_index FROM resources WHERE name = ?", (resource_name.capitalize(),))
        row = cursor.fetchone()
        if not row:
            return False

        rarity = row[0]
        equilibrium = EQUILIBRIUM_BY_RARITY[rarity]

        # Subtle: 5% to 15% of equilibrium instead of 30-50%
        # This gives a noticeable but not market-breaking push
        # At MARKET_DECAY_RATE=0.05 this still takes ~5-8 ticks to fully decay
        impact = equilibrium * random.uniform(0.05, 0.15) * direction

        floor   = equilibrium * 0.25
        ceiling = equilibrium * 2.00

        cursor.execute("""
            UPDATE resources 
            SET demand = MAX(?, MIN(?, demand + ?))
            WHERE name = ?
        """, (floor, ceiling, impact, resource_name.capitalize()))

        print(f"Demand shock on {resource_name}: {impact:+.0f} (eq={equilibrium})")
        return True
    except Exception as e:
        print(f"Error updating demand: {e}")
        return False



# --- BACKGROUND LOOPS ---

def market_loop():
    while True:
        now = time.time()
        time.sleep(TICK_INTERVAL - (now % TICK_INTERVAL))
        run_tick()


def corporate_vote_loop():
    while True:
        now = time.time()
        time.sleep(VOTE_INTERVAL - (now % VOTE_INTERVAL))

        conn = sqlite3.connect('market.db')
        cursor = conn.cursor()
        try:
            # 1. Resolve expired votes
            cursor.execute("""
                SELECT id FROM corporate_votes
                WHERE expires_at <= ? AND resolved = 0
                ORDER BY expires_at ASC
            """, (time.time(),))
            expired = cursor.fetchall()

            for (vote_id,) in expired:
                apply_vote_result(cursor, vote_id)
                cursor.execute("UPDATE corporate_votes SET resolved = 1 WHERE id = ?", (vote_id,))

            # 2. Only create a new vote if there isn't already an active one
            # This prevents double-creation when startup already made one
            cursor.execute("""
                SELECT id FROM corporate_votes 
                WHERE expires_at > ? AND resolved = 0 LIMIT 1
            """, (time.time(),))
            if not cursor.fetchone():
                create_new_vote(cursor)

            conn.commit()
        except Exception as e:
            print(f"[VOTE LOOP ERROR] {e}")
        finally:
            conn.close()


# --- SCHEMA HELPERS ---

def split_schema_lines(schema_definition):
    lines = []
    current_line = []
    paren_depth = 0
    for char in schema_definition:
        if char == '(':
            paren_depth += 1
            current_line.append(char)
        elif char == ')':
            paren_depth -= 1
            current_line.append(char)
        elif char == ',' and paren_depth == 0:
            lines.append(''.join(current_line).strip())
            current_line = []
        else:
            current_line.append(char)
    if current_line:
        lines.append(''.join(current_line).strip())
    return lines


def sync_table_schema(conn, table_name, schema_definition):
    cursor = conn.cursor()
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_definition})")

    cursor.execute(f"PRAGMA table_info({table_name})")
    db_columns = {row[1] for row in cursor.fetchall()}
    db_columns_lower = {col.lower() for col in db_columns}

    expected_columns = {}
    for line in split_schema_lines(schema_definition):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if not parts:
            continue
        raw_name = parts[0].replace('"', '').replace('`', '').replace('(', '').replace(')', '')
        if raw_name.upper() in ("PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK"):
            continue
        col_name = parts[0].replace('"', '').replace('`', '')
        col_def = " ".join(parts[1:])
        expected_columns[col_name.lower()] = {"name": col_name, "definition": col_def}

    expected_columns_lower = set(expected_columns.keys())

    for col_lower in expected_columns_lower - db_columns_lower:
        col = expected_columns[col_lower]["name"]
        col_def = expected_columns[col_lower]["definition"]
        try:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_def}")
            print(f"Migration: Added column '{col}' to '{table_name}'")
        except sqlite3.OperationalError as e:
            print(f"Migration Error adding '{col}': {e}")

    for col_lower in db_columns_lower - expected_columns_lower:
        orig_col = next(col for col in db_columns if col.lower() == col_lower)
        try:
            conn.execute(f"ALTER TABLE {table_name} DROP COLUMN {orig_col}")
            print(f"Migration: Dropped column '{orig_col}' from '{table_name}'")
        except sqlite3.OperationalError as e:
            print(f"Migration Error dropping '{orig_col}': {e}")


# --- INITIALIZATION ---

if __name__ == "__main__":
    conn = sqlite3.connect('market.db')

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
        espionage_taget TEXT,
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
        action_type TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    """

    SYSTEM_SCHEMA = """
        id INTEGER PRIMARY KEY,
        current_vote_length INTEGER DEFAULT 30
    """

    CORPORATE_VOTES_SCHEMA = """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        votes_a REAL DEFAULT 0,
        votes_b REAL DEFAULT 0,
        votes_c REAL DEFAULT 0,
        expires_at REAL,
        resolved INTEGER DEFAULT 0
    """

    VOTE_RECORDS_SCHEMA = """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vote_id INTEGER,
        user_id TEXT,
        choice TEXT,
        amount REAL DEFAULT 0,
        FOREIGN KEY(vote_id) REFERENCES corporate_votes(id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    """

    sync_table_schema(conn, "resources", RESOURCES_SCHEMA)
    sync_table_schema(conn, "users", USERS_SCHEMA)
    sync_table_schema(conn, "inventory", INVENTORY_SCHEMA)
    sync_table_schema(conn, "activity_logs", ACTIVITY_LOGS)
    sync_table_schema(conn, "system", SYSTEM_SCHEMA)
    sync_table_schema(conn, "corporate_votes", CORPORATE_VOTES_SCHEMA)
    sync_table_schema(conn, "vote_records", VOTE_RECORDS_SCHEMA)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            resource_name TEXT, price REAL, timestamp REAL
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO system (id, current_vote_length) VALUES (1, ?)
    """, (COORPRATE_VOTE_LENGTH,))

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

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM corporate_votes WHERE expires_at > ? AND resolved = 0 LIMIT 1", (time.time(),))
    if not cursor.fetchone():
        create_new_vote(cursor)
        print("[INIT] No active vote found — created initial vote.")


    conn.commit()
    conn.close()

    threading.Thread(target=market_loop, daemon=True).start()
    threading.Thread(target=corporate_vote_loop, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)