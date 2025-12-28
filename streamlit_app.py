import streamlit as st
import sqlite3
import re
import pandas as pd
from twilio.rest import Client
from io import BytesIO

# --- CONFIGURAÇÕES ---
ADMIN_PASSWORD = "ADMIN"
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

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
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
            texto_bruto = st.text_area("Cole o texto aqui:")
            if st.button("Gerar Turnos"):
                if texto_bruto:
                    linhas = texto_bruto.split('\n')
                    local, data = "", ""
                    for linha in linhas:
                        linha = linha.strip()
                        if not linha or any(x in linha.upper() for x in ["FOGO", "PSG"]): continue
                        if linha.isupper() and len(linha) > 3: local = linha
                        data_match = re.search(r"(DIA \d+|\b\d{2}\b)", linha, re.IGNORECASE)
                        if data_match and not re.search(r"\d+h", linha): data_atual = data_match.group(1)
                        horario_match = re.search(r"(Das \d{1,2}h as \d{1,2}h.*)", linha, re.IGNORECASE)
                        if horario_match and local:
                            posto_final = f"{local} ({data_atual}) | {horario_match.group(1)}"
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
            st.subheader("Descarregar Dados")
            conn = sqlite3.connect('turnos.db')
            df = pd.read_sql_query("SELECT * FROM escalas", conn)
            conn.close()
            
            if not df.empty:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Inscritos')
                
                st.download_button(
                    label="📥 Baixar Lista em Excel (.xlsx)",
                    data=output.getvalue(),
                    file_name="lista_inscritos_turnos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Ainda não existem inscrições para exportar.")

st.title("🎆 Inscrição em Turnos")
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
        if st.form_submit_button("Confirmar"):
            if nome and tel and email and escolha not in inscricoes:
                conn = sqlite3.connect('turnos.db')
                conn.execute("INSERT INTO escalas VALUES (?,?,?,?)", (escolha, nome, tel, email))
                conn.commit()
                conn.close()
                enviar_sms(tel, f"Confirmado: {escolha}")
                enviar_sms(ADMIN_PHONE, f"Registo: {nome} - {escolha}")
                st.rerun()

    st.divider()
    cols = st.columns(2)
    for i, p in enumerate(postos_disponiveis):
        with cols[i % 2]:
            if p in inscricoes: st.error(f"❌ {p} ({inscricoes[p]})")
            else: st.success(f"✅ {p}")
