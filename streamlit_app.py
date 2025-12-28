import streamlit as st
import sqlite3
from twilio.rest import Client

# --- CONFIGURAÇÕES DE ACESSO ---
# Recomenda-se mover estas chaves para o Settings > Secrets do Streamlit Cloud
ADMIN_PASSWORD = "ADMIN"
TWILIO_ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_NUMBER = "+12402930627"
ADMIN_PHONE = "+351939227659"

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    # Tabela de inscrições (com email e tlm)
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT)''')
    # Tabela de turnos disponíveis criados pelo admin
    c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos (posto TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def enviar_sms(numero, mensagem):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except:
        pass

# --- INICIALIZAÇÃO E ESTILO ---
st.set_page_config(page_title="Gestão de Eventos", layout="wide")
init_db()

# --- BARRA LATERAL (SIDEBAR) COM ÍCONE ---
with st.sidebar:
    st.title("⚙️ Configurações")
    modo_admin = st.toggle("Ativar Painel de Gestão")
    st.divider()
    st.info("Utilize este painel para gerir postos e consultar a base de dados.")

# --- LÓGICA DO ADMINISTRADOR ---
if modo_admin:
    st.header("🛠️ Administração do Sistema")
    senha = st.text_input("Introduza a senha de administrador", type="password")
    
    if senha == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Criar Turnos", "📋 Ver Inscrições", "🗄️ Base de Dados Raw"])
        
        with tab1:
            st.subheader("Configurar Novos Postos")
            novo_posto = st.text_input("Designação do Posto/Horário (ex: Ericeira 18h-02h)")
            if st.button("Adicionar Posto à Lista"):
                if novo_posto:
                    try:
                        conn = sqlite3.connect('turnos.db')
                        conn.execute("INSERT INTO configuracao_turnos (posto) VALUES (?)", (novo_posto,))
                        conn.commit()
                        conn.close()
                        st.success(f"Posto '{novo_posto}' criado com sucesso!")
                        st.rerun()
                    except:
                        st.error("Este posto já existe na configuração.")

        with tab2:
            st.subheader("Gestão de Turnos Ocupados")
            conn = sqlite3.connect('turnos.db')
            registos = conn.execute("SELECT * FROM escalas").fetchall()
            conn.close()
            if registos:
                for p, n, t, e in registos:
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"📍 **{p}** | 👤 {n} | 📞 {t} | 📧 {e}")
                    if col2.button("Remover", key=f"del_{p}"):
                        conn = sqlite3.connect('turnos.db')
                        conn.execute("DELETE FROM escalas WHERE posto = ?", (p,))
                        conn.commit()
                        conn.close()
                        st.rerun()
            else:
                st.write("Nenhum turno ocupado.")

        with tab3:
            st.subheader("Consulta Completa da Base de Dados")
            conn = sqlite3.connect('turnos.db')
            # Botão para visualizar tabela completa
            if st.button("Carregar Dados"):
                import pandas as pd
                df = pd.read_sql_query("SELECT * FROM escalas", conn)
                st.dataframe(df, use_container_width=True)
            
            if st.button("🗑️ Limpar Tudo (CUIDADO)"):
                conn.execute("DELETE FROM escalas")
                conn.execute("DELETE FROM configuracao_turnos")
                conn.commit()
                st.warning("Todos os dados foram apagados.")
                st.rerun()
            conn.close()
    elif senha:
        st.error("Senha incorreta.")

# --- INTERFACE DO UTILIZADOR ---
st.title("🎆 Inscrição em Turnos de Segurança")
st.write("Preencha os dados abaixo para reservar o seu turno.")

# Carregar postos dinâmicos da DB
conn = sqlite3.connect('turnos.db')
postos_db = [row[0] for row in conn.execute("SELECT posto FROM configuracao_turnos").fetchall()]
ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
conn.close()

if not postos_db:
    st.warning("⚠️ Não existem postos configurados pelo administrador.")
else:
    with st.form("registo_utilizador"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome Completo")
        email = col2.text_input("Endereço de E-mail")
        telemovel = col1.text_input("Telemóvel (ex: +351912345678)")
        escolha = col2.selectbox("Selecione o Turno Pretendido", postos_db)
        
        submeter = st.form_submit_button("Confirmar Marcação de Turno")

    if submeter:
        if not (nome and telemovel and email):
            st.error("Por favor, preencha todos os campos (Nome, E-mail e Telemóvel).")
        elif escolha in ocupados:
            st.error(f"O turno {escolha} já foi reservado por {ocupados[escolha]}.")
        else:
            try:
                conn = sqlite3.connect('turnos.db')
                conn.execute("INSERT INTO escalas (posto, nome, telefone, email) VALUES (?, ?, ?, ?)", 
                             (escolha, nome, telemovel, email))
                conn.commit()
                conn.close()
                
                st.success(f"Sucesso! {nome}, o turno {escolha} é teu.")
                
                # Envio de SMS via Twilio
                enviar_sms(telemovel, f"Confirmado: Turno {escolha}. Bom trabalho!")
                enviar_sms(ADMIN_PHONE, f"NOVO REGISTO: {nome} no posto {escolha}")
                
                st.rerun()
            except Exception as e:
                st.error("Erro ao gravar na base de dados.")

# --- PAINEL DE VISUALIZAÇÃO PÚBLICO ---
st.divider()
st.subheader("📊 Disponibilidade em Tempo Real")
col_a, col_b = st.columns(2)

for i, p in enumerate(postos_db):
    target_col = col_a if i % 2 == 0 else col_b
    if p in ocupados:
        target_col.error(f"❌ {p} | Ocupado por: {ocupados[p]}")
    else:
        target_col.success(f"✅ {p} | Disponível")
            st.info("Nenhum turno preenchido até ao momento.")

