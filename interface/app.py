#Streamlit  web arayüzü

import sys
from pathlib import Path

# Proje ana dizinini Python yoluna ekle (core modüllerini import edebilmek için)
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from PIL import Image

from web_state import read_live_results
from config import WATCH_FOLDER

try:
    from core.vector_db import search_in_db
except Exception:
    search_in_db = None

try:
    from core.encoder import encode_text
except Exception:
    encode_text = None

try:
    from graphclip_worker import search_graphclip
except Exception:
    search_graphclip = None


def get_selected_mode(live_results: list[dict]) -> str | None:
    for item in reversed(live_results):
        if item.get("status") == "selected_mode":
            return item.get("mode")
    return None

# Sayfa yapılandırması (Geniş ekran, başlık ve ikon)
st.set_page_config(
    page_title="Smart Gallery",
    page_icon="🖼️",
    layout="wide",
)

# Ana Başlık ve Açıklama
st.title("Smart Photo Album")
st.markdown("An AI-powered semantic search engine. You can search by typing in the image's content, color, or feel.")
st.divider()

if "last_results" not in st.session_state:
    st.session_state.last_results = []
if "last_mode" not in st.session_state:
    st.session_state.last_mode = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_error" not in st.session_state:
    st.session_state.last_error = None

with st.sidebar:
    st.subheader("Live scan feed")
    live_results = read_live_results(limit=10)
    selected_mode = get_selected_mode(read_live_results(limit=200))
    if selected_mode:
        st.caption(f"Selected mode: {selected_mode}")
    if live_results:
        for item in reversed(live_results):
            model = item.get("model", "unknown")
            status = item.get("status", "unknown")
            if status == "result":
                similarity = item.get("similarity")
                st.write(f"{model}: {status} | similarity={similarity}")
            else:
                st.write(f"{model}: {status}")
    else:
        st.info("Henüz bir tarama sonucu yok.")

search_query = st.text_input(
    "What would you like to search for?",
    placeholder="Examples: 'blue sea', 'red car', 'dog', 'man fishing'...",
    max_chars=100,
)
search_clicked = st.button("Search", type="primary")

if search_clicked:
    st.session_state.last_query = search_query
    st.session_state.last_error = None
    st.session_state.last_results = []
    st.session_state.last_mode = None

    if not search_query.strip():
        st.session_state.last_error = "Please enter a search query."
    else:
        with st.spinner("AI is scanning the photos..."):
            try:
                should_use_graphclip = selected_mode == "graphclip" or (search_in_db is None)

                if should_use_graphclip:
                    if search_graphclip is None:
                        st.session_state.last_error = "GraphCLIP arama motoru yüklenemedi."
                    else:
                        st.session_state.last_results = search_graphclip(
                            text=search_query.strip(),
                            image_folder=WATCH_FOLDER,
                            n_results=8,
                        )
                        st.session_state.last_mode = "graphclip"
                elif encode_text is None:
                    st.session_state.last_error = "OpenCLIP encoder yüklenemedi. Önce OpenCLIP modeli kurulu olmalı."
                else:
                    query_vector = encode_text(search_query.strip())
                    st.session_state.last_results = search_in_db(query_vector, n_results=8)
                    st.session_state.last_mode = "openclip"
            except Exception as exc:
                st.session_state.last_error = f"A technical error occurred during the search.: {exc}"

if st.session_state.last_error:
    st.warning(st.session_state.last_error)
elif st.session_state.last_query:
    if not st.session_state.last_results:
        st.warning("No matching photos were found.")
    else:
        st.success(f"**'{st.session_state.last_query}'** The best matches have been found!")
        cols = st.columns(4)
        for index, res in enumerate(st.session_state.last_results):
            col = cols[index % 4]
            with col:
                try:
                    if st.session_state.last_mode == "graphclip":
                        img = Image.open(res["image_path"])
                        st.image(img)
                        st.caption(f"similarity: **%{res['similarity'] * 100:.2f}**")
                    else:
                        similarity_score = (1 - res["distance"]) * 100
                        image_path = res["image_path"]
                        img = Image.open(image_path)
                        st.image(img)
                        st.caption(f"similarity: **%{similarity_score:.2f}**")
                except FileNotFoundError:
                    st.error("The photo was not found on the disk.")
