import streamlit as st
import sqlite3
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
from datetime import datetime
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

st.set_page_config(page_title="Gestão de Segurança v5.1", layout="wide")
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

# --- MODO ADMIN ---
if admin_check and st.session_state.get('admin_auth', False):
    st.header("🛠️ Administração")
    t1, t2, t3 = st.tabs(["Gerar e Visualizar Postos", "Gestão Inscrições", "Empresas"])

    with t1:
        st.subheader("1. Gerar Novos Turnos")
        if not empresas:
            st.warning("Crie uma empresa primeiro.")
        else:
            alvo_emp = st.selectbox("Empresa Destino:", empresas)
            alvo_dat = st.date_input("Data do Evento:", datetime.now(), key="gen_date")
            txt_bruto = st.text_area("Texto Bruto (Local em MAIÚSCULAS, horários abaixo):", height=150)
            
            if st.button("🚀 Processar Texto"):
                linhas = txt_bruto.split('\n')
                local_f = "Geral"
                conn = sqlite3.connect('sistema.db')
                for l in linhas:
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                    tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                    if l.isupper() and len(l) > 3 and not tem_h:
                        local_f = l
                    else:
                        p_id = f"{local_f} | {l} ({alvo_dat.strftime('%d/%m')})"
                        conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?)", 
                                     (p_id, alvo_emp, alvo_dat.strftime('%Y-%m-%d')))
                conn.commit(); conn.close(); st.success("Processado!"); st.rerun()

        st.divider()
        st.subheader("2. Postos Criados no Sistema")
        conn = sqlite3.connect('sistema.db')
        df_v = pd.read_sql_query("SELECT posto, empresa, data FROM configuracao_turnos", conn)
        conn.close()
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True)
            if st.button("🗑️ APAGAR TODOS OS POSTOS GERADOS"):
                conn = sqlite3.connect('sistema.db')
                conn.execute("DELETE FROM configuracao_turnos")
                conn.commit(); conn.close(); st.rerun()
        else: st.info("Nenhum posto gerado no sistema.")

    with t2:
        st.subheader("Inscrições Ativas")
        conn = sqlite3.connect('sistema.db')
        df_e = pd.read_sql_query("SELECT * FROM escalas", conn)
        if not df_e.empty:
            st.table(df_e)
            p_del = st.selectbox("Escolher posto para remover inscrição:", df_e['posto'].tolist())
            if st.button("Remover Inscrição"):
                conn.execute("DELETE FROM escalas WHERE posto=?", (p_del,))
                conn.commit(); conn.close(); st.rerun()
        else: st.info("Sem inscrições.")
        if conn: conn.close()

    with t3:
        st.subheader("Configuração de Empresas")
        n_emp = st.text_input("Nome da Empresa")
        if st.button("Adicionar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (n_emp.strip(),))
            conn.commit(); conn.close(); st.rerun()

# --- INTERFACE UTILIZADOR ---
elif menu == "Reserva de Turnos":
    st.title(f"📅 Disponibilidade: {data_filtro.strftime('%d/%m/%Y')}")
    conn = sqlite3.connect('sistema.db')
    query = "SELECT posto FROM configuracao_turnos WHERE data = ?"
    params = [data_filtro.strftime('%Y-%m-%d')]
    if emp_filtro != "Todas":
        query += " AND empresa = ?"; params.append(emp_filtro)
    
    lista = [r[0] for r in conn.execute(query, params).fetchall()]
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if lista:
        with st.form("reserva"):
            c1, c2 = st.columns(2)
            u_nome, u_tel = c1.text_input("Nome"), c1.text_input("Telemóvel")
            u_mail, u_posto = c2.text_input("Email"), c2.selectbox("Turno", lista)
            if st.form_submit_button("Confirmar"):
                if u_nome and u_tel and u_mail:
                    conn = sqlite3.connect('sistema.db')
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", (u_posto, u_nome, u_tel, u_mail, data_filtro.strftime('%Y-%m-%d')))
                    conn.commit(); conn.close(); st.success("Reservado!"); st.rerun()
        
        st.divider()
        cols = st.columns(3)
        for i, p in enumerate(lista):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}\n({ocupados[p]})")
                else: st.success(f"✅ {p}")
