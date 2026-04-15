import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os
import time

DB_PATH = "../data/stealth_seed.db"

def init_db():
    os.makedirs("../data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        with open("../data/schema.sql", "r") as f:
            conn.executescript(f.read())
            
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM system_config")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO system_config (target_niche, product_link, agent_status) VALUES (?, ?, ?)",
                      ("SaaS Founders", "https://your-product.com", "stopped"))
            
        try: conn.execute("ALTER TABLE accounts ADD COLUMN last_posted_at DATETIME"); conn.commit()
        except: pass
        try: conn.execute("ALTER TABLE system_config ADD COLUMN gemini_api_key TEXT"); conn.commit()
        except: pass
        try: conn.execute("ALTER TABLE system_config ADD COLUMN cooldown_minutes INTEGER DEFAULT 90"); conn.commit()
        except: pass
        
    except Exception as e:
        st.error(f"Error initializing DB: {e}")
    finally:
        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

st.set_page_config(page_title="StealthSeed-AI Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Inject Custom CSS for Premium UX Overlay
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
}
.stApp {
    background: linear-gradient(180deg, #0f111a 0%, #06080f 100%);
    color: #e2e8f0;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #1e293b;
    border-radius: 8px 8px 0px 0px;
    padding: 10px 20px;
    border: 1px solid #334155;
    border-bottom: none;
}
.stTabs [aria-selected="true"] {
    background-color: #3b82f6 !important;
    color: #ffffff !important;
}
div[data-testid="stMetricValue"] {
    color: #38bdf8 !important;
}
.stButton>button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s ease-in-out;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Login to StealthSeed-AI")
    action = st.radio("Choose Action", ["Login", "Register"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button(action):
        conn = get_db_connection()
        if action == "Register":
            try:
                conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, make_hash(password)))
                conn.commit()
                st.success("Registered successfully! You can now login.")
            except sqlite3.IntegrityError:
                st.error("Username already exists.")
        else:
            user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, make_hash(password))).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials.")
        conn.close()
    st.stop()

# Build Header with inline logout
col_h1, col_h2 = st.columns([0.9, 0.1])
col_h1.title(f"🌱 StealthSeed-AI Dashboard")
with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

conn = get_db_connection()
try:
    df_p = pd.read_sql_query("SELECT name FROM personas", conn)
    persona_opts = ["All"] + df_p['name'].tolist() if not df_p.empty else ["All"]
    df_a = pd.read_sql_query("SELECT username FROM accounts", conn)
    acc_opts = ["All"] + df_a['username'].tolist() if not df_a.empty else ["All"]
except:
    persona_opts, acc_opts = ["All"], ["All"]
conn.close()

# Contextual Filters embedded inside the expander
with st.expander("🔍 Expand Global Mission Filters", expanded=False):
    c_f1, c_f2, c_f3, c_f4 = st.columns(4)
    f_persona = c_f1.selectbox("Filter by Persona", persona_opts)
    f_account = c_f2.selectbox("Filter by SM Account", acc_opts)
    f_platform = c_f3.selectbox("Filter by Platform", ["All", "reddit", "x", "facebook"])
    f_date = c_f4.date_input("Filter by Date (On or After)", value=None)

tab_feed, tab_map, tab_personas, tab_accounts, tab_tags, tab_config, tab_override, tab_saas = st.tabs([
    "💬 Live Feed", "🗺️ Mission Map", "🎭 Personas", "📱 SM Accounts", "🎯 Discovery Tags", "⚙️ Settings & Launch", "⚠️ Manual Override", "💼 SaaS Simulation"
])

with tab_feed:
    st.header("💬 Agent Live Feed")
    st.write("Real-time stream of all agent interactions and seed drops.")
    
    conn = get_db_connection()
    try:
        query = """
            SELECT t.platform, t.thread_url, e.phase, e.timestamp, a.username, e.message_content, p.name as persona_name 
            FROM engagements e
            JOIN threads t ON e.thread_id = t.id
            JOIN accounts a ON e.account_id = a.id
            LEFT JOIN personas p ON a.persona_id = p.id
            ORDER BY e.timestamp DESC
            LIMIT 200
        """
        df_feed = pd.read_sql_query(query, conn)
        
        if not df_feed.empty:
            if f_persona != "All": df_feed = df_feed[df_feed['persona_name'] == f_persona]
            if f_account != "All": df_feed = df_feed[df_feed['username'] == f_account]
            if f_platform != "All": df_feed = df_feed[df_feed['platform'] == f_platform]
            if f_date:
                df_feed['date_only'] = pd.to_datetime(df_feed['timestamp']).dt.date
                df_feed = df_feed[df_feed['date_only'] >= f_date]
        
        rows = df_feed.to_dict('records')
        
        if not rows:
            st.info("No active missions match your filters!")
        else:
            for row in rows:
                with st.container():
                    if row["phase"] == "Seed":
                        st.success(f"🎯 **SEED DROPPED** on {row['platform'].capitalize()} by @{row['username']}")
                        st.markdown(f"> {row['message_content']}")
                    else:
                        st.info(f"🤝 **Rapport Building** on {row['platform'].capitalize()} by @{row['username']}")
                        st.markdown(f" *\"{row['message_content']}\"* ")
                    st.caption(f"⏱️ {row['timestamp']} | [{row['thread_url']}]({row['thread_url']})")
                    st.markdown("---")
    except Exception as e:
        st.error(f"Error loading feed: {e}")
    finally:
        conn.close()

with tab_map:
    st.header("🗺️ Mission Map")
    st.write("Active threads and their current phase.")
    conn = get_db_connection()
    try:
        query = """
            SELECT t.platform, t.thread_url, e.phase, e.timestamp, a.username, p.name as persona_name 
            FROM engagements e
            JOIN threads t ON e.thread_id = t.id
            JOIN accounts a ON e.account_id = a.id
            LEFT JOIN personas p ON a.persona_id = p.id
            ORDER BY e.timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            if f_persona != "All": df = df[df['persona_name'] == f_persona]
            if f_account != "All": df = df[df['username'] == f_account]
            if f_platform != "All": df = df[df['platform'] == f_platform]
            if f_date:
                df['date_only'] = pd.to_datetime(df['timestamp']).dt.date
                df = df[df['date_only'] >= f_date]
                df = df.drop(columns=['date_only'])
            
            if df.empty:
                st.info("No active missions match your filters.")
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("No active missions found. Set up your Agent in 'Settings & Launch'!")
    except Exception as e:
        st.error(f"Error fetching mission map: {e}")
    finally:
        conn.close()

with tab_personas:
    st.header("🎭 Manage Personas")
    st.write("Create the behavioral profile and organic threshold for the AI.")
    
    with st.form("persona_form"):
        p_name = st.text_input("Persona Name (e.g. 'Helpful Developer')")
        p_prompt = st.text_area("System Instructions Context (Anchor)")
        p_threshold = st.slider("Minimum Organic Posts required before Seed", 0, 10, 3)
        if st.form_submit_button("Save Persona"):
            if p_name:
                conn = get_db_connection()
                conn.execute("INSERT INTO personas (name, prompt_instructions, minimum_organic_posts) VALUES (?, ?, ?)", 
                             (p_name, p_prompt, p_threshold))
                conn.commit()
                conn.close()
                st.success(f"Persona '{p_name}' saved!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Persona name is required.")
            
    st.subheader("Existing Personas")
    conn = get_db_connection()
    df_p = pd.read_sql_query("SELECT id, name, minimum_organic_posts, prompt_instructions FROM personas", conn)
    conn.close()
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
        
        st.divider()
        st.subheader("🛠️ Action Zone (Personas)")
        with st.expander("Modify or Delete Persona"):
            p_opts = {row['name']: row['id'] for idx, row in df_p.iterrows()}
            selected_p = st.selectbox("Select Persona", list(p_opts.keys()))
            if st.button("🗑️ Delete Selected Persona", type="primary"):
                conn = get_db_connection()
                try:
                    conn.execute("DELETE FROM personas WHERE id=?", (p_opts[selected_p],))
                    conn.commit()
                    st.success("Deleted!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Cannot delete, it may be bound to an Account: {e}")
                conn.close()

with tab_accounts:
    st.header("📱 Manage SM Accounts")
    conn = get_db_connection()
    personas = conn.execute("SELECT id, name FROM personas").fetchall()
    
    if not personas:
        st.warning("Please create a Persona first!")
    else:
        with st.form("account_form"):
            platform = st.selectbox("Platform", ["reddit", "x", "facebook"])
            acc_user = st.text_input("Account Username")
            acc_pass = st.text_input("Account Password", type="password")
            persona_options = {p['name']: p['id'] for p in personas}
            selected_p = st.selectbox("Assign Persona", list(persona_options.keys()))
            
            if st.form_submit_button("Add Account"):
                conn.execute("INSERT INTO accounts (username, password, platform, persona_id) VALUES (?, ?, ?, ?)",
                    (acc_user, acc_pass, platform, persona_options[selected_p]))
                conn.commit()
                st.success("Account added!")
                time.sleep(1)
                st.rerun()
                
    st.subheader("Active Accounts")
    try:
        df_a = pd.read_sql_query("""
            SELECT a.id, a.username, a.platform, p.name as persona_name 
            FROM accounts a 
            LEFT JOIN personas p ON a.persona_id = p.id
        """, conn)
        st.dataframe(df_a, use_container_width=True)
        
        if not df_a.empty:
            st.divider()
            st.subheader("🛠️ Action Zone (Accounts)")
            with st.expander("Modify or Delete SM Account"):
                a_opts = {row['username']: row['id'] for idx, row in df_a.iterrows()}
                selected_a = st.selectbox("Select Account", list(a_opts.keys()))
                if st.button("🗑️ Delete Selected Account", type="primary"):
                    try:
                        conn.execute("DELETE FROM accounts WHERE id=?", (a_opts[selected_a],))
                        conn.commit()
                        st.success("Deleted!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Cannot delete: {e}")

    except Exception as e:
        pass
    conn.close()

with tab_tags:
    st.header("🎯 Discovery Tags")
    st.write("Keywords the AI will use to search the platform and harvest viable threads dynamically.")
    
    with st.form("tag_form"):
        search_tag = st.text_input("Search Tag (e.g. 'keto vs paleo', 'desk job fitness')")
        t_platform = st.selectbox("Platform", ["reddit", "x", "facebook"])
        if st.form_submit_button("Add Tag"):
            if search_tag:
                conn = get_db_connection()
                try:
                    conn.execute("INSERT INTO search_tags (tag, platform) VALUES (?, ?)", (search_tag.strip(), t_platform))
                    conn.commit()
                    st.success("Tag added successfully!")
                    time.sleep(1)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Tag already exists.")
                conn.close()
    
    conn = get_db_connection()
    try:
        df_tags = pd.read_sql_query("SELECT id, tag, platform, status FROM search_tags", conn)
        if not df_tags.empty:
            st.dataframe(df_tags, use_container_width=True)
            
            st.divider()
            st.subheader("🛠️ Action Zone (Tags)")
            with st.expander("Modify or Delete Tag"):
                t_opts = {f"[{row['platform']}] {row['tag']}": row['id'] for idx, row in df_tags.iterrows()}
                selected_t = st.selectbox("Select Target Tag", list(t_opts.keys()))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⏸️ Deactivate Tag"):
                        conn.execute("UPDATE search_tags SET status='inactive' WHERE id=?", (t_opts[selected_t],))
                        conn.commit()
                        st.success("Deactivated!")
                        time.sleep(1)
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete Selected Tag", type="primary"):
                        conn.execute("DELETE FROM search_tags WHERE id=?", (t_opts[selected_t],))
                        conn.commit()
                        st.success("Deleted!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("No tags configured. Add some tags for the agent to start hunting!")
    except Exception as e:
        pass
    conn.close()

with tab_config:
    st.header("⚙️ Product Context & Agent Launch")
    st.write("Configure the agent's target environment and turn it ON/OFF.")

    conn = get_db_connection()
    config_row = conn.execute("SELECT * FROM system_config LIMIT 1").fetchone()
    
    col_status, col_control = st.columns(2)
    current_status = config_row["agent_status"] if config_row else "stopped"
    
    col_status.metric("Agent Status", current_status.upper())
    
    with col_control:
        if current_status == "stopped":
            if st.button("▶️ START AGENT", use_container_width=True, type="primary"):
                conn.execute("UPDATE system_config SET agent_status = 'running'")
                conn.commit()
                st.rerun()
        else:
            if st.button("⏹ STOP AGENT", use_container_width=True):
                conn.execute("UPDATE system_config SET agent_status = 'stopped'")
                conn.commit()
                st.rerun()

    st.subheader("Global Strategy Context")
    with st.form("sys_config_form"):
        niche = st.text_input("Target Niche", value=config_row["target_niche"] if config_row else "")
        link = st.text_input("Product Link (UTM)", value=config_row["product_link"] if config_row else "")
        
        try: cooldown_val = int(config_row["cooldown_minutes"]) if config_row and "cooldown_minutes" in config_row.keys() and config_row["cooldown_minutes"] is not None else 90
        except: cooldown_val = 90
        cooldown_ui = st.number_input("Account Cooldown (Minutes)", min_value=5, max_value=1440, value=cooldown_val)
        
        try: api_key = st.text_input("Gemini API Key", value=config_row["gemini_api_key"] if config_row and "gemini_api_key" in config_row.keys() and config_row["gemini_api_key"] else "", type="password")
        except: api_key = st.text_input("Gemini API Key", value="", type="password")
            
        if st.form_submit_button("Save Strategy Context"):
            conn.execute("UPDATE system_config SET target_niche = ?, product_link = ?, gemini_api_key = ?, cooldown_minutes = ?", (niche, link, api_key, cooldown_ui))
            conn.commit()
            st.success("Strategy Context Updated!")
    
    conn.close()

with tab_override:
    st.header("⚠️ Manual Override")
    st.toggle("Enable Ebook Link-Drop", value=False, key="ebook_override")
    if st.session_state.ebook_override:
        st.warning("Manual Override ACTIVE. Next agent interaction will drop the link regardless of Rapport Phase.")
    else:
        st.success("Operating in Autonomous Mode.")
        
    st.divider()
    st.subheader("🗑️ Data Reset")
    st.write("Clear all mock and legacy engagements from the Mission Map and Live Feed.")
    if st.button("Wipe Mission History Data", type="primary"):
        conn = get_db_connection()
        conn.execute("DELETE FROM engagements")
        conn.commit()
        conn.close()
        st.success("History Reset! Refreshing...")
        time.sleep(1)
        st.rerun()

with tab_saas:
    st.header("💼 SaaS Simulation")
    try:
        conn = get_db_connection()
        df_eff = pd.read_sql_query("SELECT * FROM seeding_efficiency", conn)
        conn.close()
        total_clicks = df_eff['total_link_clicks'].sum() if not df_eff.empty else 0
    except:
        total_clicks = 0
        
    conversion_rate = st.slider("Estimated Conversion Rate (%)", 0.0, 10.0, 2.5)
    avg_revenue = st.number_input("Average Revenue Per Conversion ($)", value=29.99)
    projected_conversions = int(total_clicks * (conversion_rate / 100))
    projected_revenue = projected_conversions * avg_revenue
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Link Clicks", total_clicks)
    col2.metric("Projected Conversions", projected_conversions)
    col3.metric("Projected Revenue ($)", f"${projected_revenue:.2f}")
