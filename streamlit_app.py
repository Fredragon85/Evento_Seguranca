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
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT, 
                  status TEXT DEFAULT 'Pendente', pref_email INTEGER DEFAULT 0, pref_sms INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                 (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT, localizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS empresas (nome TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT, 
                  carta TEXT, viatura TEXT, cartoes TEXT)''')
    conn.commit()
    conn.close()

def enviar_notificacao_filtrada(email_dest, tel_dest, nome, posto, p_mail, p_sms):
    mensagem = f"Ola {nome}, o seu turno no posto {posto} foi CONFIRMADO. Bom trabalho!"
    if p_mail == 1:
        try:
            msg = MIMEText(mensagem); msg['Subject'] = "CONFIRMACAO DE TURNO"
            msg['From'] = EMAIL_USER; msg['To'] = email_dest
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(msg)
        except: pass
    if p_sms == 1:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=tel_dest)
        except: pass

st.set_page_config(page_title="Gestão de Segurança v14.0", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

# --- ESTADO DE SESSÃO ---
if 'user_email' not in st.session_state: st.session_state.user_email = None
if 'admin_auth' not in st.session_state: st.session_state.admin_auth = False

# --- SIDEBAR ---
with st.sidebar:
    if st.button("🏠 HOME / PORTAL", width='stretch'):
        st.session_state.user_email = None
        st.session_state.admin_auth = False
        st.rerun()
    st.divider()
    
    db_conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in db_conn.execute("SELECT nome FROM empresas").fetchall()]
    db_conn.close()
    
    emp_filtro = st.selectbox("Empresa", ["Todas"] + empresas)
    data_filtro = st.date_input("Data", datetime.now())
    menu = st.radio("Menu:", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    
    st.divider()
    st.subheader("⚙️ Acesso Admin")
    with st.form("admin_login_form"):
        pwd = st.text_input("Senha de Administrador", type="password")
        if st.form_submit_button("🔓 Entrar no Modo Admin"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_auth = True
                st.success("Acesso autorizado!")
                st.rerun()
            else:
                st.session_state.admin_auth = False
                st.error("Senha incorreta.")

# --- INTERFACE ADMIN ---
if st.session_state.admin_auth:
    st.header("🛠️ Painel de Administração")
    t1, t2, t3, t4 = st.tabs(["Gerar Postos", "Inscrições", "Empresas", "Sistema"])

    with t1:
        nova_emp_gen = st.text_input("Empresa:")
        local_geo = st.text_input("Localização (Morada):")
        txt_bruto = st.text_area("Texto dos Turnos:", height=150)
        if st.button("🚀 Criar Postos"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (nova_emp_gen.strip(),))
            local_f = "Geral"
            for l in txt_bruto.split('\n'):
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                if l.isupper() and len(l) > 3 and not re.search(r"\d+h", l): local_f = l
                else:
                    p_id = f"{local_f} | {l} ({data_filtro.strftime('%d/%m')})"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?,?)", 
                                 (p_id, nova_emp_gen.strip(), data_filtro.strftime('%Y-%m-%d'), local_geo))
            conn.commit(); conn.close(); st.rerun()

    with t2:
        conn = sqlite3.connect('sistema.db')
        df_i = pd.read_sql_query("SELECT * FROM escalas", conn)
        for _, row in df_i.iterrows():
            with st.expander(f"{'✅' if row['status'] == 'Confirmado' else '⏳'} {row['nome']} - {row['posto']}"):
                st.write(f"Preferências: Email={row['pref_email']}, SMS={row['pref_sms']}")
                if row['status'] == 'Pendente' and st.button("Confirmar e Notificar", key=f"adm_conf_{row['posto']}"):
                    conn.execute("UPDATE escalas SET status='Confirmado' WHERE posto=?", (row['posto'],))
                    conn.commit()
                    enviar_notificacao_filtrada(row['email'], row['telefone'], row['nome'], row['posto'], row['pref_email'], row['pref_sms'])
                    st.rerun()
                if st.button("Eliminar", key=f"adm_del_{row['posto']}"):
                    conn.execute("DELETE FROM escalas WHERE posto=?", (row['posto'],))
                    conn.commit(); st.rerun()
        conn.close()

# --- INTERFACE UTILIZADOR ---
elif menu == "Reserva de Turnos":
    st.title("📅 Turnos")
    conn = sqlite3.connect('sistema.db')
    query = "SELECT posto, localizacao FROM configuracao_turnos WHERE data=?"
    params = [data_filtro.strftime('%Y-%m-%d')]
    if emp_filtro != "Todas": query += " AND empresa=?"; params.append(emp_filtro)
    postos = conn.execute(query, params).fetchall()
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if postos:
        st.markdown(f'<iframe width="100%" height="200" src="https://maps.google.com/maps?q={postos[0][1]}&output=embed"></iframe>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (p, _) in enumerate(postos):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}")
                else:
                    st.success(f"✅ {p}")
                    if st.session_state.user_email:
                        with st.popover("Reservar"):
                            e_not = st.checkbox("Email", key=f"en_{p}")
                            s_not = st.checkbox("SMS", key=f"sn_{p}")
                            if st.button("Confirmar", key=f"c_res_{p}"):
                                conn = sqlite3.connect('sistema.db')
                                u = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                                conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?,?,?,?)", (p, u[0], u[1], u[2], data_filtro.strftime('%Y-%m-%d'), 'Pendente', int(e_not), int(s_not)))
                                conn.commit(); conn.close(); st.rerun()

elif menu == "Criar Conta":
    with st.form("reg_v14"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT INTO clientes VALUES (?,?,?,?,?,?,?)", (e, s, n, t, "Sim", "Sim", "VIG"))
            conn.commit(); conn.close(); st.session_state.user_email = e; st.rerun()

elif menu == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema.db')
        res = conn.execute("SELECT posto, status FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for p, s in res:
            st.info(f"📍 {p} | Status: {s}")
            if st.button("Desistir", key=f"cl_del_{p}"):
                conn.execute("DELETE FROM escalas WHERE posto=?", (p,)); conn.commit(); st.rerun()
        if st.button("Logout"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        e, s = st.text_input("Email"), st.text_input("Senha", type="password")
        if st.button("Login"):
            conn = sqlite3.connect('sistema.db')
            if conn.execute("SELECT email FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone():
                st.session_state.user_email = e; st.rerun()
