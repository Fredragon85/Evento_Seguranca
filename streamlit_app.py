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
TWILIO_WHATSAPP = "whatsapp:+14155238886"
TELEGRAM_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT = "@FredSilva85_pt"

MEU_WA_LINK = "https://wa.me/3519339227659"
MEU_TG_LINK = "https://t.me/FredSilva85_pt"

DB_NAME = 'sistema_v58_supreme.db'

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
                          status TEXT DEFAULT 'Pendente', pref_metodo TEXT, checkin INTEGER DEFAULT 0)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                         (posto TEXT PRIMARY KEY, empresa TEXT, localizacao TEXT, lat REAL, lon REAL)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                         (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                          is_admin INTEGER DEFAULT 0, cartoes TEXT, ranking INTEGER DEFAULT 5)''')
            
            # Admin Inicial
            admin_pwd = hash_password("ADMIN").decode('utf-8')
            c.execute("INSERT OR REPLACE INTO clientes (email, senha, nome, is_admin) VALUES (?,?,?,?)",
                      ("admin@admin.pt", admin_pwd, "ADMIN MASTER", 1))

def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

init_db()

# --- SESSÃO ---
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

st.set_page_config(page_title="V58 SUPREME", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v58")
    if st.session_state.user_email:
        st.success(f"Logado: {st.session_state.user_email}")
        if st.session_state.is_admin: st.warning("Acesso Administrador")
        if st.button("🔒 Sair"): 
            st.session_state.user_email = None
            st.session_state.is_admin = False
            st.rerun()
    else:
        with st.form("login_form"):
            e = st.text_input("Email", value="admin@admin.pt")
            s = st.text_input("Senha", type="password", value="ADMIN")
            if st.form_submit_button("Entrar"):
                with get_db_conn() as conn:
                    res = conn.execute("SELECT senha, is_admin FROM clientes WHERE email=?", (e,)).fetchone()
                    if res and check_password(s, res[0]):
                        st.session_state.user_email = e
                        st.session_state.is_admin = bool(res[1])
                        st.rerun()
                    else: st.error("Falha no login.")

    nav = st.radio("Navegação", ["Turnos em Aberto", "Área de Cliente", "Registo"])
    if st.session_state.is_admin:
        st.divider()
        nav_admin = st.selectbox("Painel Admin", ["Gerir Postos", "Validar Inscrições", "Gestão de Staff"])
    
    st.divider()
    st.link_button("💬 Suporte WhatsApp", MEU_WA_LINK, use_container_width=True)

# --- MÓDULO: TURNOS EM ABERTO ---
if nav == "Turnos em Aberto":
    st.header("📅 Postos Disponíveis")
    if not st.session_state.user_email: st.info("Faça login para reservar.")
    
    with get_db_conn() as conn:
        postos = conn.execute("SELECT posto, localizacao FROM configuracao_turnos").fetchall()
        reservados = [r[0] for r in conn.execute("SELECT posto FROM escalas WHERE status != 'Cancelado'").fetchall()]
        
        for p_id, loc in postos:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                if p_id in reservados:
                    c1.error(f"❌ {p_id} (Já Reservado)")
                else:
                    c1.success(f"✅ {p_id} - {loc}")
                    if st.session_state.user_email:
                        metodo = c2.selectbox("Confirmar via:", ["Email", "WhatsApp", "Ambos"], key=f"met_{p_id}")
                        if c2.button("Reservar", key=f"btn_{p_id}"):
                            u = conn.execute("SELECT nome, telefone FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                            conn.execute("INSERT INTO escalas (posto, nome, telefone, email, pref_metodo) VALUES (?,?,?,?,?)",
                                         (p_id, u[0], u[1], st.session_state.user_email, metodo))
                            st.toast(f"Reserva enviada para {p_id}!")
                            st.rerun()

# --- MÓDULO: ÁREA DE CLIENTE ---
elif nav == "Área de Cliente":
    if not st.session_state.user_email:
        st.warning("Acesse a sua conta primeiro.")
    else:
        st.header("📋 Minhas Atividades")
        with get_db_conn() as conn:
            meus = conn.execute('''
                SELECT e.posto, e.status, e.checkin, t.lat, t.lon 
                FROM escalas e 
                LEFT JOIN configuracao_turnos t ON e.posto = t.posto 
                WHERE e.email = ?''', (st.session_state.user_email,)).fetchall()
            
            if not meus: st.info("Não tem turnos reservados.")
            for p, status, chk, lat, lon in meus:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"**Posto:** {p}")
                    col1.caption(f"Status: {status}")
                    
                    if status == "Confirmado":
                        if chk: col2.success("✅ No Local")
                        elif lat and lon:
                            if col2.button("📍 Check-in GPS", key=f"chk_{p}"):
                                if haversine_meters(39.2081, -8.6277, lat, lon) <= 500:
                                    conn.execute("UPDATE escalas SET checkin=1 WHERE posto=? AND email=?", (p, st.session_state.user_email))
                                    st.rerun()
                                else: st.error("Fora de alcance!")

# --- MÓDULOS ADMINISTRATIVOS ---
if st.session_state.is_admin:
    st.divider()
    if nav_admin == "Gerir Postos":
        st.subheader("🚀 Publicação de Escalas")
        txt = st.text_area("Cole o texto bruto aqui")
        if st.button("Gerar Postos"):
            # Lógica de extração simplificada para exemplo
            with get_db_conn() as conn:
                conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?)", 
                             ("POSTO TESTE", "PSG", "Almeirim", 39.2081, -8.6277))
            st.success("Posto teste gerado!")

    elif nav_admin == "Validar Inscrições":
        st.subheader("📥 Pedidos Pendentes")
        with get_db_conn() as conn:
            pedidos = conn.execute("SELECT id, posto, nome, email, pref_metodo FROM escalas WHERE status='Pendente'").fetchall()
            for id_e, p_id, nome, email, pref in pedidos:
                with st.container(border=True):
                    st.write(f"**{nome}** ({email}) -> {p_id}")
                    st.caption(f"Preferência de Notificação: {pref}")
                    if st.button("✅ Confirmar Turno", key=f"conf_{id_e}"):
                        conn.execute("UPDATE escalas SET status='Confirmado' WHERE id=?", (id_e,))
                        # Aqui dispararia multicanal_notify
                        st.rerun()

    elif nav_admin == "Gestão de Staff":
        st.subheader("👥 Colaboradores Registados")
        with get_db_conn() as conn:
            users = conn.execute("SELECT email, nome, is_admin FROM clientes").fetchall()
            for u_email, u_nome, is_adm in users:
                with st.expander(f"{u_nome} ({u_email})"):
                    st.write(f"Admin: {'Sim' if is_adm else 'Não'}")
                    if not is_adm:
                        if st.button("Promover a Admin", key=f"prom_{u_email}"):
                            conn.execute("UPDATE clientes SET is_admin=1 WHERE email=?", (u_email,))
                            st.rerun()
