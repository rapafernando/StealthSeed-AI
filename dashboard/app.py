import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os

DB_PATH = "../data/stealth_seed.db"

def init_db():
    # Make sure data directory exists
    os.makedirs("../data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        with open("../data/schema.sql", "r") as f:
            conn.executescript(f.read())
            
        # Ensure at least 1 config row exists
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM system_config")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO system_config (target_niche, product_link, agent_status) VALUES (?, ?, ?)",
                      ("SaaS Founders", "https://your-product.com", "stopped"))
            
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN last_posted_at DATETIME")
            conn.commit()
        except: pass
        
        try:
            conn.execute("ALTER TABLE system_config ADD COLUMN gemini_api_key TEXT")
            conn.commit()
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

st.set_page_config(page_title="StealthSeed-AI Dashboard", layout="wide")

# Init DB automatically
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

st.title(f"🌱 StealthSeed-AI Command Center - Welcome {st.session_state.username}")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

tab_feed, tab_map, tab_personas, tab_accounts, tab_tags, tab_config, tab_override, tab_saas = st.tabs([
    "💬 Live Feed", "🗺️ Mission Map", "🎭 Personas", "📱 SM Accounts", "🎯 Discovery Tags", "⚙️ Settings & Launch", "⚠️ Manual Override", "💼 SaaS Simulation"
])

with tab_feed:
    st.header("💬 Agent Live Feed")
    st.write("Real-time stream of all agent interactions and seed drops.")
    
    conn = get_db_connection()
    try:
        query = """
            SELECT t.platform, t.thread_url, e.phase, e.timestamp, a.username, e.message_content 
            FROM engagements e
            JOIN threads t ON e.thread_id = t.id
            JOIN accounts a ON e.account_id = a.id
            ORDER BY e.timestamp DESC
            LIMIT 50
        """
        rows = conn.execute(query).fetchall()
        
        if not rows:
            st.info("No active missions found. Set up your Agent in 'Settings & Launch'!")
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
            SELECT t.platform, t.thread_url, e.phase, e.timestamp, a.username 
            FROM engagements e
            JOIN threads t ON e.thread_id = t.id
            JOIN accounts a ON e.account_id = a.id
            ORDER BY e.timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
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
            else:
                st.error("Persona name is required.")
            
    st.subheader("Existing Personas")
    conn = get_db_connection()
    df_p = pd.read_sql_query("SELECT id, name, minimum_organic_posts, prompt_instructions FROM personas", conn)
    conn.close()
    st.dataframe(df_p, use_container_width=True)

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
                conn.execute(
                    "INSERT INTO accounts (username, password, platform, persona_id) VALUES (?, ?, ?, ?)",
                    (acc_user, acc_pass, platform, persona_options[selected_p])
                )
                conn.commit()
                st.success("Account added!")
                
    st.subheader("Active Accounts")
    try:
        df_a = pd.read_sql_query("""
            SELECT a.id, a.username, a.platform, p.name as persona_name 
            FROM accounts a 
            LEFT JOIN personas p ON a.persona_id = p.id
        """, conn)
        st.dataframe(df_a, use_container_width=True)
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
                except sqlite3.IntegrityError:
                    st.error("Tag already exists.")
                conn.close()
    
    conn = get_db_connection()
    try:
        df_tags = pd.read_sql_query("SELECT id, tag, platform, status FROM search_tags", conn)
        if not df_tags.empty:
            st.dataframe(df_tags, use_container_width=True)
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
        try:
            api_key = st.text_input("Gemini API Key", value=config_row["gemini_api_key"] if config_row and "gemini_api_key" in config_row.keys() and config_row["gemini_api_key"] else "", type="password")
        except:
            api_key = st.text_input("Gemini API Key", value="", type="password")
            
        if st.form_submit_button("Save Strategy Context"):
            conn.execute("UPDATE system_config SET target_niche = ?, product_link = ?, gemini_api_key = ?", (niche, link, api_key))
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
