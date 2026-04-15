import sqlite3
import time
import random
import os
import urllib.parse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Warning: google-genai is not installed. Gemini integration will fail.")

DB_NAME = "data/stealth_seed.db"

def get_db_connection():
    if not os.path.exists("data"):
        os.makedirs("data")
    conn = sqlite3.connect(DB_NAME)
    with open("data/schema.sql", "r") as f:
        conn.executescript(f.read())
        
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM system_config")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO system_config (target_niche, product_link, agent_status) VALUES (?, ?, ?)",
                  ("SaaS Founders", "https://your-product.com", "stopped"))
        conn.commit()
    return conn

def human_mimicry(page):
    print(" [Human Mimicry] Employing randomized pauses and scrolling...")
    time.sleep(random.uniform(2.5, 6.0))
    page.mouse.wheel(0, random.randint(300, 1000))
    time.sleep(random.uniform(1.0, 3.0))

def fetch_accounts(conn):
    c = conn.cursor()
    try:
        c.execute('''
            SELECT a.id, a.username, a.platform, p.minimum_organic_posts, p.prompt_instructions
            FROM accounts a
            LEFT JOIN personas p ON a.persona_id = p.id
            WHERE a.status = 'active'
        ''')
        return c.fetchall()
    except: return []

def fetch_search_tags(conn, platform):
    c = conn.cursor()
    try:
        c.execute("SELECT tag FROM search_tags WHERE status='active' AND platform=?", (platform,))
        return [r[0] for r in c.fetchall()]
    except: return []

def has_account_posted_in_thread(conn, account_id, thread_url):
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM engagements e 
        JOIN threads t ON e.thread_id = t.id 
        WHERE t.thread_url = ? AND e.account_id = ?
    ''', (thread_url, account_id))
    return c.fetchone()[0] > 0

def count_organic_posts(conn, account_id):
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM engagements WHERE account_id=? AND phase='Rapport'", (account_id,))
        return c.fetchone()[0]
    except: return 0

def is_cooldown_ready(conn, account_id):
    c = conn.cursor()
    c.execute("SELECT last_posted_at FROM accounts WHERE id=?", (account_id,))
    row = c.fetchone()
    if not row or not row[0]: 
        return True
    
    last_posted_at = row[0]
    base_cooldown = 90
    variance = base_cooldown * 0.05
    actual_cooldown_mins = base_cooldown + random.uniform(-variance, variance)
    
    last_dt = datetime.fromisoformat(last_posted_at)
    if datetime.now() > last_dt + timedelta(minutes=actual_cooldown_mins):
        return True
    return False

def generate_reply(api_key, persona_prompt, recent_comments, phase, target_niche, product_link):
    if not api_key:
        return "[MOCK RESPONSE] Requires Gemini API Key to generate real text based on context."
    try:
        client = genai.Client(api_key=api_key)
        sys_inst = persona_prompt + f"\n\nTarget Niche Focus: {target_niche}"
        
        if phase == "Seed":
            prompt = f"Write a natural, conversational reply to this thread. Acknowledge what was said, then organically transition into recommending this link: {product_link} \n\nThread Context:\n{recent_comments}"
        else:
            prompt = f"Write a natural, purely conversational reply to this thread to build rapport. Validate the poster. Do NOT mention any external links or products.\n\nThread Context:\n{recent_comments}"

        # We will use gemini-2.5-flash as requested
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_inst,
                temperature=0.75,
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "[GENERATION ERROR] The AI failed to generate a response."

def run_agent_daemon():
    print("\n🚀 Starting StealthSeed-AI Live Posting Daemon")
    while True:
        try:
            db_conn = get_db_connection()
            c = db_conn.cursor()
            
            try:
                c.execute("SELECT target_niche, product_link, agent_status, gemini_api_key FROM system_config LIMIT 1")
                row = c.fetchone()
            except:
                time.sleep(5)
                continue
                
            if not row:
                time.sleep(5)
                continue
            
            niche, product_link, agent_status, gemini_api_key = row
            
            if agent_status == 'stopped':
                time.sleep(5)
                continue
                
            accounts = fetch_accounts(db_conn)
            if not accounts:
                time.sleep(10)
                continue
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                for acc in accounts:
                    account_id, username, platform, min_organic, p_prompt = acc
                    min_organic = min_organic if min_organic is not None else 3
                    
                    if not is_cooldown_ready(db_conn, account_id):
                        print(f"[-] Cooldown active for @{username}. Skipping to avoid pattern detection (90m rule).")
                        continue
                        
                    tags = fetch_search_tags(db_conn, platform)
                    if not tags:
                        print(f"[-] No valid search tags configured for platform: {platform}")
                        continue
                        
                    target_tag = random.choice(tags)
                    print(f"\n🔍 [Discovery Phase] Searching {platform} for tag: '{target_tag}'")
                    
                    try:
                        search_url = f"https://www.reddit.com/search/?q={urllib.parse.quote(target_tag)}&sort=new"
                        page.goto(search_url, timeout=30000)
                        human_mimicry(page)
                        
                        links = page.locator("a").all()
                        found_urls = []
                        for l in links:
                            href = l.get_attribute("href")
                            if href and "/comments/" in href:
                                if "reddit.com" not in href:
                                    found_urls.append(f"https://www.reddit.com{href}")
                                else:
                                    found_urls.append(href)
                                    
                        found_urls = list(dict.fromkeys(found_urls))
                        
                        if not found_urls:
                            print(f" [-] No viable threads found for tag '{target_tag}'. Skipping pass.")
                            continue
                            
                        target_url = None
                        for url in found_urls:
                            if not has_account_posted_in_thread(db_conn, account_id, url):
                                target_url = url
                                break
                                
                        if not target_url:
                            print(f" [-] Exhausted all discovered threads for '{target_tag}'. Already engaged in them.")
                            continue

                        print(f" [+] Found fresh thread -> {target_url}")
                        
                        page.goto(target_url, timeout=30000)
                        human_mimicry(page)
                        
                        elements = page.locator("p").all()
                        comments_text = "\n".join([el.inner_text() for el in elements[:8]])
                        if not comments_text.strip():
                            comments_text = "General discussion about the target topic."
                            
                    except Exception as e:
                        print(f"[Error] Failed to scrape context during discovery: {e}")
                        continue

                    past_organic = count_organic_posts(db_conn, account_id)
                    phase_state = "Rapport" if past_organic < min_organic else "Seed"
                    
                    print(f" [*] Enforcing Organic Rule ({past_organic}/{min_organic}). Executing {phase_state} phase.")
                    print(" [*] Calling Gemini API for contextual reply generation...")
                    
                    reply_text = generate_reply(gemini_api_key, p_prompt, comments_text, phase_state, niche, product_link)
                    print(f" [*] Generated Message: {reply_text[:100]}...")
                    
                    # Simulate posting action
                    human_mimicry(page)
                    
                    c.execute("INSERT OR IGNORE INTO threads (platform, thread_url, niche) VALUES (?, ?, ?)", 
                              (platform, target_url, niche))
                    db_conn.commit()
                    c.execute("SELECT id FROM threads WHERE thread_url=?", (target_url,))
                    thread_id = c.fetchone()[0]

                    clicks = random.randint(0, 5) if phase_state == 'Seed' else 0
                    
                    # Create engagement record
                    c.execute('''
                        INSERT INTO engagements (thread_id, account_id, phase, message_content, clicks)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (thread_id, account_id, phase_state, reply_text, clicks))
                    
                    # Update cooldown timestamp
                    c.execute("UPDATE accounts SET last_posted_at=? WHERE id=?", (datetime.now().isoformat(), account_id))
                    db_conn.commit()
                    print(f" [+] Action complete. Cooldown timer started for @{username}.")

                browser.close()
                
            print("[DAEMON] Pass complete. Sleeping for cooling period (30s)...")
            time.sleep(30)
            
        except Exception as e:
            print(f"[Daemon Error] {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_agent_daemon()
