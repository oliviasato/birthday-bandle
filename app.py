import base64
# import json
from pathlib import Path

import requests
import streamlit as st
# import streamlit.components.v1 as components

from io import BytesIO
from pydub import AudioSegment


# --------------------------------------------------
# Page settings
# --------------------------------------------------

st.set_page_config(
    page_title="Normal Bandle",
    page_icon="🎵",
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

        .song-info {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 25px;
        }

        .info-box {
            background: #292331;
            border: 1px solid #51445c;
            border-radius: 12px;
            padding: 14px 8px;
            text-align: center;
        }

        .info-label {
            display: block;
            color: #aaa1b3;
            font-size: 12px;
            margin-bottom: 5px;
        }

        .info-value {
            display: block;
            color: #f5ba3c;
            font-weight: bold;
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

        @media (max-width: 500px) {
            .song-info {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Spotify search
# --------------------------------------------------

@st.cache_data(ttl=3300)
def get_spotify_token(client_id, client_secret):
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=10,
    )

    response.raise_for_status()
    return response.json()["access_token"]


@st.cache_data(ttl=300)
def search_spotify(query, client_id, client_secret):
    if not query.strip():
        return []

    token = get_spotify_token(client_id, client_secret)

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

    tracks = response.json().get("tracks", {}).get("items", [])

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
# Audio mixing
# --------------------------------------------------

AUDIO_FOLDER = Path(__file__).parent / "audio"

TRACK_NAMES = [
    "drums",
    "bass",
    "misc",
    "backup",
    "star vocals",
]

TRACK_FILES = [
    AUDIO_FOLDER / "track1.mp3",
    AUDIO_FOLDER / "track2.mp3",
    AUDIO_FOLDER / "track3.mp3",
    AUDIO_FOLDER / "track4.mp3",
    AUDIO_FOLDER / "track5.mp3",
]


@st.cache_data
def load_audio_as_base64(file_path):
    with open(file_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode("utf-8")


def get_audio_tracks(number_of_tracks):
    audio_tracks = []

    for file_path in TRACK_FILES[:number_of_tracks]:
        if file_path.exists():
            audio_tracks.append(
                load_audio_as_base64(file_path)
            )

    return audio_tracks


@st.cache_data
def create_combined_audio(track_count):
    """
    Mixes track1.mp3 through trackN.mp3 together.
    Every track starts at time zero.
    Shorter tracks simply end earlier.
    """

    audio_folder = Path(__file__).parent / "audio"

    track_paths = [
        audio_folder / f"track{i}.mp3"
        for i in range(1, track_count + 1)
    ]

    missing_files = [
        str(path)
        for path in track_paths
        if not path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing audio file(s): " + ", ".join(missing_files)
        )

    # Load the first track as the base.
    combined = AudioSegment.from_file(
        track_paths[0],
        format="mp3",
    )

    # Standardize audio format for reliable mixing.
    combined = (
        combined
        .set_frame_rate(44100)
        .set_channels(2)
        .set_sample_width(2)
    )

    # Add each later track at time zero.
    for track_path in track_paths[1:]:
        next_track = AudioSegment.from_file(
            track_path,
            format="mp3",
        )

        next_track = (
            next_track
            .set_frame_rate(44100)
            .set_channels(2)
            .set_sample_width(2)
        )

        combined = combined.overlay(next_track)

    # Convert the final mix to WAV bytes.
    output = BytesIO()

    combined.export(
        output,
        format="wav",
    )

    return output.getvalue()


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "guess_number" not in st.session_state:
    st.session_state.guess_number = 0

if "guesses" not in st.session_state:
    st.session_state.guesses = []

if "game_won" not in st.session_state:
    st.session_state.game_won = False


# Top-of-page song info

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

st.title("🎵 Normal Bandle")

st.markdown(
    "<p style='text-align:center; color:#c8bfd0;'>"
    "Guess the song one track at a time."
    "</p>",
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Track labels
# --------------------------------------------------

current_track_count = min(
    st.session_state.guess_number + 1,
    5,
)

for index, track_name in enumerate(TRACK_NAMES):
    track_number = index + 1

    if track_number <= current_track_count:
        st.markdown(
            f"""
            <div class="track-box">
                <div class="track-name">
                    {track_name.upper()}
                </div>
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
# One current combined audio player
# --------------------------------------------------

audio_tracks = get_audio_tracks(current_track_count)

if audio_tracks:
    show_combined_audio(audio_tracks)
else:
    st.error(
        "No audio files were found. Make sure your files are inside "
        "the audio folder and are named track1.mp3 through track5.mp3."
    )


# --------------------------------------------------
# Guess search
# --------------------------------------------------

st.subheader("Make a guess")

guess_text = st.text_input(
    "Search for a song or artist:",
    placeholder="Start typing a song title...",
)

client_id = st.secrets.get("SPOTIFY_CLIENT_ID", "")
client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET", "")

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
# Guess button
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

    st.session_state.guesses.append(final_guess)

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
            st.write(f"**Guess {number}:** {guess} — ❌")
        else:
            st.write(f"**Guess {number}:** {guess} — 🎉")


# --------------------------------------------------
# Final reveal
# --------------------------------------------------

if st.session_state.game_won:
    st.markdown(
        """
        <div class="answer-box">
            <div style="font-size: 32px;">🎉 🎂 🎉</div>
            <h2>HAPPY BIRTHDAY IAN</h2>
            <h3>“HAPPY BIRTHDAY IAN”</h3>
            <p>by <strong>Lil Snatch</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
