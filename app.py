import json
import random
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ----------------------------
# Config
# ----------------------------
st.set_page_config(
    page_title="Snake & Ladder Arena",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded",
)

BOARD_SIZE = 10
WIN_CELL = 100
LEADERBOARD_FILE = Path("leaderboard.json")
SNAKES = {
    99: 54,
    95: 72,
    92: 88,
    83: 19,
    73: 53,
    69: 33,
    64: 36,
    59: 17,
    52: 42,
    48: 9,
    25: 2,
}
LADDERS = {
    4: 14,
    9: 31,
    20: 38,
    28: 84,
    40: 59,
    51: 67,
    63: 81,
    71: 91,
}
DICE_FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

# ----------------------------
# Styling
# ----------------------------
CUSTOM_CSS = """
<style>
:root {
    --bg1: #0f172a;
    --bg2: #111827;
    --card: rgba(17, 24, 39, 0.65);
    --text: #e5e7eb;
    --muted: #9ca3af;
}

html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, #111827 0%, #0f172a 45%, #020617 100%);
}

.main-title {
    font-size: 2.25rem;
    font-weight: 800;
    line-height: 1.1;
    color: var(--text);
    margin-bottom: .25rem;
}

.subtitle {
    color: var(--muted);
    margin-bottom: 1rem;
}

.glass-card {
    background: var(--card);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 1rem 1.1rem;
    box-shadow: 0 12px 40px rgba(2, 6, 23, 0.35);
}

.metric-pill {
    display: inline-flex;
    align-items: center;
    gap: .5rem;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 999px;
    padding: .35rem .7rem;
    background: rgba(255,255,255,0.04);
    color: var(--text);
    margin-right: .5rem;
    margin-bottom: .5rem;
    font-size: .92rem;
}

.board-grid {
    display: grid;
    grid-template-columns: repeat(10, minmax(48px, 1fr));
    gap: 6px;
}

.cell {
    position: relative;
    min-height: 68px;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.08);
    background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    color: var(--text);
    padding: 6px;
}

.cell.snake {
    box-shadow: inset 0 0 0 2px rgba(239,68,68,0.35);
}

.cell.ladder {
    box-shadow: inset 0 0 0 2px rgba(16,185,129,0.35);
}

.cell-number {
    position: absolute;
    top: 6px;
    right: 8px;
    font-size: .82rem;
    color: rgba(229,231,235,0.85);
    font-weight: 700;
}

.marker-row {
    position: absolute;
    left: 6px;
    right: 6px;
    bottom: 6px;
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
}

.marker {
    border-radius: 999px;
    padding: 2px 8px;
    font-size: .76rem;
    font-weight: 700;
    color: #fff;
    box-shadow: 0 6px 18px rgba(0,0,0,0.28);
}

.marker.active {
    animation: pulse 1.15s infinite;
}

.info-badge {
    position: absolute;
    left: 6px;
    top: 6px;
    font-size: .72rem;
    font-weight: 800;
    border-radius: 999px;
    padding: 2px 6px;
}

.badge-snake { background: rgba(239,68,68,0.15); color: #fca5a5; }
.badge-ladder { background: rgba(16,185,129,0.15); color: #86efac; }

.dice-box {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 92px;
    height: 92px;
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(139,92,246,0.16), rgba(6,182,212,0.16));
    border: 1px solid rgba(255,255,255,0.08);
    font-size: 3rem;
    box-shadow: 0 12px 30px rgba(2,6,23,0.35);
}

.event-log {
    max-height: 360px;
    overflow-y: auto;
    font-size: .95rem;
    color: var(--text);
}

.event-item {
    padding: .55rem .75rem;
    margin-bottom: .45rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
}

.small-muted { color: var(--muted); font-size: .88rem; }

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.08); }
    100% { transform: scale(1); }
}
</style>
"""


# ----------------------------
# Utilities
# ----------------------------
def load_leaderboard():
    if not LEADERBOARD_FILE.exists():
        return {}
    try:
        return json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_leaderboard(data):
    LEADERBOARD_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_leaderboard(winner_name, total_turns):
    board = load_leaderboard()
    board.setdefault(winner_name, {"wins": 0, "games": 0, "best_turns": None})
    for player in st.session_state.players:
        board.setdefault(player["name"], {"wins": 0, "games": 0, "best_turns": None})
        board[player["name"]]["games"] += 1
    board[winner_name]["wins"] += 1
    current_best = board[winner_name].get("best_turns")
    if current_best is None or total_turns < current_best:
        board[winner_name]["best_turns"] = total_turns
    save_leaderboard(board)


def init_state():
    defaults = {
        "players": [],
        "current_turn": 0,
        "game_started": False,
        "winner": None,
        "dice_value": 1,
        "event_log": [],
        "total_turns": 0,
        "game_mode": "Human vs Human",
        "last_roll": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def new_game(player1_name, player2_name, mode):
    st.session_state.players = [
        {
            "name": player1_name.strip() or "Player 1",
            "position": 0,
            "is_ai": False,
            "color": "#8b5cf6",
            "turns": 0,
        },
        {
            "name": player2_name.strip() or ("AI Bot" if mode == "Human vs AI" else "Player 2"),
            "position": 0,
            "is_ai": mode == "Human vs AI",
            "color": "#06b6d4",
            "turns": 0,
        },
    ]
    st.session_state.current_turn = 0
    st.session_state.game_started = True
    st.session_state.winner = None
    st.session_state.dice_value = 1
    st.session_state.last_roll = None
    st.session_state.total_turns = 0
    st.session_state.event_log = [
        f"🎮 New game started: {st.session_state.players[0]['name']} vs {st.session_state.players[1]['name']}"
    ]


def board_numbers():
    rows = []
    current = WIN_CELL
    for row_index in range(BOARD_SIZE):
        row = list(range(current - 9, current + 1))
        if row_index % 2 == 0:
            row = row[::-1]
        rows.append(row)
        current -= 10
    return rows


def render_board(players, active_idx=None):
    position_map = {}
    for idx, player in enumerate(players):
        pos = player["position"]
        if pos <= 0:
            continue
        position_map.setdefault(pos, []).append((idx, player))

    html_parts = ['<div class="board-grid">']
    for row in board_numbers():
        for cell in row:
            classes = ["cell"]
            if cell in SNAKES:
                classes.append("snake")
            if cell in LADDERS:
                classes.append("ladder")

            html_parts.append(f'<div class="{" ".join(classes)}">')
            html_parts.append(f'<div class="cell-number">{cell}</div>')

            if cell in SNAKES:
                html_parts.append('<div class="info-badge badge-snake">🐍</div>')
            elif cell in LADDERS:
                html_parts.append('<div class="info-badge badge-ladder">🪜</div>')

            html_parts.append('<div class="marker-row">')
            for idx, player in position_map.get(cell, []):
                active = "active" if active_idx == idx else ""
                safe_name = player["name"][:10]
                html_parts.append(
                    f'<div class="marker {active}" style="background:{player["color"]}">{safe_name}</div>'
                )
            html_parts.append("</div></div>")

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def animate_dice():
    placeholder = st.empty()
    final_value = 1
    for _ in range(9):
        final_value = random.randint(1, 6)
        placeholder.markdown(
            f'<div class="dice-box">{DICE_FACES[final_value - 1]}</div>',
            unsafe_allow_html=True,
        )
        time.sleep(0.08)
    return final_value


def get_current_player():
    return st.session_state.players[st.session_state.current_turn]


def append_event(message):
    st.session_state.event_log.insert(0, message)
    st.session_state.event_log = st.session_state.event_log[:40]


def advance_turn(current_idx, dice):
    if dice == 6:
        append_event(f"✨ {st.session_state.players[current_idx]['name']} rolled a 6 and gets another turn!")
        st.session_state.current_turn = current_idx
    else:
        st.session_state.current_turn = 1 - current_idx


def take_turn():
    if not st.session_state.game_started or st.session_state.winner:
        return

    current_idx = st.session_state.current_turn
    player = st.session_state.players[current_idx]

    dice = animate_dice()
    st.session_state.dice_value = dice
    st.session_state.last_roll = dice
    st.session_state.total_turns += 1
    player["turns"] += 1

    start_pos = player["position"]
    tentative = start_pos + dice

    if tentative > WIN_CELL:
        append_event(f"🎲 {player['name']} rolled {dice}, but needs an exact roll to reach {WIN_CELL}.")
        advance_turn(current_idx, dice)
        return

    player["position"] = tentative
    append_event(f"🎲 {player['name']} rolled {dice} and moved from {start_pos} to {tentative}.")

    if tentative in SNAKES:
        player["position"] = SNAKES[tentative]
        append_event(f"🐍 Snake bite! {player['name']} slid down to {player['position']}.")
    elif tentative in LADDERS:
        player["position"] = LADDERS[tentative]
        append_event(f"🪜 Ladder boost! {player['name']} climbed up to {player['position']}.")

    if player["position"] == WIN_CELL:
        st.session_state.winner = player["name"]
        update_leaderboard(player["name"], st.session_state.total_turns)
        append_event(
            f"🏆 {player['name']} wins in {player['turns']} personal turns and {st.session_state.total_turns} total turns!"
        )
        return

    advance_turn(current_idx, dice)


def maybe_auto_play_ai():
    if not st.session_state.game_started or st.session_state.winner:
        return
    current = get_current_player()
    if current["is_ai"]:
        with st.spinner(f"🤖 {current['name']} is thinking..."):
            time.sleep(0.45)
            take_turn()
        st.rerun()


def render_event_log():
    items = [f'<div class="event-item">{msg}</div>' for msg in st.session_state.event_log]
    st.markdown(f'<div class="event-log">{"".join(items)}</div>', unsafe_allow_html=True)


def leaderboard_df():
    board = load_leaderboard()
    rows = []
    for name, stats in board.items():
        wins = stats.get("wins", 0)
        games = stats.get("games", 0)
        win_rate = round((wins / games) * 100, 1) if games else 0.0
        rows.append(
            {
                "Player": name,
                "Wins": wins,
                "Games": games,
                "Win %": win_rate,
                "Best Total Turns": stats.get("best_turns") or "-",
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Player", "Wins", "Games", "Win %", "Best Total Turns"])

    df = pd.DataFrame(rows).sort_values(["Wins", "Win %", "Player"], ascending=[False, False, True])
    df.index = range(1, len(df) + 1)
    return df


# ----------------------------
# UI
# ----------------------------
init_state()
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown('<div class="main-title">🐍 Snake & Ladder Arena</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">A polished Streamlit portfolio app with local multiplayer, AI mode, animated dice, custom board UI, and a persistent leaderboard.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ⚙️ Game Setup")
    mode = st.radio(
        "Mode",
        ["Human vs Human", "Human vs AI"],
        index=0 if st.session_state.game_mode == "Human vs Human" else 1,
    )
    st.session_state.game_mode = mode

    p1 = st.text_input("Player 1 name", value="Player 1")
    p2_default = "AI Bot" if mode == "Human vs AI" else "Player 2"
    p2 = st.text_input("Player 2 name", value=p2_default, disabled=mode == "Human vs AI")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Start New Game", use_container_width=True):
            new_game(p1, p2, mode)
            st.rerun()
    with c2:
        if st.button("🧹 Reset Leaderboard", use_container_width=True):
            save_leaderboard({})
            st.success("Leaderboard cleared.")
            st.rerun()

    st.markdown("---")
    st.markdown("### ✨ What this version includes")
    st.markdown(
        """
- Local multiplayer (2 players, same screen)
- AI opponent mode
- Animated dice
- Persistent leaderboard
- Portfolio-friendly custom UI
        """
    )

left, right = st.columns([2.1, 1.1], gap="large")

with left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if not st.session_state.game_started:
        st.markdown("### 👋 Start a game from the sidebar")
        st.markdown(
            """
- **Local multiplayer**: 2 humans on one screen
- **AI mode**: challenge the built-in bot
- **Exact roll to win**
- **Persistent leaderboard** stored in `leaderboard.json`
            """
        )
    else:
        active_idx = st.session_state.current_turn if not st.session_state.winner else None
        render_board(st.session_state.players, active_idx=active_idx)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if st.session_state.game_started:
        current = get_current_player()
        turn_type = "AI" if current["is_ai"] else "Human"

        st.markdown("### 🎯 Current Turn")
        st.markdown(
            f'<div class="metric-pill">👤 <strong>{current["name"]}</strong></div>'
            f'<div class="metric-pill">🎮 {turn_type}</div>',
            unsafe_allow_html=True,
        )

        stat1, stat2 = st.columns(2)
        with stat1:
            st.metric("Last Dice", DICE_FACES[st.session_state.dice_value - 1], help="Latest dice roll")
        with stat2:
            st.metric("Total Turns", st.session_state.total_turns)

        st.markdown("### 🎲 Dice")
        st.markdown(f'<div class="dice-box">{DICE_FACES[st.session_state.dice_value - 1]}</div>', unsafe_allow_html=True)

        button_label = "🤖 AI Turn" if current["is_ai"] else "🎲 Roll Dice"
        if st.button(button_label, use_container_width=True, disabled=bool(st.session_state.winner)):
            take_turn()
            st.rerun()

        if st.session_state.winner:
            st.success(f"🏆 Winner: {st.session_state.winner}")
            if st.button("🔁 Play Again", use_container_width=True):
                new_game(st.session_state.players[0]["name"], st.session_state.players[1]["name"], st.session_state.game_mode)
                st.rerun()

        st.markdown("### 🧍 Player Positions")
        for idx, player in enumerate(st.session_state.players):
            badge = "🤖" if player["is_ai"] else "👤"
            active_tag = " ← active" if idx == st.session_state.current_turn and not st.session_state.winner else ""
            st.markdown(
                f'<div class="metric-pill" style="border-color:{player["color"]};">{badge} '
                f'<strong>{player["name"]}</strong>: {player["position"]}{active_tag}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown("### ✨ Features")
        st.markdown(
            """
- Animated dice
- Custom board UI
- Human vs Human
- Human vs AI
- Persistent leaderboard
- Portfolio-friendly design
            """
        )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")
info_col, log_col = st.columns([1.1, 1.4], gap="large")

with info_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🏅 Leaderboard")
    df = leaderboard_df()
    st.dataframe(df, use_container_width=True, hide_index=False)
    st.markdown(
        '<div class="small-muted">Tip: wins are stored in <code>leaderboard.json</code>. '
        'On Streamlit Community Cloud, file-based data may reset on redeploy or restart.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with log_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📜 Match Log")
    render_event_log()
    st.markdown("</div>", unsafe_allow_html=True)

maybe_auto_play_ai()
