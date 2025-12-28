import streamlit as st
import sqlite3
from twilio.rest import Client
import pandas as pd

# --- CONFIGURAÇÕES DE ACESSO ---
ADMIN_PASSWORD = "ADMIN"
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except:
        pass

# --- INICIALIZAÇÃO ---
st.set_page_config(page_title="Gestão de Eventos", layout="wide")
init_db()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Configurações")
    modo_admin = st.toggle("Ativar Painel de Gestão")
    st.divider()
    st.info("Painel para gestão de postos e base de dados.")

# --- LÓGICA DO ADMINISTRADOR ---
if modo_admin:
    st.header("🛠️ Administração do Sistema")
    senha = st.text_input("Introduza a senha de administrador", type="password")
    
    if senha == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Criar Turnos", "📋 Ver Inscrições", "🗄️ Base de Dados Raw"])
        
        with tab1:
            st.subheader("Configurar Novos Postos")
            novo_posto = st.text_input("Designação do Posto (ex: Ericeira 18h-02h)")
            if st.button("Adicionar Posto à Lista"):
                if novo_posto:
                    try:
                        conn = sqlite3.connect('turnos.db')
                        conn.execute("INSERT INTO configuracao_turnos (posto) VALUES (?)", (novo_posto,))
                        conn.commit()
                        conn.close()
                        st.success(f"Posto '{novo_posto}' criado!")
                        st.rerun()
                    except:
                        st.error("Este posto já existe.")

        with tab2:
            st.subheader("Gestão de Turnos Ocupados")
            conn = sqlite3.connect('turnos.db')
            registos = conn.execute("SELECT * FROM escalas").fetchall()
            conn.close()
            if registos:
                for p, n, t, e in registos:
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"📍 **{p}** | 👤 {n} | 📞 {t}")
                    if col2.button("Remover", key=f"del_{p}"):
                        conn = sqlite3.connect('turnos.db')
                        conn.execute("DELETE FROM escalas WHERE posto = ?", (p,))
                        conn.commit()
                        conn.close()
                        st.rerun()
            else:
                st.write("Nenhum turno ocupado.")

        with tab3:
            st.subheader("Consulta Completa")
            conn = sqlite3.connect('turnos.db')
            if st.button("Carregar Dados"):
                df = pd.read_sql_query("SELECT * FROM escalas", conn)
                st.dataframe(df, use_container_width=True)
            
            if st.button("🗑️ Limpar Tudo"):
                conn.execute("DELETE FROM escalas")
                conn.execute("DELETE FROM configuracao_turnos")
                conn.commit()
                conn.close()
                st.warning("Dados apagados.")
                st.rerun()
            conn.close()
    elif senha:
        st.error("Senha incorreta.")

# --- INTERFACE DO UTILIZADOR ---
st.title("🎆 Inscrição em Turnos")
conn = sqlite3.connect('turnos.db')
postos_db = [row[0] for row in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
conn.close()

if not postos_db:
    st.warning("⚠️ Aguarde que o administrador configure os postos.")
else:
    with st.form("registo_utilizador"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome Completo")
        email = col2.text_input("E-mail")
        telemovel = col1.text_input("Telemóvel (ex: +351912345678)")
        escolha = col2.selectbox("Selecione o Turno", postos_db)
        submeter = st.form_submit_button("Confirmar Marcação")

    if submeter:
        if not (nome and telemovel and email):
            st.error("Preencha todos os campos.")
        elif escolha in ocupados:
            st.error(f"O turno {escolha} já foi preenchido.")
        else:
            try:
                conn = sqlite3.connect('turnos.db')
                conn.execute("INSERT INTO escalas (posto, nome, telefone, email) VALUES (?, ?, ?, ?)", 
                             (escolha, nome, telemovel, email))
                conn.commit()
                conn.close()
                st.success("Marcação efetuada!")
                enviar_sms(telemovel, f"Confirmado: {escolha}")
                enviar_sms(ADMIN_PHONE, f"Novo: {nome} em {escolha}")
                st.rerun()
            except:
                st.error("Erro na base de dados.")

# --- VISUALIZAÇÃO PÚBLICA ---
st.divider()
st.subheader("📊 Disponibilidade")
if postos_db:
    c1, c2 = st.columns(2)
    for i, p in enumerate(postos_db):
        alvo = c1 if i % 2 == 0 else c2
        if p in ocupados:
            alvo.error(f"❌ {p} ({ocupados[p]})")
        else:
            alvo.success(f"✅ {p}")
else:
    st.info("Nenhum turno configurado até ao momento.")
