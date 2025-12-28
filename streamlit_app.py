import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import time
import urllib.parse
from email.mime.text import MIMEText
from twilio.rest import Client
from datetime import datetime
from math import sin, cos, sqrt, atan2, radians

# --- CONFIGURAÇÕES DO UTILIZADOR ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"

# --- CORE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect('sistema_seguranca_v27.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER, pref_sms INTEGER, checkin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5, docs BLOB)''')
    conn.commit(); conn.close()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0 # Metros
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def enviar_notificacao(email_dest, tel_dest, nome, posto, p_mail, p_sms):
    msg = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO. Bom trabalho!"
    if p_mail:
        try:
            m = MIMEText(msg); m['Subject'] = "CONFIRMACAO DE TURNO"; m['From'] = EMAIL_USER; m['To'] = email_dest
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        except: pass
    if p_sms:
        try: Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(body=msg, from_=TWILIO_NUMBER, to=tel_dest)
        except: pass

init_db()
st.set_page_config(page_title="Segurança Pro v27.0", layout="wide")

# --- AUTH STATE ---
if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Segurança Pro v27")
    if st.session_state.admin_auth:
        st.success("Admin Logado")
        if st.button("🔒 Logout Admin"): st.session_state.admin_auth = False; st.rerun()
    else:
        with st.form("a_l"):
            p = st.text_input("Senha Admin", type="password")
            if st.form_submit_button("Entrar"):
                if p == ADMIN_PASSWORD: st.session_state.admin_auth = True; st.rerun()
    st.divider()
    menu = st.radio("Navegação", ["📅 Reserva de Turnos", "👤 Área de Cliente", "📝 Criar Conta"])

# --- MODULO ADMIN ---
if st.session_state.admin_auth:
    st.header("🛠️ Painel de Controlo Total")
    t1, t2, t3 = st.tabs(["🚀 Processar Postos", "👥 Gestão de Clientes", "📥 Inscrições & SMS"])

    with t1:
        st.subheader("Gerador Inteligente de Escalas")
        emp = st.text_input("Empresa", "PSG-REAL")
        txt = st.text_area("Cole a lista bruta de turnos aqui", height=200)
        c_lat = st.number_input("Latitude do Local", format="%.6f", value=38.7071)
        c_lon = st.number_input("Longitude do Local", format="%.6f", value=-9.1355)
        if st.button("Criar Postos"):
            conn = sqlite3.connect('sistema_seguranca_v27.db')
            linhas = txt.split('\n')
            loc_ref, dia_ref = "Geral", "31"
            for l in linhas:
                l = l.strip()
                if "DIA" in l.upper(): dia_ref = l
                elif l.isupper() and len(l) > 3: loc_ref = l
                elif "Das" in l and "€" in l:
                    p_id = f"{dia_ref} | {loc_ref} | {l}"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", (p_id, emp, "2025-12-31", loc_ref, c_lat, c_lon))
            conn.commit(); conn.close(); st.success("Postos Criados!"); st.rerun()

    with t2:
        conn = sqlite3.connect('sistema_seguranca_v27.db')
        df_u = pd.read_sql_query("SELECT nome, email, telefone, ranking FROM clientes", conn)
        for _, u in df_u.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{u['nome']}** - Rank: {'⭐'*u['ranking']}")
                if col2.button("Remover", key=f"del_{u['email']}"):
                    conn.execute("DELETE FROM clientes WHERE email=?", (u['email'],))
                    conn.commit(); st.rerun()
        conn.close()

    with t3:
        st.subheader("Validar Inscrições")
        conn = sqlite3.connect('sistema_seguranca_v27.db')
        insc = conn.execute("SELECT * FROM escalas").fetchall()
        if st.button("📢 BROADCAST SMS/EMAIL (Tudo Confirmado)"):
            for r in insc:
                if r[5] == 'Confirmado': enviar_notificacao(r[3], r[2], r[1], r[0], r[6], r[7])
            st.success("Notificações enviadas!")
        
        for r in insc:
            with st.expander(f"{r[5]} | {r[1]} -> {r[0]}"):
                if r[5] == 'Pendente' and st.button("Validar", key=f"val_{r[0]}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r[0],))
                    conn.commit(); st.rerun()
                if st.button("Apagar", key=f"rem_{r[0]}"):
                    conn.execute("DELETE FROM escalas WHERE posto=?", (r[0],)); conn.commit(); st.rerun()
        conn.close()

# --- RESERVA DE TURNOS ---
elif menu == "📅 Reserva de Turnos":
    st.header("Escalas Disponíveis")
    conn = sqlite3.connect('sistema_seguranca_v27.db')
    postos = conn.execute("SELECT posto, localizacao FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    for p, loc in postos:
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.write(f"### {p}")
            if p in ocupados:
                c1.error(f"Ocupado por: {ocupados[p]}")
            else:
                c1.success("Disponível")
                if st.session_state.user_email:
                    with c2.popover("Reservar"):
                        e_n = st.checkbox("Email", True, key=f"e_{p}")
                        s_n = st.checkbox("SMS", key=f"s_{p}")
                        if st.button("Confirmar", key=f"btn_{p}"):
                            conn = sqlite3.connect('sistema_seguranca_v27.db')
                            u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                            conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?)", (p, u[0], u[1], u[2], "2025-12-31", 'Pendente', int(e_n), int(s_n), 0))
                            conn.commit(); conn.close(); st.rerun()
                else: c2.info("Faça Login")

# --- AREA CLIENTE / CHECK-IN ---
elif menu == "👤 Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema_seguranca_v27.db')
        u = conn.execute("SELECT nome, ranking FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Perfil: {u[0]} | Nível: {'⭐'*u[1]}")
        
        st.divider()
        st.write("### Meus Turnos e Check-in GPS (Raio 500m)")
        meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
        
        for p, lat, lon, check in meus:
            with st.container(border=True):
                st.write(f"📍 {p}")
                if check: st.success("✅ Check-in Efetuado no Local")
                else:
                    if st.button("📍 Validar Presença GPS", key=f"chk_{p}"):
                        dist = haversine(38.7071, -9.1355, lat, lon) # Mocked GPS
                        if dist <= 500:
                            conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?", (p,))
                            conn.commit(); st.success("Presença Confirmada!"); st.rerun()
                        else: st.error(f"Fora de alcance: {int(dist)}m")
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("u_l"):
            e, s = st.text_input("Email"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema_seguranca_v27.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                conn.close()

# --- REGISTO ---
elif menu == "📝 Criar Conta":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar Conta"):
            conn = sqlite3.connect('sistema_seguranca_v27.db')
            conn.execute("INSERT INTO clientes (email, senha, nome, telefone, ranking) VALUES (?,?,?,?,?)", (e, s, n, t, 5))
            conn.commit(); conn.close(); st.session_state.user_email = e; st.rerun()
