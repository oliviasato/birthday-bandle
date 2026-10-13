import base64
import json
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components


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


def show_combined_audio(audio_tracks):
    """
    Mixes all currently unlocked MP3 tracks into one browser audio player.
    """

    tracks_json = json.dumps(audio_tracks)

    mixer_html = f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin: 0;
        padding: 0;
        background: transparent;
        font-family: Arial, sans-serif;
        color: white;
    ">
        <div id="message" style="margin-bottom: 8px;">
            Preparing combined audio...
        </div>

        <audio
            id="player"
            controls
            style="width: 100%; display: none;"
        ></audio>

        <script>
            const trackData = {tracks_json};

            function base64ToArrayBuffer(base64) {{
                const binary = atob(base64);
                const bytes = new Uint8Array(binary.length);

                for (let i = 0; i < binary.length; i++) {{
                    bytes[i] = binary.charCodeAt(i);
                }}

                return bytes.buffer;
            }}

            function audioBufferToWav(buffer) {{
                const numberOfChannels = buffer.numberOfChannels;
                const sampleRate = buffer.sampleRate;
                const bytesPerSample = 2;
                const blockAlign = numberOfChannels * bytesPerSample;
                const dataSize = buffer.length * blockAlign;

                const arrayBuffer = new ArrayBuffer(44 + dataSize);
                const view = new DataView(arrayBuffer);

                function writeString(offset, text) {{
                    for (let i = 0; i < text.length; i++) {{
                        view.setUint8(offset + i, text.charCodeAt(i));
                    }}
                }}

                writeString(0, "RIFF");
                view.setUint32(4, 36 + dataSize, true);
                writeString(8, "WAVE");
                writeString(12, "fmt ");

                view.setUint32(16, 16, true);
                view.setUint16(20, 1, true);
                view.setUint16(22, numberOfChannels, true);
                view.setUint32(24, sampleRate, true);
                view.setUint32(
                    28,
                    sampleRate * blockAlign,
                    true
                );
                view.setUint16(32, blockAlign, true);
                view.setUint16(34, 16, true);

                writeString(36, "data");
                view.setUint32(40, dataSize, true);

                let offset = 44;

                for (let i = 0; i < buffer.length; i++) {{
                    for (let channel = 0; channel < numberOfChannels; channel++) {{
                        let sample = buffer.getChannelData(channel)[i];

                        sample = Math.max(-1, Math.min(1, sample));

                        const integerSample =
                            sample < 0
                                ? sample * 0x8000
                                : sample * 0x7FFF;

                        view.setInt16(
                            offset,
                            Math.round(integerSample),
                            true
                        );

                        offset += 2;
                    }}
                }}

                return new Blob(
                    [arrayBuffer],
                    {{ type: "audio/wav" }}
                );
            }}

            async function createMixedAudio() {{
                const message = document.getElementById("message");
                const player = document.getElementById("player");

                if (!trackData.length) {{
                    message.textContent = "No audio tracks found.";
                    return;
                }}

                try {{
                    const decodeContext = new AudioContext();
                    const decodedTracks = [];

                    for (const encodedTrack of trackData) {{
                        const arrayBuffer =
                            base64ToArrayBuffer(encodedTrack);

                        const decoded =
                            await decodeContext.decodeAudioData(
                                arrayBuffer.slice(0)
                            );

                        decodedTracks.push(decoded);
                    }}

                    const sampleRate = 44100;

                    const longestDuration = Math.max(
                        ...decodedTracks.map(
                            track => track.duration
                        )
                    );

                    const frameCount = Math.ceil(
                        longestDuration * sampleRate
                    );

                    const offlineContext =
                        new OfflineAudioContext(
                            2,
                            frameCount,
                            sampleRate
                        );

                    for (const decodedTrack of decodedTracks) {{
                        const source =
                            offlineContext.createBufferSource();

                        source.buffer = decodedTrack;
                        source.connect(
                            offlineContext.destination
                        );
                        source.start(0);
                    }}

                    const renderedAudio =
                        await offlineContext.startRendering();

                    const wavBlob =
                        audioBufferToWav(renderedAudio);

                    const audioUrl =
                        URL.createObjectURL(wavBlob);

                    player.src = audioUrl;
                    player.style.display = "block";
                    message.textContent =
                        "All unlocked tracks are combined:";

                }} catch (error) {{
                    console.error(error);
                    message.textContent =
                        "Audio error: " + error.message;
                }}
            }}

            createMixedAudio();
        </script>
    </body>
    </html>
    """

    components.html(mixer_html, height=85)


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
