import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import logging
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians
from contextlib import closing
from passlib.hash import bcrypt

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES MESTRE (RECOMENDADO: USAR st.secrets) ---
# Se estiveres a usar o Streamlit Cloud, coloca estas variáveis no painel "Secrets"
ADMIN_PASS_SISTEMA = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_WHATSAPP = "whatsapp:+14155238886"
TELEGRAM_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT = "@FredSilva85_pt"

# LINKS DE SUPORTE
MEU_WA_LINK = "https://wa.me/3519339227659"
MEU_TG_LINK = "https://t.me/FredSilva85_pt"

DB_NAME = 'sistema_v54_supreme.db'

# --- DATABASE ENGINE (CONTEXT MANAGERS) ---
def get_db_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db(force_reset=False):
    with get_db_conn() as conn:
        with closing(conn.cursor()) as c:
            if force_reset:
                c.execute("DROP TABLE IF EXISTS escalas")
                c.execute("DROP TABLE IF EXISTS configuracao_turnos")
                c.execute("DROP TABLE IF EXISTS clientes")
                c.execute("DROP TABLE IF EXISTS logs_notificacoes")
            
            c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, posto TEXT, nome TEXT, telefone TEXT, email TEXT, 
                          data TEXT, status TEXT DEFAULT 'Pendente', pref_email INTEGER, pref_sms INTEGER, checkin INTEGER DEFAULT 0)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                         (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT, lat REAL, lon REAL)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                         (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                          carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5, docs BLOB)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS logs_notificacoes 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, tipo TEXT, mensagem TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            
            # Conta Master Admin/Colaborador (com password em Hash)
            admin_hash = bcrypt.hash("ADMIN")
            c.execute("INSERT OR REPLACE INTO clientes (email, senha, nome, telefone, carta, viatura, cartoes, ranking) VALUES (?,?,?,?,?,?,?,?)",
                      ("admin@admin.pt", admin_hash, "FRED SILVA ADMIN", "+3519339227659", "Sim", "Sim", "VIG,ARE,ARD,COORDENADOR", 5))

def log_notif(email, tipo, msg):
    with get_db_conn() as conn:
        conn.execute("INSERT INTO logs_notificacoes (email, tipo, mensagem) VALUES (?,?,?)", (email, tipo, msg))

# --- UTILITÁRIOS ---
def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def multicanal_notify(email, tel, nome, posto, acao="CONFIRMADO"):
    msg = f"Ola {nome}, o seu turno {posto} foi {acao}."
    # Email
    try:
        m = MIMEText(msg); m['Subject'] = acao; m['From'] = EMAIL_USER; m['To'] = email
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        log_notif(email, "EMAIL", "Sucesso")
    except Exception as e:
        log_notif(email, "EMAIL", f"Erro: {str(e)}")
    
    # Twilio WhatsApp
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:{tel}")
        log_notif(email, "WHATSAPP", "Enviado")
    except Exception as e:
        log_notif(email, "WHATSAPP", f"Erro: {str(e)}")
    
    # Telegram
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": f"📢 {acao}: {nome} em {posto}"}, timeout=5)
    except Exception as e:
        logger.error(f"Telegram erro: {e}")

# --- INTERFACE ---
st.set_page_config(page_title="V54 SUPREME OMNI", layout="wide")
init_db()

if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'preview_data' not in st.session_state: st.session_state.preview_data = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v54")
    if st.session_state.admin_auth:
        st.success("ADMIN: FRED SILVA")
        if st.button("🔒 LOGOUT ADMIN"): st.session_state.admin_auth = False; st.rerun()
    else:
        with st.form("l_adm"):
            pwd = st.text_input("Senha Admin Sistema", type="password")
            if st.form_submit_button("🔓"):
                if pwd == ADMIN_PASS_SISTEMA: st.session_state.admin_auth = True; st.rerun()
    
    st.divider()
    nav = st.radio("Módulos", ["Turnos em Aberto", "Área de Cliente", "Registo"])
    
    st.divider()
    st.write("🆘 SUPORTE TÉCNICO")
    st.link_button("💬 WhatsApp Admin", MEU_WA_LINK, use_container_width=True)
    st.link_button("✈️ Telegram Admin", MEU_TG_LINK, use_container_width=True)

# --- MODULO ADMIN ---
if st.session_state.admin_auth:
    t1, t2, t3, t4, t5 = st.tabs(["🚀 Gerador", "👥 Staff Info", "📥 Inscrições", "📋 Postos Ativos", "⚙️ Sistema"])
    
    with t1:
        txt = st.text_area("Texto Bruto para Processamento", height=150)
        if st.button("🔍 GERAR PREVISUALIZAÇÃO"):
            if txt:
                p_list = []
                loc, dia = "Geral", "31"
                for l in txt.split('\n'):
                    l = l.strip()
                    if "DIA" in l.upper(): dia = l
                    elif l.isupper() and len(l) > 3 and "DAS" not in l.upper(): loc = l
                    elif "Das" in l and "€" in l:
                        p_list.append({"ID": f"{dia} | {loc} | {l}", "Local": loc, "Horário": l})
                st.session_state.preview_data = p_list
        
        if st.session_state.preview_data:
            st.table(pd.DataFrame(st.session_state.preview_data))
            if st.button("✅ PUBLICAR TUDO"):
                with get_db_conn() as conn:
                    for i in st.session_state.preview_data:
                        conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", 
                                     (i['ID'], "PSG-REAL", "2025-12-31", i['Local'], 39.2081, -8.6277))
                st.session_state.preview_data = []; st.success("Postos Publicados!"); st.rerun()

    with t2:
        with get_db_conn() as conn:
            staff = conn.execute("SELECT email, nome, telefone, ranking FROM clientes").fetchall()
            for e, n, t, r in staff:
                with st.expander(f"👤 {n} ({e})"):
                    st.write(f"Ranking: {'⭐'*r}")
                    logs = conn.execute("SELECT tipo, mensagem, timestamp FROM logs_notificacoes WHERE email=? ORDER BY timestamp DESC LIMIT 3", (e,)).fetchall()
                    for lt, lm, lts in logs: st.caption(f"{lts} | {lt}: {lm}")
                    if st.button(f"Remover {n}", key=f"del_{e}"):
                        conn.execute("DELETE FROM clientes WHERE email=?"); st.rerun()

    with t3:
        with get_db_conn() as conn:
            insc = conn.execute("SELECT * FROM escalas WHERE status='Pendente'").fetchall()
            for r in insc:
                with st.container(border=True):
                    st.write(f"**{r[2]}** quer: `{r[1]}`")
                    if st.button("✅ Confirmar & Notificar", key=f"v_{r[0]}"):
                        conn.execute("UPDATE escalas SET status='Confirmado' WHERE id=?", (r[0],))
                        multicanal_notify(r[4], r[3], r[2], r[1])
                        st.rerun()

    with t5:
        if st.button("🚨 NUCLEAR RESET DB"): init_db(force_reset=True); st.rerun()

# --- MÓDULOS PÚBLICOS ---
elif nav == "Área de Cliente":
    if st.session_state.user_email:
        with get_db_conn() as conn:
            u = conn.execute("SELECT nome FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
            st.subheader(f"Área Pessoal: {u[0]}")
            
            # Query corrigida para evitar crash
            meus = conn.execute('''
                SELECT e.posto, t.lat, t.lon, e.checkin 
                FROM escalas e 
                JOIN configuracao_turnos t ON e.posto = t.posto 
                WHERE e.email = ? AND e.status = 'Confirmado'
            ''', (st.session_state.user_email,)).fetchall()
            
            for p, lat, lon, chk in meus:
                with st.container(border=True):
                    st.write(f"📍 {p}")
                    if chk: st.success("✅ Presença Confirmada")
                    else:
                        if st.button(f"Fazer Check-in GPS: {p}"):
                            if haversine_meters(39.2081, -8.6277, lat, lon) <= 500:
                                conn.execute("UPDATE escalas SET checkin=1 WHERE posto=? AND email=?", (p, st.session_state.user_email))
                                st.rerun()
                            else: st.error("Longe do local!")
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
    else:
        with st.form("log_u"):
            e = st.text_input("Email", value="admin@admin.pt")
            s = st.text_input("Senha", type="password", value="ADMIN")
            if st.form_submit_button("Entrar"):
                with get_db_conn() as conn:
                    res = conn.execute("SELECT senha FROM clientes WHERE email=?", (e,)).fetchone()
                    if res and bcrypt.verify(s, res[0]):
                        st.session_state.user_email = e; st.rerun()
                    else: st.error("Incorreto.")

elif nav == "Turnos em Aberto":
    st.header("📅 Postos Disponíveis")
    with get_db_conn() as conn:
        postos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
        ocupados = [r[0] for r in conn.execute("SELECT posto FROM escalas WHERE status != 'Pendente'").fetchall()]
        for p in postos:
            p_id = p[0]
            with st.container(border=True):
                if p_id in ocupados: st.error(f"❌ {p_id}")
                else:
                    st.success(f"✅ {p_id}")
                    if st.session_state.user_email and st.button("Reservar", key=f"res_{p_id}"):
                        u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                        conn.execute("INSERT INTO escalas (posto, nome, telefone, email, data) VALUES (?,?,?,?,?)", 
                                     (p_id, u[0], u[1], u[2], "2025-12-31"))
                        st.rerun()

elif nav == "Registo":
    with st.form("r"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar / Atualizar Conta"):
            hashed = bcrypt.hash(s)
            with get_db_conn() as conn:
                conn.execute("INSERT OR REPLACE INTO clientes (email, senha, nome, telefone, carta, viatura, cartoes) VALUES (?,?,?,?,?,?,?)", 
                             (e, hashed, n, t, "Sim", "Sim", "VIG"))
            st.session_state.user_email = e; st.rerun()
