import random
import time
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="Cinema Group Ticket Booking - Mutex Dashboard",
    page_icon="🎬",
    layout="wide",
)

# ---------- Styling ----------
st.markdown("""
<style>
:root { color-scheme: light dark; }
.block-container { max-width: 1100px; padding-top: 1.2rem; }
.top-banner {
    background: #1a4d8f; color: white; padding: 15px 20px;
    border-radius: 10px; margin-bottom: 18px;
}
.top-banner h1 { font-size: 1.45rem; margin: 0; }
.top-banner p { font-size: .82rem; margin: 4px 0 0; opacity: .9; }
.metric-card {
    border: 1px solid rgba(128,128,128,.3); border-radius: 10px;
    padding: 12px; min-height: 86px;
}
.metric-value { font-size: 1.8rem; font-weight: 700; }
.metric-label { font-size: .78rem; opacity: .72; }
.seat-available button { background: #7ed957 !important; color: #10151d !important; }
.seat-selected button { background: #ffd84d !important; color: #10151d !important; }
.seat-booked button { background: #e85d5d !important; color: white !important; }
.screen {
    background: #444; color: white; text-align: center; padding: 5px;
    border-radius: 4px; letter-spacing: 3px; font-size: 12px; margin-bottom: 12px;
}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.25); padding: 10px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

ROWS = list("ABCDEFGH")
COLS = 10
TOTAL = len(ROWS) * COLS


# ---------- Session state ----------
def initialize():
    defaults = {
        "seats": {f"{r}{c}": None for r in ROWS for c in range(1, COLS + 1)},
        "selected": set(),
        "stats": {"ok": 0, "rej": 0, "bad": 0},
        "history": [],
        "logs": [],
        "lock_owner": None,
        "waiting_queue": [],
        "last_simulation": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_log(message, level="info"):
    st.session_state.logs.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message,
        "level": level,
    })
    st.session_state.logs = st.session_state.logs[-150:]


def reset_all():
    st.session_state.seats = {f"{r}{c}": None for r in ROWS for c in range(1, COLS + 1)}
    st.session_state.selected = set()
    st.session_state.stats = {"ok": 0, "rej": 0, "bad": 0}
    add_log("Theatre reset")


def validate(ids):
    if not ids:
        return False, "no seats selected"
    positions = sorted([(seat[0], int(seat[1:])) for seat in ids], key=lambda x: x[1])
    if len({row for row, _ in positions}) > 1:
        return False, "seats must be in the same row"
    for i in range(1, len(positions)):
        if positions[i][1] != positions[i - 1][1] + 1:
            return False, "seats must be adjacent"
    return True, ""


def book(customer, ids, use_mutex=True, delay=0.0):
    valid, message = validate(ids)
    if not valid:
        st.session_state.stats["rej"] += 1
        add_log(f"{customer}: rejected, {message}", "bad")
        return

    if use_mutex:
        st.session_state.lock_owner = customer
        add_log(f"{customer} requests the lock")
        add_log(f"{customer} acquired the lock (critical section)")

    try:
        taken = [seat for seat in ids if st.session_state.seats[seat] is not None]
        if taken:
            st.session_state.stats["rej"] += 1
            add_log(f"{customer}: rejected, already taken: {', '.join(taken)}", "bad")
            return

        add_log(f"{customer} checked {', '.join(ids)}: all free")
        if delay:
            time.sleep(delay)

        double = [
            seat for seat in ids
            if st.session_state.seats[seat] is not None
            and st.session_state.seats[seat] != customer
        ]
        for seat in ids:
            st.session_state.seats[seat] = customer

        if double:
            st.session_state.stats["bad"] += len(double)
            add_log(f"DOUBLE BOOKING: {', '.join(double)} sold to two customers", "bad")

        st.session_state.stats["ok"] += 1
        add_log(f"{customer}: booking confirmed for {', '.join(ids)}", "ok")
    finally:
        if use_mutex:
            st.session_state.lock_owner = None
            add_log(f"{customer} released the lock")


def simulate(customer_count, use_mutex):
    reset_all()
    row = random.choice(ROWS)
    names = ["Alice", "Bob", "Carol", "Dave"][:customer_count]
    requests = [
        (name, [f"{row}{2 + i * 2 + k}" for k in range(3)])
        for i, name in enumerate(names)
    ]

    add_log(
        f"--- Simulation: {customer_count} overlapping group bookings "
        f"in row {row}, mutex {'ON' if use_mutex else 'OFF'} ---"
    )

    if use_mutex:
        # Requests enter the critical section one at a time.
        for name, ids in requests:
            book(name, ids, use_mutex=True)
    else:
        # Demonstrate the race: all customers read availability before any update.
        snapshots = []
        for name, ids in requests:
            valid, message = validate(ids)
            if not valid:
                st.session_state.stats["rej"] += 1
                add_log(f"{name}: rejected, {message}", "bad")
                continue
            taken = [seat for seat in ids if st.session_state.seats[seat] is not None]
            if taken:
                st.session_state.stats["rej"] += 1
                add_log(f"{name}: rejected, already taken: {', '.join(taken)}", "bad")
                continue
            add_log(f"{name} checked {', '.join(ids)}: all free (before updates)")
            snapshots.append((name, ids))

        # All requests now commit based on their earlier checks, causing overlap.
        for name, ids in snapshots:
            double = [
                seat for seat in ids
                if st.session_state.seats[seat] is not None
                and st.session_state.seats[seat] != name
            ]
            for seat in ids:
                if st.session_state.seats[seat] is None:
                    st.session_state.seats[seat] = name
            if double:
                st.session_state.stats["bad"] += len(double)
                add_log(
                    f"DOUBLE BOOKING: {', '.join(double)} requested by multiple customers",
                    "bad",
                )
            st.session_state.stats["ok"] += 1
            add_log(f"{name}: booking confirmed for {', '.join(ids)}", "ok")

    stats = st.session_state.stats
    result = {
        "Mutex": "ON" if use_mutex else "OFF",
        "Req": customer_count,
        "OK": stats["ok"],
        "Rej": stats["rej"],
        "Double": stats["bad"],
    }
    st.session_state.history.insert(0, result)
    add_log(
        f"Result: {'race condition, ' + str(stats['bad']) + ' seat(s) double booked' if stats['bad'] else 'safe, no double booking'}",
        "bad" if stats["bad"] else "ok",
    )


initialize()

st.markdown("""
<div class="top-banner">
  <h1>Cinema Group Ticket Booking System</h1>
  <p>Product 3 · Race condition &amp; mutex · OS and Computer Networks (25CAI402PC203), SR University</p>
</div>
""", unsafe_allow_html=True)

stats = st.session_state.stats
booked_count = sum(value is not None for value in st.session_state.seats.values())
free_count = TOTAL - booked_count
occupancy = round(booked_count / TOTAL * 100)

kpis = st.columns(5)
metrics = [
    (booked_count, "Seats booked"),
    (free_count, "Seats available"),
    (stats["ok"], "Bookings confirmed"),
    (stats["rej"], "Requests rejected"),
    (stats["bad"], "Double-booked seats"),
]
for col, (value, label) in zip(kpis, metrics):
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")
left, right = st.columns([2, 1], gap="medium")

with left:
    st.subheader("Theatre layout")
    st.markdown('<div class="screen">SCREEN</div>', unsafe_allow_html=True)

    for row in ROWS:
        seat_cols = st.columns([0.45] + [1] * COLS, gap="small")
        with seat_cols[0]:
            st.caption(row)
        for col_num in range(1, COLS + 1):
            seat_id = f"{row}{col_num}"
            owner = st.session_state.seats[seat_id]
            with seat_cols[col_num]:
                if owner:
                    st.button(
                        seat_id, key=f"seat_{seat_id}", disabled=True,
                        help=f"Booked by {owner}", use_container_width=True
                    )
                else:
                    label = f"🟨 {seat_id}" if seat_id in st.session_state.selected else seat_id
                    if st.button(label, key=f"seat_{seat_id}", use_container_width=True):
                        if seat_id in st.session_state.selected:
                            st.session_state.selected.remove(seat_id)
                        else:
                            st.session_state.selected.add(seat_id)
                        st.rerun()

    st.caption("🟩 Available  ·  🟨 Selected  ·  🟥 Booked")
    customer_name = st.text_input("Customer name", value="Customer1")
    use_mutex = st.checkbox("Use mutex", value=True)
    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("Book selected seats", type="primary", use_container_width=True):
            ids = sorted(st.session_state.selected)
            st.session_state.selected.clear()
            book(customer_name.strip() or "Guest", ids, use_mutex=use_mutex)
            st.rerun()
    with action_cols[1]:
        if st.button("Reset", use_container_width=True):
            reset_all()
            st.rerun()

    st.divider()
    customer_count = st.selectbox("Customers", [2, 3, 4], index=1)
    if st.button("Simulate overlapping group bookings", type="primary", use_container_width=True):
        simulate(customer_count, use_mutex)
        st.rerun()

    st.caption(
        "Each simulated customer requests 3 adjacent seats in the same row; "
        "neighbouring requests overlap by one seat. Turn the mutex off to see a double booking."
    )

with right:
    st.subheader("Mutex status")
    if st.session_state.lock_owner:
        st.error(f"LOCKED by {st.session_state.lock_owner}")
    else:
        st.success("UNLOCKED")
    queue = st.session_state.waiting_queue
    st.caption("Waiting queue: " + (", ".join(queue) if queue else "empty"))
    st.write(f"**Theatre occupancy** · {occupancy}%")
    st.progress(occupancy / 100)

    st.subheader("Simulation history")
    if st.session_state.history:
        st.dataframe(st.session_state.history, use_container_width=True, hide_index=True)
    else:
        st.caption("No runs yet")

st.write("")
st.subheader("Activity log")
if st.session_state.logs:
    for item in reversed(st.session_state.logs):
        if item["level"] == "bad":
            st.error(f'{item["time"]}  {item["message"]}')
        elif item["level"] == "ok":
            st.success(f'{item["time"]}  {item["message"]}')
        else:
            st.caption(f'{item["time"]}  {item["message"]}')
else:
    st.caption("Dashboard ready. Select seats and book, or run the simulation.")

st.caption(
    "Note: This Streamlit version keeps booking data in session memory. "
    "A server restart or a new session can reset the data."
)
