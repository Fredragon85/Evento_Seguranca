import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
import time
import base64
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

def init_db():
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER, pref_sms INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS empresas (nome TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT, docs BLOB, ranking INTEGER DEFAULT 5)''')
    conn.commit()
    conn.close()

def enviar_notificacao(email_dest, tel_dest, nome, posto, p_mail, p_sms):
    msg_txt = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO."
    if p_mail:
        try:
            msg = MIMEText(msg_txt); msg['Subject'] = "CONFIRMACAO"; msg['From'] = EMAIL_USER; msg['To'] = email_dest
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(msg)
        except: pass
    if p_sms:
        try: Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).messages.create(body=msg_txt, from_=TWILIO_NUMBER, to=tel_dest)
        except: pass

st.set_page_config(page_title="Segurança Pro v18.0", layout="wide")
init_db()

# --- ADMIN TIMEOUT ---
if st.session_state.get('admin_auth'):
    if 'last_act' not in st.session_state: st.session_state.last_act = time.time()
    if time.time() - st.session_state.last_act > 600:
        st.session_state.admin_auth = False
        st.rerun()
    st.session_state.last_act = time.time()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Sistema Pro")
    if st.button("🏠 PORTAL"): st.session_state.admin_auth = False; st.rerun()
    st.divider()
    if not st.session_state.get('admin_auth'):
        with st.form("admin_login"):
            pwd = st.text_input("Senha Admin", type="password")
            if st.form_submit_button("Entrar"):
                if pwd == ADMIN_PASSWORD: st.session_state.admin_auth = True; st.rerun()
    else:
        st.success("Admin Logado")
        if st.button("Sair"): st.session_state.admin_auth = False; st.rerun()
    
    menu = st.radio("Menu", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])

# --- ADMIN PANEL ---
if st.session_state.get('admin_auth'):
    st.header("🛠️ Administração Avançada")
    t1, t2, t3, t4 = st.tabs(["Gerar Postos", "Validação e Ranking", "Exportar", "Empresas"])

    with t1:
        emp, loc, dat = st.text_input("Empresa"), st.text_input("Localização"), st.date_input("Data", datetime.now())
        txt = st.text_area("Texto dos Turnos", height=100)
        if st.button("Gerar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (emp,))
            l_ref = "Geral"
            for l in txt.split('\n'):
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                if l.isupper() and len(l) > 3: l_ref = l
                else:
                    p_id = f"{l_ref} | {l} ({dat.strftime('%d/%m')})"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?)", (p_id, emp, dat.strftime('%Y-%m-%d'), loc))
            conn.commit(); conn.close(); st.rerun()

    with t2:
        conn = sqlite3.connect('sistema.db')
        df = pd.read_sql_query("SELECT * FROM escalas", conn)
        for _, r in df.iterrows():
            u_info = conn.execute("SELECT ranking FROM clientes WHERE email=?", (r['email'],)).fetchone()
            stars = "⭐" * (u_info[0] if u_info else 0)
            with st.expander(f"{stars} {r['nome']} -> {r['posto']}"):
                col1, col2 = st.columns(2)
                if r['status'] == 'Pendente' and col1.button("Confirmar", key=f"c_{r['posto']}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (r['posto'],))
                    conn.commit()
                    enviar_notificacao(r['email'], r['telefone'], r['nome'], r['posto'], r['pref_email'], r['pref_sms'])
                    st.rerun()
                new_rank = col2.slider("Avaliar Colaborador", 1, 5, u_info[0] if u_info else 5, key=f"rk_{r['posto']}")
                if col2.button("Guardar Nota", key=f"s_rk_{r['posto']}"):
                    conn.execute("UPDATE clientes SET ranking=? WHERE email=?", (new_rank, r['email']))
                    conn.commit(); st.rerun()
        conn.close()

    with t3:
        if st.button("📥 Gerar Relatório Excel"):
            conn = sqlite3.connect('sistema.db')
            df_exp = pd.read_sql_query("SELECT * FROM escalas", conn)
            df_exp.to_excel("relatorio_turnos.xlsx", index=False)
            st.success("Relatório gerado!")

# --- USER INTERFACE ---
elif menu == "Reserva de Turnos":
    st.header("📅 Turnos Disponíveis")
    conn = sqlite3.connect('sistema.db')
    postos = conn.execute("SELECT posto, localizacao FROM configuracao_turnos").fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()
    if postos:
        st.markdown(f'<iframe width="100%" height="200" src="https://maps.google.com/maps?q={postos[0][1]}&output=embed"></iframe>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (p, _) in enumerate(postos):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}")
                elif st.session_state.get('user_email'):
                    with st.popover(f"✅ {p}"):
                        e_ok, s_ok = st.checkbox("Email"), st.checkbox("SMS")
                        if st.button("Reservar", key=f"r_{p}"):
                            conn = sqlite3.connect('sistema.db')
                            u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                            conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?)", (p, u[0], u[1], u[2], datetime.now().strftime('%Y-%m-%d'), 'Pendente', int(e_ok), int(s_ok)))
                            conn.commit(); conn.close(); st.rerun()
                else: st.info(f"🔑 {p}")

elif menu == "Criar Conta":
    st.header("👤 Registo Profissional")
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        doc = st.file_uploader("Upload Cartão Profissional (PNG/JPG)", type=["png", "jpg"])
        if st.form_submit_button("Finalizar"):
            conn = sqlite3.connect('sistema.db')
            blob = doc.read() if doc else None
            conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", "VIG", blob, 5))
            conn.commit(); conn.close(); st.session_state.user_email = e; st.rerun()

elif menu == "Área de Cliente":
    if st.session_state.get('user_email'):
        conn = sqlite3.connect('sistema.db')
        u = conn.execute("SELECT nome, ranking FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Olá {u[0]} | Nível: {'⭐' * u[1]}")
        res = conn.execute("SELECT posto, status FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for p, s in res:
            st.info(f"📍 {p} | Status: {s}")
            if st.button("Desistir", key=f"d_{p}"):
                conn.execute("DELETE FROM escalas WHERE posto=?", (p,)); conn.commit(); st.rerun()
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        e, s = st.text_input("Email"), st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('sistema.db')
            if conn.execute("SELECT 1 FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                st.session_state.user_email = e; st.rerun()
