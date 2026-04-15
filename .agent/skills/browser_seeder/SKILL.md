# Browser Seeder Skill

This skill defines the technical capabilities for the Antigravity Browser Agent.

## Core Capabilities

1. **Platform Navigation**: Automatically navigate to Reddit, X, and Facebook.
2. **Intent Identification**: Scan feeds and search results to identify "High Intent" threads based on configured keyword profiles.
3. **Human Mimicry (Playwright)**: Ensure all browser actions mimic human behavior to avoid bot detection:
   - Use randomized typing speeds with occasional backspaces.
   - Implement randomized, non-linear scrolling patterns.
   - Include organic pauses between page loads, clicks, and keystrokes.
4. **Verification Evidence**: Capture and save a screenshot of every "Seed" post created in the browser to serve as the verification log.
