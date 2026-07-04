#!/usr/bin/env python3
"""Panopticon bootstrap installer — thin entry point.

Run from inside the child repo you want to initialize:

    export PANOPTICON_INSTANCE=acme/panopticon-instance
    curl -fsSL https://raw.githubusercontent.com/acme/panopticon-instance/main/install.py | python3

Or download and run directly:

    python3 install.py
"""
import sys

from panopticon.bootstrap import main

if __name__ == "__main__":
    sys.exit(main() or 0)
