import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from io import BytesIO

# --- CONFIGURAÇÕES ---
ADMIN_PASSWORD = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"

BG_IMG = "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&q=80&w=1920"

def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def enviar_email(dest, nome, posto):
    try:
        msg = MIMEText(f"Olá {nome}, o seu turno foi confirmado com sucesso: {posto}")
        msg['Subject'] = "Confirmação de Turno"
        msg['From'] = EMAIL_USER
        msg['To'] = dest
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except Exception as e: st.error(f"Erro e-mail: {e}")

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except Exception as e: st.error(f"Erro SMS: {e}")

st.set_page_config(page_title="Segurança Eventos", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}
    .admin-btn {{ position: fixed; bottom: 10px; right: 10px; opacity: 0.1; cursor: pointer; font-size: 20px; z-index: 1000; }}
    .admin-btn:hover {{ opacity: 1.0; }}
    </style>
""", unsafe_allow_html=True)

init_db()

if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

if st.markdown('<div class="admin-btn">🔒</div>', unsafe_allow_html=True):
    if st.button("Acesso Admin", key="hidden_admin_trigger"):
        st.session_state.admin_mode = not st.session_state.admin_mode

if st.session_state.admin_mode:
    senha = st.text_input("Senha Admin", type="password")
    if senha == ADMIN_PASSWORD:
        t1, t2, t3 = st.tabs(["Gerar Turnos", "Inscrições", "Exportar"])
        with t1:
            texto = st.text_area("Cole o texto bruto:")
            if st.button("Criar Turnos"):
                linhas = texto.split('\n')
                loc, dat = "", ""
                for l in linhas:
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                    if l.isupper() and len(l) > 3 and "DIA" not in l: loc = l
                    dm = re.search(r"(DIA \d+|\b\d{2}\b)", l, re.IGNORECASE)
                    if dm and not re.search(r"\d+h", l): dat = dm.group(1).upper()
                    hm = re.search(r"(Das \d{1,2}h as \d{1,2}h.*)", l, re.IGNORECASE)
                    if hm and loc:
                        p_fin = f"{loc} ({dat}) | {hm.group(1)}"
                        try:
                            conn = sqlite3.connect('turnos.db')
                            conn.execute("INSERT INTO configuracao_turnos VALUES (?)", (p_fin,))
                            conn.commit(); conn.close()
                        except: pass
                st.rerun()
        with t2:
            conn = sqlite3.connect('turnos.db')
            reg = conn.execute("SELECT * FROM escalas").fetchall()
            for p, n, t, e in reg:
                c1, c2 = st.columns([4, 1])
                c1.write(f"📍 {p} | 👤 {n} ({t})")
                if c2.button("Eliminar", key=p):
                    conn.execute("DELETE FROM escalas WHERE posto=?", (p,))
                    conn.commit(); st.rerun()
            conn.close()
        with t3:
            conn = sqlite3.connect('turnos.db')
            df = pd.read_sql_query("SELECT * FROM escalas", conn)
            if not df.empty:
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                    df.to_excel(wr, index=False)
                st.download_button("📥 Baixar Excel", out.getvalue(), "turnos.xlsx")
            conn.close()

# --- INTERFACE UTILIZADOR ---
st.title("🎆 Reserva de Turnos")

conn = sqlite3.connect('turnos.db')
postos = [r[0] for r in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
dados = conn.execute("SELECT posto, nome, telefone FROM escalas").fetchall()
ocupados = {r[0]: r[1] for r in dados}
bloqueados_nome = [r[1].upper() for r in dados]
bloqueados_tel = [r[2] for r in dados]
conn.close()

if postos:
    with st.form("registo"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Completo")
        tel = c1.text_input("Telemóvel")
        mail = c2.text_input("E-mail")
        escolha = c2.selectbox("Posto", postos)
        metodo = st.radio("Como prefere receber a confirmação?", ["E-mail", "SMS"], horizontal=True)
        
        if st.form_submit_button("Confirmar"):
            if not (nome and tel and mail):
                st.error("Preencha todos os campos.")
            elif nome.upper() in bloqueados_nome or tel in bloqueados_tel:
                st.warning("Já tem um turno atribuído.")
            elif escolha in ocupados:
                st.error("Turno já ocupado.")
            else:
                conn = sqlite3.connect('turnos.db')
                conn.execute("INSERT INTO escalas VALUES (?,?,?,?)", (escolha, nome, tel, mail))
                conn.commit(); conn.close()
                
                msg = f"Turno Confirmado: {escolha}"
                if metodo == "E-mail": enviar_email(mail, nome, escolha)
                else: enviar_sms(tel, f"Ola {nome}, {msg}")
                
                enviar_sms(ADMIN_PHONE, f"Novo Registo: {nome} - {escolha}")
                st.success("Marcação Concluída!")
                st.rerun()

    st.divider()
    cols = st.columns(2)
    for i, p in enumerate(postos):
        with cols[i%2]:
            if p in ocupados: st.error(f"❌ {p} ({ocupados[p]})")
            else: st.success(f"✅ {p}")
else:
    st.info("Sem postos disponíveis.")
