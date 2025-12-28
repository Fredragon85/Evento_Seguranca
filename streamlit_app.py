import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
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

# --- INICIALIZAÇÃO DA BASE DE DADOS (COM PROTEÇÃO CONTRA ERROS) ---
def init_db(force_reset=False):
    conn = sqlite3.connect('sistema_mestre.db', check_same_thread=False)
    c = conn.cursor()
    if force_reset:
        c.execute("DROP TABLE IF EXISTS escalas")
        c.execute("DROP TABLE IF EXISTS configuracao_turnos")
        c.execute("DROP TABLE IF EXISTS clientes")
    
    # Tabela Escalas: 9 colunas exatas
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER DEFAULT 0, 
                  pref_sms INTEGER DEFAULT 0, checkin INTEGER DEFAULT 0)''')
    
    # Tabela Configuração: 6 colunas exatas
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT, lat REAL, lon REAL)''')
    
    # Tabela Clientes: Informação completa solicitada
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, ranking INTEGER DEFAULT 5, docs BLOB)''')
    conn.commit()
    conn.close()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0 # Metros
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

def enviar_notificacao(email_dest, tel_dest, nome, posto, p_mail, p_sms):
    msg = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO. Bom trabalho!"
    if p_mail:
        try:
            m = MIMEText(msg); m['Subject'] = "CONFIRMACAO"; m['From'] = EMAIL_USER; m['To'] = email_dest
            with smtplib.SMTP("smtp.gmail.com", 587) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        except: pass
    if p_sms:
        try: Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(body=msg, from_=TWILIO_NUMBER, to=tel_dest)
        except: pass

init_db()

# --- ESTADO DA SESSÃO ---
if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False
if 'user_email' not in st.session_state: st.session_state.user_email = None

st.set_page_config(page_title="Gestão de Segurança v30.0", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Segurança Pro")
    if st.button("🏠 PORTAL / HOME", width='stretch'):
        st.session_state.admin_auth = False
        st.rerun()
    st.divider()
    
    if st.session_state.admin_auth:
        st.success("Admin Ativo")
        if st.button("🔒 Sair do Admin"): st.session_state.admin_auth = False; st.rerun()
    else:
        with st.form("login_adm"):
            pw = st.text_input("Senha Admin", type="password")
            if st.form_submit_button("Aceder"):
                if pw == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun()
                else: st.error("Incorreta")
    
    st.divider()
    menu = st.radio("Navegação", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])

# --- MODO ADMIN ---
if st.session_state.admin_auth:
    st.header("🛠️ Painel de Controlo Administrativo")
    t1, t2, t3, t4 = st.tabs(["🚀 Processar Postos", "👥 Base Clientes", "📥 Inscrições", "⚙️ Manutenção"])
    
    with t1:
        st.subheader("Gerador Inteligente de Postos")
        emp = st.text_input("Empresa Responsável", "PSG-REAL")
        txt = st.text_area("Cole a lista bruta de turnos aqui", height=200)
        c_lat = st.number_input("Latitude Almeirim (Referência)", value=39.2081, format="%.6f")
        c_lon = st.number_input("Longitude Almeirim (Referência)", value=-8.6277, format="%.6f")
        if st.button("Gerar Postos"):
            conn = sqlite3.connect('sistema_mestre.db')
            loc_ref, dia_ref = "Geral", "31"
            for l in txt.split('\n'):
                l = l.strip()
                if "DIA" in l.upper(): dia_ref = l
                elif l.isupper() and len(l) > 3: loc_ref = l
                elif "Das" in l and "€" in l:
                    p_id = f"{dia_ref} | {loc_ref} | {l}"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?,?,?)", (p_id, emp, "2025-12-31", loc_ref, c_lat, c_lon))
            conn.commit(); conn.close(); st.success("Postos Criados!")

    with t2:
        st.subheader("Ranking e Gestão de Clientes")
        conn = sqlite3.connect('sistema_mestre.db')
        clis = pd.read_sql_query("SELECT nome, email, telefone, ranking FROM clientes", conn)
        for _, u in clis.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{u['nome']}** - Rank: {'⭐'*u['ranking']}")
                if col2.button("Remover", key=f"del_{u['email']}"):
                    conn.execute("DELETE FROM clientes WHERE email=?", (u['email'],))
                    conn.commit(); st.rerun()
        conn.close()

    with t4:
        st.error("ZONA CRÍTICA")
        if st.button("RECONSTRUIR BASE DE DADOS (Limpa tudo para corrigir erros)"):
            init_db(force_reset=True)
            st.success("Tabelas reconstruídas!"); st.rerun()

# --- RESERVA DE TURNOS ---
elif menu == "Reserva de Turnos":
    st.header("📅 Escalas Disponíveis")
    conn = sqlite3.connect('sistema_mestre.db')
    postos = conn.execute("SELECT posto FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    
    for p in postos:
        p_id = p[0]
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.write(f"### {p_id}")
            if p_id in ocupados:
                c1.error(f"❌ Ocupado por: {ocupados[p_id]}")
            else:
                c1.success("✅ Disponível")
                if st.session_state.user_email:
                    with c2.popover("Confirmar"):
                        e_n, s_n = st.checkbox("Aviso Email", True), st.checkbox("Aviso SMS", True)
                        if st.button("Reservar", key=f"res_{p_id}"):
                            u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                            conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?,?)", (p_id, u[0], u[1], u[2], "2025-12-31", 'Pendente', int(e_n), int(s_n), 0))
                            conn.commit(); st.rerun()
                else: c2.info("Login Necessário")
    conn.close()

# --- ÁREA DE CLIENTE (COM LOGIN E CHECK-IN GPS) ---
elif menu == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema_mestre.db')
        u = conn.execute("SELECT nome, ranking FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Olá {u[0]} | Nível: {'⭐'*u[1]}")
        
        st.divider()
        st.write("### Meus Turnos e Check-in GPS (500 metros)")
        meus = conn.execute("SELECT e.posto, t.lat, t.lon, e.checkin FROM escalas e JOIN configuracao_turnos t ON e.posto = t.posto WHERE e.email = ? AND e.status = 'Confirmado'", (st.session_state.user_email,)).fetchall()
        
        for p, lat, lon, chk in meus:
            with st.container(border=True):
                st.write(f"📍 {p}")
                if chk: st.success("✅ Check-in Efetuado!")
                else:
                    if st.button("📍 Validar Presença Local", key=f"chk_{p}"):
                        # Simulador de GPS em Almeirim
                        dist = haversine(39.2081, -8.6277, lat, lon)
                        if dist <= 500:
                            conn.execute("UPDATE escalas SET checkin=1 WHERE posto=?", (p,))
                            conn.commit(); st.success("Check-in Válido!"); st.rerun()
                        else: st.error(f"Está a {int(dist)}m do local.")
        
        if st.button("Terminar Sessão"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        with st.form("u_login"):
            e = st.text_input("Email")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                conn = sqlite3.connect('sistema_mestre.db')
                if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                    st.session_state.user_email = e; st.rerun()
                else: st.error("Email/Senha Inválidos")
                conn.close()

# --- CRIAR CONTA (FORMULÁRIO DETALHADO) ---
elif menu == "Criar Conta":
    st.header("👤 Novo Registo de Colaborador")
    with st.form("registo"):
        n = st.text_input("Nome Completo")
        e = st.text_input("Email")
        t = st.text_input("Telemóvel")
        s = st.text_input("Senha", type="password")
        col1, col2 = st.columns(2)
        carta = col1.selectbox("Carta Condução", ["Sim", "Não"])
        viatura = col2.selectbox("Viatura Própria", ["Sim", "Não"])
        cartoes = st.multiselect("Cartões Profissionais", ["VIG", "ARE", "ARD", "SPR"])
        doc = st.file_uploader("Upload do Cartão (Imagem)", type=['png', 'jpg'])
        if st.form_submit_button("Finalizar Registo"):
            conn = sqlite3.connect('sistema_mestre.db')
            blob = doc.read() if doc else None
            try:
                conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?,?)", (e, s, n, t, carta, viatura, ",".join(cartoes), 5, blob))
                conn.commit(); st.session_state.user_email = e; st.rerun()
            except: st.error("Erro: Email já registado.")
            finally: conn.close()

