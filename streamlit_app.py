import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import logging
import bcrypt
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians
from contextlib import closing

# --- CONFIGURAÇÕES MESTRE ---
ADMIN_PASS_SISTEMA = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_WHATSAPP = "whatsapp:+3519339227659"
TELEGRAM_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT = "@Dragonblack85"

MEU_WA_LINK = "https://wa.me/3519339227659"
MEU_TG_LINK = "https://t.me/Dragonblack85"
DB_NAME = 'sistema_v59_supreme.db'

# --- SEGURANÇA ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    if isinstance(hashed, str): hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# --- DATABASE ENGINE ---
def get_db_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db(force_reset=False):
    with get_db_conn() as conn:
        with closing(conn.cursor()) as c:
            if force_reset:
                c.execute("DROP TABLE IF EXISTS escalas")
                c.execute("DROP TABLE IF EXISTS configuracao_turnos")
                c.execute("DROP TABLE IF EXISTS clientes")
            
            c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, posto TEXT, nome TEXT, telefone TEXT, email TEXT, 
                          status TEXT DEFAULT 'Pendente', pref_metodo TEXT, checkin INTEGER DEFAULT 0)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                         (posto TEXT PRIMARY KEY, empresa TEXT, localizacao TEXT, lat REAL, lon REAL)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                         (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                          is_admin INTEGER DEFAULT 0, cartoes TEXT, ranking INTEGER DEFAULT 5)''')
            
            # Admin Inicial
            admin_pwd = hash_password("ADMIN").decode('utf-8')
            c.execute("INSERT OR REPLACE INTO clientes (email, senha, nome, is_admin) VALUES (?,?,?,?)",
                      ("admin@admin.pt", admin_pwd, "FRED SILVA MASTER", 1))

def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def multicanal_notify(email, tel, nome, posto, pref):
    msg = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO."
    if pref in ["Email", "Ambos"]:
        try:
            m = MIMEText(msg); m['Subject'] = "CONFIRMACAO"; m['From'] = EMAIL_USER; m['To'] = email
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        except: pass
    if pref in ["WhatsApp", "Ambos"]:
        try:
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            client.messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:{tel}")
        except: pass

init_db()

# --- INTERFACE ---
st.set_page_config(page_title="V59 SUPREME FULL", layout="wide")

if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'preview_data' not in st.session_state: st.session_state.preview_data = []

with st.sidebar:
    st.title("🛡️ SUPREME v59")
    if st.session_state.user_email:
        st.success(f"Logado: {st.session_state.user_email}")
        if st.button("🔒 Sair"):
            st.session_state.user_email = None
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.form("login"):
            e = st.text_input("Email", value="admin@admin.pt")
            s = st.text_input("Senha", type="password", value="ADMIN")
            if st.form_submit_button("Entrar"):
                with get_db_conn() as conn:
                    res = conn.execute("SELECT senha, is_admin FROM clientes WHERE email=?", (e,)).fetchone()
                    if res and check_password(s, res[0]):
                        st.session_state.user_email = e
                        st.session_state.is_admin = bool(res[1])
                        st.rerun()
                    else: st.error("Erro no login.")

    nav = st.radio("Módulos", ["Turnos em Aberto", "Área de Cliente", "Registo"])
    st.divider()
    st.link_button("💬 Suporte WhatsApp", MEU_WA_LINK, use_container_width=True)

# --- MÓDULO: ADMIN (INTEGRADO) ---
if st.session_state.is_admin:
    with st.expander("🛠️ PAINEL DE CONTROLO ADMINISTRATIVO", expanded=False):
        t1, t2, t3 = st.tabs(["🚀 Gerar Postos", "📥 Validar Inscrições", "👥 Gestão Staff"])
        
        with t1:
            txt = st.text_area("Texto Bruto (DIA/LOCAL/HORARIO/€)", height=150)
            if st.button("🔍 Gerar Preview"):
                if txt:
                    p_list = []
                    loc, dia = "Geral", "31"
                    for l in txt.split('\n'):
                        l = l.strip()
                        if "DIA" in l.upper(): dia = l
                        elif l.isupper() and len(l) > 3 and "DAS" not in l.upper(): loc = l
                        elif "Das" in l and "€" in l:
                            p_id = f"{dia} | {loc} | {l}"
                            p_list.append({"ID": p_id, "Local": loc, "Horário": l})
                    st.session_state.preview_data = p_list
            
            if st.session_state.preview_data:
                st.table(pd.DataFrame(st.session_state.preview_data))
                if st.button("✅ Publicar Todos"):
                    with get_db_conn() as conn:
                        for i in st.session_state.preview_data:
                            conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?)", 
                                         (i['ID'], "PSG", i['Local'], 39.2081, -8.6277))
                    st.session_state.preview_data = []; st.success("Postos Online!"); st.rerun()

        with t2:
            with get_db_conn() as conn:
                pedidos = conn.execute("SELECT id, posto, nome, email, pref_metodo, telefone FROM escalas WHERE status='Pendente'").fetchall()
                for id_e, p_id, nome, email, pref, tel in pedidos:
                    with st.container(border=True):
                        st.write(f"**{nome}** -> {p_id}")
                        if st.button("✅ Confirmar", key=f"conf_{id_e}"):
                            conn.execute("UPDATE escalas SET status='Confirmado' WHERE id=?", (id_e,))
                            multicanal_notify(email, tel, nome, p_id, pref)
                            st.rerun()

        with t3:
            with get_db_conn() as conn:
                users = conn.execute("SELECT email, nome, is_admin FROM clientes").fetchall()
                for u_e, u_n, adm in users:
                    with st.expander(f"{u_n} ({u_e})"):
                        st.write(f"Admin: {'Sim' if adm else 'Não'}")
                        if not adm and st.button("Promover", key=f"p_{u_e}"):
                            conn.execute("UPDATE clientes SET is_admin=1 WHERE email=?", (u_e,)); st.rerun()

# --- MÓDULOS PÚBLICOS ---
if nav == "Turnos em Aberto":
    st.header("📅 Escalas Disponíveis")
    with get_db_conn() as conn:
        postos = conn.execute("SELECT posto, localizacao FROM configuracao_turnos").fetchall()
        reservados = [r[0] for r in conn.execute("SELECT posto FROM escalas WHERE status != 'Cancelado'").fetchall()]
        for p_id, loc in postos:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                if p_id in reservados: c1.error(f"❌ {p_id}")
                else:
                    c1.success(f"✅ {p_id}")
                    if st.session_state.user_email:
                        met = c2.selectbox("Notificação:", ["Email", "WhatsApp", "Ambos"], key=f"m_{p_id}")
                        if c2.button("Reservar", key=f"r_{p_id}"):
                            u = conn.execute("SELECT nome, telefone FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                            conn.execute("INSERT INTO escalas (posto, nome, telefone, email, pref_metodo) VALUES (?,?,?,?,?)",
                                         (p_id, u[0], u[1], st.session_state.user_email, met))
                            st.rerun()

elif nav == "Área de Cliente":
    if not st.session_state.user_email: st.warning("Faça login.")
    else:
        st.header("📋 Meus Turnos")
        with get_db_conn() as conn:
            meus = conn.execute('''SELECT e.posto, e.status, e.checkin, t.lat, t.lon 
                                   FROM escalas e LEFT JOIN configuracao_turnos t ON e.posto = t.posto 
                                   WHERE e.email = ?''', (st.session_state.user_email,)).fetchall()
            for p, status, chk, lat, lon in meus:
                with st.container(border=True):
                    st.write(f"**Posto:** {p} | **Status:** {status}")
                    if status == "Confirmado" and not chk:
                        if st.button(f"Validar GPS: {p}"):
                            if haversine_meters(39.2081, -8.6277, lat, lon) <= 500:
                                conn.execute("UPDATE escalas SET checkin=1 WHERE posto=? AND email=?", (p, st.session_state.user_email))
                                st.rerun()
                    elif chk: st.success("✅ Presença Confirmada")

elif nav == "Registo":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar Conta"):
            hashed = hash_password(s).decode('utf-8')
            with get_db_conn() as conn:
                conn.execute("INSERT OR REPLACE INTO clientes (email, senha, nome, telefone) VALUES (?,?,?,?)", (e, hashed, n, t))
            st.success("Registado!"); time.sleep(1); st.rerun()

