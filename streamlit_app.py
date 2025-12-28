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

st.set_page_config(page_title="Gestão de Segurança v8.0", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Portal")
    db_conn = sqlite3.connect('sistema.db')
    empresas = [r[0] for r in db_conn.execute("SELECT nome FROM empresas").fetchall()]
    db_conn.close()
    
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
    t1, t2 = st.tabs(["Gerar Postos & Empresas", "Inscrições & Sistema"])

    with t1:
        st.subheader("Gerar Turnos")
        nova_empresa_input = st.text_input("Empresa para estes turnos:", placeholder="Ex: GNR, Prosegur...")
        alvo_dat = st.date_input("Data do Evento:", datetime.now(), key="date_gen_v8")
        txt_bruto = st.text_area("Texto Bruto (LOCAIS EM MAIÚSCULAS):", height=150)
        
        if txt_bruto and nova_empresa_input:
            st.subheader("👁️ Previsualização")
            preview = []
            local_temp = "Geral"
            for l in txt_bruto.split('\n'):
                l = l.strip()
                if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                if l.isupper() and len(l) > 3 and not tem_h: local_temp = l
                else: preview.append({"Posto": f"{local_temp} | {l} ({alvo_dat.strftime('%d/%m')})", "Empresa": nova_empresa_input})
            st.table(preview)

        if st.button("🚀 Gerar e Registar Empresa"):
            if not nova_empresa_input:
                st.error("Insira o nome da empresa.")
            else:
                conn = sqlite3.connect('sistema.db')
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (nova_empresa_input.strip(),))
                    local_f = "Geral"
                    for l in txt_bruto.split('\n'):
                        l = l.strip()
                        if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                        tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                        if l.isupper() and len(l) > 3 and not tem_h: local_f = l
                        else:
                            p_id = f"{local_f} | {l} ({alvo_dat.strftime('%d/%m')})"
                            cursor.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?)", 
                                          (p_id, nova_empresa_input.strip(), alvo_dat.strftime('%Y-%m-%d')))
                    conn.commit()
                    st.success("Processado com sucesso.")
                finally:
                    conn.close()
                    st.rerun()

    with t2:
        conn = sqlite3.connect('sistema.db')
        st.subheader("Inscrições")
        df_e = pd.read_sql_query("SELECT * FROM escalas", conn)
        # Atualizado use_container_width para width conforme solicitado
        st.dataframe(df_e, width='stretch')
        
        if st.button("🧨 Reset Total Sistema"):
            conn.execute("DROP TABLE IF EXISTS escalas")
            conn.execute("DROP TABLE IF EXISTS configuracao_turnos")
            conn.execute("DROP TABLE IF EXISTS empresas")
            conn.execute("DROP TABLE IF EXISTS clientes")
            conn.commit(); conn.close(); init_db(); st.rerun()
        conn.close()

# --- INTERFACE UTILIZADOR ---
elif menu == "Reserva de Turnos":
    st.title("📅 Turnos")
    conn = sqlite3.connect('sistema.db')
    query = "SELECT posto FROM configuracao_turnos WHERE data = ?"
    params = [data_filtro.strftime('%Y-%m-%d')]
    if emp_filtro != "Todas":
        query += " AND empresa = ?"; params.append(emp_filtro)
    
    lista = [r[0] for r in conn.execute(query, params).fetchall()]
    ocupados = dict(conn.execute("SELECT posto, nome FROM escalas").fetchall())
    conn.close()

    if lista:
        with st.form("f_reserva"):
            u_posto = st.selectbox("Turno", lista)
            if not st.session_state.user_email:
                u_n, u_t, u_m = st.text_input("Nome"), st.text_input("Tel"), st.text_input("Email")
            else:
                conn = sqlite3.connect('sistema.db')
                udata = conn.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                conn.close()
                u_n, u_t, u_m = udata[0], udata[1], udata[2]
                st.write(f"Reserva para: **{u_n}**")

            if st.form_submit_button("Confirmar Reserva"):
                conn = sqlite3.connect('sistema.db')
                try:
                    conn.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", (u_posto, u_n, u_t, u_m, data_filtro.strftime('%Y-%m-%d')))
                    conn.commit(); st.success("Confirmado!"); st.rerun()
                except: st.error("Turno ocupado.")
                finally: conn.close()

        cols = st.columns(3)
        for i, p in enumerate(lista):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}\n({ocupados[p]})")
                else: st.success(f"✅ {p}")

elif menu == "Criar Conta":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar"):
            conn = sqlite3.connect('sistema.db')
            conn.execute("INSERT INTO clientes VALUES (?,?,?,?)", (e, s, n, t))
            conn.commit(); conn.close()
            st.session_state.user_email = e
            st.rerun()

elif menu == "Área de Cliente":
    if st.session_state.user_email:
        conn = sqlite3.connect('sistema.db')
        user = conn.execute("SELECT nome FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.write(f"### Olá {user[0]}!")
        res = conn.execute("SELECT posto FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for r in res: st.info(f"📍 {r[0]}")
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        conn.close()
    else:
        e, s = st.text_input("Email"), st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('sistema.db')
            u = conn.execute("SELECT email FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone()
            conn.close()
            if u: st.session_state.user_email = e; st.rerun()
