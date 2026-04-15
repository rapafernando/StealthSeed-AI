# Seeding Loop Workflow

This defines the core automation loop for social media seeding.

## Workflow Steps

1. **Account Rotation**: Cycle through the available accounts defined in `config.yaml`.
2. **State Management**: Maintain a running state for each identified thread. Track whether an account is currently in the "Rapport phase" (building up to 3 posts) or the "Seeding phase" (ready to drop the product link).
3. **Database Logging**: Log all interactions, including timestamps, account used, target platform, target thread URL, phase state, and message content to a local SQLite database (`stealth_seed.db`).
