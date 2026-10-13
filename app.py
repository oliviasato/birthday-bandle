{\rtf1\ansi\ansicpg1252\cocoartf2870
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import base64\
from pathlib import Path\
\
import requests\
import streamlit as st\
\
\
# ---------- Page setup ----------\
\
st.set_page_config(\
    page_title="Birthday Bandle",\
    page_icon="\uc0\u55356 \u57269 ",\
    layout="centered",\
)\
\
st.markdown(\
    """\
    <style>\
        .stApp \{\
            background: linear-gradient(180deg, #321d43, #17131d);\
            color: white;\
        \}\
\
        h1, h2, h3 \{\
            text-align: center;\
        \}\
\
        .subtitle \{\
            text-align: center;\
            color: #c8bfd0;\
            margin-bottom: 30px;\
        \}\
\
        .track-box \{\
            background: #292331;\
            border: 1px solid #51445c;\
            border-radius: 14px;\
            padding: 16px;\
            margin: 12px 0;\
        \}\
\
        .locked \{\
            color: #99909f;\
        \}\
\
        .track-title \{\
            color: #f5ba3c;\
            font-weight: bold;\
            letter-spacing: 2px;\
            margin-bottom: 8px;\
        \}\
\
        .answer-box \{\
            background: #382548;\
            border: 2px solid #f5ba3c;\
            border-radius: 18px;\
            padding: 25px;\
            text-align: center;\
            margin-top: 25px;\
        \}\
\
        .answer-box h2 \{\
            color: #f5ba3c;\
        \}\
    </style>\
    """,\
    unsafe_allow_html=True,\
)\
\
\
# ---------- Spotify functions ----------\
\
@st.cache_data(ttl=3300)\
def get_spotify_token(client_id, client_secret):\
    """Get a temporary Spotify API token."""\
    credentials = f"\{client_id\}:\{client_secret\}"\
    encoded_credentials = base64.b64encode(\
        credentials.encode("utf-8")\
    ).decode("utf-8")\
\
    response = requests.post(\
        "https://accounts.spotify.com/api/token",\
        headers=\{\
            "Authorization": f"Basic \{encoded_credentials\}",\
            "Content-Type": "application/x-www-form-urlencoded",\
        \},\
        data=\{"grant_type": "client_credentials"\},\
        timeout=10,\
    )\
\
    response.raise_for_status()\
    return response.json()["access_token"]\
\
\
@st.cache_data(ttl=300)\
def search_spotify(query, client_id, client_secret):\
    """Search Spotify for tracks matching the guess."""\
    if not query.strip():\
        return []\
\
    token = get_spotify_token(client_id, client_secret)\
\
    response = requests.get(\
        "https://api.spotify.com/v1/search",\
        headers=\{"Authorization": f"Bearer \{token\}"\},\
        params=\{\
            "q": query,\
            "type": "track",\
            "limit": 8,\
        \},\
        timeout=10,\
    )\
\
    response.raise_for_status()\
\
    tracks = response.json().get("tracks", \{\}).get("items", [])\
\
    results = []\
\
    for track in tracks:\
        artists = ", ".join(\
            artist["name"] for artist in track.get("artists", [])\
        )\
\
        results.append(\{\
            "label": f"\{track['name']\} \'97 \{artists\}",\
            "name": track["name"],\
            "artist": artists,\
        \})\
\
    return results\
\
\
# ---------- Session state ----------\
\
if "guess_number" not in st.session_state:\
    st.session_state.guess_number = 0\
\
if "guesses" not in st.session_state:\
    st.session_state.guesses = []\
\
if "game_won" not in st.session_state:\
    st.session_state.game_won = False\
\
\
# ---------- Header ----------\
\
st.markdown(\
    '<div class="subtitle">IAN\\'S BIRTHDAY EDITION</div>',\
    unsafe_allow_html=True,\
)\
\
st.title("\uc0\u55356 \u57269  Birthday Bandle")\
\
st.markdown(\
    '<p class="subtitle">Guess the song one track at a time.</p>',\
    unsafe_allow_html=True,\
)\
\
\
# ---------- Audio tracks ----------\
\
audio_folder = Path("audio")\
\
for track_number in range(1, 6):\
    unlocked = track_number <= st.session_state.guess_number + 1\
\
    if unlocked:\
        st.markdown(\
            f"""\
            <div class="track-box">\
                <div class="track-title">TRACK \{track_number\}</div>\
            </div>\
            """,\
            unsafe_allow_html=True,\
        )\
\
        audio_file = audio_folder / f"track\{track_number\}.mp3"\
\
        if audio_file.exists():\
            st.audio(audio_file)\
        else:\
            st.error(f"Missing file: \{audio_file\}")\
\
    else:\
        st.markdown(\
            f"""\
            <div class="track-box locked">\
                <div class="track-title">TRACK \{track_number\}</div>\
                \uc0\u55357 \u56594  Locked\
            </div>\
            """,\
            unsafe_allow_html=True,\
        )\
\
\
# ---------- Spotify search ----------\
\
st.subheader("Make a guess")\
\
guess_text = st.text_input(\
    "Search for a song or artist:",\
    placeholder="Start typing a song title...",\
)\
\
\
# Read Spotify credentials from Streamlit Secrets.\
# These should be added in Streamlit's deployment settings.\
client_id = st.secrets.get("SPOTIFY_CLIENT_ID", "")\
client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET", "")\
\
spotify_results = []\
spotify_error = None\
\
if guess_text.strip() and len(guess_text.strip()) >= 2:\
    if client_id and client_secret:\
        try:\
            spotify_results = search_spotify(\
                guess_text,\
                client_id,\
                client_secret,\
            )\
        except Exception:\
            spotify_error = (\
                "Spotify search is temporarily unavailable. "\
                "You can still submit your typed guess."\
            )\
    else:\
        spotify_error = (\
            "Spotify credentials have not been added yet. "\
            "You can still submit your typed guess."\
        )\
\
if spotify_results:\
    selected_guess = st.selectbox(\
        "Choose a result:",\
        options=spotify_results,\
        format_func=lambda result: result["label"],\
    )\
    final_guess = selected_guess["label"]\
else:\
    final_guess = guess_text.strip()\
\
if spotify_error:\
    st.caption(spotify_error)\
\
\
# ---------- Guess button ----------\
\
button_disabled = (\
    not final_guess\
    or st.session_state.guess_number >= 5\
    or st.session_state.game_won\
)\
\
if st.button(\
    "Submit Guess",\
    disabled=button_disabled,\
    use_container_width=True,\
):\
    st.session_state.guess_number += 1\
\
    st.session_state.guesses.append(\{\
        "number": st.session_state.guess_number,\
        "text": final_guess,\
    \})\
\
    if st.session_state.guess_number >= 5:\
        st.session_state.game_won = True\
\
    st.rerun()\
\
\
# ---------- Guess history ----------\
\
if st.session_state.guesses:\
    st.subheader("Guesses")\
\
    for guess in st.session_state.guesses:\
        if guess["number"] < 5:\
            st.write(f"**Guess \{guess['number']\}:** \{guess['text']\} \'97 \uc0\u10060 ")\
        else:\
            st.write(f"**Guess \{guess['number']\}:** \{guess['text']\} \'97 \uc0\u55356 \u57225 ")\
\
\
# ---------- Final answer ----------\
\
if st.session_state.game_won:\
    st.markdown(\
        """\
        <div class="answer-box">\
            <div style="font-size: 32px;">\uc0\u55356 \u57225  \u55356 \u57218  \u55356 \u57225 </div>\
            <h2>HAPPY BIRTHDAY IAN</h2>\
            <h3>\'93HAPPY BIRTHDAY IAN\'94</h3>\
            <p>by <strong>Lil Snatch</strong></p>\
            <br>\
            <p><strong>100 billion views</strong></p>\
            <p>Genre: <strong>Alternative</strong></p>\
            <p>Release year: <strong>1999/2026</strong></p>\
        </div>\
        """,\
        unsafe_allow_html=True,\
    )}