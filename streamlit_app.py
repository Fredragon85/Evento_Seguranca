import streamlit as st
import sqlite3
from twilio.rest import Client

# --- CONFIGURAÇÕES DE ACESSO E SMS ---
ADMIN_PHONE = "+351939227659"  # O teu número para receber alertas
TWILIO_NUMBER = "+12402930627"   # O teu número comprado na Twilio
ACCOUNT_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
AUTH_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
ADMIN_PASSWORD = "ADMIN"    # Altera para a tua senha de gestão

# --- FUNÇÕES DE BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect('turnos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                 (posto TEXT PRIMARY KEY, nome TEXT, telefone TEXT)''')
    conn.commit()
    conn.close()

def enviar_sms(numero, mensagem):
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(body=mensagem, from_=TWILIO_NUMBER, to=numero)
    except Exception:
        pass # Falha silenciosa se as credenciais Twilio não estiverem configuradas

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Registo de Turnos Fogo de Artifício", layout="centered")
init_db()

# --- INTERFACE DE UTILIZADOR ---
st.title("🎆 Registo de Turnos")
st.write("Selecione o seu turno. Sistema de exclusividade: o primeiro a registar-se garante a vaga.")

with st.form("form_registo"):
    nome = st.text_input("Nome Completo")
    telemovel = st.text_input("Telemóvel (ex: +351912345678)")
    
    postos = [
        "Milharado (18h-02h) - 15€", 
        "Enxara do Bispo (18h-02h) - 15€", 
        "Ericeira (12h-18h) - 10€", 
        "Ericeira (18h-02h) - 15€",
        "Venda do Pinheiro (12h-18h) - 10€", 
        "Venda do Pinheiro (18h-02h) - 15€",
        "Sobral da Abelheira (12h-18h) - 10€", 
        "Sobral da Abelheira (18h-02h) - 15€",
        "Igreja Nova (18h-02h) - 15€", 
        "Baleia/Carvoeira (18h-02h) - 15€"
    ]
    escolha = st.selectbox("Escolha o Posto/Horário", postos)
    submetido = st.form_submit_button("Confirmar Marcação")

if submetido:
    if not nome or not telemovel:
        st.error("Erro: Preencha o Nome e o Telemóvel.")
    else:
        try:
            conn = sqlite3.connect('turnos.db')
            c = conn.cursor()
            c.execute("INSERT INTO escalas (posto, nome, telefone) VALUES (?, ?, ?)", (escolha, nome, telemovel))
            conn.commit()
            conn.close()
            
            st.success(f"Confirmado! O turno {escolha} foi atribuído a {nome}.")
            
            # Alertas SMS
            msg = f"Turno Confirmado: {escolha}. Bom trabalho!"
            enviar_sms(telemovel, msg)
            enviar_sms(ADMIN_PHONE, f"NOVO REGISTO: {nome} ({telemovel}) no posto {escolha}")
            st.rerun()

        except sqlite3.IntegrityError:
            st.error("Este turno já foi preenchido. Por favor, escolha outro disponível na lista abaixo.")

# --- LISTA PÚBLICA DE ESTADO ---
st.divider()
st.subheader("Estado dos Postos em Tempo Real")
conn = sqlite3.connect('turnos.db')
ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
conn.close()

for p in postos:
    if p in ocupados:
        st.error(f"🔴 Ocupado: {p} ({ocupados[p]})")
    else:
        st.success(f"🟢 Disponível: {p}")

# --- PAINEL DE ADMINISTRADOR (REMOVER REGISTOS) ---
st.divider()
with st.expander("🔐 Gestão de Administrador"):
    pwd = st.text_input("Introduza a senha para gerir", type="password")
    if pwd == ADMIN_PASSWORD:
        conn = sqlite3.connect('turnos.db')
        registos = conn.execute("SELECT * FROM escalas").fetchall()
        conn.close()
        
        if registos:
            for p, n, t in registos:
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{p}** | {n} ({t})")
                if col2.button("Eliminar", key=f"del_{p}"):
                    conn = sqlite3.connect('turnos.db')
                    conn.execute("DELETE FROM escalas WHERE posto = ?", (p,))
                    conn.commit()
                    conn.close()
                    st.rerun()
        else:
            st.info("Nenhum turno preenchido até ao momento.")
