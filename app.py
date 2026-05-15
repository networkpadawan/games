import base64
import json
import random
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------
# Config
# ----------------------------
st.set_page_config(
    page_title="Snake & Ladder Arena",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded",
)

WIN_CELL = 100
LEADERBOARD_FILE = Path("leaderboard.json")
ASSETS_DIR = Path("assets")
BOARD_IMAGE_PATH = ASSETS_DIR / "board.png"
DICE_SOUND_PATH = ASSETS_DIR / "dice.mp3"
SNAKE_SOUND_PATH = ASSETS_DIR / "snake.mp3"
LADDER_SOUND_PATH = ASSETS_DIR / "ladder.mp3"
WIN_SOUND_PATH = ASSETS_DIR / "win.mp3"

# Adjust these if your board image has larger or smaller borders.
BOARD_PADDING_PERCENT = 4.8
BOARD_TOKEN_SIZE_PERCENT = 5.8

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
    --card: rgba(17, 24, 39, 0.70);
    --text: #e5e7eb;
    --muted: #9ca3af;
}

html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, #111827 0%, #0f172a 45%, #020617 100%);
}

.main-title {
    font-size: 2.5rem;
    font-weight: 900;
    color: var(--text);
    margin-bottom: .2rem;
}

.subtitle {
    color: var(--muted);
    margin-bottom: 1rem;
}

.glass-card {
    background: rgba(17, 24, 39, 0.70);
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

.dice-box {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 92px;
    height: 92px;
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(139,92,246,0.18), rgba(6,182,212,0.18));
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
</style>
"""


# ----------------------------
# Asset helpers
# ----------------------------
def asset_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def file_to_base64(path: Path):
    if not asset_exists(path):
        return None
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def data_uri(path: Path, mime: str):
    encoded = file_to_base64(path)
    if not encoded:
        return None
    return f"data:{mime};base64,{encoded}"


# ----------------------------
# State / storage helpers
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
        "sound_to_play": None,
        "confetti_shown": False,
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
            "color": "#ef4444",
            "turns": 0,
            "emoji": "🔴",
        },
        {
            "name": player2_name.strip() or ("AI Bot" if mode == "Human vs AI" else "Player 2"),
            "position": 0,
            "is_ai": mode == "Human vs AI",
            "color": "#3b82f6",
            "turns": 0,
            "emoji": "🔵",
        },
    ]
    st.session_state.current_turn = 0
    st.session_state.game_started = True
    st.session_state.winner = None
    st.session_state.dice_value = 1
    st.session_state.last_roll = None
    st.session_state.total_turns = 0
    st.session_state.sound_to_play = None
    st.session_state.confetti_shown = False
    st.session_state.event_log = [
        f"🎮 New game started: {st.session_state.players[0]['name']} vs {st.session_state.players[1]['name']}"
    ]


def get_current_player():
    return st.session_state.players[st.session_state.current_turn]


def append_event(message):
    st.session_state.event_log.insert(0, message)
    st.session_state.event_log = st.session_state.event_log[:40]


def set_sound(path: Path):
    if asset_exists(path):
        st.session_state.sound_to_play = str(path)


def board_xy_percent(position: int):
    if position <= 0:
        return None

    row = (position - 1) // 10
    col = (position - 1) % 10
    if row % 2 == 1:
        col = 9 - col

    inner = 100 - 2 * BOARD_PADDING_PERCENT
    x = BOARD_PADDING_PERCENT + ((col + 0.5) * inner / 10)
    y = 100 - (BOARD_PADDING_PERCENT + ((row + 0.5) * inner / 10))
    return x, y


def render_board_image(players, active_idx=None):
    board_uri = data_uri(BOARD_IMAGE_PATH, "image/png")

    if not board_uri:
        st.warning(
            "Board image not found. Add `assets/board.png` to your repo for the upgraded visual board. The rest of the game will still work."
        )
        st.info("Expected path: `assets/board.png`")
        return

    tokens_html = []
    for idx, player in enumerate(players):
        pos = player["position"]
        xy = board_xy_percent(pos)
        if not xy:
            continue
        x, y = xy

        same_cell_players = [p for p in players if p["position"] == pos and pos > 0]
        offset_x = 0
        if len(same_cell_players) > 1:
            offset_x = -2.2 if idx == 0 else 2.2

        active_class = "active-token" if active_idx == idx else ""
        token_size = BOARD_TOKEN_SIZE_PERCENT
        tokens_html.append(
            f'''<div class="token {active_class}" title="{player['name']}" style="left: calc({x + offset_x}% - {token_size / 2}%); top: calc({y}% - {token_size / 2}%); width:{token_size}%; height:{token_size}%; background:{player['color']};"><span>{player['emoji']}</span></div>'''
        )

    board_html = f'''
    <style>
      .board-shell {{
        position: relative;
        width: 100%;
        aspect-ratio: 1 / 1;
        border-radius: 24px;
        overflow: hidden;
        box-shadow: 0 16px 40px rgba(2,6,23,.35);
        border: 1px solid rgba(255,255,255,.08);
        background-image: url("{board_uri}");
        background-size: cover;
        background-position: center;
      }}
      .board-overlay {{
        position: absolute;
        inset: 0;
        pointer-events: none;
      }}
      .token {{
        position: absolute;
        border-radius: 999px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: clamp(14px, 1.3vw, 24px);
        font-weight: 900;
        box-shadow: 0 10px 24px rgba(0,0,0,.35), inset 0 2px 6px rgba(255,255,255,.24);
        border: 2px solid rgba(255,255,255,.9);
      }}
      .active-token {{ animation: pulse 1.0s ease-in-out infinite; }}
      @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.12); }}
        100% {{ transform: scale(1); }}
      }}
      .board-caption {{
        margin-top: 10px;
        color: #cbd5e1;
        font-size: 0.92rem;
      }}
    </style>
    <div class="board-shell"><div class="board-overlay">{''.join(tokens_html)}</div></div>
    <div class="board-caption">Tip: if tokens look slightly off-center, adjust <code>BOARD_PADDING_PERCENT</code> near the top of <code>app.py</code>.</div>
    '''

    st.markdown(board_html, unsafe_allow_html=True)


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

    set_sound(DICE_SOUND_PATH)
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
        set_sound(SNAKE_SOUND_PATH)
    elif tentative in LADDERS:
        player["position"] = LADDERS[tentative]
        append_event(f"🪜 Ladder boost! {player['name']} climbed up to {player['position']}.")
        set_sound(LADDER_SOUND_PATH)

    if player["position"] == WIN_CELL:
        st.session_state.winner = player["name"]
        update_leaderboard(player["name"], st.session_state.total_turns)
        append_event(
            f"🏆 {player['name']} wins in {player['turns']} personal turns and {st.session_state.total_turns} total turns!"
        )
        set_sound(WIN_SOUND_PATH)
        return

    advance_turn(current_idx, dice)


def maybe_auto_play_ai():
    if not st.session_state.game_started or st.session_state.winner:
        return
    current = get_current_player()
    if current["is_ai"]:
        with st.spinner(f"🤖 {current['name']} is thinking..."):
            time.sleep(0.5)
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
        rows.append({
            "Player": name,
            "Wins": wins,
            "Games": games,
            "Win %": win_rate,
            "Best Total Turns": stats.get("best_turns") or "-",
        })

    if not rows:
        return pd.DataFrame(columns=["Player", "Wins", "Games", "Win %", "Best Total Turns"])

    df = pd.DataFrame(rows).sort_values(["Wins", "Win %", "Player"], ascending=[False, False, True])
    df.index = range(1, len(df) + 1)
    return df


def play_pending_sound():
    sound_path_str = st.session_state.get("sound_to_play")
    if not sound_path_str:
        return

    sound_path = Path(sound_path_str)
    if not asset_exists(sound_path):
        st.session_state.sound_to_play = None
        return

    ext = sound_path.suffix.lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
    }
    mime = mime_map.get(ext, "audio/mpeg")
    audio_uri = data_uri(sound_path, mime)
    if audio_uri:
        components.html(
    f'''
    <audio autoplay>
        <source src="{audio_uri}" type="audio/mpeg">
    </audio>
    ''',
    height=0,
)

    st.session_state.sound_to_play = None


# ----------------------------
# UI
# ----------------------------
init_state()
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown('<div class="main-title">🐍 Snake & Ladder Arena</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Now upgraded for a real-board feel: board image background, token overlays, sound hooks, AI mode, and leaderboard tracking.</div>',
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
    st.markdown("### 🗂️ Asset checklist")
    st.code(
        "assets/board.png\nassets/dice.mp3\nassets/snake.mp3\nassets/ladder.mp3\nassets/win.mp3",
        language="text",
    )
    st.markdown(
        "If sounds are missing, the game still works. If the board image is missing, you will only see a warning in the board area."
    )

left, right = st.columns([2.05, 1.0], gap="large")

with left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if not st.session_state.game_started:
        st.markdown("### 👋 Start a game from the sidebar")
        st.markdown(
            """
- Add your board image to `assets/board.png`
- Add optional sound effects to the `assets/` folder
- Then click **Start New Game**
- Tokens will appear on top of the board image automatically
            """
        )
    else:
        active_idx = st.session_state.current_turn if not st.session_state.winner else None
        render_board_image(st.session_state.players, active_idx=active_idx)
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown(
            f'<div class="dice-box">{DICE_FACES[st.session_state.dice_value - 1]}</div>',
            unsafe_allow_html=True,
        )

        button_label = "🤖 AI Turn" if current["is_ai"] else "🎲 Roll Dice"
        if st.button(button_label, use_container_width=True, disabled=bool(st.session_state.winner)):
            take_turn()
            st.rerun()

        if st.session_state.winner:
            if not st.session_state.confetti_shown:
                st.balloons()
                st.session_state.confetti_shown = True
            st.success(f"🏆 Winner: {st.session_state.winner}")
            if st.button("🔁 Play Again", use_container_width=True):
                new_game(
                    st.session_state.players[0]["name"],
                    st.session_state.players[1]["name"],
                    st.session_state.game_mode,
                )
                st.rerun()

        st.markdown("### 🧍 Player Positions")
        for idx, player in enumerate(st.session_state.players):
            badge = "🤖" if player["is_ai"] else "👤"
            active_tag = " ← active" if idx == st.session_state.current_turn and not st.session_state.winner else ""
            st.markdown(
                f'<div class="metric-pill" style="border-color:{player["color"]};">{badge} <strong>{player["name"]}</strong>: {player["position"]}{active_tag}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown("### ✨ Features in this version")
        st.markdown(
            """
- Real board image support
- Token overlay markers
- Dice / snake / ladder / win sounds
- Human vs Human
- Human vs AI
- Leaderboard + winner celebration
            """
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")
info_col, log_col = st.columns([1.05, 1.45], gap="large")

with info_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🏅 Leaderboard")
    df = leaderboard_df()
    st.dataframe(df, use_container_width=True, hide_index=False)
    st.markdown(
        '<div class="small-muted">Tip: leaderboard data is stored in <code>leaderboard.json</code>. On Streamlit Community Cloud, file-based data may reset when the app sleeps, restarts, or redeploys.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with log_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📜 Match Log")
    render_event_log()
    st.markdown('</div>', unsafe_allow_html=True)

play_pending_sound()
maybe_auto_play_ai()
