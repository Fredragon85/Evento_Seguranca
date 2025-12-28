import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import time
import urllib.parse
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians

# --- CONFIGURAÇÕES MESTRE ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
TWILIO_WHATSAPP = "whatsapp:+14155238886"
TELEGRAM_BOT_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT_ID = "@sua_canal_seguranca"

# --- DATABASE ENGINE ---
def init_db(force_reset=False):
    conn = sqlite3.connect('sistema_supreme_v36.db', check_same_thread=False)
    c = conn.cursor()
    if force_reset:
        c.execute("DROP TABLE IF EXISTS escalas")
        c.execute("DROP TABLE IF EXISTS configuracao_turnos")
        c.execute("DROP TABLE IF EXISTS clientes")
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER, pref_sms INTEGER, checkin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5, docs BLOB)''')
    conn.commit(); conn.close()

# --- GEO & NOTIFICAÇÕES ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def dispatch_alerts(email, tel, nome, posto):
    msg = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO."
    # Email
    try:
        m = MIMEText(msg); m['Subject'] = "CONFIRMACAO"; m['From'] = EMAIL_USER; m['To'] = email
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
    except: pass
    # Twilio (SMS & WA)
    tw = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try: tw.messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:{tel}")
    except: pass
    try: tw.messages.create(from_=TWILIO_NUMBER, body=msg, to=tel)
    except: pass
    # Telegram
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                       data={"chat_id": TELEGRAM_CHAT_ID, "text": f"📢 CONFIRMADO: {nome} em {posto}"})
    except: pass

# --- APP START ---
st.set_page_config(page_title="Segurança Supreme v36.0", layout="wide")
init_db()

if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v36")
    if st.button("🔄 REFRESH"): st.rerun()
    st.divider()
    if st.session_state.admin_auth:
        st.success("Admin Ativo")
        if st.button("🔒 LOGOUT"): st.session_state.admin_auth = False; st.rerun()
    else:
        with st.form("adm_l"):
            p = st.text_input("Admin Password", type="password")
            if st.form_submit_button("🔓"):
                if p == ADMIN_PASSWORD: st.session_state.admin_auth = True; st.rerun()
    st.divider()
    nav = st.radio("Módulos", ["Turnos Disponíveis", "Área de Cliente", "Registo"])

# --- MODULO ADMIN ---
if st.session_state.admin_auth:
    tabs = st.tabs(["🚀 Gerador", "👥 Clientes", "📥 Gestão Escalas", "⚠️ Manutenção"])
    
    with tabs[0]:
        st.subheader("Processador de Texto e Broadcast")
        txt = st.text_area("Texto Bruto Turnos", height=200, placeholder="MILHARADO\nDIA 31\nDas 18h as 02h (15€)")
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude Local", value=39.2081, format="%.6f") # Almeirim
        lon = c2.number_input("Longitude Local", value=-8.6277, format="%.6f")
        if st.button("🚀 Publicar e Notificar Multicanal"):
            conn = sqlite3.connect('sistema_supreme_v36.db')
            loc, dia, count = "Geral", "31", 0
            for l in txt.split('\n'):
                l = l.strip()
                if "DIA" in l.upper(): dia = l
                elif l.isupper() and len(l) > 3: loc = l
                elif "Das" in l and "€" in l:
                    p_id = f"{dia} | {loc} | {l}"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", (p_id, "PSG-REAL", "2025-12-31", loc, lat, lon))
                    count += 1
            conn.commit(); conn.close()
            if count > 0:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                              data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🚨 ALERTA: {count} novos postos em {loc}!"})
                st.success(f"{count} postos criados.")

    with tabs[2]:
        conn = sqlite3.connect('sistema_supreme_v36.db')
        inscritos = conn.execute("SELECT * FROM escalas").fetchall()
        for r in inscritos:
            with st.expander(f"{r[5]} | {r[1]} - {r[0]}"):
                if r[5] == 'Pendente' and st.button("Validar & Notificar 360º", key=f"val_{r[0]}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r[0],))
                    conn.commit()
                    dispatch_alerts(r[3], r[2], r[1], r[0])
                    st.rerun()
                if st.button("Excluir", key=f"del_{r[0]}"):
                    conn.execute("DELETE FROM escalas WHERE posto=?", (r[0],)); conn.commit(); st.rerun()
        conn.close()

    with tabs[3]:
        if st.button("🚨 RESET DATABASE"): init_db(True); st.rerun()

# --- MODULO CLIENTE / RESERVA ---
elif nav == "Turnos Disponíveis":
    st.header("📅 Postos em Aberto")
    conn = sqlite3.connect('sistema_supreme_v36.db')
    postos = conn.execute("SELECT posto, lat, lon FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    
    for p, lat, lon in postos:
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            if p in ocupados: col_a.error(f"❌ {p}")
            else:
                col_a.success(f"✅ {p}")
                if st.session_state.user_email:
                    if col_b.button("Reservar", key=f"res_{p}"):
                        u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                        conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?,?)", (p, u[0], u[1], u[2], "2025-12-31", 'Pendente', 1, 1, 0))
                        conn.commit(); st.rerun()
                else: col_b.info("Login")
    conn.close()

elif nav == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema_supreme_v36.db')
        u = conn.execute("SELECT nome, ranking FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Perfil: {u[0]} | Nível: {'⭐'*u[1]}")
        
        # Geofencing Check-in
        st.divider()
        st.subheader("📍 Check-in Local (500m)")
        meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
        for p, lat, lon, chk in meus:
            with st.container(border=True):
                if chk: st.success(f"✅ Presença Validada: {p}")
                else:
                    if st.button(f"Fazer Check-in GPS: {p}", key=f"chk_{p}"):
                        # Simulador GPS Almeirim
                        dist = haversine(39.2081, -8.6277, lat, lon)
                        if dist <= 500:
                            conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?", (p,))
                            conn.commit(); st.success("Confirmado no local!"); st.rerun()
                        else: st.error(f"Demasiado longe: {int(dist)}m")
        if st.button("Terminar Sessão"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("login_u"):
            e, s = st.text_input("Email"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema_supreme_v36.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                conn.close()

elif nav == "Registo":
    with st.form("reg_supreme"):
        st.subheader("Registo Profissional")
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Telemóvel"), st.text_input("Senha", type="password")
        cart = st.multiselect("Cartões", ["VIG", "ARE", "ARD", "SPR", "COORDENADOR", "MARE"])
        if st.form_submit_button("Criar Conta"):
            conn = sqlite3.connect('sistema_supreme_v36.db')
            try:
                conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", ",".join(cart), 5, None))
                conn.commit(); st.session_state.user_email = e; st.rerun()
            except: st.error("Email já em uso.")
            finally: conn.close()
