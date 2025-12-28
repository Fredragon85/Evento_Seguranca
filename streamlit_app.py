import streamlit as st
import sqlite3
import pandas as pd
import smtplib
import requests
import logging
import bcrypt
import time
import re
from email.mime.text import MIMEText
from twilio.rest import Client
from math import sin, cos, sqrt, atan2, radians
from contextlib import closing

# --- CONFIGURAÇÕES MESTRE ---
ADMIN_PASS_SISTEMA = "ADMIN"
EMAIL_USER = "silvafrederico280385@gmail.com"
EMAIL_PASS = "*.*Fr3d5ilv488" 
TWILIO_SID = 'AC0c0da7648d2ad34f5c2df4253e371910'
TWILIO_TOKEN = 'a83cb0baf2dce52ba061171d3f69a9f9'
TWILIO_WHATSAPP = "whatsapp:+14155238886"
TELEGRAM_TOKEN = "7950949216:AAHTmB8Z5UfV_B7oE8eH-m2U_Y_f6Z3w2kU"
TELEGRAM_CHAT = "@FredSilva85_pt"

MEU_WA_LINK = "https://wa.me/3519339227659"
MEU_TG_LINK = "https://t.me/FredSilva85_pt"
DB_NAME = 'sistema_v66_supreme.db'

# --- SEGURANÇA ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    if isinstance(hashed, str): hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# --- DATABASE ENGINE ---
def get_db_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db(force_reset=False):
    with get_db_conn() as conn:
        with closing(conn.cursor()) as c:
            if force_reset:
                c.execute("DROP TABLE IF EXISTS escalas")
                c.execute("DROP TABLE IF EXISTS configuracao_turnos")
                c.execute("DROP TABLE IF EXISTS clientes")
            
            c.execute('''CREATE TABLE IF NOT EXISTS escalas 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, posto TEXT, nome TEXT, telefone TEXT, email TEXT, 
                          status TEXT DEFAULT 'Pendente', pref_metodo TEXT, checkin INTEGER DEFAULT 0, pago INTEGER DEFAULT 0, valor REAL DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS configuracao_turnos 
                         (posto TEXT PRIMARY KEY, empresa TEXT, localizacao TEXT, lat REAL, lon REAL, valor REAL DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                         (telefone TEXT PRIMARY KEY, senha TEXT, nome TEXT, email TEXT, 
                          is_admin INTEGER DEFAULT 0, cartoes TEXT, ranking INTEGER DEFAULT 5)''')
            
            admin_pwd = hash_password("ADMIN").decode('utf-8')
            c.execute("INSERT OR REPLACE INTO clientes (telefone, senha, nome, is_admin) VALUES (?,?,?,?)",
                      ("9339227659", admin_pwd, "FRED SILVA MASTER", 1))

def multicanal_notify(tel, nome, posto, metodo, email=None):
    msg = f"Ola {nome}, o seu turno {posto} foi CONFIRMADO."
    if metodo in ["WhatsApp", "Ambos"]:
        try:
            Client(TWILIO_SID, TWILIO_TOKEN).messages.create(from_=TWILIO_WHATSAPP, body=msg, to=f"whatsapp:+351{tel}")
        except: pass
    if (metodo in ["Email", "Ambos"]) and email:
        try:
            m = MIMEText(msg); m['Subject'] = "CONFIRMACAO"; m['From'] = EMAIL_USER; m['To'] = email
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
                s.starttls(); s.login(EMAIL_USER, EMAIL_PASS); s.send_message(m)
        except: pass

def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * (2 * atan2(sqrt(a), sqrt(1-a)))

init_db()

# --- SESSÃO ---
if 'user_tel' not in st.session_state: st.session_state.user_tel = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'preview_data' not in st.session_state: st.session_state.preview_data = []

st.set_page_config(page_title="V66 OMNI SUPREME", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ SUPREME v66")
    if st.session_state.user_tel:
        st.success(f"📱 {st.session_state.user_tel}")
        if st.session_state.is_admin: st.warning("Acesso Administrador")
        if st.button("🔒 Sair"):
            st.session_state.user_tel = None; st.session_state.is_admin = False; st.rerun()
    else:
        with st.form("login"):
            t = st.text_input("Telemóvel", value="9339227659")
            s = st.text_input("Senha", type="password", value="ADMIN")
            if st.form_submit_button("Entrar"):
                with get_db_conn() as conn:
                    res = conn.execute("SELECT senha, is_admin FROM clientes WHERE telefone=?", (t,)).fetchone()
                    if res and check_password(s, res[0]):
                        st.session_state.user_tel = t; st.session_state.is_admin = bool(res[1]); st.rerun()
                    else: st.error("Login Inválido.")

    nav = st.radio("Módulos", ["Turnos em Aberto", "Área de Cliente", "Registo"])
    st.divider()
    st.link_button("💬 Suporte WhatsApp", MEU_WA_LINK, use_container_width=True)

# --- MÓDULO: TURNOS EM ABERTO ---
if nav == "Turnos em Aberto":
    st.header("📅 Escalas Disponíveis")
    with get_db_conn() as conn:
        postos = conn.execute("SELECT posto, localizacao, valor FROM configuracao_turnos").fetchall()
        reservados = [r[0] for r in conn.execute("SELECT posto FROM escalas WHERE status != 'Cancelado'").fetchall()]
        for p_id, loc, val in postos:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                if p_id in reservados: c1.error(f"❌ {p_id} (Ocupado)")
                else:
                    c1.success(f"✅ {p_id} - {loc} ({val}€)")
                    if st.session_state.user_tel:
                        met = c2.selectbox("Notificação:", ["WhatsApp", "Email", "Ambos"], key=f"m_{p_id}")
                        if c2.button("Reservar", key=f"r_{p_id}"):
                            u = conn.execute("SELECT nome, email FROM clientes WHERE telefone=?", (st.session_state.user_tel,)).fetchone()
                            conn.execute("INSERT INTO escalas (posto, nome, telefone, email, pref_metodo, valor) VALUES (?,?,?,?,?,?)", 
                                         (p_id, u[0], st.session_state.user_tel, u[1], met, val))
                            st.success("Pedido enviado!"); time.sleep(0.5); st.rerun()

# --- MÓDULO: ÁREA DE CLIENTE ---
elif nav == "Área de Cliente":
    if not st.session_state.user_tel: st.warning("Faça login com o telemóvel.")
    else:
        with get_db_conn() as conn:
            saldo = conn.execute("SELECT SUM(valor) FROM escalas WHERE telefone=? AND status='Confirmado' AND checkin=1 AND pago=0", (st.session_state.user_tel,)).fetchone()[0] or 0
            st.metric("Saldo a Receber", f"{saldo}€")
            
            st.subheader("📋 Minhas Escalas")
            meus = conn.execute('''SELECT e.posto, e.status, e.checkin, e.pago, t.lat, t.lon, e.valor 
                                   FROM escalas e LEFT JOIN configuracao_turnos t ON e.posto = t.posto 
                                   WHERE e.telefone = ?''', (st.session_state.user_tel,)).fetchall()
            for p, stt, chk, pago, lat, lon, val in meus:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**Posto:** {p} ({val}€)")
                    c1.caption(f"Status: {stt} | Pago: {'✅' if pago else '⏳'}")
                    if stt == "Confirmado" and not chk:
                        if c2.button("📍 Check-in GPS", key=f"chk_{p}"):
                            if haversine_meters(39.2081, -8.6277, lat, lon) <= 500:
                                conn.execute("UPDATE escalas SET checkin=1 WHERE posto=? AND telefone=?", (p, st.session_state.user_tel))
                                st.rerun()

# --- PAINEL ADMIN ---
if st.session_state.is_admin:
    with st.expander("🛠️ PAINEL ADMINISTRATIVO", expanded=True):
        t1, t2, t3, t4 = st.tabs(["🚀 Gerador", "📥 Inscrições", "💰 Pagamentos", "👥 Staff"])
        
        with t1:
            txt = st.text_area("Texto Bruto (DIA/LOCAL/HORARIO/€)")
            if st.button("Analisar Texto"):
                if txt:
                    p_list = []
                    loc, dia = "Geral", "31"
                    for l in txt.split('\n'):
                        l = l.strip()
                        if "DIA" in l.upper(): dia = l
                        elif l.isupper() and len(l) > 3 and "DAS" not in l.upper(): loc = l
                        elif "Das" in l:
                            match = re.search(r'(\d+[\.,]?\d*)\s*(?:€|euro)', l, re.IGNORECASE)
                            preco = float(match.group(1).replace(',', '.')) if match else 0.0
                            p_list.append({"ID": f"{dia} | {loc} | {l}", "Loc": loc, "Valor": preco})
                    st.session_state.preview_data = p_list
            if st.session_state.preview_data:
                st.table(pd.DataFrame(st.session_state.preview_data))
                if st.button("✅ Publicar"):
                    with get_db_conn() as conn:
                        for i in st.session_state.preview_data:
                            conn.execute("INSERT OR IGNORE INTO configuracao_turnos (posto, empresa, localizacao, lat, lon, valor) VALUES (?,?,?,?,?,?)", 
                                         (i['ID'], "PSG", i['Loc'], 39.2081, -8.6277, i['Valor']))
                    st.session_state.preview_data = []; st.success("Postos Criados!"); st.rerun()

        with t2:
            with get_db_conn() as conn:
                pedidos = conn.execute("SELECT id, posto, nome, telefone, email, pref_metodo FROM escalas WHERE status='Pendente'").fetchall()
                for id_e, p_id, nome, tel, mail, pref in pedidos:
                    with st.container(border=True):
                        st.write(f"**{nome}** ({tel}) solicita: {p_id}")
                        if st.button("✅ Confirmar & WhatsApp", key=f"conf_{id_e}"):
                            conn.execute("UPDATE escalas SET status='Confirmado' WHERE id=?", (id_e,))
                            multicanal_notify(tel, nome, p_id, pref, mail)
                            st.rerun()

        with t3:
            with get_db_conn() as conn:
                lista_pagar = conn.execute("SELECT id, nome, posto, valor, pago FROM escalas WHERE status='Confirmado' AND checkin=1").fetchall()
                for id_p, n_p, post_p, val_p, pago_p in lista_pagar:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"**{n_p}** -> {post_p} (**{val_p}€**)")
                        if not pago_p:
                            if c2.button("Pagar", key=f"pay_{id_p}"):
                                conn.execute("UPDATE escalas SET pago=1 WHERE id=?", (id_p,)); st.rerun()
                        else: c2.success("Pago")

        with t4:
            with get_db_conn() as conn:
                users = conn.execute("SELECT telefone, nome, is_admin FROM clientes").fetchall()
                for u_t, u_n, adm in users:
                    with st.expander(f"{u_n} ({u_t})"):
                        if not adm and st.button("Promover Admin", key=f"adm_{u_t}"):
                            conn.execute("UPDATE clientes SET is_admin=1 WHERE telefone=?", (u_t,)); st.rerun()

elif nav == "Registo":
    with st.form("reg"):
        n, t, e, s = st.text_input("Nome"), st.text_input("Telemóvel"), st.text_input("Email"), st.text_input("Senha", type="password")
        if st.form_submit_button("Criar Conta"):
            with get_db_conn() as conn:
                conn.execute("INSERT OR REPLACE INTO clientes (telefone, senha, nome, email) VALUES (?,?,?,?)", 
                             (t, hash_password(s).decode('utf-8'), n, e))
            st.success("Conta criada!"); time.sleep(1); st.rerun()
