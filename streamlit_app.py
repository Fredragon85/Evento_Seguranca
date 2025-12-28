import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from datetime import datetime

# --- CONFIGURAÇÕES ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"

BG_IMG = "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&q=80&w=1920"

def init_db():
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS empresas (nome TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT)''')
    conn.commit()
    conn.close()

def test_email():
    try:
        msg = MIMEText("Teste de Sistema")
        msg['Subject'] = "Teste Funcional"
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_USER
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        return True
    except: return False

def test_sms():
    try:
        c = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        c.messages.create(body="Teste de Sistema", from_=TWILIO_NUMBER, to="+351939227659")
        return True
    except: return False

st.set_page_config(page_title="Gestão de Segurança v9.0", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

if 'user_email' not in st.session_state: st.session_state.user_email = None

# --- SIDEBAR & NAVEGAÇÃO ---
with st.sidebar:
    if st.button("🏠 HOME / PORTAL", width='stretch'):
        st.session_state.menu_choice = "Home"
        st.rerun()
    
    st.divider()
    db_conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in db_conn.execute("SELECT nome FROM empresas").fetchall()]
    db_conn.close()
    
    emp_filtro = st.selectbox("Empresa", ["Todas"] + empresas)
    data_filtro = st.date_input("Data", datetime.now())
    
    menu = st.radio("Navegação:", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    
    st.divider()
    admin_check = st.checkbox("⚙️ Admin Mode")
    if admin_check:
        pwd = st.text_input("Senha", type="password")
        st.session_state.admin_auth = (pwd == ADMIN_PASSWORD)

# --- LOGICA DE PAGINAÇÃO DE TURNOS ---
def get_postos(emp, dt):
    conn = sqlite3.connect('sistema.db')
    query = "SELECT posto, localizacao FROM configuracao_turnos WHERE data = ?"
    params = [dt.strftime('%Y-%m-%d')]
    if emp != "Todas":
        query += " AND empresa = ?"
        params.append(emp)
    res = conn.execute(query, params).fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()
    return res, ocupados

# --- MODO ADMIN ---
if admin_check and st.session_state.get('admin_auth', False):
    st.header("🛠️ Administração")
    t1, t2, t3 = st.tabs(["Gerar Postos", "Inscrições", "Testes de Comunicação"])

    with t3:
        if st.button("Enviar Email de Teste"):
            if test_email(): st.success("Email funcional!")
            else: st.error("Falha no Email.")
        if st.button("Enviar SMS de Teste"):
            if test_sms(): st.success("SMS funcional!")
            else: st.error("Falha no SMS.")

    with t1:
        nova_emp = st.text_input("Nome da Empresa")
        local_geo = st.text_input("Localização (Cidade/Morada para Maps)")
        alvo_dat = st.date_input("Data Evento", datetime.now(), key="admin_dt")
        txt_bruto = st.text_area("Texto Bruto (LOCAIS MAIÚSCULAS)", height=150)
        
        if st.button("🚀 Gerar"):
            conn = sqlite3.connect('sistema.db')
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (nova_emp.strip(),))
            local_f = "Geral"
            for l in txt_bruto.split('\n'):
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                if l.isupper() and len(l) > 3 and not tem_h: local_f = l
                else:
                    p_id = f"{local_f} | {l} ({alvo_dat.strftime('%d/%m')})"
                    cursor.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?)", 
                                 (p_id, nova_emp.strip(), alvo_dat.strftime('%Y-%m-%d'), local_geo))
            conn.commit(); conn.close(); st.rerun()

# --- ÁREA DE CLIENTE ---
elif menu == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema.db')
        user = conn.execute("SELECT * FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Perfil: {user[2]}")
        
        st.write("### Meus Turnos")
        meus_turnos = conn.execute("SELECT posto FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for r in meus_turnos:
            col_t, col_b = st.columns([4,1])
            col_t.info(f"📍 {r[0]}")
            if col_b.button("Apagar", key=f"del_{r[0]}"):
                conn.execute("DELETE FROM escalas WHERE posto=?", (r[0],))
                conn.commit(); st.rerun()
        
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        e, s = st.text_input("Email"), st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('sistema.db')
            u = conn.execute("SELECT email FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone()
            if u: st.session_state.user_email = e; st.rerun()
            else: st.error("Dados Inválidos.")

# --- RESERVA E PREVISUALIZAÇÃO ---
elif menu == "Reserva de Turnos":
    st.title("📅 Turnos Disponíveis")
    postos, ocupados = get_postos(emp_filtro, data_filtro)
    
    if postos:
        # MAPA DO LOCAL (Utiliza a localização do primeiro turno da lista)
        loc = postos[0][1] if postos[0][1] else "Portugal"
        st.markdown(f'<iframe width="100%" height="300" src="https://maps.google.com/maps?q={loc}&t=&z=13&ie=UTF8&iwloc=&output=embed"></iframe>', unsafe_allow_html=True)
        
        st.divider()
        
        # Paginação / Navegação de Turnos
        if 'idx' not in st.session_state: st.session_state.idx = 0
        
        c_prev, c_info, c_next = st.columns([1,3,1])
        if c_prev.button("⬅️ Anterior") and st.session_state.idx > 0: st.session_state.idx -= 1
        if c_next.button("Próximo ➡️") and st.session_state.idx < len(postos)-1: st.session_state.idx += 1
        
        p_atual = postos[st.session_state.idx][0]
        is_oc = p_atual in ocupados
        
        with c_info:
            st.markdown(f"### Turno: {p_atual}")
            if is_oc: st.error("STATUS: OCUPADO")
            else: st.success("STATUS: LIVRE (Requer Login para reservar)")

            if not is_oc:
                if st.session_state.user_email:
                    if st.button("✅ CONFIRMAR RESERVA"):
                        conn = sqlite3.connect('sistema.db')
                        udata = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                        conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", (p_atual, udata[0], udata[1], udata[2], data_filtro.strftime('%Y-%m-%d')))
                        conn.commit(); conn.close(); st.success("Reservado!"); st.rerun()
                else:
                    st.warning("Efetue Login ou Registe-se para confirmar este turno.")

# --- CRIAR CONTA COM EXTRAS ---
elif menu == "Criar Conta":
    st.subheader("Registo de Profissional")
    with st.form("reg_ext"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        carta = st.selectbox("Carta de Condução", ["Sim", "Não"])
        viatura = st.selectbox("Viatura Própria", ["Sim", "Não"])
        cartoes = st.multiselect("Cartões Segurança Privada", ["VIG", "ARE", "ADIR", "MARE", "SPR"])
        
        if st.form_submit_button("Registar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?)", 
                         (e, s, n, t, carta, viatura, ", ".join(cartoes)))
            conn.commit(); conn.close()
            st.session_state.user_email = e; st.rerun()
