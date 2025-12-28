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
# Twilio
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"
# E-mail (SMTP)
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" # Senha de app do Google
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except: pass

def enviar_email(destinatario, assunto, corpo):
    try:
        msg = MIMEText(corpo)
        msg['Subject'] = assunto
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except: pass

st.set_page_config(page_title="Gestão de Eventos", layout="wide")
init_db()

with st.sidebar:
    st.title("⚙️ Painel")
    modo_admin = st.toggle("Modo Administrador")

if modo_admin:
    st.header("🛠️ Administração")
    senha = st.text_input("Senha", type="password")
    
    if senha == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Gerar Turnos", "📋 Inscrições", "📥 Exportar"])
        
        with tab1:
            texto_bruto = st.text_area("Cole o texto aqui:", height=300)
            if st.button("Gerar Turnos"):
                if texto_bruto:
                    linhas = texto_bruto.split('\n')
                    local_atual, data_atual = "", ""
                    for linha in linhas:
                        linha = linha.strip()
                        if not linha or any(x in linha.upper() for x in ["FOGO", "PSG"]): continue
                        if linha.isupper() and len(linha) > 3 and "DIA" not in linha: local_atual = linha
                        data_match = re.search(r"(DIA \d+|\b\d{2}\b)", linha, re.IGNORECASE)
                        if data_match and not re.search(r"\d+h", linha): data_atual = data_match.group(1).upper()
                        horario_match = re.search(r"(Das \d{1,2}h as \d{1,2}h.*)", linha, re.IGNORECASE)
                        if horario_match and local_atual:
                            prefixo_data = f" ({data_atual})" if data_atual else ""
                            posto_final = f"{local_atual}{prefixo_data} | {horario_match.group(1)}"
                            try:
                                conn = sqlite3.connect('turnos.db')
                                conn.execute("INSERT INTO configuracao_turnos VALUES (?)", (posto_final,))
                                conn.commit()
                                conn.close()
                            except: pass
                    st.rerun()

        with tab2:
            conn = sqlite3.connect('turnos.db')
            registos = conn.execute("SELECT * FROM escalas").fetchall()
            conn.close()
            for p, n, t, e in registos:
                c1, c2 = st.columns([4, 1])
                c1.write(f"📍 **{p}** | 👤 {n}")
                if c2.button("Remover", key=f"del_{p}"):
                    conn = sqlite3.connect('turnos.db')
                    conn.execute("DELETE FROM escalas WHERE posto = ?", (p,))
                    conn.commit()
                    conn.close()
                    st.rerun()

        with tab3:
            st.subheader("Exportar Excel")
            conn = sqlite3.connect('turnos.db')
            df = pd.read_sql_query("SELECT * FROM escalas", conn)
            conn.close()
            if not df.empty:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), "turnos.xlsx")

# --- INTERFACE UTILIZADOR ---
st.title("🎆 Reserva de Turnos")
conn = sqlite3.connect('turnos.db')
postos_disponiveis = [row[0] for row in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
inscricoes = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
conn.close()

if postos_disponiveis:
    with st.form("registo"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        tel = c1.text_input("Telemóvel")
        email = c2.text_input("E-mail")
        escolha = c2.selectbox("Turno", postos_disponiveis)
        notificacao = st.radio("Como deseja receber a confirmação?", ["SMS", "E-mail"], horizontal=True)
        
        if st.form_submit_button("Confirmar Marcação"):
            if nome and tel and email and escolha not in inscricoes:
                conn = sqlite3.connect('turnos.db')
                conn.execute("INSERT INTO escalas VALUES (?,?,?,?)", (escolha, nome, tel, email))
                conn.commit()
                conn.close()
                
                msg_texto = f"Olá {nome}, o seu turno foi confirmado: {escolha}"
                
                if notificacao == "SMS":
                    enviar_sms(tel, msg_texto)
                else:
                    enviar_email(email, "Confirmação de Turno", msg_texto)
                
                enviar_sms(ADMIN_PHONE, f"Registo: {nome} - {escolha}")
                st.success("Marcação realizada com sucesso!")
                st.rerun()

    st.divider()
    cols = st.columns(2)
    for i, p in enumerate(postos_disponiveis):
        with cols[i % 2]:
            if p in inscricoes: st.error(f"❌ {p} ({inscricoes[p]})")
            else: st.success(f"✅ {p}")
