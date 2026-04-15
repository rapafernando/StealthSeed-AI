import streamlit as st
import sqlite3
import pandas as pd

# Path to the SQLite DB
DB_PATH = "../data/stealth_seed.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

st.set_page_config(page_title="StealthSeed-AI Dashboard", layout="wide")

st.title("🌱 StealthSeed-AI Command Center")

tab1, tab2, tab3 = st.tabs(["Mission Map", "Manual Override", "SaaS Simulation"])

with tab1:
    st.header("🗺️ Mission Map")
    st.write("Active threads and their current phase.")
    try:
        conn = get_db_connection()
        # Fallback query if DB lacks schema
        # In a real scenario, DB initialization handles this.
        query = """
            SELECT t.platform, t.thread_url, e.phase, e.timestamp, a.username 
            FROM engagements e
            JOIN threads t ON e.thread_id = t.id
            JOIN accounts a ON e.account_id = a.id
            ORDER BY e.timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No active missions found. Run the agent to populate data.")
    except Exception as e:
        st.error(f"Waiting for agent DB initialization...")

with tab2:
    st.header("⚠️ Manual Override")
    st.write("Control the Seeding flow directly.")
    
    st.toggle("Enable Ebook Link-Drop", value=False, key="ebook_override")
    
    if st.session_state.ebook_override:
        st.warning("Manual Override ACTIVE. Next agent interaction will drop the link regardless of Rapport Phase.")
    else:
        st.success("Operating in Autonomous Mode.")

with tab3:
    st.header("💼 SaaS Simulation")
    st.write("Projected revenue based on current seed success rates.")
    
    try:
        conn = get_db_connection()
        query = "SELECT * FROM seeding_efficiency"
        df_eff = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df_eff.empty:
            total_clicks = df_eff['total_link_clicks'].sum()
        else:
            total_clicks = 0
            
    except Exception as e:
        total_clicks = 0
        st.write("Awaiting analytics data...")
        
    conversion_rate = st.slider("Estimated Conversion Rate (%)", 0.0, 10.0, 2.5)
    avg_revenue = st.number_input("Average Revenue Per Conversion ($)", value=29.99)
    
    projected_conversions = int(total_clicks * (conversion_rate / 100))
    projected_revenue = projected_conversions * avg_revenue
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Link Clicks", total_clicks)
    col2.metric("Projected Conversions", projected_conversions)
    col3.metric("Projected Revenue ($)", f"${projected_revenue:.2f}")
