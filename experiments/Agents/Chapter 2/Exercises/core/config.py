"""
config.py
---------
Shared configuration for the Chapter 2 Exercises ecosystem.

Loads the root .env (where all API keys live), and exposes:
  - MODEL:            the default LLM used by agents (overridable per agent)
  - ROOT_DIR:         the repository root (parent chain from this file)
  - EXERCISES_DIR:    this Exercises package
  - env(key):         safe lookup of API keys from the environment
  - require(key):     lookup that fails loudly if the key is missing

All agents / tools / memory layers import from here so there is a single
source of truth for paths and secrets.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# --- Paths -------------------------------------------------------------------
# core/config.py -> core -> Exercises -> Chapter 2 -> <repo root>
CORE_DIR = Path(__file__).resolve().parent
EXERCISES_DIR = CORE_DIR.parent
CHAPTER_DIR = EXERCISES_DIR.parent
ROOT_DIR = CHAPTER_DIR.parent

# A .env may exist in the repo root or directly inside Exercises (or both).
# We load the root one first (it is the shared secret store for all chapters),
# then allow an Exercises-local override on top.
load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(EXERCISES_DIR / ".env", override=True)

# --- Defaults -----------------------------------------------------------------
# gpt-4o-mini == the model used across Chapter 2. Cheap, fast, good enough for
# patterns labs, and already approved for use in the root environment.
MODEL = "gpt-4o-mini"

# Lab 1's core lesson is the LLM knowledge-cutoff trap: asked for the "most
# recent fiscal year", gpt-4o-mini happily answers with data from its training
# cutoff (e.g. 2023) unless it is told the current year. Agents inject
# CURRENT_YEAR into their instructions so they ask the tools for the right
# period.
CURRENT_YEAR = date.today().year

# Any Chroma / SQLite artifacts created by the memory layers land here so a
# single `data/` dir is easy to inspect or wipe between experiments.
DATA_DIR = EXERCISES_DIR / "data"


def env(name: str, default: str | None = None) -> str | None:
    """Look up a key from the environment (root .env already loaded)."""
    return os.environ.get(name, default)


def require(name: str) -> str:
    """Look up a key, raising a clear error if it is missing."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Environment variable {name!r} is not set. "
            f"Check {ROOT_DIR / '.env'} (or {EXERCISES_DIR / '.env'})."
        )
    return value