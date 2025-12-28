import streamlit as st
import sqlite3
import re
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES ---
ADMIN_PASSWORD = "ADMIN"
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

st.set_page_config(page_title="Gestão de Segurança v6.0", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

# --- ESTADO DA SESSÃO ---
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Portal")
    conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in conn.execute("SELECT nome FROM empresas").fetchall()]
    conn.close()
    
    emp_filtro = st.selectbox("Empresa", ["Todas"] + empresas)
    data_filtro = st.date_input("Data", datetime.now())
    
    opcoes_menu = ["Reserva de Turnos", "Área de Cliente", "Criar Conta"]
    menu = st.radio("Menu:", opcoes_menu)
    
    st.divider()
    admin_check = st.checkbox("⚙️ Admin Mode")
    if admin_check:
        pwd = st.text_input("Senha", type="password")
        st.session_state.admin_auth = (pwd == ADMIN_PASSWORD)

# --- MODO ADMIN ---
if admin_check and st.session_state.get('admin_auth', False):
    st.header("🛠️ Administração")
    t1, t2, t3 = st.tabs(["Gerar Postos", "Gestão Inscrições", "Sistema"])

    with t1:
        alvo_emp = st.selectbox("Empresa:", empresas) if empresas else st.warning("Crie uma empresa.")
        alvo_dat = st.date_input("Data Evento:", datetime.now())
        txt_bruto = st.text_area("Texto Bruto (LOCAIS EM MAIÚSCULAS):", height=150)
        
        # Previsualização em tempo real
        if txt_bruto:
            st.subheader("👁️ Previsualização dos Turnos")
            preview_data = []
            linhas = txt_bruto.split('\n')
            local_temp = "Geral"
            for l in linhas:
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                if l.isupper() and len(l) > 3 and not tem_h:
                    local_temp = l
                else:
                    preview_data.append({"Posto": f"{local_temp} | {l} ({alvo_dat.strftime('%d/%m')})", "Empresa": alvo_emp})
            st.table(preview_data)

        if st.button("🚀 Confirmar e Gerar na Base de Dados"):
            conn = sqlite3.connect('sistema.db')
            local_f = "Geral"
            for l in txt_bruto.split('\n'):
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                if l.isupper() and len(l) > 3 and not tem_h: local_f = l
                else:
                    p_id = f"{local_f} | {l} ({alvo_dat.strftime('%d/%m')})"
                    conn.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?)", (p_id, alvo_emp, alvo_dat.strftime('%Y-%m-%d')))
            conn.commit(); conn.close(); st.success("Postos Criados!"); st.rerun()

    with t3:
        st.subheader("Configuração Base")
        if st.button("⚠️ REINICIALIZAR TODA A BASE DE DADOS"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("DROP TABLE IF EXISTS escalas")
            conn.execute("DROP TABLE IF EXISTS configuracao_turnos")
            conn.execute("DROP TABLE IF EXISTS empresas")
            conn.execute("DROP TABLE IF EXISTS clientes")
            conn.commit(); conn.close()
            init_db(); st.rerun()
        
        n_emp = st.text_input("Nome Nova Empresa")
        if st.button("Adicionar Empresa"):
            conn = sqlite3.connect('sistema.db'); conn.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (n_emp.strip(),))
            conn.commit(); conn.close(); st.rerun()

    with t2:
        conn = sqlite3.connect('sistema.db')
        df_e = pd.read_sql_query("SELECT * FROM escalas", conn)
        st.dataframe(df_e, use_container_width=True)
        if st.button("Limpar Inscrições"):
            conn.execute("DELETE FROM escalas"); conn.commit(); conn.close(); st.rerun()
        conn.close()

# --- INTERFACE UTILIZADOR ---
elif menu == "Criar Conta":
    st.subheader("Registo de Novo Utilizador")
    with st.form("reg_form"):
        n, e, t, s = st.text_input("Nome Completo"), st.text_input("Email"), st.text_input("Telemóvel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Finalizar Registo"):
            if n and e and s:
                conn = sqlite3.connect('sistema.db')
                conn.execute("INSERT INTO clientes VALUES (?,?,?,?)", (e, s, n, t))
                conn.commit(); conn.close()
                st.session_state.user_email = e # Login automático
                st.success("Conta criada com sucesso!")
                # Forçar redirecionamento para Área de Cliente
                st.info("Redirecionando para Área de Cliente...")
                st.markdown('<meta http-equiv="refresh" content="1">', unsafe_allow_html=True) 
            else: st.error("Preencha os campos obrigatórios.")

elif menu == "Área de Cliente" or st.session_state.user_email:
    st.subheader("Área Pessoal")
    email_login = st.session_state.user_email
    
    if not email_login:
        e = st.text_input("Email")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('sistema.db')
            u = conn.execute("SELECT email FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone()
            conn.close()
            if u: st.session_state.user_email = e; st.rerun()
            else: st.error("Credenciais inválidas.")
    else:
        conn = sqlite3.connect('sistema.db')
        user = conn.execute("SELECT nome FROM clientes WHERE email=?", (email_login,)).fetchone()
        st.write(f"Bem-vindo, **{user[0]}**!")
        res = conn.execute("SELECT posto, data FROM escalas WHERE email=?", (email_login,)).fetchall()
        if res:
            st.write("### Os Seus Turnos:")
            for r in res: st.info(f"📍 {r[0]} | 📅 {r[1]}")
        else: st.write("Ainda não tem turnos reservados.")
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()

elif menu == "Reserva de Turnos":
    st.title(f"📅 Postos Disponíveis")
    conn = sqlite3.connect('sistema.db')
    query = "SELECT posto FROM configuracao_turnos WHERE data = ?"
    params = [data_filtro.strftime('%Y-%m-%d')]
    if emp_filtro != "Todas": query += " AND empresa = ?"; params.append(emp_filtro)
    lista = [r[0] for r in conn.execute(query, params).fetchall()]
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if lista:
        with st.form("f_reserva"):
            u_posto = st.selectbox("Escolha o Turno", lista)
            if not st.session_state.user_email:
                u_n, u_t, u_m = st.text_input("Nome"), st.text_input("Tel"), st.text_input("Email")
            else:
                conn = sqlite3.connect('sistema.db')
                u_data = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                conn.close()
                u_n, u_t, u_m = u_data[0], u_data[1], u_data[2]
                st.write(f"Reservar como: **{u_n}**")

            if st.form_submit_button("Confirmar Reserva"):
                conn = sqlite3.connect('sistema.db')
                try:
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", (u_posto, u_n, u_t, u_m, data_filtro.strftime('%Y-%m-%d')))
                    conn.commit(); st.success("Turno reservado!")
                except: st.error("Este turno já foi ocupado.")
                finally: conn.close(); st.rerun()

        cols = st.columns(3)
        for i, p in enumerate(lista):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}\n({ocupados[p]})")
                else: st.success(f"✅ {p}")
