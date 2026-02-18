import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- 1. VERİTABANI İŞLEMLERİ (BACKEND) ---
def init_db():
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    c = conn.cursor()
    
    # Raporlar Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS raporlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            kullanici TEXT,
            bolge TEXT,
            asi_sayisi INTEGER,
            performans_puani REAL
        )
    ''')
    
    # Kullanıcılar Tablosu (YENİ)
    c.execute('''
        CREATE TABLE IF NOT EXISTS kullanicilar (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT
        )
    ''')
    
    # Varsayılan Admin Hesabı Oluştur (Eğer yoksa)
    c.execute("SELECT * FROM kullanicilar WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO kullanicilar (username, password, role) VALUES (?, ?, ?)", 
                  ('admin', '1234', 'admin'))
    
    conn.commit()
    conn.close()

# --- Kullanıcı Yönetimi Fonksiyonları ---
def login_user(username, password):
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT role FROM kullanicilar WHERE username = ? AND password = ?", (username, password))
    data = c.fetchone()
    conn.close()
    return data # Eğer kullanıcı varsa rolünü döndürür (admin/user), yoksa None döner

def add_user(username, password, role):
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO kullanicilar (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False # Kullanıcı adı zaten varsa hata verir
    conn.close()
    return result

def get_all_users():
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT username, role FROM kullanicilar", conn)
    conn.close()
    return df

def delete_user(username):
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM kullanicilar WHERE username = ?", (username,))
    conn.commit()
    conn.close()

# --- Veri İşlemleri Fonksiyonları ---
def veri_ekle(kullanici, bolge, asi_sayisi, performans_puani):
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    c = conn.cursor()
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO raporlar (tarih, kullanici, bolge, asi_sayisi, performans_puani) VALUES (?,?,?,?,?)',
              (tarih, kullanici, bolge, asi_sayisi, performans_puani))
    conn.commit()
    conn.close()

def veri_sil(kayit_id):
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM raporlar WHERE id=?", (kayit_id,))
    conn.commit()
    conn.close()

def verileri_getir():
    conn = sqlite3.connect('veritabani.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM raporlar", conn)
    conn.close()
    return df

# Başlangıçta veritabanını hazırla
init_db()

# --- 2. OTURUM YÖNETİMİ (SESSION STATE) ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False
if 'kullanici_adi' not in st.session_state:
    st.session_state['kullanici_adi'] = ''
if 'rol' not in st.session_state:
    st.session_state['rol'] = ''

def giris_kontrol():
    kull = st.session_state.kull_input
    sifre = st.session_state.sifre_input
    
    rol = login_user(kull, sifre)
    
    if rol:
        st.session_state['giris_yapildi'] = True
        st.session_state['kullanici_adi'] = kull
        st.session_state['rol'] = rol[0] # Tuple'dan string'i al
    else:
        st.error("Hatalı kullanıcı adı veya şifre!")

# --- 3. ARAYÜZ (FRONTEND) ---

if not st.session_state['giris_yapildi']:
    st.title("🏥 Sağlık Veri Sistemi Giriş")
    with st.form("giris_formu"):
        st.text_input("Kullanıcı Adı", key="kull_input")
        st.text_input("Şifre", type="password", key="sifre_input")
        st.form_submit_button("Giriş Yap", on_click=giris_kontrol)

else:
    # Yan Menü Tasarımı
    st.sidebar.info(f"👤 **{st.session_state['kullanici_adi']}** ({st.session_state['rol']})")
    
    # Menü seçeneklerini Role göre belirle
    menu_secenekleri = ["Veri Girişi", "Rapor & Analiz"]
    if st.session_state['rol'] == 'admin':
        menu_secenekleri.append("Kullanıcı Yönetimi (Admin)")
        
    secim = st.sidebar.radio("Menü", menu_secenekleri)
    
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['giris_yapildi'] = False
        st.session_state['kullanici_adi'] = ''
        st.session_state['rol'] = ''
        st.rerun()

    # --- SAYFA 1: VERİ GİRİŞİ ---
    if secim == "Veri Girişi":
        st.header("📝 Veri Giriş Formu")
        with st.form("veri_formu", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                bolge = st.selectbox("Bölge / Birim", ["Merkez ASM", "1 Nolu ASM", "2 Nolu ASM", "Mobil Ekip"])
            with col2:
                asi_sayisi = st.number_input("Aşı Sayısı", min_value=0, step=1)
            performans = st.slider("Performans Puanı", 0, 100, 80)
            
            if st.form_submit_button("Kaydet"):
                veri_ekle(st.session_state['kullanici_adi'], bolge, asi_sayisi, performans)
                st.success("Kayıt Başarılı!")

    # --- SAYFA 2: RAPOR & ANALİZ ---
    elif secim == "Rapor & Analiz":
        st.header("📊 Analiz Paneli")
        df = verileri_getir()
        
        if not df.empty:
            c1, c2 = st.columns(2)
            c1.metric("Toplam Aşı", df['asi_sayisi'].sum())
            c2.metric("Ort. Performans", f"{df['performans_puani'].mean():.1f}")
            
            st.divider()
            st.bar_chart(df.groupby("bolge")["asi_sayisi"].sum())
            
            st.subheader("Veri Listesi")
            st.dataframe(df)
            
            # Excel İndir
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Excel İndir", buffer, file_name="Rapor.xlsx")
            
            # SİLME YETKİSİ: Sadece Admin silebilir
            if st.session_state['rol'] == 'admin':
                st.divider()
                st.error("Yönetici Paneli: Kayıt Silme")
                sil_id = st.selectbox("Silinecek ID", df['id'].tolist())
                if st.button("Seçili Kaydı Sil"):
                    veri_sil(sil_id)
                    st.rerun()
            else:
                st.info("Kayıt silme yetkisi sadece yöneticilerdedir.")
        else:
            st.warning("Veri yok.")

    # --- SAYFA 3: KULLANICI YÖNETİMİ (Sadece Admin Görür) ---
    elif secim == "Kullanıcı Yönetimi (Admin)":
        st.header("🔑 Kullanıcı Tanımlama Paneli")
        
        # 1. Yeni Kullanıcı Ekleme Formu
        with st.form("yeni_kullanici_form"):
            st.subheader("Yeni Personel Ekle")
            new_user = st.text_input("Yeni Kullanıcı Adı")
            new_pass = st.text_input("Şifre", type="password")
            new_role = st.selectbox("Yetki Rolü", ["user", "admin"])
            
            if st.form_submit_button("Kullanıcıyı Oluştur"):
                if new_user and new_pass:
                    basari = add_user(new_user, new_pass, new_role)
                    if basari:
                        st.success(f"{new_user} başarıyla oluşturuldu!")
                    else:
                        st.error("Bu kullanıcı adı zaten kullanılıyor!")
                else:
                    st.warning("Lütfen kullanıcı adı ve şifre giriniz.")
        
        st.divider()
        
        # 2. Mevcut Kullanıcıları Listeleme
        st.subheader("Mevcut Kullanıcı Listesi")
        users_df = get_all_users()
        st.dataframe(users_df)
        
        # 3. Kullanıcı Silme
        st.subheader("Kullanıcı Sil")
        user_to_delete = st.selectbox("Silinecek Kullanıcı", users_df['username'].tolist())
        if st.button("Kullanıcıyı Sil"):
            if user_to_delete == 'admin':
                st.error("Ana Yönetici (admin) silinemez!")
            else:
                delete_user(user_to_delete)
                st.success(f"{user_to_delete} silindi.")
                st.rerun()
