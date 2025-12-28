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
    conn = sqlite3.connect('sistema_v45_supreme.db', check_same_thread=False)
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
    conn.commit(); conn.close()

def log_notif(email, tipo, msg):
    conn = sqlite3.connect('sistema_v45_supreme.db')
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
    # Twilio/WA
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

st.set_page_config(page_title="V45 OMNI SUPREME", layout="wide")
init_db()

if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'preview_data' not in st.session_state: st.session_state.preview_data = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v45")
    if st.session_state.admin_auth:
        st.success("MODO ADMIN")
        if st.button("🔒 LOGOUT"): st.session_state.admin_auth = False; st.rerun()
    else:
        with st.form("adm_login"):
            pw = st.text_input("Acesso", type="password")
            if st.form_submit_button("🔓"):
                if pw == ADMIN_PASSWORD: st.session_state.admin_auth = True; st.rerun()
    nav = st.radio("Menu", ["Turnos em Aberto", "Área de Cliente", "Registo"])

# --- MODULO ADMIN ---
if st.session_state.admin_auth:
    t1, t2, t3, t4, t5 = st.tabs(["🚀 Gerador", "👥 Staff & Info", "📥 Inscrições", "📋 Postos Ativos", "⚠️ Sistema"])
    
    with t1:
        txt_input = st.text_area("Texto Bruto", height=150)
        if st.button("🔍 GERAR PREVISUALIZAÇÃO"):
            if txt_input:
                preview_list = []
                loc, dia = "Geral", "31"
                for l in txt_input.split('\n'):
                    l = l.strip()
                    if "DIA" in l.upper(): dia = l
                    elif l.isupper() and len(l) > 3 and "DAS" not in l.upper(): loc = l
                    elif "Das" in l and "€" in l:
                        p_id = f"{dia} | {loc} | {l}"
                        preview_list.append({"ID": p_id, "Local": loc, "Horário": l})
                st.session_state.preview_data = preview_list
        if st.session_state.preview_data:
            st.table(pd.DataFrame(st.session_state.preview_data))
            if st.button("✅ PUBLICAR TUDO"):
                conn = sqlite3.connect('sistema_v45_supreme.db')
                for item in st.session_state.preview_data:
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", (item['ID'], "PSG-REAL", "2025-12-31", item['Local'], 39.2081, -8.6277))
                conn.commit(); conn.close(); st.session_state.preview_data = []; st.rerun()

    with t2:
        st.subheader("Informação Detalhada do Colaborador")
        conn = sqlite3.connect('sistema_v45_supreme.db')
        staff = conn.execute("SELECT email, nome, telefone, cartoes, ranking FROM clientes").fetchall()
        for s_email, s_nome, s_tel, s_cart, s_rank in staff:
            with st.expander(f"👤 {s_nome} ({s_email})"):
                c1, c2 = st.columns(2)
                c1.write(f"**Telefone:** {s_tel}")
                c1.write(f"**Cartões:** {s_cart}")
                c1.write(f"**Ranking:** {'⭐'*s_rank}")
                # Turnos Reservados
                reservas = conn.execute("SELECT posto, status, checkin FROM escalas WHERE email=?", (s_email,)).fetchall()
                c2.write("**Turnos Reservados:**")
                if reservas:
                    for r_p, r_s, r_c in reservas:
                        chk_status = "✅ Local" if r_c else "⏳ GPS"
                        c2.caption(f"- {r_p} | {r_s} | {chk_status}")
                else: c2.caption("Sem reservas.")
                # Histórico Notificações
                st.divider()
                st.write("**Histórico de Envio de Mensagens/Emails:**")
                logs = conn.execute("SELECT tipo, mensagem, timestamp FROM logs_notificacoes WHERE email=? ORDER BY timestamp DESC LIMIT 5", (s_email,)).fetchall()
                if logs:
                    for l_t, l_m, l_ts in logs:
                        st.caption(f"{l_ts} | {l_t}: {l_m}")
                else: st.caption("Nenhuma notificação enviada.")
                if st.button("🗑️ Eliminar Staff", key=f"del_st_{s_email}"):
                    conn.execute("DELETE FROM clientes WHERE email=?", (s_email,)); conn.commit(); st.rerun()
        conn.close()

    with t3:
        st.subheader("Modo Confirmação")
        conn = sqlite3.connect('sistema_v45_supreme.db')
        insc = conn.execute("SELECT * FROM escalas WHERE status='Pendente'").fetchall()
        for r in insc:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{r[1]}** quer o posto: `{r[0]}`")
                if col2.button("✅ Confirmar", key=f"v_{r[0]}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r[0],))
                    conn.commit(); multicanal_notify(r[3], r[2], r[1], r[0]); st.rerun()
        conn.close()

    with t4:
        conn = sqlite3.connect('sistema_v45_supreme.db')
        ativos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
        for p in ativos:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.write(p[0])
                if c2.button("🗑️", key=f"rm_p_{p[0]}"):
                    conn.execute("DELETE FROM configuracao_turnos WHERE posto=?"); conn.commit(); st.rerun()
        conn.close()

    with t5:
        if st.button("🚨 NUCLEAR RESET"): init_db(True); st.rerun()

# --- MÓDULOS PÚBLICOS (RESERVA, CLIENTE, REGISTO) ---
elif nav == "Turnos em Aberto":
    st.header("📅 Escalas")
    conn = sqlite3.connect('sistema_v45_supreme.db')
    postos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    for p in postos:
        p_id = p[0]
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            if p_id in ocupados: c1.error(f"❌ {p_id}")
            else:
                c1.success(f"✅ {p_id}")
                if st.session_state.user_email and c2.button("Reservar", key=f"res_{p_id}"):
                    u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?,?)", (p_id, u[0], u[1], u[2], "2025-12-31", 'Pendente', 1, 1, 0))
                    conn.commit(); st.rerun()
    conn.close()

elif nav == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema_v45_supreme.db')
        u = conn.execute("SELECT nome FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Área de {u[0]}")
        meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
        for p, lat, lon, chk in meus:
            with st.container(border=True):
                st.write(p)
                if not chk and st.button(f"Validar Local: {p}"):
                    if haversine(39.2081, -8.6277, lat, lon) <= 500:
                        conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?"); conn.commit(); st.rerun()
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("l"):
            e, s = st.text_input("Email"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema_v45_supreme.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                conn.close()

elif nav == "Registo":
    with st.form("r"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        cart = st.multiselect("Cartões", ["VIG", "ARE", "ARD", "SPR", "COORDENADOR"])
        if st.form_submit_button("Registar/Atualizar"):
            conn = sqlite3.connect('sistema_v45_supreme.db')
            conn.execute("INSERT OR REPLACE INTO clientes VALUES (?,?,?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", ",".join(cart), 5, None))
            conn.commit(); conn.close(); st.session_state.user_email = e; st.rerun()
