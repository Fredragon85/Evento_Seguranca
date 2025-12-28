import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import bcrypt
import time
import re
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians
from contextlib import closing

# --- CONFIGURAÇÕES MESTRE ---
ADMIN_PASS_MESTRE = "ADMIN123" # ALTERA ESTA PASSWORD PARA A SEGURANÇA DO PAINEL
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_WHATSAPP = "whatsapp:+14155238886"
TELEGRAM_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT = "@FredSilva85_pt"

MEU_WA_LINK = "https://wa.me/3519339227659"
DB_NAME = 'sistema_v68_supreme.db'

# --- SEGURANÇA ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    if isinstance(hashed, str): hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# --- DATABASE ---
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
                          status TEXT DEFAULT 'Pendente', pref_metodo TEXT, checkin INTEGER DEFAULT 0, pago INTEGER DEFAULT 0, valor REAL DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                         (posto TEXT PRIMARY KEY, localizacao TEXT, lat REAL, lon REAL, valor REAL DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                         (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT)''')

def multicanal_notify(tel, nome, posto, metodo, email=None):
    msg = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO."
    if metodo in ["WhatsApp", "Ambos"]:
        try: Client(TWILIO_SID, TWILIO_TOKEN).messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:+351{tel}")
        except: pass
    if (metodo in ["Email", "Ambos"]) and email:
        try:
            m = MIMEText(msg); m['Subject'] = "CONFIRMACAO"; m['From'] = EMAIL_USER; m['To'] = email
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        except: pass

init_db()

# --- SESSÃO ---
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'admin_unlocked' not in st.session_state: st.session_state.admin_unlocked = False

st.set_page_config(page_title="V68 SUPREME", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v68")
    
    # LOGIN UTILIZADOR
    if st.session_state.user_email:
        st.success(f"👤 {st.session_state.user_email}")
        if st.button("🔒 Logout"): st.session_state.user_email = None; st.rerun()
    else:
        with st.form("login_u"):
            e = st.text_input("Email")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                with get_db_conn() as conn:
                    res = conn.execute("SELECT senha FROM clientes WHERE email=?", (e,)).fetchone()
                    if res and check_password(s, res[0]):
                        st.session_state.user_email = e; st.rerun()
                    else: st.error("Erro")

    st.divider()
    
    # ACESSO ADMIN COM PASSWORD
    if not st.session_state.admin_unlocked:
        with st.expander("🔑 ÁREA RESTRITA (ADMIN)"):
            pw = st.text_input("Password Mestre", type="password")
            if st.button("Desbloquear Painel"):
                if pw == ADMIN_PASS_MESTRE:
                    st.session_state.admin_unlocked = True; st.rerun()
                else: st.error("Incorreta")
    else:
        st.warning("⚠️ MODO ADMIN ATIVO")
        if st.button("Trancar Painel"): st.session_state.admin_unlocked = False; st.rerun()

    nav = st.radio("Menu", ["Turnos Disponíveis", "Minha Área", "Criar Conta"])

# --- ÁREA ADMIN (SÓ APARECE SE DESBLOQUEADO) ---
if st.session_state.admin_unlocked:
    st.divider()
    st.subheader("🛠️ Gestão Administrativa")
    tab_ins, tab_pag, tab_ger = st.tabs(["📥 Inscrições", "💰 Pagamentos", "🚀 Gerador"])
    
    with tab_ger:
        txt = st.text_area("Texto Bruto")
        if st.button("Analisar e Publicar"):
            # Lógica de Regex para valor em € integrada
            for l in txt.split('\n'):
                if "Das" in l:
                    match = re.search(r'(\d+[\.,]?\d*)\s*(?:€|euro)', l, re.IGNORECASE)
                    preco = float(match.group(1).replace(',', '.')) if match else 0.0
                    with get_db_conn() as conn:
                        conn.execute("INSERT OR IGNORE INTO configuracao_turnos (posto, valor, lat, lon) VALUES (?,?,?,?)", 
                                     (l.strip(), preco, 39.2081, -8.6277))
            st.success("Publicado")

    with tab_ins:
        with get_db_conn() as conn:
            pedidos = conn.execute("SELECT id, posto, nome, telefone, email, pref_metodo FROM escalas WHERE status='Pendente'").fetchall()
            for id_e, p_id, nome, tel, mail, pref in pedidos:
                st.write(f"**{nome}** -> {p_id}")
                if st.button("✅ Confirmar", key=f"c_{id_e}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE id=?", (id_e,))
                    multicanal_notify(tel, nome, p_id, pref, mail); st.rerun()

    with tab_pag:
        with get_db_conn() as conn:
            lista = conn.execute("SELECT id, nome, posto, valor FROM escalas WHERE status='Confirmado' AND checkin=1 AND pago=0").fetchall()
            for id_p, n_p, post_p, val_p in lista:
                c1, c2 = st.columns([4, 1])
                c1.write(f"{n_p} | {post_p} | **{val_p}€**")
                if c2.button("Pagar", key=f"p_{id_p}"):
                    conn.execute("UPDATE escalas SET pago=1 WHERE id=?", (id_p,)); st.rerun()

# --- MÓDULOS PÚBLICOS ---
if nav == "Turnos Disponíveis":
    st.header("📅 Escalas")
    with get_db_conn() as conn:
        postos = conn.execute("SELECT posto, valor FROM configuracao_turnos").fetchall()
        for p_id, val in postos:
            with st.container(border=True):
                st.write(f"**{p_id}** ({val}€)")
                if st.session_state.user_email and st.button("Reservar", key=f"r_{p_id}"):
                    u = conn.execute("SELECT nome, telefone FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                    conn.execute("INSERT INTO escalas (posto, nome, telefone, email, valor) VALUES (?,?,?,?,?)", 
                                 (p_id, u[0], u[1], st.session_state.user_email, val))
                    st.success("Reservado")

elif nav == "Minha Área":
    if not st.session_state.user_email: st.info("Login necessário")
    else:
        with get_db_conn() as conn:
            meus = conn.execute("SELECT posto, status, valor, pago FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
            for p, s, v, pg in meus:
                st.write(f"{p} | {s} | {v}€ | {'Pago ✅' if pg else 'Pendente ⏳'}")

elif nav == "Criar Conta":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Registar"):
            with get_db_conn() as conn:
                conn.execute("INSERT INTO clientes VALUES (?,?,?,?)", (e, hash_password(s).decode('utf-8'), n, t))
            st.success("OK"); st.rerun()
