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
    page_title="Akıllı Galeri",
    page_icon="🖼️",
    layout="wide"
)

# Ana Başlık ve Açıklama
st.title(" Akıllı Fotoğraf Albümü")
st.markdown("Yapay zeka destekli anlamsal arama motoru. Görselin içeriğini, rengini veya hissini yazarak arama yapabilirsiniz.")
st.divider()

# Arama Çubuğu
search_query = st.text_input(
    "Ne aramak istersin?", 
    placeholder="Örn: 'mavi deniz', 'kırmızı araba', 'köpek', 'balık tutan adam'...",
    max_chars=100
)

# Eğer arama çubuğuna bir şey yazıldıysa işlemi başlat
if search_query:
    with st.spinner("Yapay zeka fotoğrafları tarıyor..."):
        try:
            # 1. Kullanıcının metnini vektöre çevir
            query_vector = encode_text(search_query)
            
            # 2. ChromaDB'de en çok benzeyen 6 fotoğrafı ara
            # Ekranda daha güzel durması için 3 yerine 6 sonuç getiriyoruz
            results = search_in_db(query_vector, n_results=6)
            
            if not results:
                st.warning("Veritabanında eşleşen fotoğraf bulunamadı. Klasörünüzü kontrol edin.")
            else:
                st.success(f"**'{search_query}'** için en iyi eşleşmeler bulundu!")
                
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
                            st.caption(f" Benzerlik: **%{similarity_score:.2f}**")
                            
                        except FileNotFoundError:
                            st.error(f"Fotoğraf diskte bulunamadı: {res['filename']}")
                            
        except Exception as e:
            st.error(f"Arama sırasında teknik bir hata oluştu: {e}")
