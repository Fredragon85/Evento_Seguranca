import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians

# --- CREDENCIAIS FIXAS ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"

def init_db(force_reset=False):
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    if force_reset:
        c.execute("DROP TABLE IF EXISTS escalas")
        c.execute("DROP TABLE IF EXISTS configuracao_turnos")
        c.execute("DROP TABLE IF EXISTS clientes")
    
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER DEFAULT 0, 
                  pref_sms INTEGER DEFAULT 0, checkin INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT, lat REAL, lon REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5, docs BLOB)''')
    conn.commit()
    conn.close()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

init_db()

# --- INTERFACE ADMIN ---
if st.session_state.get('admin_auth'):
    st.header("🛠️ Administração e Manutenção")
    
    with st.expander("🚨 ZONA DE PERIGO - MANUTENÇÃO"):
        st.warning("O botão abaixo apagará todos os dados (clientes e turnos) para corrigir erros de base de dados.")
        if st.button("RECONSTRUIR BASE DE DADOS DO ZERO"):
            init_db(force_reset=True)
            st.success("Base de dados limpa e reconstruída com sucesso!")
            st.rerun()

    t1, t2 = st.tabs(["🚀 Gerar Turnos", "📋 Gestão de Inscritos"])
    
    with t1:
        txt = st.text_area("Texto dos Postos")
        p_lat = st.number_input("Lat do Evento (Almeirim: 39.2081)", value=39.2081, format="%.6f")
        p_lon = st.number_input("Lon do Evento (Almeirim: -8.6277)", value=-8.6277, format="%.6f")
        if st.button("Processar e Criar"):
            conn = sqlite3.connect('sistema.db')
            for l in txt.split('\n'):
                if "Das" in l and "€" in l:
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", 
                                 (l, "PSG-REAL", "2025-12-31", "Almeirim", p_lat, p_lon))
            conn.commit(); conn.close(); st.success("Postos Criados")

# --- INTERFACE UTILIZADOR ---
elif st.sidebar.radio("Menu", ["Reservar", "Check-in GPS"]) == "Reservar":
    st.header("📅 Reserva de Postos")
    conn = sqlite3.connect('sistema.db')
    postos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    
    for p in postos:
        p_nome = p[0]
        with st.container(border=True):
            if p_nome in ocupados:
                st.error(f"❌ {p_nome}")
            else:
                st.success(f"✅ {p_nome}")
                if st.session_state.get('user_email') and st.button("Confirmar Reserva", key=p_nome):
                    u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?,?)", 
                                 (p_nome, u[0], u[1], u[2], "2025-12-31", 'Pendente', 1, 0, 0))
                    conn.commit(); st.rerun()
    conn.close()

elif st.session_state.get('user_email'):
    st.header("📍 Check-in Local (Raio 500m)")
    conn = sqlite3.connect('sistema.db')
    meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
    
    for p, lat, lon, chk in meus:
        if chk: st.success(f"✅ {p}: Check-in efetuado.")
        else:
            if st.button(f"Validar Presença: {p}"):
                dist = haversine(39.2081, -8.6277, lat, lon) # Coordenadas Almeirim
                if dist <= 500:
                    conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?", (p,))
                    conn.commit(); st.success("Localização validada!"); st.rerun()
                else: st.error(f"Está a {int(dist)}m. Acesso negado.")
    conn.close()
