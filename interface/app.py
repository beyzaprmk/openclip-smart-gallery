#Streamlit  web arayüzü

import sys
from concurrent.futures import ThreadPoolExecutor
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


def run_openclip_search(text: str) -> list[dict]:
    if search_in_db is None:
        raise RuntimeError("ChromaDB bağlantısı hazır değil.")
    if encode_text is None:
        raise RuntimeError("OpenCLIP encoder yüklenemedi.")
    query_vector = encode_text(text)
    return search_in_db(query_vector, n_results=8)


def render_openclip_results(results: list[dict]) -> None:
    if not results:
        st.warning("OpenCLIP: eşleşen fotoğraf bulunamadı.")
        return

    grid = st.columns(2)
    for index, res in enumerate(results):
        with grid[index % 2]:
            try:
                similarity_score = (1 - res["distance"]) * 100
                img = Image.open(res["image_path"])
                st.image(img)
                st.caption(f"similarity: **%{similarity_score:.2f}**")
            except FileNotFoundError:
                st.error("The photo was not found on the disk.")


def render_graphclip_results(results: list[dict]) -> None:
    if not results:
        st.warning("GraphCLIP: eşleşen fotoğraf bulunamadı.")
        return

    grid = st.columns(2)
    for index, res in enumerate(results):
        with grid[index % 2]:
            try:
                img = Image.open(res["image_path"])
                st.image(img)
                st.caption(f"similarity: **%{res['similarity'] * 100:.2f}**")
            except FileNotFoundError:
                st.error("The photo was not found on the disk.")

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

if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "openclip_results" not in st.session_state:
    st.session_state.openclip_results = []
if "graphclip_results" not in st.session_state:
    st.session_state.graphclip_results = []
if "openclip_error" not in st.session_state:
    st.session_state.openclip_error = None
if "graphclip_error" not in st.session_state:
    st.session_state.graphclip_error = None
if "effective_mode" not in st.session_state:
    st.session_state.effective_mode = None

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
    st.session_state.openclip_results = []
    st.session_state.graphclip_results = []
    st.session_state.openclip_error = None
    st.session_state.graphclip_error = None
    st.session_state.effective_mode = None

    if not search_query.strip():
        st.session_state.openclip_error = "Please enter a search query."
    else:
        with st.spinner("AI is scanning the photos..."):
            try:
                query = search_query.strip()
                mode = selected_mode or ("graphclip" if search_in_db is None else "openclip")
                st.session_state.effective_mode = mode

                if mode == "both":
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        openclip_future = executor.submit(run_openclip_search, query)
                        graphclip_future = None
                        if search_graphclip is None:
                            st.session_state.graphclip_error = "GraphCLIP arama motoru yüklenemedi."
                        else:
                            graphclip_future = executor.submit(
                                search_graphclip,
                                query,
                                WATCH_FOLDER,
                                8,
                            )

                        try:
                            st.session_state.openclip_results = openclip_future.result()
                        except Exception as exc:
                            st.session_state.openclip_error = f"OpenCLIP error: {exc}"

                        if graphclip_future is not None:
                            try:
                                st.session_state.graphclip_results = graphclip_future.result()
                            except Exception as exc:
                                st.session_state.graphclip_error = f"GraphCLIP error: {exc}"

                elif mode == "graphclip":
                    if search_graphclip is None:
                        st.session_state.graphclip_error = "GraphCLIP arama motoru yüklenemedi."
                    else:
                        st.session_state.graphclip_results = search_graphclip(
                            text=query,
                            image_folder=WATCH_FOLDER,
                            n_results=8,
                        )
                else:
                    st.session_state.openclip_results = run_openclip_search(query)
            except Exception as exc:
                st.session_state.openclip_error = f"A technical error occurred during the search.: {exc}"

if st.session_state.last_query:
    if st.session_state.effective_mode == "both":
        st.success(f"**'{st.session_state.last_query}'** Model sonuçları hazır.")
        left, right = st.columns(2)
        with left:
            st.subheader("OpenCLIP")
            if st.session_state.openclip_error:
                st.warning(st.session_state.openclip_error)
            else:
                render_openclip_results(st.session_state.openclip_results)
        with right:
            st.subheader("GraphCLIP")
            if st.session_state.graphclip_error:
                st.warning(st.session_state.graphclip_error)
            else:
                render_graphclip_results(st.session_state.graphclip_results)
    else:
        if st.session_state.effective_mode == "graphclip":
            if st.session_state.graphclip_error:
                st.warning(st.session_state.graphclip_error)
            else:
                st.success(f"**'{st.session_state.last_query}'** The best matches have been found!")
                render_graphclip_results(st.session_state.graphclip_results)
        else:
            if st.session_state.openclip_error:
                st.warning(st.session_state.openclip_error)
            else:
                st.success(f"**'{st.session_state.last_query}'** The best matches have been found!")
                render_openclip_results(st.session_state.openclip_results)
