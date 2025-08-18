#!/usr/bin/env python3
"""
Simple launcher script for the Farm Lifecycle Daemon
"""

import sys
import os

# Add src directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from farm_daemon import main

if __name__ == "__main__":
    main()
