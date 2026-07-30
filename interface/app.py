#Streamlit  web arayüzü

import sys
import os
from pathlib import Path

# Proje ana dizinini Python yoluna ekle (core modüllerini import edebilmek için)
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from PIL import Image

from core.encoder import encode_text
from core.vector_db import search_in_db

# Sayfa yapılandırması (Geniş ekran, başlık ve ikon)
st.set_page_config(
    page_title="Smart Gallery",
    page_icon="🖼️",
    layout="wide"
)

# Ana Başlık ve Açıklama
st.title(" Smart Photo Album")
st.markdown("An AI-powered semantic search engine. You can search by typing in the image's content, color, or feel.")
st.divider()

# Arama Çubuğu
search_query = st.text_input(
    "What would you like to search for?", 
    placeholder="Examples: 'blue sea', 'red car', 'dog', 'man fishing'...",
    max_chars=100
)

# Eğer arama çubuğuna bir şey yazıldıysa işlemi başlat
if search_query:
    with st.spinner("AI is scanning the photos..."):
        try:
            # 1. Kullanıcının metnini vektöre çevir
            query_vector = encode_text(search_query)
            
            # 2. ChromaDB'de en çok benzeyen 6 fotoğrafı ara
            # Ekranda daha güzel durması için 3 yerine 6 sonuç getiriyoruz
            results = search_in_db(query_vector, n_results=6)
            
            if not results:
                st.warning("No matching photos were found in the database. Please check your folder.")
            else:
                st.success(f"**'{search_query}'** The best matches have been found!")
                
                # Fotoğrafları ekranda 3 sütunlu bir Grid (Izgara) yapısında göstermek için
                cols = st.columns(3)
                
                for index, res in enumerate(results):
                    # Sütun sırasını belirle (0, 1, 2)
                    col = cols[index % 3]
                    
                    with col:
                        # Benzerlik skorunu yüzdeye çevir
                        similarity_score = (1 - res['distance']) * 100
                        image_path = res['image_path']
                        
                        try:
                            # Fotoğrafı diskten oku ve ekrana bas
                            img = Image.open(image_path)
                            
                            # Resim gösterimi ve altında benzerlik oranı
                            st.image(img, use_column_width=True)
                            st.caption(f"similarity: **%{similarity_score:.2f}**")
                            
                        except FileNotFoundError:
                            st.error(f"The photo was not found on the disk.: {res['filename']}")
                            
        except Exception as e:
            st.error(f"A technical error occurred during the search.: {e}")
