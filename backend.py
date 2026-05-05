import math
import random
import time
import threading
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import ArrayUnion, Increment, FieldFilter

# ── FIREBASE INIT ─────────────────────────────────────────────────────────────
cred = credentials.Certificate(r"C:\Users\danmi\Desktop\site\serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ── FIRESTORE COLLECTION REFS ─────────────────────────────────────────────────
# Centralised so changing a collection name only needs one edit.
COL_RESOURCES      = db.collection("resources")
COL_USERS          = db.collection("users")
COL_INVENTORY      = db.collection("inventory")       # flat: doc-id = uid__resource
COL_PRICE_HISTORY  = db.collection("price_history")
COL_ACTIVITY_LOGS  = db.collection("activity_logs")
COL_CORP_VOTES     = db.collection("corporate_votes")
COL_VOTE_RECORDS   = db.collection("vote_records")
COL_SYSTEM         = db.collection("system")

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
TICK_INTERVAL   = 60.0
VOTE_INTERVAL   = 60.0 * 60

MARKET_DECAY_RATE              = 0.05
HISTORY_RETAIN_TIME            = 1800
CURRENT_TAX                    = 0.05
RECRUITING_CHANCE              = 15
SABOTAGE_MAX_DETECTION_PRECENT = 40
SABOTAGE_MAX_DETECTION_SEND    = 10
SABOTAGE_CHANCE_OF_DEATH       = 20
WORKFORCE_RETURN_TIME          = 1
SHOW_INVENTORY_IN_LEADERBOARD  = 0

MATERIALS = [
    #  Name    | Price | Change | Supply | Demand | Updated |  Base   | Rarity
    ('Wood'    , 20.0,    0.0,  60000, 60000, 0,    20.0,  1),
    ('Iron'    , 100.0,   0.0,  30000, 30000, 0,   100.0,  2),
    ('Copper'  , 300.0,   0.0,  30000, 30000, 0,   300.0,  2),
    ('Gold'    , 500.0,   0.0,  12000, 12000, 0,   500.0,  3),
    ('Oil'     , 700.0,   0.0,   5000,  5000, 0,   700.0,  4),
    ('Lithium' , 1200.0,  0.0,   5000,  5000, 0,  1200.0,  4),
    ('Silicon' , 2500.0,  0.0,   5000,  5000, 0,  2500.0,  4),
    ('Diamond' , 20000.0, 0.0,    800,   800, 0, 20000.0,  5),
]

EQUILIBRIUM_BY_RARITY = {1: 60000, 2: 30000, 3: 12000, 4: 5000, 5: 800}
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


# ═════════════════════════════════════════════════════════════════════════════
#  FIRESTORE HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _inv_doc_id(user_id: str, resource_name: str) -> str:
    """Deterministic doc-id for the flat inventory collection."""
    return f"{user_id}__{resource_name}"


def _get_user(user_id: str) -> dict | None:
    doc = COL_USERS.document(user_id).get()
    return doc.to_dict() if doc.exists else None


def _get_resource(name: str) -> dict | None:
    doc = COL_RESOURCES.document(name).get()
    return doc.to_dict() if doc.exists else None


def _get_inventory(user_id: str) -> dict:
    """Returns {resource_name: amount} for a user (only amounts > 0)."""
    docs = COL_INVENTORY.where(filter=FieldFilter("user_id", "==", user_id)).stream()
    return {d.to_dict()["resource_name"]: d.to_dict()["amount"]
            for d in docs if d.to_dict().get("amount", 0) > 0}


def _get_inv_amount(user_id: str, resource_name: str) -> int:
    doc = COL_INVENTORY.document(_inv_doc_id(user_id, resource_name)).get()
    return doc.to_dict().get("amount", 0) if doc.exists else 0


def _set_inv_amount(batch, user_id: str, resource_name: str, delta: int):
    """Increment (positive) or decrement (negative) inventory inside a batch."""
    ref = COL_INVENTORY.document(_inv_doc_id(user_id, resource_name))
    batch.set(ref, {
        "user_id": user_id,
        "resource_name": resource_name,
        "amount": Increment(delta),
    }, merge=True)


def add_log(user_id: str, log_msg: str, log_type: str):
    COL_ACTIVITY_LOGS.add({
        "user_id": user_id,
        "action_type": log_type,
        "message": log_msg,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })


def get_user_logs(user_id: str, limit: int = 15) -> list:
    color_map = {
        'BUY': 'text-emerald-400', 'SELL': 'text-blue-400',
        'SABOTAGE': 'text-orange-400', 'ERROR': 'text-red-500',
        'SYSTEM': 'text-slate-500', 'HQ': 'text-amber-400',
        'FAIL': 'text-red-600', 'KILLED': 'text-red-600',
        'VOTE': 'text-purple-400',
    }
    docs = (COL_ACTIVITY_LOGS
            .where(filter=FieldFilter("user_id", "==", user_id))
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream())

    logs = []
    for d in docs:
        data = d.to_dict()
        ts = data.get("timestamp")
        if ts:
            # Firestore timestamps are datetime objects
            try:
                formatted_time = ts.strftime('%H:%M:%S')
            except Exception:
                formatted_time = "??:??:??"
        else:
            formatted_time = "??:??:??"
        logs.append({
            "text": f"[{formatted_time}] {data.get('message', '')}",
            "color": color_map.get(data.get("action_type", ""), "text-white"),
        })
    return logs


# ═════════════════════════════════════════════════════════════════════════════
#  WEB ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/get_user/<u_id>')
def get_game_state(u_id):
    user = _get_user(u_id)
    if user:
        balance                   = user.get("balance", 0)
        max_total                 = user.get("max_workforce", 0)
        w_ext                     = user.get("workers_extraction", 0)
        w_rnd                     = user.get("workers_rnd", 0)
        w_esp                     = user.get("workers_espionage", 0)
        workforce_deployment_length = user.get("workforce_deployment_length", 0)
    else:
        balance = max_total = w_ext = w_rnd = w_esp = workforce_deployment_length = 0

    inventory = _get_inventory(u_id)

    now        = time.time()
    next_tick  = now + (TICK_INTERVAL - (now % TICK_INTERVAL))
    next_vote  = now + (VOTE_INTERVAL  - (now % VOTE_INTERVAL))

    return jsonify({
        "balance": round(balance, 2),
        "inventory": inventory,
        "max_workforce": max_total,
        "deployed_workers": {"extraction": w_ext, "rnd": w_rnd, "espionage": w_esp},
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
    try:
        # Prices
        prices = {d.id: d.to_dict().get("price", 0) for d in COL_RESOURCES.stream()}

        # All users
        users = [(d.id, d.to_dict()) for d in COL_USERS.stream()]

        # All inventory (one pass)
        inventories: dict[str, dict] = {}
        for d in COL_INVENTORY.stream():
            data = d.to_dict()
            uid  = data["user_id"]
            res  = data["resource_name"]
            amt  = data.get("amount", 0)
            inventories.setdefault(uid, {})[res] = amt

        leaderboard = []
        for uid, udata in users:
            balance  = udata.get("balance", 0)
            user_inv = inventories.get(uid, {})
            inv_val  = sum(prices.get(res, 0) * amt for res, amt in user_inv.items())
            net      = balance + inv_val
            leaderboard.append({
                "user_id": uid,
                "balance": round(balance, 2),
                "inventory_value": round(inv_val, 2),
                "net_worth": round(net, 2),
                "raw_inventory": user_inv,
            })

        leaderboard.sort(key=lambda x: x["net_worth"], reverse=True)

        for i, entry in enumerate(leaderboard):
            rank = i + 1
            entry["rank"] = rank
            if rank <= SHOW_INVENTORY_IN_LEADERBOARD:
                entry["inventory"] = {r: a for r, a in entry["raw_inventory"].items() if a > 0}
            else:
                entry["inventory"] = "Hidden"
            del entry["raw_inventory"]

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/state/prices')
def get_prices():
    return fetch_market_state()


@app.route('/api/deploy_workers/<u_id>', methods=['POST'])
def deploy_workers(u_id):
    data   = request.get_json()
    u_id   = data.get('user_id', '')

    if not u_id:
        return jsonify({"error": "user_id does not exist"}), 400

    try:
        ext    = abs(int(data.get('extraction', 0)))
        rnd    = abs(int(data.get('rnd', 0)))
        esp    = abs(int(data.get('espionage', 0)))
        target = data.get('target', 'RANDOM')
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid worker counts provided"}), 400

    user = _get_user(u_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    max_limit       = user.get("max_workforce", 0)
    total_requested = ext + rnd + esp

    if total_requested > max_limit:
        return jsonify({"error": "Workforce limit exceeded",
                        "requested": total_requested, "max": max_limit}), 400

    COL_USERS.document(u_id).update({
        "workers_extraction":        ext,
        "workers_rnd":               rnd,
        "workers_espionage":         esp,
        "espionage_target":          target,
        "workforce_deployment_length": WORKFORCE_RETURN_TIME,
    })
    add_log(u_id, f"Sent {ext + rnd + esp} workers.", "HQ")

    return jsonify({"message": "Workers reassigned successfully",
                    "distribution": {"extraction": ext, "rnd": rnd, "espionage": esp}}), 200


@app.route('/api/buy', methods=['POST'])
def buy_resource():
    data  = request.get_json()
    u_id  = data.get('user_id', 'user123')
    item  = data.get('item').capitalize()
    qty   = int(data.get('amount', 1))

    try:
        resource = _get_resource(item)
        if not resource:
            return jsonify({"error": "Item not found"}), 400

        old_price  = resource["price"]
        total_cost = old_price * qty

        user = _get_user(u_id)
        if not user or user.get("balance", 0) < total_cost:
            return jsonify({"error": "Insufficient funds"}), 400

        # Atomic-ish batch
        batch = db.batch()

        batch.update(COL_USERS.document(u_id), {"balance": Increment(-total_cost)})
        batch.update(COL_RESOURCES.document(item), {
            "demand": Increment(qty),
            "supply": Increment(-qty),
        })
        _set_inv_amount(batch, u_id, item, qty)

        batch.commit()

        add_log(u_id, f"Purchased {qty}x {item} for ${total_cost:,.2f}.", "BUY")
        print(f"[BUY] {u_id} | {item} x{qty} | ${total_cost:,.2f}")
        return fetch_market_state()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sell', methods=['POST'])
def sell_resource():
    data = request.get_json()
    u_id = data.get('user_id', 'user123')
    item = data.get('item').capitalize()
    qty  = int(data.get('amount', 1))

    try:
        owned = _get_inv_amount(u_id, item)
        if owned < qty:
            return jsonify({"error": "Not enough items"}), 400

        resource = _get_resource(item)
        if not resource:
            return jsonify({"error": "Item not found"}), 400

        current_price = resource["price"]
        gain          = (current_price * qty) * (1.0 - CURRENT_TAX)

        batch = db.batch()
        batch.update(COL_USERS.document(u_id), {"balance": Increment(gain)})
        batch.update(COL_RESOURCES.document(item), {
            "supply": Increment(qty),
            "demand": Increment(-qty),
        })
        _set_inv_amount(batch, u_id, item, -qty)
        batch.commit()

        add_log(u_id, f"Sold {qty}x {item} for ${current_price * qty:,.2f}.", "SELL")
        print(f"[SELL] {u_id} | {item} x{qty} | gained ${gain:,.2f}")
        return fetch_market_state()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── VOTING ROUTES ─────────────────────────────────────────────────────────────

@app.route('/api/vote/current')
def get_current_vote():
    now  = time.time()
    docs = (COL_CORP_VOTES
            .where(filter=FieldFilter("expires_at", ">", now))
            .where(filter=FieldFilter("resolved", "==", False))
            .order_by("expires_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream())

    row = next(docs, None)
    if not row:
        return jsonify({"active": False}), 200

    v = row.to_dict()
    return jsonify({
        "active":     True,
        "vote_id":    row.id,
        "option_a":   v["option_a"],  "option_b": v["option_b"],  "option_c": v["option_c"],
        "votes_a":    v["votes_a"],   "votes_b":  v["votes_b"],   "votes_c":  v["votes_c"],
        "expires_at": v["expires_at"],
        "server_time": now,
    }), 200


@app.route('/api/vote/cast', methods=['POST'])
def cast_vote():
    data    = request.get_json()
    u_id    = data.get('user_id', '')
    vote_id = data.get('vote_id')
    choice  = data.get('choice', '').lower()
    amount  = float(data.get('amount', 0))

    if not u_id or not vote_id or choice not in ('a', 'b', 'c') or amount <= 0:
        return jsonify({"error": "Invalid request"}), 400

    try:
        vote_ref = COL_CORP_VOTES.document(str(vote_id))
        vote_doc = vote_ref.get()
        if not vote_doc.exists or vote_doc.to_dict().get("expires_at", 0) < time.time():
            return jsonify({"error": "Vote has expired or does not exist"}), 400

        user = _get_user(u_id)
        if not user or user.get("balance", 0) < amount:
            return jsonify({"error": "Insufficient funds"}), 400

        col_field = f"votes_{choice}"

        batch = db.batch()
        batch.update(COL_USERS.document(u_id), {"balance": Increment(-amount)})
        batch.update(vote_ref, {col_field: Increment(amount)})
        batch.commit()

        COL_VOTE_RECORDS.add({
            "vote_id": vote_id, "user_id": u_id,
            "choice": choice, "amount": amount,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

        v = vote_ref.get().to_dict()
        return jsonify({
            "message": "Vote cast successfully",
            "vote_id": vote_id,
            "option_a": v["option_a"], "option_b": v["option_b"], "option_c": v["option_c"],
            "votes_a":  v["votes_a"],  "votes_b":  v["votes_b"],  "votes_c":  v["votes_c"],
            "expires_at": v["expires_at"],
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═════════════════════════════════════════════════════════════════════════════
#  FIREBASE LOGIC
# ═════════════════════════════════════════════════════════════════════════════

def sync_configs_from_db():
    """Reads the 'system' document and updates global variables in memory."""
    global CURRENT_TAX, MARKET_DECAY_RATE, RECRUITING_CHANCE
    global SABOTAGE_MAX_DETECTION_PRECENT, SABOTAGE_MAX_DETECTION_SEND
    global SABOTAGE_CHANCE_OF_DEATH, WORKFORCE_RETURN_TIME
    global SHOW_INVENTORY_IN_LEADERBOARD

    try:
        sys_doc = COL_SYSTEM.document("1").get()
        if sys_doc.exists:
            data = sys_doc.to_dict()
            CURRENT_TAX = data.get("current_tax", CURRENT_TAX)
            MARKET_DECAY_RATE = data.get("market_decay_rate", MARKET_DECAY_RATE)
            RECRUITING_CHANCE = data.get("recruit_chance", RECRUITING_CHANCE)
            SABOTAGE_MAX_DETECTION_PRECENT = data.get("sabotage_max_detection_precent", SABOTAGE_MAX_DETECTION_PRECENT)
            SABOTAGE_MAX_DETECTION_SEND = data.get("sabotage_max_detection_send", SABOTAGE_MAX_DETECTION_SEND)
            SABOTAGE_CHANCE_OF_DEATH = data.get("sabotage_chance_of_death", SABOTAGE_CHANCE_OF_DEATH)
            WORKFORCE_RETURN_TIME = data.get("workforce_return_time", WORKFORCE_RETURN_TIME)
            SHOW_INVENTORY_IN_LEADERBOARD = data.get("show_inventory_in_leaderboard", SHOW_INVENTORY_IN_LEADERBOARD)
            # print("[SYSTEM] Configs synced from Firestore.")
    except Exception as e:
        print(f"[SYSTEM ERROR] Could not sync configs: {e}")

# ═════════════════════════════════════════════════════════════════════════════
#  MARKET LOGIC
# ═════════════════════════════════════════════════════════════════════════════

def fetch_market_state():
    market_data    = []
    resource_names = []

    for doc in COL_RESOURCES.stream():
        r = doc.to_dict()
        resource_names.append(r["name"])
        market_data.append({
            "name":       r["name"],
            "price":      round(r["price"], 2),
            "supply":     r["supply"],
            "demand":     r["demand"],
            "base_price": r["base_price"],
        })

    all_histories: dict[str, list] = {}
    cutoff = time.time() - HISTORY_RETAIN_TIME

    for name in resource_names:
        docs = (COL_PRICE_HISTORY
                .where(filter=FieldFilter("resource_name", "==", name))
                .where(filter=FieldFilter("timestamp", ">=", cutoff))
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(30)
                .stream())
        rows = list(docs)
        all_histories[name] = [
            {"time":  time.strftime('%H:%M:%S', time.localtime(d.to_dict()["timestamp"])),
             "price": round(d.to_dict()["price"], 2)}
            for d in reversed(rows)
        ]

    now = time.time()
    return jsonify({
        "market":      market_data,
        "history":     all_histories,
        "next_tick":   now + (TICK_INTERVAL - (now % TICK_INTERVAL)),
        "tick_length": TICK_INTERVAL,
        "server_time": now,
    })


def get_price_momentum(resource_name: str, window: int = MOMENTUM_WINDOW) -> float:
    cutoff = time.time() - HISTORY_RETAIN_TIME
    docs = (COL_PRICE_HISTORY
            .where("resource_name", "==", resource_name)
            .where(filter=FieldFilter("timestamp", ">=", cutoff))
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(window + 1)
            .stream())
    prices = [d.to_dict()["price"] for d in docs]
    if len(prices) < 2:
        return 0.0
    changes = [prices[i] - prices[i + 1] for i in range(len(prices) - 1)]
    return sum(changes) / len(changes)


def calculate_market_price(current_price, base_price, supply, demand, momentum, rarity_index):
    elasticity     = 0.35 + (rarity_index * 0.15)
    ratio          = max(demand, 1) / max(supply, 1)
    adjusted_ratio = min(math.pow(ratio, elasticity), 15.0)
    target_price   = min(base_price * adjusted_ratio, base_price * 20.0)

    diff            = target_price - current_price
    distance_ratio  = abs(diff) / max(current_price, 1)
    reaction_speed  = min(0.03 * (1 + distance_ratio), 0.15)
    movement        = diff * reaction_speed

    momentum_dampener = min(abs(diff) / base_price, 1.0)
    momentum_force    = momentum * 0.1 * momentum_dampener

    noise_scale  = rarity_index * 0.005
    noise        = random.uniform(-noise_scale, noise_scale) * base_price
    total_change = movement + momentum_force + noise

    volatility_limit = 0.08 + (rarity_index * 0.02)
    max_move         = current_price * volatility_limit
    total_change     = max(min(total_change, max_move), -max_move)

    new_price = max(current_price + total_change, base_price * 0.1)
    return new_price, total_change


def run_tick():
    sync_configs_from_db()
    now   = time.time()
    batch = db.batch()

    for doc in COL_RESOURCES.stream():
        r            = doc.to_dict()
        name         = r["name"]
        price        = r["price"]
        supply       = r["supply"]
        demand       = r["demand"]
        base_price   = r["base_price"]
        rarity_index = r["rarity_index"]

        momentum  = get_price_momentum(name)
        new_price, change = calculate_market_price(
            price, base_price, supply, demand, momentum, rarity_index
        )

        equilibrium = EQUILIBRIUM_BY_RARITY.get(rarity_index, 5000)
        new_supply  = supply + (equilibrium - supply) * MARKET_DECAY_RATE
        new_demand  = demand + (equilibrium - demand) * MARKET_DECAY_RATE

        batch.update(COL_RESOURCES.document(name), {
            "price":        new_price,
            "last_change":  change,
            "supply":       new_supply,
            "demand":       new_demand,
            "last_updated": now,
        })

        # Write price history entry
        COL_PRICE_HISTORY.add({
            "resource_name": name,
            "price":         new_price,
            "timestamp":     now,
        })

        print(f"[{name}] ${new_price:.2f} | S:{int(new_supply)} D:{int(new_demand)} | EQ:{equilibrium}")

    batch.commit()

    # Prune old price history
    cutoff = now - HISTORY_RETAIN_TIME
    old_docs = COL_PRICE_HISTORY.where(filter=FieldFilter("timestamp", "<", cutoff)).stream()
    prune_batch = db.batch()
    count = 0
    for d in old_docs:
        prune_batch.delete(d.reference)
        count += 1
        if count % 400 == 0:
            prune_batch.commit()
            prune_batch = db.batch()
    if count % 400 != 0:
        prune_batch.commit()

    handle_workers_done()


# ═════════════════════════════════════════════════════════════════════════════
#  WORKER LOGIC
# ═════════════════════════════════════════════════════════════════════════════

def handle_workers_done():
    # Decrement deployment counter for everyone who has workers out
    active_docs = (COL_USERS
                   .where(filter=FieldFilter("workforce_deployment_length", ">", 0))
                   .stream())

    dec_batch = db.batch()
    for d in active_docs:
        dec_batch.update(d.reference, {
            "workforce_deployment_length": Increment(-1)
        })
    dec_batch.commit()

    # Find users whose counter just hit 0 and have workers deployed
    finished_docs = (COL_USERS
                     .where(filter=FieldFilter("workforce_deployment_length", "==", 0))
                     .stream())

    finished = []
    for d in finished_docs:
        u = d.to_dict()
        total = (u.get("workers_extraction", 0)
                 + u.get("workers_rnd", 0)
                 + u.get("workers_espionage", 0))
        if total > 0:
            finished.append((d.id, u))

    for u_id, u in finished:
        handle_workers_reward(u_id, u)
        COL_USERS.document(u_id).update({
            "workers_extraction": 0,
            "workers_rnd":        0,
            "workers_espionage":  0,
            "espionage_target":   "RANDOM",
        })

    print(f"Tick: Processed {len(finished)} completed deployments.")


def handle_workers_reward(u_id: str, user: dict):
    global RECRUITING_CHANCE

    rarity_map = {d.id: d.to_dict()["rarity_index"] for d in COL_RESOURCES.stream()}

    ext_count       = user.get("workers_extraction", 0)
    rnd_count       = user.get("workers_rnd", 0)
    sabo_count      = user.get("workers_espionage", 0)
    espionage_target = user.get("espionage_target", "RANDOM")
    max_wf          = user.get("max_workforce", 10)

    # Split R&D
    rnd_splitter = random.randint(0, rnd_count)
    floor_   = int(rnd_count / 4)
    ceiling_ = int(rnd_count / 4 * 3)
    rnd_splitter = max(floor_, min(rnd_splitter, ceiling_))
    enhancers  = min(rnd_splitter, ext_count)
    recruiters = rnd_count - enhancers

    # Recruiting
    overall_recruited = sum(
        1 for _ in range(recruiters)
        if random.uniform(0, 100) <= RECRUITING_CHANCE
    )

    # Extraction (diminishing returns)
    if ext_count > 0:
        effective_extractors = max(1, int(math.sqrt(ext_count) * math.sqrt(ext_count + 1) / 2))
    else:
        effective_extractors = 0

    overall_rewards = extraction_reward(rarity_map, enhancers, max_wf, effective_extractors)

    # Sabotage
    if sabo_count > 0:
        if espionage_target != "RANDOM":
            target_doc = COL_USERS.document(espionage_target).get()
            target_id  = espionage_target if target_doc.exists else None
        else:
            candidates = [d.id for d in COL_USERS.stream() if d.id != u_id]
            target_id  = random.choice(candidates) if candidates else None

        if target_id:
            rewards = sabotage_reward(u_id, target_id, sabo_count)
            if rewards["failed"]:
                count = rewards['user_eliminated']
                msg   = f"Sabotage failed — {count} of your worker{'s were' if count != 1 else ' was'} killed."
                add_log(u_id, msg, 'FAIL')
            else:
                parts = []
                if rewards["target_eliminated"] > 0:
                    c = rewards['target_eliminated']
                    parts.append(f"{c} worker{'s' if c != 1 else ''} neutralized")
                if rewards["money_stolen"] > 0:
                    parts.append(f"${rewards['money_stolen']:,.2f} stolen")
                if rewards["materials_stolen"]:
                    parts.append(", ".join(f"{a}x {r}" for r, a in rewards["materials_stolen"].items()) + " stolen")
                msg = f"Sabotage success — {', '.join(parts)}." if parts else "Sabotage mission returned empty handed."
                add_log(u_id, msg, 'SABOTAGE')

    # Apply rewards
    if overall_recruited > 0:
        COL_USERS.document(u_id).update({"max_workforce": Increment(overall_recruited)})
        add_log(u_id, f"R&D recruited {overall_recruited} new worker{'s' if overall_recruited != 1 else ''}.", "HQ")

    if overall_rewards:
        rewards_batch = db.batch()
        for res_name, amount in overall_rewards.items():
            _set_inv_amount(rewards_batch, u_id, res_name, amount)
            rewards_batch.update(COL_RESOURCES.document(res_name), {"supply": Increment(amount)})
        rewards_batch.commit()

        summary = ", ".join(f"{amt}x {name}" for name, amt in overall_rewards.items())
        add_log(u_id, f"Extraction harvested: {summary}.", "HQ")
    else:
        print(f"User {u_id} extraction came up empty.")


def extraction_reward(rarity_map: dict, enhancers: int, max_wf: int, workers: int) -> dict:
    resources       = list(rarity_map.keys())
    overall_rewards = {}

    for _ in range(workers):
        rnd_ratio = enhancers / max(max_wf, 1)
        weights   = []
        for res_name in resources:
            rarity = rarity_map[res_name]
            w      = (rnd_ratio * rarity) + (1 - rnd_ratio) * (1 / rarity)
            weights.append(w)

        resource_to_mine = random.choices(resources, weights=weights, k=1)[0]
        rarity           = rarity_map[resource_to_mine]
        base_potential   = 25 + (rnd_ratio * 75)
        dampened_rarity  = math.pow(rarity, 0.6)
        threshold        = max(base_potential / dampened_rarity, 5.0)

        if random.uniform(0, 100) <= threshold:
            overall_rewards[resource_to_mine] = overall_rewards.get(resource_to_mine, 0) + 1

    return overall_rewards


def sabotage_reward(user_id: str, target_id: str, sabo_count: int) -> dict:
    global SABOTAGE_MAX_DETECTION_SEND, SABOTAGE_MAX_DETECTION_PRECENT, SABOTAGE_CHANCE_OF_DEATH

    ACTIONS = ["steal_materials", "steal_money", "neutralize"]

    precent_for_caught = min(
        (sabo_count / SABOTAGE_MAX_DETECTION_SEND) * SABOTAGE_MAX_DETECTION_PRECENT,
        SABOTAGE_MAX_DETECTION_PRECENT,
    )
    success_chance = min(5.0 + sabo_count * 2.0, 25.0)

    user_eliminated   = 0
    target_eliminated = 0
    materials_stolen: dict[str, int] = {}
    money_stolen = 0.0
    failed       = False

    # Phase 1 – detection
    if precent_for_caught > SABOTAGE_CHANCE_OF_DEATH:
        for _ in range(sabo_count):
            if random.uniform(0, 100) <= precent_for_caught:
                user_eliminated += 1
                failed = True

    # Phase 2 – actions
    if not failed:
        surviving = sabo_count - user_eliminated

        target_inv = _get_inventory(target_id)
        target_user = _get_user(target_id)
        target_balance = target_user.get("balance", 0.0) if target_user else 0.0

        for _ in range(surviving):
            if random.uniform(0, 100) > success_chance:
                continue
            action = random.choice(ACTIONS)

            if action == "neutralize":
                target_eliminated += 1

            elif action == "steal_money" and target_balance > 0:
                stolen          = round(target_balance * random.uniform(0.01, 0.05), 2)
                money_stolen   += stolen
                target_balance -= stolen

            elif action == "steal_materials":
                available = [(r, a) for r, a in target_inv.items() if a > 0]
                if available:
                    resource, _ = random.choice(available)
                    materials_stolen[resource] = materials_stolen.get(resource, 0) + 1
                    target_inv[resource]       = max(0, target_inv[resource] - 1)

    # Phase 3 – apply
    sab_batch = db.batch()

    if user_eliminated > 0:
        sab_batch.update(COL_USERS.document(user_id),
                         {"max_workforce": Increment(-user_eliminated)})

    if target_eliminated > 0:
        sab_batch.update(COL_USERS.document(target_id),
                         {"max_workforce": Increment(-target_eliminated)})
        add_log(target_id, f"User {user_id} eliminated {target_eliminated} of your workers.", "KILLED")

    if money_stolen > 0:
        sab_batch.update(COL_USERS.document(target_id), {"balance": Increment(-money_stolen)})
        sab_batch.update(COL_USERS.document(user_id),   {"balance": Increment(money_stolen)})
        add_log(target_id, f"User {user_id} stole ${money_stolen:,.2f} from you.", "KILLED")

    if materials_stolen:
        for resource, amount in materials_stolen.items():
            _set_inv_amount(sab_batch, target_id, resource, -amount)
            _set_inv_amount(sab_batch, user_id,   resource,  amount)
        summary = ", ".join(f"{a}x {r}" for r, a in materials_stolen.items())
        add_log(target_id, f"User {user_id} stole {summary} from you.", "KILLED")

    sab_batch.commit()

    return {
        "user_eliminated":   user_eliminated,
        "target_eliminated": target_eliminated,
        "money_stolen":      money_stolen,
        "materials_stolen":  materials_stolen,
        "failed":            failed,
    }


# ═════════════════════════════════════════════════════════════════════════════
#  CORPORATE VOTE LOGIC
# ═════════════════════════════════════════════════════════════════════════════

def create_new_vote():
    options      = random.sample(CORPORATE_CHANGES_OPTIONS, 3)
    all_res_docs = list(COL_RESOURCES.stream())
    random.shuffle(all_res_docs)
    resource_pool = iter(d.id for d in all_res_docs)

    resolved = []
    for opt in options:
        placeholders = re.findall(r'\$element_name\d*', opt)
        for ph in placeholders:
            opt = opt.replace(ph, next(resource_pool, "Unknown"), 1)
        resolved.append(opt)

    now        = time.time()
    expires_at = now + (VOTE_INTERVAL - (now % VOTE_INTERVAL))

    ref = COL_CORP_VOTES.add({
        "option_a": resolved[0], "option_b": resolved[1], "option_c": resolved[2],
        "votes_a": 0, "votes_b": 0, "votes_c": 0,
        "expires_at": expires_at,
        "resolved": False,
    })
    vote_id = ref[1].id
    print(f"[VOTE] New vote {vote_id} — expires {time.strftime('%H:%M:%S', time.localtime(expires_at))}")
    return vote_id


def apply_vote_result(vote_id: str):
    global CURRENT_TAX, RECRUITING_CHANCE, SABOTAGE_MAX_DETECTION_PRECENT
    global SABOTAGE_MAX_DETECTION_SEND, SABOTAGE_CHANCE_OF_DEATH, WORKFORCE_RETURN_TIME
    global SHOW_INVENTORY_IN_LEADERBOARD

    doc = COL_CORP_VOTES.document(vote_id).get()
    if not doc.exists:
        return
    v = doc.to_dict()

    winner = max(
        [("a", v["option_a"], v["votes_a"]),
         ("b", v["option_b"], v["votes_b"]),
         ("c", v["option_c"], v["votes_c"])],
        key=lambda x: (x[2], random.random()),
    )[1]

    print(f"[VOTE] #{vote_id} resolved → '{winner}'")
    SHOW_INVENTORY_IN_LEADERBOARD = 1

    if   "Tax Policy | +0.05" in winner: CURRENT_TAX = min(CURRENT_TAX + 0.05, 0.3)
    elif "Tax Policy | -0.05" in winner: CURRENT_TAX = max(CURRENT_TAX - 0.05, 0.03)
    elif "Tax Policy | +0.07" in winner: CURRENT_TAX = min(CURRENT_TAX + 0.07, 0.3)
    elif "Tax Policy | -0.07" in winner: CURRENT_TAX = max(CURRENT_TAX - 0.07, 0.03)
    elif "Tax Policy | +0.02" in winner: CURRENT_TAX = min(CURRENT_TAX + 0.02, 0.3)
    elif "Tax Policy | -0.02" in winner: CURRENT_TAX = max(CURRENT_TAX - 0.02, 0.03)

    elif "Unemployment"  in winner: RECRUITING_CHANCE = min(RECRUITING_CHANCE + 5, 50)
    elif "Tough Market"  in winner: RECRUITING_CHANCE = max(RECRUITING_CHANCE - 5, 5)

    elif "Global Security Crisis"   in winner and "success chance" in winner:
        SABOTAGE_MAX_DETECTION_PRECENT = max(SABOTAGE_MAX_DETECTION_PRECENT - 10, 5)
    elif "Global Security Upgrades" in winner and "success chance" in winner:
        SABOTAGE_MAX_DETECTION_PRECENT = min(SABOTAGE_MAX_DETECTION_PRECENT + 10, 80)
    elif "Global Security Crisis"   in winner and "death" in winner:
        SABOTAGE_CHANCE_OF_DEATH = max(SABOTAGE_CHANCE_OF_DEATH - 5, 5)
    elif "Global Security Upgrades" in winner and "death" in winner:
        SABOTAGE_CHANCE_OF_DEATH = min(SABOTAGE_CHANCE_OF_DEATH + 5, 60)

    elif "Area Contaminated" in winner: WORKFORCE_RETURN_TIME = min(WORKFORCE_RETURN_TIME + 1, 5)
    elif "New Area Found"    in winner: WORKFORCE_RETURN_TIME = max(WORKFORCE_RETURN_TIME - 1, 1)
    elif "Public Report"     in winner: SHOW_INVENTORY_IN_LEADERBOARD = 10

    elif any(k in winner for k in ("increased in value", "decreased in value",
                                    "increased in demand", "decreased in demand")):
        all_res = {d.id: d.to_dict()["base_price"] for d in COL_RESOURCES.stream()}
        for res_name, base_price in all_res.items():
            if res_name not in winner:
                continue
            if "increased in value" in winner or "decreased in value" in winner:
                update_resource_base_price(res_name, base_price * random.uniform(0.7, 1.3))
            elif "increased in demand" in winner:
                update_resource_demand(res_name, +random.uniform(0.5, 1.0))
            elif "decreased in demand" in winner:
                update_resource_demand(res_name, -random.uniform(0.5, 1.0))

    

    try:
        COL_SYSTEM.document("1").update({
            "current_tax": CURRENT_TAX,
            "recruit_chance": RECRUITING_CHANCE,
            "sabotage_max_detection_precent": SABOTAGE_MAX_DETECTION_PRECENT,
            "sabotage_chance_of_death": SABOTAGE_CHANCE_OF_DEATH,
            "workforce_return_time": WORKFORCE_RETURN_TIME,
            "show_inventory_in_leaderboard": SHOW_INVENTORY_IN_LEADERBOARD
        })
        print(f"[VOTE] Firestore 'system' document updated with new policies.")
    except Exception as e:
        print(f"[VOTE ERROR] Failed to save result to Firestore: {e}")

    # Broadcast to all users
    for d in COL_USERS.stream():
        add_log(d.id, f"[Corporate] New policy enacted: {winner}", "SYSTEM")


# ── RESOURCE HELPERS ──────────────────────────────────────────────────────────

def update_resource_base_price(resource_name: str, new_base_price: float):
    try:
        COL_RESOURCES.document(resource_name.capitalize()).update({
            "base_price":  new_base_price,
            "price":       new_base_price,
            "last_change": 0,
        })
        print(f"Base price for {resource_name} → {new_base_price:.2f}")
        return True
    except Exception as e:
        print(f"Error updating base price: {e}")
        return False


def update_resource_demand(resource_name: str, direction: float):
    try:
        res = _get_resource(resource_name.capitalize())
        if not res:
            return False
        rarity      = res["rarity_index"]
        equilibrium = EQUILIBRIUM_BY_RARITY[rarity]
        impact      = equilibrium * random.uniform(0.05, 0.15) * direction
        floor_      = equilibrium * 0.25
        ceiling_    = equilibrium * 2.0

        # Read-modify-write (acceptable: vote effects are low-frequency)
        current_demand = res.get("demand", equilibrium)
        new_demand     = max(floor_, min(ceiling_, current_demand + impact))
        COL_RESOURCES.document(resource_name.capitalize()).update({"demand": new_demand})
        print(f"Demand shock on {resource_name}: {impact:+.0f}")
        return True
    except Exception as e:
        print(f"Error updating demand: {e}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
#  BACKGROUND LOOPS
# ═════════════════════════════════════════════════════════════════════════════

def market_loop():
    while True:
        now = time.time()
        time.sleep(TICK_INTERVAL - (now % TICK_INTERVAL))
        run_tick()


def corporate_vote_loop():
    while True:
        now = time.time()
        time.sleep(VOTE_INTERVAL - (now % VOTE_INTERVAL))

        try:
            # Resolve expired votes
            expired = (COL_CORP_VOTES
                       .where(filter=FieldFilter("expires_at", "<=", now))
                        .where(filter=FieldFilter("resolved", "==", False))
                       .stream())

            for d in expired:
                apply_vote_result(d.id)
                d.reference.update({"resolved": True})

            # Create new vote if none active
            active = list(COL_CORP_VOTES
                          .where(filter=FieldFilter("expires_at", ">", now))
                        .where(filter=FieldFilter("resolved", "==", False))
                          .limit(1)
                          .stream())
            if not active:
                create_new_vote()

        except Exception as e:
            print(f"[VOTE LOOP ERROR] {e}")


# ═════════════════════════════════════════════════════════════════════════════
#  INITIALIZATION
# ═════════════════════════════════════════════════════════════════════════════

def init_firestore_data():
    """Seeds Firestore with initial data the first time the server starts."""

    # Resources
    for (name, price, change, supply, demand, updated, base_price, rarity) in MATERIALS:
        ref = COL_RESOURCES.document(name)
        if not ref.get().exists:
            ref.set({
                "name": name, "price": price, "last_change": change,
                "supply": supply, "demand": demand, "last_updated": float(updated),
                "base_price": base_price, "rarity_index": rarity,
            })
            print(f"[INIT] Created resource: {name}")

    # Default test users
    for uid, bal in [("user123", 1000.0), ("test_user321", 1000.0)]:
        ref = COL_USERS.document(uid)
        if not ref.get().exists:
            ref.set({
                "user_id": uid, "balance": bal,
                "max_workforce": 10,
                "workers_extraction": 0, "workers_rnd": 0, "workers_espionage": 0,
                "espionage_target": "RANDOM", "workforce_deployment_length": 0,
            })
            print(f"[INIT] Created user: {uid}")


    # System doc
    sys_ref = COL_SYSTEM.document("1")
    if not sys_ref.get().exists:
        sys_ref.set({
            "current_tax": CURRENT_TAX,
            "market_decay_rate": MARKET_DECAY_RATE,
            "recruit_chance": RECRUITING_CHANCE,
            "sabotage_max_detection_precent": SABOTAGE_MAX_DETECTION_PRECENT,
            "sabotage_max_detection_send": SABOTAGE_MAX_DETECTION_SEND,
            "sabotage_chance_of_death": SABOTAGE_CHANCE_OF_DEATH,
            "workforce_return_time": WORKFORCE_RETURN_TIME,
            "show_inventory_in_leaderboard": SHOW_INVENTORY_IN_LEADERBOARD
        })

    # Initial vote if none active
    active = list(COL_CORP_VOTES
                  .where(filter=FieldFilter("expires_at", ">", time.time()))
                  .where(filter=FieldFilter("resolved", "==", False))
                  .limit(1)
                  .stream())
    if not active:
        create_new_vote()
        print("[INIT] Created initial corporate vote.")


if __name__ == "__main__":
    init_firestore_data()
    sync_configs_from_db()

    threading.Thread(target=market_loop,        daemon=True).start()
    threading.Thread(target=corporate_vote_loop, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)