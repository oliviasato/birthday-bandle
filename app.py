import base64
import subprocess
from pathlib import Path

import requests
import streamlit as st


# --------------------------------------------------
# Page setup
# --------------------------------------------------

st.set_page_config(
    page_title="Normal Bandle",
    layout="centered",
)


# --------------------------------------------------
# Styling
# --------------------------------------------------

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #321d43, #17131d);
            color: white;
        }

        .track-box {
            background: #292331;
            border: 1px solid #51445c;
            border-radius: 14px;
            padding: 16px;
            margin: 12px 0;
        }

        .track-name {
            color: #f5ba3c;
            font-weight: bold;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }

        .locked {
            color: #99909f;
            opacity: 0.6;
        }

        .answer-box {
            background: #382548;
            border: 2px solid #f5ba3c;
            border-radius: 18px;
            padding: 25px;
            text-align: center;
            margin-top: 25px;
        }

        .answer-box h2 {
            color: #f5ba3c;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Audio settings
# --------------------------------------------------

AUDIO_FOLDER = Path(__file__).parent / "audio"

TRACK_NAMES = [
    "drums",
    "bass",
    "misc",
    "backup",
    "star vocals",
]


# --------------------------------------------------
# Audio mixing with FFmpeg
# --------------------------------------------------

@st.cache_data
def create_combined_audio(track_count):
    """
    Mixes track1.mp3 through trackN.mp3.

    Every track begins at time zero.
    Tracks are not stretched or time-distorted.
    Shorter tracks end naturally.
    The combined audio lasts as long as the longest track.
    """

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

    # Add every MP3 as an input.
    for path in track_paths:
        command.extend([
            "-i",
            str(path),
        ])

    # Put every track into the mix from time zero.
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

        raise RuntimeError(
            "FFmpeg could not mix the audio:\n"
            + error_message
        )

    if not result.stdout:
        raise RuntimeError(
            "FFmpeg produced an empty audio file."
        )

    return result.stdout


# --------------------------------------------------
# Spotify API functions
# --------------------------------------------------

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
        artist_names = ", ".join(
            artist["name"]
            for artist in track.get("artists", [])
        )

        results.append(
            f"{track['name']} — {artist_names}"
        )

    return results


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "guess_number" not in st.session_state:
    st.session_state.guess_number = 0

if "guesses" not in st.session_state:
    st.session_state.guesses = []

if "game_won" not in st.session_state:
    st.session_state.game_won = False


# --------------------------------------------------
# Song information at the top
# --------------------------------------------------

info_col1, info_col2, info_col3 = st.columns(3)

with info_col1:
    st.metric("VIEWS", "100 billion")

with info_col2:
    st.metric("GENRE", "Alternative")

with info_col3:
    st.metric("YEAR", "1999/2026")


# --------------------------------------------------
# Title
# --------------------------------------------------

st.title("Normal Bandle")

st.markdown(
    "<p style='text-align:center; color:#c8bfd0;'>"
    "Guess the song one track at a time."
    "</p>",
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Determine unlocked tracks
# --------------------------------------------------

current_track_count = min(
    st.session_state.guess_number + 1,
    5,
)


# --------------------------------------------------
# Display track labels
# --------------------------------------------------

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
                🔒 Locked
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# Display one combined audio player
# --------------------------------------------------

try:
    combined_audio = create_combined_audio(
        current_track_count
    )

    st.audio(
        combined_audio,
        format="audio/wav",
    )

    st.caption(
        "All unlocked tracks are combined from the beginning."
    )

except Exception as error:
    st.error(
        "Could not combine the audio."
    )

    st.code(
        str(error),
        language="text",
    )


# --------------------------------------------------
# Guess search
# --------------------------------------------------

st.subheader("Make a guess")

guess_text = st.text_input(
    "Search for a song or artist:",
    placeholder="Start typing a song title...",
)


# Read Spotify credentials safely.
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
                "Spotify search is unavailable right now. "
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


# --------------------------------------------------
# Submit guess
# --------------------------------------------------

button_disabled = (
    not final_guess
    or st.session_state.guess_number >= 5
    or st.session_state.game_won
)

if st.button(
    "Submit Guess",
    disabled=button_disabled,
    use_container_width=True,
):
    st.session_state.guess_number += 1

    st.session_state.guesses.append(
        final_guess
    )

    if st.session_state.guess_number >= 5:
        st.session_state.game_won = True

    st.rerun()


# --------------------------------------------------
# Guess history
# --------------------------------------------------

if st.session_state.guesses:
    st.subheader("Guesses")

    for number, guess in enumerate(
        st.session_state.guesses,
        start=1,
    ):
        if number < 5:
            st.write(
                f"**Guess {number}:** "
                f"{guess} — ❌"
            )
        else:
            st.write(
                f"**Guess {number}:** "
                f"{guess} — 🎉"
            )


# --------------------------------------------------
# Final answer
# --------------------------------------------------

if st.session_state.game_won:
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
