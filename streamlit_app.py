import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from datetime import datetime
import plotly.express as px
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
    conn = sqlite3.connect('sistema.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS escalas (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT, data TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY, empresa TEXT, data TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS empresas (nome TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (email TEXT PRIMARY KEY, senha TEXT, nome TEXT, telefone TEXT)')
    conn.commit()
    conn.close()

def enviar_email(dest, assunto, corpo):
    try:
        msg = MIMEText(corpo)
        msg['Subject'] = assunto
        msg['From'] = EMAIL_USER
        msg['To'] = dest
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        return True
    except:
        return False

def enviar_sms(num, msg):
    try:
        c = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        c.messages.create(body=msg, from_=TWILIO_NUMBER, to=num)
        return True
    except:
        return False

st.set_page_config(page_title="Gestão de Segurança v4.1", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Portal de Segurança")
    conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in conn.execute("SELECT nome FROM empresas").fetchall()]
    conn.close()
    
    emp_filtro = st.selectbox("Empresa", ["Todas"] + empresas)
    data_filtro = st.date_input("Data", datetime.now())
    menu = st.radio("Menu:", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    
    st.divider()
    admin_check = st.checkbox("⚙️ Admin Mode")
    if admin_check:
        pwd = st.text_input("Senha", type="password")
        st.session_state.admin_auth = (pwd == ADMIN_PASSWORD)
    else:
        st.session_state.admin_auth = False

# --- MODO ADMIN ---
if admin_check and st.session_state.get('admin_auth', False):
    st.header("🛠️ Administração")
    t1, t2, t3 = st.tabs(["Estatísticas", "Gerar Postos", "Empresas"])

    with t3:
        n_emp = st.text_input("Nova Empresa")
        if st.button("Adicionar Empresa"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (n_emp.strip(),))
            conn.commit()
            conn.close()
            st.rerun()
        
        if empresas:
            rem_emp = st.selectbox("Remover Empresa:", empresas)
            if st.button("Eliminar"):
                conn = sqlite3.connect('sistema.db')
                conn.execute("DELETE FROM empresas WHERE nome=?", (rem_emp,))
                conn.execute("DELETE FROM configuracao_turnos WHERE empresa=?", (rem_emp,))
                conn.commit()
                conn.close()
                st.rerun()

    with t2:
        if not empresas:
            st.warning("Crie uma empresa primeiro.")
        else:
            alvo_emp = st.selectbox("Atribuir a:", empresas)
            alvo_dat = st.date_input("Data do Evento:", datetime.now(), key="admin_date_gen")
            txt_bruto = st.text_area("Texto Bruto:", height=200)
            if st.button("🚀 Gerar Turnos"):
                linhas = txt_bruto.split('\n')
                local_f = "Posto"
                conn = sqlite3.connect('sistema.db')
                for l in linhas:
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG

# --- INTERFACE UTILIZADOR ---
elif menu == "Reserva de Turnos":
    st.title(f"📅 Disponibilidade: {data_filtro.strftime('%d/%m/%Y')}")
    conn = sqlite3.connect('sistema.db')
    query = "SELECT posto FROM configuracao_turnos WHERE data = ?"
    params = [data_filtro.strftime('%Y-%m-%d')]
    if emp_filtro != "Todas":
        query += " AND empresa = ?"
        params.append(emp_filtro)
    
    lista_postos = [r[0] for r in conn.execute(query, params).fetchall()]
    dict_ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if lista_postos:
        with st.form("reserva_final"):
            c1, c2 = st.columns(2)
            u_nome = c1.text_input("Nome")
            u_tel = c1.text_input("Telemóvel")
            u_mail = c2.text_input("Email")
            u_escolha = c2.selectbox("Selecione o Turno", lista_postos)
            u_sms = st.checkbox("Confirmar por SMS")
            
            if st.form_submit_button("Confirmar Reserva"):
                if not (u_nome and u_tel and u_mail): 
                    st.error("Preencha todos os dados.")
                elif u_escolha in dict_ocupados: 
                    st.error("Turno ocupado.")
                else:
                    conn = sqlite3.connect('sistema.db')
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", 
                                 (u_escolha,

