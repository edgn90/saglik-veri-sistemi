import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io

# --- 1. GOOGLE SHEETS BAĞLANTISI ---
def connect_db():
    # Streamlit Secrets'tan bilgileri al
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Secrets içindeki JSON verisini kullan
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Tabloyu aç (Tablo adının 'saglik_verileri' olduğundan emin olun)
    sheet = client.open("saglik_verileri").sheet1
    return sheet

def veri_ekle(kullanici, bolge, asi_sayisi, performans_puani):
    sheet = connect_db()
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Yeni satırı ekle
    sheet.append_row([tarih, kullanici, bolge, asi_sayisi, performans_puani])

def verileri_getir():
    sheet = connect_db()
    # Tüm verileri al ve DataFrame'e çevir
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def veri_sil(satir_numarasi):
    sheet = connect_db()
    # Google Sheets'te satır sil (Header 1. satır olduğu için +2 eklenir genelde ama get_all_records mantığına göre index+2)
    sheet.delete_rows(satir_numarasi)

# --- 2. KULLANICI GİRİŞİ (SABİT) ---
# Gerçek projede kullanıcıları da ayrı bir sheet'te tutabilirsiniz.
# Şimdilik basitlik için admin/user sabit kalsın.
KULLANICILAR = {
    "admin": "1234",
    "doktor": "123",
    "hemsire": "123"
}

if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False
if 'kullanici_adi' not in st.session_state:
    st.session_state['kullanici_adi'] = ''

def giris_kontrol():
    kull = st.session_state.kull_input
    sifre = st.session_state.sifre_input
    if kull in KULLANICILAR and KULLANICILAR[kull] == sifre:
        st.session_state['giris_yapildi'] = True
        st.session_state['kullanici_adi'] = kull
    else:
        st.error("Hatalı giriş!")

# --- 3. ARAYÜZ ---
if not st.session_state['giris_yapildi']:
    st.title("☁️ Bulut Sağlık Sistemi")
    with st.form("giris"):
        st.text_input("Kullanıcı Adı", key="kull_input")
        st.text_input("Şifre", type="password", key="sifre_input")
        st.form_submit_button("Giriş", on_click=giris_kontrol)

else:
    st.sidebar.success(f"Giriş: {st.session_state['kullanici_adi']}")
    menu = st.sidebar.radio("Menü", ["Veri Girişi", "Raporlar"])
    
    if st.sidebar.button("Çıkış"):
        st.session_state['giris_yapildi'] = False
        st.rerun()

    if menu == "Veri Girişi":
        st.header("📝 Veri Ekle (Google Sheets)")
        with st.form("ekle", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                bolge = st.selectbox("Bölge", ["Merkez", "Şube 1", "Şube 2"])
            with c2:
                sayi = st.number_input("Sayı", min_value=0)
            puan = st.slider("Puan", 0, 100, 80)
            
            if st.form_submit_button("Kaydet"):
                try:
                    veri_ekle(st.session_state['kullanici_adi'], bolge, sayi, puan)
                    st.success("Veri Google E-Tablo'ya işlendi! ✅")
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

    elif menu == "Raporlar":
        st.header("📊 Canlı Veriler")
        try:
            df = verileri_getir()
            if not df.empty:
                st.dataframe(df)
                
                # Excel İndir
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("Excel İndir", buffer, "rapor.xlsx")
                
                # Google Sheets Linki
                st.markdown("[Google E-Tabloyu Görüntülemek İçin Tıkla](https://docs.google.com/spreadsheets)")
            else:
                st.info("Tablo boş.")
        except Exception as e:
            st.error(f"Veri çekilemedi. Bağlantı hatası: {e}")
