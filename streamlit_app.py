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
        msg = MIMEText(corpo); msg['Subject'] = assunto; msg['From'] = EMAIL_USER; msg['To'] = dest
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(msg)
        return True
    except: return False

def enviar_sms(num, msg):
    try:
        c = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        c.messages.create(body=msg, from_=TWILIO_NUMBER, to=num)
        return True
    except: return False

st.set_page_config(page_title="Gestão de Segurança v3.4", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Portal")
    conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in conn.execute("SELECT nome FROM empresas").fetchall()]
    conn.close()
    
    empresa_filtro = st.selectbox("Filtrar Empresa", ["Todas"] + empresas)
    data_filtro = st.date_input("Filtrar Data", datetime.now())
    menu = st.radio("Menu:", ["Reserva de Turnos", "Área de Cliente", "Criar Conta"])
    
    st.divider()
    admin_check = st.checkbox("⚙️ Admin Mode")
    if admin_check:
        pwd = st.text_input("Senha", type="password")
        if pwd == ADMIN_PASSWORD: st.session_state.admin_auth = True
        else: st.session_state.admin_auth = False

# --- PAINEL ESTATÍSTICO E ADMIN ---
if admin_check and st.session_state.get('admin_auth', False):
    st.header("📊 Dashboard Administrativo")
    t1, t2, t3 = st.tabs(["Estatísticas", "Gerar Postos", "Empresas"])
    
    conn = sqlite3.connect('sistema.db')
    df_postos = pd.read_sql_query("SELECT * FROM configuracao_turnos", conn)
    df_escalas = pd.read_sql_query("SELECT * FROM escalas", conn)
    conn.close()

    with t1:
        if not df_postos.empty:
            df_merged = pd.merge(df_postos, df_escalas, on="posto", how="left")
            df_merged['Status'] = df_merged['nome'].apply(lambda x: 'Ocupado' if pd.notnull(x) else 'Livre')
            
            fig = px.bar(df_merged, x="empresa", color="Status", 
                         title="Estado dos Turnos por Empresa",
                         barmode="group",
                         color_discrete_map={'Livre':'#2ecc71', 'Ocupado':'#e74c3c'},
                         template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Postos", len(df_postos))
            c2.metric("Ocupados", len(df_escalas))
            c3.metric("Taxa", f"{(len(df_escalas)/len(df_postos)*100):.1f}%" if len(df_postos)>0 else "0%")
            
            st.divider()
            # Botão de Exportação
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_merged.to_excel(writer, index=False, sheet_name='Relatorio_Turnos')
            st.download_button(
                label="📥 Descarregar Relatório Excel",
                data=output.getvalue(),
                file_name=f"relatorio_seguranca_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Sem dados para exportar.")

    with t2:
        if empresas:
            emp_alvo = st.selectbox("Empresa:", empresas)
            data_alvo = st.date_input("Data Evento:", datetime.now(), key="admin_data")
            txt = st.text_area("Texto Bruto (Das XXh as XXh):")
            if st.button("Gerar Turnos"):
                for l in txt.split('\n'):
                    if "Das" in l:
                        conn = sqlite3.connect('sistema.db')
                        p_id = f"{emp_alvo} | {l} ({data_alvo})"
                        conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?)", 
                                     (p_id, emp_alvo, data_alvo.strftime('%Y-%m-%d')))
                        conn.commit(); conn.close()
                st.rerun()
        else: st.warning("Crie uma empresa primeiro.")

    with t3:
        nova_e = st.text_input("Nome Empresa")
        if st.button("Adicionar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (nova_e,))
            conn.commit(); conn.close(); st.rerun()
        
        st.divider()
        if empresas:
            emp_rem = st.selectbox("Empresa a remover:", empresas)
            if st.button("🗑️ Remover Empresa"):
                conn = sqlite3.connect('sistema.db')
                conn.execute("DELETE FROM empresas WHERE nome=?", (emp_rem,))
                conn.execute("DELETE FROM configuracao_turnos WHERE empresa=?", (emp_rem,))
                conn.commit(); conn.close(); st.rerun()

# --- INTERFACE DE RESERVA ---
elif menu == "Reserva de Turnos":
    st.title(f"📅 Escalas - {data_filtro.strftime('%d/%m/%Y')}")
    conn = sqlite3.connect('sistema.db')
    q = "SELECT posto FROM configuracao_turnos WHERE data = ?"
    p_sql = [data_filtro.strftime('%Y-%m-%d')]
    if empresa_filtro != "Todas":
        q += " AND empresa = ?"; p_sql.append(empresa_filtro)
    
    postos = [r[0] for r in conn.execute(q, p_sql).fetchall()]
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if postos:
        with st.form("reserva"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome")
            tel = c1.text_input("Telemóvel")
            mail = c2.text_input("Email")
            escolha = c2.selectbox("Turno", postos)
            q_sms = st.checkbox("Confirmar por SMS")
            if st.form_submit_button("Reservar"):
                if not (nome and tel and mail): st.error("Erro: Preencha tudo")
                else:
                    conn = sqlite3.connect('sistema.db')
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", 
                                 (escolha, nome, tel, mail, data_filtro.strftime('%Y-%m-%d')))
                    conn.commit(); conn.close()
                    enviar_email(mail, "Reserva", f"Confirmado: {escolha}")
                    if q_sms: enviar_sms(tel, f"Reserva: {escolha}")
                    st.success("Concluído!"); st.rerun()
        
        cols = st.columns(3)
        for i, p in enumerate(postos):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}\n({ocupados[p]})")
                else: st.success(f"✅ {p}")
    else: st.info("Sem postos disponíveis.")

# --- LOGIN E RECUPERAÇÃO ---
elif menu == "Área de Cliente":
    st.header("👤 Login")
    e, s = st.text_input("Email"), st.text_input("Senha", type="password")
    col1, col2, col3 = st.columns(3)
    if col1.button("Login"):
        conn = sqlite3.connect('sistema.db')
        u = conn.execute("SELECT nome FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone()
        if u: st.success(f"Bem-vindo, {u[0]}!")
        else: st.error("Dados inválidos.")
        conn.close()
    
    if col2.button("Recuperar por SMS"):
        conn = sqlite3.connect('sistema.db')
        u = conn.execute("SELECT senha, telefone FROM clientes WHERE email=?", (e,)).fetchone()
        if u and enviar_sms(u[1], f"Senha: {u[0]}"): st.success("SMS Enviado.")
        else: st.error("Email ou telemóvel não encontrado.")
        conn.close()

elif menu == "Criar Conta":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Telemóvel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Registar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT INTO clientes VALUES (?,?,?,?)", (e, s, n, t))
            conn.commit(); conn.close(); st.success("Conta Criada.")
