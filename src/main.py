import yaml
import sqlite3
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

DB_NAME = "data/stealth_seed.db"

def setup_db():
    """Initializes the SQLite database as per the seeding loop workflow."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            account_username TEXT,
            target_platform TEXT,
            target_thread_url TEXT,
            phase_state TEXT,
            message_content TEXT
        )
    ''')
    conn.commit()
    return conn

def log_interaction(conn, username, platform, thread_url, phase, message):
    """Logs an interaction to the database."""
    c = conn.cursor()
    c.execute('''
        INSERT INTO interactions (account_username, target_platform, target_thread_url, phase_state, message_content)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, platform, thread_url, phase, message))
    conn.commit()

def load_config():
    """Loads settings from config.yaml."""
    with open('config/config.yaml', 'r') as file:
        return yaml.safe_load(file)

def human_mimicry(page):
    """Simulates organic human behavior to prevent bot detection."""
    print(" [Human Mimicry] Employing randomized pauses and scrolling...")
    # Organic pause
    time.sleep(random.uniform(1.2, 4.5))
    # Randomized scrolling
    page.mouse.wheel(0, random.randint(100, 700))
    time.sleep(random.uniform(0.5, 2.0))

def run_agent():
    config = load_config()
    db_conn = setup_db()
    
    print("\n🚀 Starting StealthSeed-AI Agent Validation")
    print(f"🎯 Target Niche: {config.get('target_niche')}")
    
    with sync_playwright() as p:
        # headless=False allows you to visually monitor the agent's behavior
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        # Iterate via the workflows rules
        platforms = ['reddit', 'x', 'facebook']
        for platform in platforms:
            accounts = config.get('accounts', {}).get(platform, [])
            for account in accounts:
                username = account.get('username')
                print(f"\n🔄 Rotating to {platform.capitalize()} account: {username}")
                
                # Mock navigation and interaction for demonstration
                # page.goto("https://www.example.com")
                human_mimicry(page)
                
                # State tracking: Rapport vs Seeding phase
                print(f" [*] Enforcing 3-Post Rapport Rule before dropping link...")
                phase_state = "Rapport Phase"
                mock_message = "This is a highly valuable, organic-sounding contribution."
                
                print(f" [*] Executing interaction under {phase_state}...")
                log_interaction(
                    db_conn, 
                    username, 
                    platform, 
                    "https://mock-thread.com/123", 
                    phase_state, 
                    mock_message
                )
                
                # Simulate screenshot capture on seeding post (as per SKILL.md)
                # target_screenshot = f"{platform}_{username}_seed_log.png"
                # page.screenshot(path=target_screenshot)

        browser.close()
        db_conn.close()

if __name__ == "__main__":
    run_agent()
