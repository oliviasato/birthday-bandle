import base64
import subprocess
from pathlib import Path

import requests
import streamlit as st


# -----------------------------
# Page setup
# -----------------------------

st.set_page_config(
    page_title="Normal Bandle",
    layout="centered",
)


# -----------------------------
# Visual styling
# -----------------------------

st.markdown(
    """
    <style>
        .stApp {
            background: #071525;
            color: #f2f4f7;
            font-family: Arial, Helvetica, sans-serif;
        }

        .block-container {
            max-width: 720px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        h1 {
            text-align: center;
            font-size: 2.2rem !important;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 0.25rem;
        }

        h2, h3 {
            font-weight: 700;
            letter-spacing: -0.2px;
        }

        p {
            line-height: 1.35;
        }

        .track-box {
            background: #d9dde3;
            color: #17202b;
            border: 1px solid #eef1f4;
            border-radius: 7px;
            padding: 11px 14px;
            margin: 7px 0;
            font-size: 0.92rem;
        }

        .track-name {
            color: #17202b;
            font-weight: 700;
            letter-spacing: 0.8px;
            font-size: 0.82rem;
            margin-bottom: 4px;
        }

        .locked {
            background: #aeb5be;
            color: #3f4852;
            border-color: #c4c9cf;
        }

        .locked .track-name {
            color: #3f4852;
        }

        .clue-box {
            background: #10263d;
            border: 1px solid #6f91b4;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            margin-top: 18px;
            font-size: 1.1rem;
            font-weight: 700;
        }

        .answer-box {
            background: #132d49;
            border: 1px solid #6f91b4;
            border-radius: 9px;
            padding: 20px;
            text-align: center;
            margin-top: 18px;
        }

        .answer-box h2 {
            color: #ffffff;
            margin-bottom: 8px;
        }

        .stMetric {
            background: #10263d;
            border: 1px solid #284968;
            border-radius: 7px;
            padding: 8px;
        }

        .stMetric label {
            font-size: 0.72rem !important;
        }

        .stMetric [data-testid="stMetricValue"] {
            font-size: 1.05rem;
        }

        audio {
            width: 100%;
        }

        button {
            border-radius: 6px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Audio settings
# -----------------------------

AUDIO_FOLDER = Path(__file__).parent / "audio"

TRACK_NAMES = [
    "drums",
    "bass",
    "misc",
    "backup",
    "star vocals",
]


# -----------------------------
# Combine audio with FFmpeg
# -----------------------------

@st.cache_data
def create_combined_audio(track_count):
    track_paths = [
        AUDIO_FOLDER / f"track{i}.mp3"
        for i in range(1, track_count + 1)
    ]

    missing_files = [
        str(path)
        for path in track_paths
        if not path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing audio file(s): "
            + ", ".join(missing_files)
        )

    command = ["ffmpeg", "-y"]

    for path in track_paths:
        command.extend([
            "-i",
            str(path),
        ])

    filter_text = (
        f"amix=inputs={track_count}:"
        "duration=longest:"
        "dropout_transition=0:"
        "normalize=1"
    )

    command.extend([
        "-filter_complex",
        filter_text,
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-f",
        "wav",
        "pipe:1",
    ])

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        error_message = result.stderr.decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(error_message)

    if not result.stdout:
        raise RuntimeError(
            "FFmpeg produced an empty audio file."
        )

    return result.stdout


# -----------------------------
# Spotify functions
# -----------------------------

@st.cache_data(ttl=3300)
def get_spotify_token(client_id, client_secret):
    credentials = f"{client_id}:{client_secret}"

    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()["access_token"]


@st.cache_data(ttl=300)
def search_spotify(query, client_id, client_secret):
    if not query.strip():
        return []

    token = get_spotify_token(
        client_id,
        client_secret,
    )

    response = requests.get(
        "https://api.spotify.com/v1/search",
        headers={
            "Authorization": f"Bearer {token}",
        },
        params={
            "q": query,
            "type": "track",
            "limit": 8,
        },
        timeout=10,
    )

    response.raise_for_status()

    tracks = response.json().get(
        "tracks",
        {},
    ).get(
        "items",
        [],
    )

    results = []

    for track in tracks:
        artists = ", ".join(
            artist["name"]
            for artist in track.get("artists", [])
        )

        results.append(
            f"{track['name']} — {artists}"
        )

    return results


# -----------------------------
# Session state
# -----------------------------

if "guess_number" not in st.session_state:
    st.session_state.guess_number = 0

if "guesses" not in st.session_state:
    st.session_state.guesses = []

if "clue_shown" not in st.session_state:
    st.session_state.clue_shown = False


# -----------------------------
# Song information
# -----------------------------

info_col1, info_col2, info_col3 = st.columns(3)

with info_col1:
    st.metric("VIEWS", "100 billion")

with info_col2:
    st.metric("GENRE", "Alternative")

with info_col3:
    st.metric("YEAR", "1999/2026")


# -----------------------------
# Title
# -----------------------------

st.title("Normal Bandle")

st.markdown(
    "<p style='text-align:center; color:#aebdce; margin-top:0;'>"
    "Guess the song one track at a time."
    "</p>",
    unsafe_allow_html=True,
)


# -----------------------------
# Determine unlocked tracks
# -----------------------------

current_track_count = min(
    st.session_state.guess_number + 1,
    5,
)


# -----------------------------
# Display instruments
# -----------------------------

for index, track_name in enumerate(TRACK_NAMES):
    track_number = index + 1

    if track_number <= current_track_count:
        st.markdown(
            f"""
            <div class="track-box">
                <div class="track-name">
                    {track_name.upper()}
                </div>
                Unlocked
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="track-box locked">
                <div class="track-name">
                    {track_name.upper()}
                </div>
                Locked
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# Combined audio player
# -----------------------------

try:
    combined_audio = create_combined_audio(
        current_track_count
    )

    st.audio(
        combined_audio,
        format="audio/wav",
    )

except Exception as error:
    st.error("Could not combine the audio.")
    st.code(
        str(error),
        language="text",
    )


# -----------------------------
# Get a clue
# This appears directly below
# the instruments and audio.
# -----------------------------

if st.session_state.guess_number >= 5:
    if not st.session_state.clue_shown:
        if st.button(
            "Get a clue",
            use_container_width=True,
        ):
            st.session_state.clue_shown = True
            st.rerun()

    else:
        st.markdown(
            """
            <div class="clue-box">
                phone a friend
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="answer-box">
                <h2>HAPPY BIRTHDAY IAN</h2>
                <h3>“HAPPY BIRTHDAY IAN”</h3>
                <p>by <strong>Lil Snatch</strong></p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# Guess input
# -----------------------------

st.subheader("Make a guess")

guess_text = st.text_input(
    "Search for a song or artist:",
    placeholder="Start typing a song title...",
)


# -----------------------------
# Spotify credentials
# -----------------------------

try:
    client_id = st.secrets.get(
        "SPOTIFY_CLIENT_ID",
        "",
    )

    client_secret = st.secrets.get(
        "SPOTIFY_CLIENT_SECRET",
        "",
    )

except Exception:
    client_id = ""
    client_secret = ""


# -----------------------------
# Spotify search results
# -----------------------------

spotify_results = []

if guess_text.strip() and len(guess_text.strip()) >= 2:
    if client_id and client_secret:
        try:
            spotify_results = search_spotify(
                guess_text,
                client_id,
                client_secret,
            )

        except Exception:
            st.caption(
                "Spotify search is unavailable. "
                "You can still submit your typed guess."
            )

    else:
        st.caption(
            "Spotify credentials are not set. "
            "You can still submit your typed guess."
        )


if spotify_results:
    selected_result = st.selectbox(
        "Choose a search result:",
        spotify_results,
    )

    final_guess = selected_result

else:
    final_guess = guess_text.strip()


# -----------------------------
# Submit guess
# -----------------------------

guess_button_disabled = (
    not final_guess
    or st.session_state.guess_number >= 5
)

if st.button(
    "Submit Guess",
    disabled=guess_button_disabled,
    use_container_width=True,
):
    st.session_state.guess_number += 1

    st.session_state.guesses.append(
        final_guess
    )

    st.rerun()


# -----------------------------
# Guess history
# -----------------------------

if st.session_state.guesses:
    st.subheader("Guesses")

    for number, guess in enumerate(
        st.session_state.guesses,
        start=1,
    ):
        st.write(
            f"**Guess {number}:** "
            f"{guess} — ❌"
        )
