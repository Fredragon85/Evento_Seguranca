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

# E-mail (Configuração Obrigatória)
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Twilio (Opcional - Deixar em branco se não quiser usar)
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"

def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def enviar_confirmacao_email(destinatario, nome, posto):
    corpo = f"Ola {nome},\n\nO seu turno foi confirmado com sucesso!\n\nDetalhes: {posto}\n\nBom trabalho!"
    try:
        msg = MIMEText(corpo)
        msg['Subject'] = "Confirmacao de Turno"
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar email: {e}")
        return False

def alerta_admin_sms(mensagem):
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=ADMIN_PHONE)
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
        tab1, tab2, tab3 = st.tabs(["➕ Gerar Turnos", "📋 Inscrições", "📥 Exportar Excel"])
        
        with tab1:
            texto = st.text_area("Cole o texto bruto aqui:", height=250)
            if st.button("Processar e Criar Turnos"):
                linhas = texto.split('\n')
                local, data = "", ""
                for l in linhas:
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                    if l.isupper() and len(l) > 3 and "DIA" not in l: local = l
                    dm = re.search(r"(DIA \d+|\b\d{2}\b)", l, re.IGNORECASE)
                    if dm and not re.search(r"\d+h", l): data = dm.group(1).upper()
                    hm = re.search(r"(Das \d{1,2}h as \d{1,2}h.*)", l, re.IGNORECASE)
                    if hm and local:
                        prefixo_data = f" ({data})" if data else ""
                        p_final = f"{local}{prefixo_data} | {hm.group(1)}"
                        try:
                            conn = sqlite3.connect('turnos.db')
                            conn.execute("INSERT INTO configuracao_turnos VALUES (?)", (p_final,))
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
                if c2.button("Eliminar", key=f"del_{p}"):
                    conn = sqlite3.connect('turnos.db')
                    conn.execute("DELETE FROM escalas WHERE posto = ?", (p,))
                    conn.commit()
                    conn.close()
                    st.rerun()

        with tab3:
            conn = sqlite3.connect('turnos.db')
            df = pd.read_sql_query("SELECT * FROM escalas", conn)
            conn.close()
            if not df.empty:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Descarregar Excel", output.getvalue(), "lista_turnos.xlsx")

# --- INTERFACE UTILIZADOR ---
st.title("🎆 Reserva de Turnos")

conn = sqlite3.connect('turnos.db')
postos_db = [r[0] for r in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
conn.close()

if postos_db:
    with st.form("registo_oficial"):
        c1, c2 = st.columns(2)
        nome_f = c1.text_input("Nome Completo")
        tel_f = c1.text_input("Telemóvel")
        email_f = c2.text_input("E-mail para Confirmação")
        escolha_f = c2.selectbox("Selecione o Turno", postos_db)
        
        btn_confirmar = st.form_submit_button("Confirmar Marcação")

    if btn_confirmar:
        if not (nome_f and tel_f and email_f):
            st.error("Por favor, preencha todos os campos.")
        elif escolha_f in ocupados:
            st.error("Este turno já foi reservado.")
        else:
            try:
                # 1. Gravar na Base de Dados
                conn = sqlite3.connect('turnos.db')
                conn.execute("INSERT INTO escalas VALUES (?,?,?,?)", (escolha_f, nome_f, tel_f, email_f))
                conn.commit()
                conn.close()
                
                # 2. Enviar E-mail (Prioridade)
                enviar_confirmacao_email(email_f, nome_f, escolha_f)
                
                # 3. Alerta Admin (SMS Opcional)
                alerta_admin_sms(f"Novo Registo: {nome_f} - {escolha_f}")

                st.success(f"Garantido! Verifique o e-mail: {email_f}")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

    st
