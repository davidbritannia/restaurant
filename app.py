"""
app.py — Restaurant Spy Streamlit Dashboard

Run with: streamlit run app.py
"""

import sys
import os
from pathlib import Path

# Ensure the project root is on sys.path (fixes ModuleNotFoundError on Windows)
sys.path.insert(0, str(Path(__file__).parent))

import json
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Restaurant Spy 🕵️",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports (after page config) ───────────────────────────────────────────────
from config import config
from database import (
    init_db, SessionLocal, add_competitor, get_competitors,
    deactivate_competitor, get_briefs, get_latest_ghost_menu,
    get_recent_alerts, get_last_scrape,
)
from scheduler import start_scheduler, run_full_intelligence_cycle, get_next_run_time
from utils import warn_missing_keys

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
start_scheduler()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif !important;
}

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: #0d0d0d !important;
    border-right: 1px solid #222;
}
[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #e0e0e0 !important;
}

/* Main bg */
.main .block-container {
    background: #f8f7f4;
    padding-top: 1.5rem;
}

/* Cards */
.spy-card {
    background: white;
    border: 1px solid #e8e4dc;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* Ghost badge */
.ghost-badge {
    display: inline-block;
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    margin: 2px;
}

/* Red alert */
.red-alert {
    background: #fff0f0;
    border-left: 4px solid #e63946;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
}

/* Action item */
.action-item {
    background: #f0fff4;
    border-left: 4px solid #2d6a4f;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
    font-weight: 600;
}

/* Metric override */
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #e8e4dc;
    border-radius: 10px;
    padding: 12px 16px;
}

/* Buttons */
.stButton button {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

h1 { font-weight: 700; }
h2 { font-weight: 600; color: #1a1a2e; }
h3 { font-weight: 600; color: #2b2d42; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_db():
    return SessionLocal()


def api_status():
    missing = warn_missing_keys()
    return missing


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🕵️ Restaurant Spy")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard", "➕ Add Competitor", "👻 Ghost Menus", "📋 Briefs", "🔴 Red Alerts", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f"**Next auto-run:**")
    st.caption(get_next_run_time())

    missing_keys = api_status()
    if missing_keys:
        st.warning(f"⚠️ Missing keys:\n{', '.join(missing_keys)}")
    else:
        st.success("✅ All API keys set")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Dashboard":
    st.title("🕵️ Restaurant Spy")
    st.caption("Your WhatsApp Pocket Consultant — Competitor Intelligence at a Glance")

    db = get_db()
    competitors = get_competitors(db)

    # ── Top metrics ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Competitors Tracked", len(competitors))
    with col2:
        total_ghost = sum(
            len(get_latest_ghost_menu(db, c.id)) for c in competitors
        )
        st.metric("👻 Ghost Items Found", total_ghost)
    with col3:
        alerts = get_recent_alerts(db, hours=168)  # last 7 days
        st.metric("🔴 Alerts (7 days)", len(alerts))
    with col4:
        briefs = []
        if competitors:
            restaurant_names = list({c.user_restaurant_name for c in competitors})
            for rn in restaurant_names:
                briefs += get_briefs(db, rn, limit=1)
        st.metric("📋 Briefs Generated", len(briefs))

    st.markdown("---")

    # ── Run Now button ─────────────────────────────────────────────────────────
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_clicked = st.button(
            "▶️ Run Full Intelligence Now",
            type="primary",
            use_container_width=True,
        )
    with col_info:
        st.caption(
            "Scrapes all competitors, detects ghost menus, analyzes with Claude, "
            "and generates your weekly brief."
        )

    if run_clicked:
        if not competitors:
            st.warning("Add at least one competitor first!")
        else:
            with st.spinner("🔍 Running intelligence cycle... this may take a minute."):
                results = run_full_intelligence_cycle()
            if results:
                st.success("✅ Intelligence cycle complete! Check Briefs and Ghost Menus.")
                st.rerun()
            else:
                st.error("Cycle failed — check logs for details.")

    # ── Competitor overview ────────────────────────────────────────────────────
    st.markdown("### Tracked Competitors")

    if not competitors:
        st.info("No competitors yet. Head to **➕ Add Competitor** to get started.")
    else:
        for c in competitors:
            ghost_items = get_latest_ghost_menu(db, c.id)
            last_scrape = c.last_scrape_date
            last_scrape_str = (
                last_scrape.strftime("%b %d %H:%M") if last_scrape else "Never"
            )

            with st.container():
                st.markdown(f"""
<div class="spy-card">
  <strong>{c.name}</strong>
  {"&nbsp;&nbsp;<span style='color:#e63946;font-weight:600;'>👻 " + str(len(ghost_items)) + " ghost items</span>" if ghost_items else ""}
  <br>
  <small style="color:#888">
    {c.cuisine_category or '—'} &nbsp;|&nbsp;
    Last scan: {last_scrape_str} &nbsp;|&nbsp;
    Delivery: {"✅" if c.delivery_url else "❌"} &nbsp;|&nbsp;
    Instagram: {"✅" if c.instagram_handle else "❌"}
  </small>
</div>
""", unsafe_allow_html=True)

    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ADD COMPETITOR
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "➕ Add Competitor":
    st.title("➕ Add a Competitor")
    st.caption("Add the restaurants you want to spy on. The **delivery URL** is required for ghost menu detection.")

    with st.form("add_competitor_form"):
        st.markdown("#### Your Restaurant")
        user_restaurant = st.text_input(
            "Your restaurant name *",
            placeholder="e.g. Mario's Pizzeria",
        )

        st.markdown("#### Competitor Details")
        col1, col2 = st.columns(2)
        with col1:
            comp_name = st.text_input("Competitor name *", placeholder="e.g. Joe's Pizza")
            instagram = st.text_input("Instagram handle", placeholder="@joespizza (no @ needed)")
            cuisine = st.text_input("Cuisine category", placeholder="e.g. Italian, Burger, Sushi")

        with col2:
            google_url = st.text_input(
                "Google Maps URL",
                placeholder="https://maps.google.com/?cid=...",
            )
            delivery_url = st.text_input(
                "Delivery URL * (UberEats / DoorDash) 👻",
                placeholder="https://www.ubereats.com/store/joes-pizza/...",
                help="Required for ghost menu detection — the most valuable feature!",
            )
            notes = st.text_area("Notes (optional)", height=80)

        submitted = st.form_submit_button("Add Competitor", type="primary")

        if submitted:
            if not user_restaurant or not comp_name:
                st.error("Your restaurant name and competitor name are required.")
            else:
                db = get_db()
                comp = add_competitor(
                    db,
                    name=comp_name,
                    user_restaurant_name=user_restaurant,
                    google_maps_url=google_url,
                    instagram_handle=instagram.lstrip("@") if instagram else "",
                    delivery_url=delivery_url,
                    cuisine_category=cuisine,
                    notes=notes,
                )
                db.close()
                st.success(f"✅ **{comp_name}** added! Run the intelligence cycle from the Dashboard.")

    # ── Existing competitors list ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Existing Competitors")
    db = get_db()
    competitors = get_competitors(db)

    if competitors:
        for c in competitors:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write(f"**{c.name}** ({c.user_restaurant_name})")
            with col2:
                st.caption("👻" if c.delivery_url else "—")
            with col3:
                if st.button("Remove", key=f"del_{c.id}"):
                    deactivate_competitor(db, c.id)
                    st.rerun()
    else:
        st.info("No competitors yet.")
    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: GHOST MENUS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "👻 Ghost Menus":
    st.title("👻 Ghost Menu Intelligence")
    st.caption(
        "Items your competitors sell on **UberEats / DoorDash** but NOT on their physical menu. "
        "These are secret tests — your early-mover advantage."
    )

    db = get_db()
    competitors = get_competitors(db)

    if not competitors:
        st.info("Add competitors and run the intelligence cycle to see ghost menus.")
    else:
        any_found = False
        for c in competitors:
            ghost_items = get_latest_ghost_menu(db, c.id)
            if not ghost_items:
                continue
            any_found = True

            st.markdown(f"### {c.name}")
            st.caption(f"Delivery: {c.delivery_url or 'N/A'}")

            df_data = []
            for item in ghost_items:
                df_data.append({
                    "Item": item.get("name", ""),
                    "Price": f"${item['price']:.2f}" if item.get("price") else "N/A",
                    "Category": item.get("category") or "—",
                    "Hypothesis": item.get("hypothesis") or "Testing delivery demand",
                })

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown("---")

        if not any_found:
            st.info("No ghost menu items detected yet. Run an intelligence cycle first.")

    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: BRIEFS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📋 Briefs":
    st.title("📋 Weekly Intelligence Briefs")

    db = get_db()
    competitors = get_competitors(db)

    if not competitors:
        st.info("No data yet. Add competitors and run the intelligence cycle.")
    else:
        restaurant_names = sorted({c.user_restaurant_name for c in competitors})
        selected = st.selectbox("Restaurant", restaurant_names) if len(restaurant_names) > 1 else restaurant_names[0]

        briefs = get_briefs(db, selected, limit=20)

        if not briefs:
            st.info("No briefs yet. Run the intelligence cycle from the Dashboard.")
        else:
            for brief in briefs:
                date_str = brief.brief_date.strftime("%B %d, %Y") if brief.brief_date else "Unknown"
                with st.expander(
                    f"📋 {date_str} — {brief.competitor_count} competitors | 🔴 {brief.red_alert_count} alerts",
                    expanded=(brief == briefs[0]),
                ):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(brief.markdown_content)
                    with col2:
                        if brief.pdf_path and Path(brief.pdf_path).exists():
                            with open(brief.pdf_path, "rb") as f:
                                st.download_button(
                                    "⬇️ Download PDF",
                                    f.read(),
                                    file_name=Path(brief.pdf_path).name,
                                    mime="application/pdf",
                                )

    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: RED ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🔴 Red Alerts":
    st.title("🔴 Red Alerts")
    st.caption("Immediate-action intelligence — price undercuts, review spikes, and new ghost menu launches.")

    db = get_db()
    alerts = get_recent_alerts(db, hours=168)

    if not alerts:
        st.success("✅ No red alerts in the last 7 days. All quiet on the front.")
    else:
        for alert in alerts:
            icon = {
                "price_undercut": "💰",
                "review_spike": "⭐",
                "ghost_menu": "👻",
                "sentiment_drop": "📉",
            }.get(alert.alert_type, "🔴")

            fired_str = alert.fired_at.strftime("%b %d %H:%M") if alert.fired_at else "Unknown"
            comp = alert.competitor

            st.markdown(f"""
<div class="red-alert">
  <strong>{icon} [{alert.alert_type.replace('_', ' ').title()}]</strong>
  &nbsp;<small style="color:#999">{fired_str}</small><br>
  {alert.alert_message}
  {"<br><small style='color:#888'>Competitor: " + comp.name + "</small>" if comp else ""}
</div>
""", unsafe_allow_html=True)

    db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.markdown("### API Keys Status")
    missing = warn_missing_keys()
    if missing:
        st.error(
            f"Missing: **{', '.join(missing)}**\n\n"
            "Copy `.env.example` → `.env` and fill in your keys, then restart the app."
        )
    else:
        st.success("✅ All API keys configured")

    st.markdown("---")
    st.markdown("### Configuration")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Claude model:** {config.CLAUDE_MODEL}")
        st.info(f"**Weekly brief:** {config.WEEKLY_BRIEF_DAY.title()} at {config.WEEKLY_BRIEF_HOUR}:00")
        st.info(f"**Scrape delay:** {config.SCRAPE_DELAY_MIN}–{config.SCRAPE_DELAY_MAX}s")
    with col2:
        st.info(f"**Price alert threshold:** {int(config.PRICE_ALERT_THRESHOLD * 100)}%")
        st.info(f"**Review spike threshold:** {config.NEGATIVE_REVIEW_ALERT_COUNT} reviews in 24h")
        st.info(f"**Data dir:** {config.DATA_DIR}")

    st.markdown("---")
    st.markdown("### Setup Guide")
    st.markdown("""
1. **Get API Keys:**
   - [Anthropic API](https://console.anthropic.com) — for AI intelligence
   - [Firecrawl API](https://firecrawl.dev) — for web scraping

2. **Configure `.env`:** Copy `.env.example` → `.env` and fill in your keys

3. **Add Competitors:** Go to ➕ Add Competitor, paste their delivery URL (ghost menu detection!)

4. **Run First Cycle:** Click the green button on the Dashboard

5. **Phase 2 — WhatsApp:** Uncomment `twilio` in `requirements.txt` and configure `whatsapp.py`
""")

    st.markdown("---")
    st.caption("Restaurant Spy v1.0 — Built with Claude + Firecrawl + Streamlit")
