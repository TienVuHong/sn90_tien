#!/usr/bin/env python3
"""
Run the DegenBrain miner.

Usage:
    python run_miner.py
"""
import asyncio
import sys
import sqlite3
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from miner.main import main

if __name__ == "__main__":
    try:
        if (not os.path.exists('sn90.db')):
            conn = sqlite3.connect('sn90.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Data_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement TEXT NOT NULL,
                    response TEXT NOT NULL
                )
            ''')
            conn.close()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMiner stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)