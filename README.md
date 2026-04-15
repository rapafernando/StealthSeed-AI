# StealthSeed-AI

StealthSeed-AI is an autonomous social media name-seeding tool engineered for maximum stealth and high-conversion organic marketing.

## Project Structure
- `/src` - Core Python agent logic.
- `/dashboard` - Streamlit command center.
- `/data` - Local SQLite databases and SQL schemas.
- `/config` - Agent personas and YAML configuration files.
- `/.agent` - Guidelines, skills, and behavior definitions for the LLM.

## Setup
1. Define your personas in `/config`.
2. Review the schema in `/data/schema.sql` and initialize the DB.
3. Start the stack utilizing Docker Compose.

```bash
docker-compose up -d
```

## First Mission Instructions: "Diet Ebook"
1. **Goal**: Seed awareness for a new Diet Ebook focusing on sustainable weight loss for busy professionals.
2. **Persona**: 50-year-old IT professional from Florida.
3. **Execution**:
   - The agent will scan Reddit (e.g., r/loseit, r/OverFifty).
   - In the **Rapport Phase**, the agent will engage empathetically related to health struggles at desk jobs.
   - After establishing rapport (3+ posts), the agent transitions to the **Seed Phase** and seamlessly integrates a tracked UTM link to the Diet Ebook.
4. **Monitoring**: Open the dashboard on `http://localhost:8501` to view the Mission Map and track seeding efficiency. If necessary, use the "Manual Override" to force target seeding.
