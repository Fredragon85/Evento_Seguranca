import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import time
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians

# --- CONFIGURAÇÕES MESTRE ---
ADMIN_PASS_SISTEMA = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
TWILIO_WHATSAPP = "whatsapp:+3519339227659" # Teu WhatsApp configurado

# CONTACTOS ADMIN (FRED SILVA)
MEU_WHATSAPP_NUM = "3519339227659"
MEU_WHATSAPP_LINK = f"https://wa.me/{MEU_WHATSAPP_NUM}"
MEU_TELEGRAM_LINK = "https://t.me/FredSilva85_pt"
TELEGRAM_BOT_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT_ID = "@FredSilva85_pt"

# --- DATABASE ENGINE ---
def init_db(force_reset=False):
    conn = sqlite3.connect('sistema_v52_supreme.db', check_same_thread=False)
    c = conn.cursor()
    if force_reset:
        c.execute("DROP TABLE IF EXISTS escalas")
        c.execute("DROP TABLE IF EXISTS configuracao_turnos")
        c.execute("DROP TABLE IF EXISTS clientes")
        c.execute("DROP TABLE IF EXISTS logs_notificacoes")
    
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER, pref_sms INTEGER, checkin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT, lat REAL, lon REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5, docs BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs_notificacoes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, tipo TEXT, mensagem TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # CONTA MASTER FRED SILVA (Auto-registo para testes)
    c.execute("INSERT OR REPLACE INTO clientes (email, senha, nome, telefone, carta, viatura, cartoes, ranking) VALUES (?,?,?,?,?,?,?,?)",
              ("admin@admin.pt", "ADMIN", "FRED SILVA ADMIN", f"+{MEU_WHATSAPP_NUM}", "Sim", "Sim", "VIG,ARE,ARD,COORDENADOR", 5))
    conn.commit()
    conn.close()

def log_notif(email, tipo, msg):
    conn = sqlite3.connect('sistema_v52_supreme.db')
    conn.execute("INSERT INTO logs_notificacoes (email, tipo, mensagem) VALUES (?,?,?)", (email, tipo, msg))
    conn.commit(); conn.close()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def multicanal_notify(email, tel, nome, posto, acao="CONFIRMADO"):
    msg = f"Ola {nome}, o seu turno {posto} foi {acao}."
    # Email
    try:
        m = MIMEText(msg); m['Subject'] = acao; m['From'] = EMAIL_USER; m['To'] = email
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        log_notif(email, "EMAIL", "Sucesso")
    except: log_notif(email, "EMAIL", "Erro")
    # WA/SMS
    try:
        tw = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        tw.messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:{tel}")
        log_notif(email, "WHATSAPP", "Enviado")
    except: log_notif(email, "WHATSAPP", "Erro")
    # Telegram
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                       data={"chat_id": TELEGRAM_CHAT_ID, "text": f"📢 {acao}: {nome} em {posto}"})
    except: pass

init_db()

# --- SESSÃO ---
if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'preview_data' not in st.session_state: st.session_state.preview_data = []

st.set_page_config(page_title="V52 OMNI SUPREME", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v52")
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
    st.write("🆘 SUPRETE TÉCNICO")
    st.link_button("💬 WhatsApp Admin", MEU_WHATSAPP_LINK, use_container_width=True)
    st.link_button("✈️ Telegram Admin", MEU_TELEGRAM_LINK, use_container_width=True)

# --- MODULO ADMIN ---
if st.session_state.admin_auth:
    t1, t2, t3, t4, t5 = st.tabs(["🚀 Gerador", "👥 Staff Info", "📥 Inscrições", "📋 Postos", "⚠️ Sistema"])
    
    with t1:
        txt = st.text_area("Texto Bruto", height=150)
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
                conn = sqlite3.connect('sistema_v52_supreme.db')
                for i in st.session_state.preview_data:
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", (i['ID'], "PSG-REAL", "2025-12-31", i['Local'], 39.2081, -8.6277))
                conn.commit(); conn.close(); st.session_state.preview_data = []; st.rerun()

    with t2:
        conn = sqlite3.connect('sistema_v52_supreme.db')
        staff = conn.execute("SELECT email, nome, telefone, cartoes, ranking FROM clientes").fetchall()
        for e, n, t, c, r in staff:
            with st.expander(f"👤 {n} ({e})"):
                col_a, col_b = st.columns(2)
                col_a.write(f"Ranking: {'⭐'*r}")
                # Log de Notificações
                logs = conn.execute("SELECT tipo, mensagem, timestamp FROM logs_notificacoes WHERE email=? ORDER BY timestamp DESC LIMIT 3", (e,)).fetchall()
                col_b.write("**Últimas Notificações:**")
                for lt, lm, lts in logs: col_b.caption(f"{lts} | {lt}: {lm}")
                if st.button(f"Eliminar {n}", key=f"del_{e}"):
                    conn.execute("DELETE FROM clientes WHERE email=?"); conn.commit(); st.rerun()
        conn.close()

    with t3:
        conn = sqlite3.connect('sistema_v52_supreme.db')
        insc = conn.execute("SELECT * FROM escalas WHERE status='Pendente'").fetchall()
        for r in insc:
            with st.container(border=True):
                st.write(f"**{r[1]}** -> {r[0]}")
                if st.button("✅ Confirmar & Notificar 360º", key=f"v_{r[0]}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r[0],))
                    conn.commit(); multicanal_notify(r[3], r[2], r[1], r[0]); st.rerun()
        conn.close()

    with t5:
        if st.button("🚨 NUCLEAR RESET DB"): init_db(True); st.rerun()

# --- MÓDULOS PÚBLICOS ---
elif nav == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema_v52_supreme.db')
        u = conn.execute("SELECT nome FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Área de {u[0]}")
        meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
        for p, lat, lon, chk in meus:
            with st.container(border=True):
                st.write(p)
                if chk: st.success("✅ Check-in Efetuado")
                elif st.button(f"Validar GPS: {p}"):
                    if haversine(39.2081, -8.6277, lat, lon) <= 500:
                        conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?"); conn.commit(); st.rerun()
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("log_u"):
            st.subheader("Login Colaborador")
            e = st.text_input("Email", value="admin@admin.pt")
            s = st.text_input("Senha", type="password", value="ADMIN")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema_v52_supreme.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                conn.close()

elif nav == "Turnos em Aberto":
    st.header("📅 Postos Disponíveis")
    conn = sqlite3.connect('sistema_v52_supreme.db')
    postos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    for p in postos:
        with st.container(border=True):
            if p[0] in ocupados: st.error(f"❌ {p[0]}")
            else:
                st.success(f"✅ {p[0]}")
                if st.session_state.user_email and st.button("Reservar", key=f"res_{p[0]}"):
                    u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?,?)", (p[0], u[0], u[1], u[2], "2025-12-31", 'Pendente', 1, 1, 0))
                    conn.commit(); st.rerun()
    conn.close()

elif nav == "Registo":
    with st.form("r"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        cart = st.multiselect("Cartões", ["VIG", "ARE", "ARD", "SPR", "COORDENADOR"])
        if st.form_submit_button("Criar / Atualizar"):
            conn = sqlite3.connect('sistema_v52_supreme.db')
            conn.execute("INSERT OR REPLACE INTO clientes VALUES (?,?,?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", ",".join(cart), 5, None))
            conn.commit(); conn.close(); st.session_state.user_email = e; st.rerun()
