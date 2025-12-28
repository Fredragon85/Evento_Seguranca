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

st.set_page_config(page_title="Gestão de Segurança v6.1", layout="wide")
init_db()

st.markdown(f"""<style>.stApp {{ background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url("{BG_IMG}"); background-size: cover; }}</style>""", unsafe_allow_html=True)

if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Portal")
    db_conn = sqlite3.connect('sistema.db')
    cursor = db_conn.cursor()
    empresas = [r[0] for r in cursor.execute("SELECT nome FROM empresas").fetchall()]
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
    t1, t2, t3 = st.tabs(["Gerar Postos", "Gestão Inscrições", "Sistema"])

    with t1:
        if not empresas:
            st.warning("Crie uma empresa primeiro na aba 'Sistema'.")
        else:
            alvo_emp = st.selectbox("Empresa:", empresas)
            alvo_dat = st.date_input("Data Evento:", datetime.now(), key="date_gen")
            txt_bruto = st.text_area("Texto Bruto (LOCAIS EM MAIÚSCULAS):", height=150)
            
            if txt_bruto:
                st.subheader("👁️ Previsualização")
                preview = []
                local_temp = "Geral"
                for l in txt_bruto.split('\n'):
                    l = l.strip()
                    if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                    tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                    if l.isupper() and len(l) > 3 and not tem_h: local_temp = l
                    else: preview.append({"Posto": f"{local_temp} | {l} ({alvo_dat.strftime('%d/%m')})"})
                st.table(preview)

            if st.button("🚀 Gerar Turnos"):
                conn_gen = sqlite3.connect('sistema.db')
                curr_gen = conn_gen.cursor()
                local_f = "Geral"
                try:
                    for l in txt_bruto.split('\n'):
                        l = l.strip()
                        if not l or any(x in l.upper() for x in ["FOGO", "PSG"]): continue
                        tem_h = re.search(r"\d+h", l, re.IGNORECASE)
                        if l.isupper() and len(l) > 3 and not tem_h: local_f = l
                        else:
                            p_id = f"{local_f} | {l} ({alvo_dat.strftime('%d/%m')})"
                            curr_gen.execute("INSERT OR IGNORE INTO configuracao_turnos VALUES (?,?,?)", 
                                          (p_id, alvo_emp, alvo_dat.strftime('%Y-%m-%d')))
                    conn_gen.commit()
                    st.success("Turnos gerados!")
                except Exception as e:
                    st.error(f"Erro ao gravar: {e}")
                finally:
                    conn_gen.close()
                    st.rerun()

    with t3:
        n_emp = st.text_input("Nome Nova Empresa")
        if st.button("Adicionar Empresa"):
            c = sqlite3.connect('sistema.db')
            c.execute("INSERT OR IGNORE INTO empresas VALUES (?)", (n_emp.strip(),))
            c.commit(); c.close(); st.rerun()

    with t2:
        c = sqlite3.connect('sistema.db')
        df_e = pd.read_sql_query("SELECT * FROM escalas", c)
        c.close()
        st.dataframe(df_e, use_container_width=True)

# --- INTERFACE UTILIZADOR (RESERVA) ---
elif menu == "Reserva de Turnos":
    st.title("🎆 Postos Disponíveis")
    conn_res = sqlite3.connect('sistema.db')
    curr_res = conn_res.cursor()
    
    query = "SELECT posto FROM configuracao_turnos WHERE data = ?"
    params = [data_filtro.strftime('%Y-%m-%d')]
    if emp_filtro != "Todas":
        query += " AND empresa = ?"
        params.append(emp_filtro)
    
    lista = [r[0] for r in curr_res.execute(query, params).fetchall()]
    ocupados = dict(curr_res.execute("SELECT posto, nome FROM escalas").fetchall())
    conn_res.close()

    if lista:
        with st.form("f_reserva"):
            u_posto = st.selectbox("Escolha o Turno", lista)
            if not st.session_state.user_email:
                u_n = st.text_input("Nome")
                u_t = st.text_input("Telemóvel")
                u_m = st.text_input("Email")
            else:
                c = sqlite3.connect('sistema.db')
                u_data = c.execute("SELECT nome, telefone, email FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
                c.close()
                u_n, u_t, u_m = u_data[0], u_data[1], u_data[2]
                st.write(f"Reserva para: **{u_n}**")

            if st.form_submit_button("Confirmar"):
                c = sqlite3.connect('sistema.db')
                try:
                    c.execute("INSERT INTO escalas VALUES (?,?,?,?,?)", 
                             (u_posto, u_n, u_t, u_m, data_filtro.strftime('%Y-%m-%d')))
                    c.commit()
                    st.success("Reservado!")
                except: st.error("Turno já ocupado.")
                finally: c.close(); st.rerun()

        cols = st.columns(3)
        for i, p in enumerate(lista):
            with cols[i%3]:
                if p in ocupados: st.error(f"❌ {p}\n({ocupados[p]})")
                else: st.success(f"✅ {p}")

elif menu == "Criar Conta":
    with st.form("reg"):
        n, e, t, s = st.text_input("Nome"), st.text_input("Email"), st.text_input("Tel"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar"):
            c = sqlite3.connect('sistema.db')
            c.execute("INSERT INTO clientes VALUES (?,?,?,?)", (e, s, n, t))
            c.commit(); c.close()
            st.session_state.user_email = e
            st.rerun()

elif menu == "Área de Cliente":
    if st.session_state.user_email:
        c = sqlite3.connect('sistema.db')
        user = c.execute("SELECT nome FROM clientes WHERE email=?", (st.session_state.user_email,)).fetchone()
        st.subheader(f"Olá, {user[0]}")
        res = c.execute("SELECT posto, data FROM escalas WHERE email=?", (st.session_state.user_email,)).fetchall()
        for r in res: st.info(f"📍 {r[0]} | 📅 {r[1]}")
        if st.button("Sair"): st.session_state.user_email = None; st.rerun()
        c.close()
    else:
        e = st.text_input("Email")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            c = sqlite3.connect('sistema.db')
            u = c.execute("SELECT email FROM clientes WHERE email=? AND senha=?", (e, s)).fetchone()
            c.close()
            if u: st.session_state.user_email = e; st.rerun()
