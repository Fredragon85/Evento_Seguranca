import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import time
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians

# --- CONFIGURAÇÕES E CREDENCIAIS ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
TWILIO_WHATSAPP = "whatsapp:+351939227659"
TELEGRAM_BOT_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT_ID = "@sua_canal_seguranca"

# --- CORE: DATABASE ---
def init_db(force_reset=False):
    conn = sqlite3.connect('sistema_v40_supreme.db', check_same_thread=False)
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

# --- UTILS: GEO & ALERTS ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def multicanal_notify(email, tel, nome, posto, acao="CONFIRMADO"):
    msg = f"Ola {nome}, o seu turno {posto} foi {acao}."
    try:
        m = MIMEText(msg); m['Subject'] = acao; m['From'] = EMAIL_USER; m['To'] = email
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
    except: pass
    tw = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try: tw.messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:{tel}")
    except: pass
    try: tw.messages.create(from_=TWILIO_NUMBER, body=msg, to=tel)
    except: pass
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                       data={"chat_id": TELEGRAM_CHAT_ID, "text": f"📢 {acao}: {nome} em {posto}"})
    except: pass

# --- UI CONFIG ---
st.set_page_config(page_title="V40 OMNI SUPREME", layout="wide")
init_db()

if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ V40 OMNI")
    if st.button("🔄 ATUALIZAR SISTEMA"): st.rerun()
    st.divider()
    if st.session_state.admin_auth:
        st.success("Sessão Admin Ativa")
        if st.button("🔒 LOGOUT"): st.session_state.admin_auth = False; st.rerun()
    else:
        with st.form("adm_login"):
            pw = st.text_input("Acesso Restrito", type="password")
            if st.form_submit_button("Entrar"):
                if pw == ADMIN_PASSWORD: st.session_state.admin_auth = True; st.rerun()
    st.divider()
    nav = st.radio("Navegação", ["Turnos em Aberto", "Área de Cliente", "Registo Profissional"])

# --- MODULO ADMIN ---
if st.session_state.admin_auth:
    t1, t2, t3, t4, t5 = st.tabs(["🚀 Publicador", "📋 Gestão Postos", "👥 Staff", "📥 Inscrições", "⚠️ Sistema"])
    
    with t1:
        st.subheader("Processamento de Texto para Postos")
        txt_input = st.text_area("Texto Bruto (WhatsApp/Email)", height=150)
        c1, c2 = st.columns(2)
        lat_pub = c1.number_input("Lat Ref", value=39.2081, format="%.6f")
        lon_pub = c2.number_input("Lon Ref", value=-8.6277, format="%.6f")

        if txt_input:
            st.divider()
            dados_extraidos = []
            loc, dia = "Geral", "31"
            for l in txt_input.split('\n'):
                l = l.strip()
                if "DIA" in l.upper(): dia = l
                elif l.isupper() and len(l) > 3 and "DAS" not in l.upper(): loc = l
                elif "Das" in l and "€" in l:
                    p_id = f"{dia} | {loc} | {l}"
                    dados_extraidos.append({"ID": p_id, "Local": loc, "Horário": l})
            
            if dados_extraidos:
                st.write("### 👁️ Previsualização do Draft")
                st.table(pd.DataFrame(dados_extraidos))
                if st.button("🚀 CONFIRMAR PUBLICAÇÃO FINAL", use_container_width=True):
                    conn = sqlite3.connect('sistema_v40_supreme.db')
                    for item in dados_extraidos:
                        conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", 
                                     (item['ID'], "PSG-REAL", "2025-12-31", item['Local'], lat_pub, lon_pub))
                    conn.commit(); conn.close()
                    st.success("Postos Publicados!"); time.sleep(1); st.rerun()

    with t2:
        st.subheader("Controlo de Postos Ativos")
        conn = sqlite3.connect('sistema_v40_supreme.db')
        ativos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
        for p in ativos:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                col1.write(p[0])
                if col2.button("🗑️", key=f"rm_p_{p[0]}"):
                    conn.execute("DELETE FROM configuracao_turnos WHERE posto=?", (p[0],))
                    conn.execute("DELETE FROM escalas WHERE posto=?", (p[0],))
                    conn.commit(); st.rerun()
        conn.close()

    with t4:
        st.subheader("Inscrições Pendentes")
        conn = sqlite3.connect('sistema_v40_supreme.db')
        insc = conn.execute("SELECT * FROM escalas").fetchall()
        for r in insc:
            with st.expander(f"{r[5]} | {r[1]} -> {r[0]}"):
                if r[5] == 'Pendente' and st.button("Validar & Notificar", key=f"ok_{r[0]}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r[0],))
                    conn.commit(); multicanal_notify(r[3], r[2], r[1], r[0]); st.rerun()
                if st.button("Remover Inscrição", key=f"del_ins_{r[0]}"):
                    conn.execute("DELETE FROM escalas WHERE posto=?", (r[0],)); conn.commit(); st.rerun()
        conn.close()

    with t5:
        if st.button("🚨 NUCLEAR RESET DB"): init_db(True); st.rerun()

# --- MODULO RESERVA ---
elif nav == "Turnos em Aberto":
    st.header("📅 Lista de Postos")
    conn = sqlite3.connect('sistema_v40_supreme.db')
    postos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    
    for p in postos:
        p_id = p[0]
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            if p_id in ocupados: c1.error(f"❌ Ocupado por: {ocupados[p_id]}")
            else:
                c1.success(f"✅ Disponível: {p_id}")
                if st.session_state.user_email and c2.button("Reservar", key=f"res_{p_id}"):
                    u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?,?)", (p_id, u[0], u[1], u[2], "2025-12-31", 'Pendente', 1, 1, 0))
                    conn.commit(); st.rerun()
    conn.close()

# --- MODULO CLIENTE ---
elif nav == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema_v40_supreme.db')
        u = conn.execute("SELECT nome, ranking FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Colaborador: {u[0]} | Nível: {'⭐'*u[1]}")
        
        st.divider()
        st.write("### Meus Turnos Confirmados (Check-in GPS)")
        meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
        for p, lat, lon, chk in meus:
            with st.container(border=True):
                st.write(p)
                if chk: st.success("✅ Presença Confirmada no Local")
                else:
                    if st.button("📍 Validar Check-in (500m)", key=f"chk_{p}"):
                        dist = haversine(39.2081, -8.6277, lat, lon) # Referência Almeirim
                        if dist <= 500:
                            conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?", (p,))
                            conn.commit(); st.rerun()
                        else: st.error(f"Fora de Alcance ({int(dist)}m)")
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("login_u"):
            e, s = st.text_input("Email"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema_v40_supreme.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                conn.close()

# --- MODULO REGISTO ---
elif nav == "Registo Profissional":
    with st.form("reg_final"):
        st.subheader("Novo Registo de Colaborador")
        n, e, t, s = st.text_input("Nome Completo"), st.text_input("Email"), st.text_input("Telemóvel"), st.text_input("Senha", type="password")
        cart = st.multiselect("Qualificações", ["VIG", "ARE", "ARD", "SPR", "COORDENADOR", "MARE", "ASSISTENTE"])
        if st.form_submit_button("Criar Conta Profissional"):
            conn = sqlite3.connect('sistema_v40_supreme.db')
            try:
                conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", ",".join(cart), 5, None))
                conn.commit(); st.session_state.user_email = e; st.rerun()
            except: st.error("Erro no registo (Email existente).")
            finally: conn.close()


