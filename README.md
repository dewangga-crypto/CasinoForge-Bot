# 🎰 CasinoForge

An advanced, high-stakes Discord economy and gambling bot built with **discord.py** and powered by a cloud-hosted **Supabase PostgreSQL** database. Optimized for ephemeral cloud container environments.

---

## 🚀 Key Features

*   **Gambling Suite (15+ Commands):** High-stakes casino games including `/blackjack`, `/slots`, `/crash`, and `/roulette`.
*   **Dual-Layer Moderation System:** 10 economy management commands for staff alongside 10 high-level restriction tools (`/eco-freeze`, `/eco-wipe`).
*   **God-Mode Creator Layer:** 10 administrative developer commands strictly hardlocked to developer identity validation.
*   **Modular Architecture:** Built entirely utilizing Discord Cogs for independent module hot-reloading (`/dev-reload`) without container restarts.

---

## 📁 Project Structure

```text
CasinoForge/
│
├── main.py               # Main bot engine & Supabase coordinator
├── requirements.txt      # Dependency manifest
├── LICENSE               # Apache License 2.0
│
└── cogs/                 # Modular command cogs
    ├── gambling.py       # Full casino suite
    ├── economy.py        # Core wallet & action commands
    ├── staff.py          # Economy management & severe moderation
    ├── creator.py        # Developer commands (hyperjay_951)
    └── fun.py            # Non-economy chat utility commands
    --- beg.py.           # Begging Command ig
