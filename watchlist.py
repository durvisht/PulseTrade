"""PulseTrade — per-user watchlist backed by a Supabase table.

Table schema (see schema.sql for the exact DDL + RLS policies):
    watchlist(id uuid pk, user_id uuid, ticker text, created_at timestamptz)
    unique(user_id, ticker)
"""

from __future__ import annotations

import streamlit as st

from auth import get_client


def get_watchlist(user_id: str) -> list[str]:
    client = get_client()
    if client is None or not user_id:
        return []
    try:
        res = (
            client.table("watchlist")
            .select("ticker")
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        return [row["ticker"] for row in res.data]
    except Exception as exc:
        st.warning(f"Could not load watchlist: {exc}")
        return []


def add_to_watchlist(user_id: str, ticker: str) -> bool:
    client = get_client()
    if client is None or not user_id:
        return False
    try:
        client.table("watchlist").insert({"user_id": user_id, "ticker": ticker}).execute()
        return True
    except Exception as exc:
        # Likely a duplicate (unique constraint) — treat as already-added, not an error.
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            return True
        st.warning(f"Could not add to watchlist: {exc}")
        return False


def remove_from_watchlist(user_id: str, ticker: str) -> bool:
    client = get_client()
    if client is None or not user_id:
        return False
    try:
        client.table("watchlist").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
        return True
    except Exception as exc:
        st.warning(f"Could not remove from watchlist: {exc}")
        return False


def is_watchlisted(user_id: str, ticker: str) -> bool:
    return ticker in get_watchlist(user_id)
