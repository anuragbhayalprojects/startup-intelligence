"""
backend/services/email_service.py
--------------------------------
SMTP Email service for dispatching HTML digests via Gmail.
Loads delivery constraints and targets from config/email_config.json.
"""

from __future__ import annotations
import os
import json
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from backend.services.supabase_service import supabase

logger = logging.getLogger("startup_intelligence.services.email_service")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
EMAIL_CONFIG_PATH = os.path.join(PROJECT_ROOT, "backend", "config", "email_config.json")


def load_email_config() -> Dict[str, Any]:
    """Loads email digest configuration."""
    if not os.path.exists(EMAIL_CONFIG_PATH):
        logger.warning(f"email_config.json not found at {EMAIL_CONFIG_PATH}")
        return {}
    try:
        with open(EMAIL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load email config: {e}")
        return {}


def generate_html_digest(articles: List[Dict[str, Any]], edition: str = "Daily") -> str:
    """Generates a professional, mobile-friendly HTML template for the email digest using Gmail-safe table layouts and inline styles."""
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    
    # Header Section
    html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>ICICI Startup Intelligence Digest</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 0; -webkit-font-smoothing: antialiased;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; padding: 24px 12px;">
        <tr>
            <td align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 32px 24px; text-align: left; border-bottom: 4px solid #f59e0b;">
                            <h1 style="font-size: 20px; font-weight: 800; margin: 0; text-transform: uppercase; letter-spacing: 1px; color: #ffffff; font-family: inherit;">ICICI Startup Intelligence</h1>
                            <p style="font-size: 13px; color: #94a3b8; margin: 6px 0 0 0; font-family: inherit;">{edition} Edition &bull; {date_str}</p>
                        </td>
                    </tr>
                    
                    <!-- Summary Banner -->
                    <tr>
                        <td style="padding: 20px 24px 10px 24px;">
                            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fef3c7; border-left: 4px solid #d97706; border-radius: 6px;">
                                <tr>
                                    <td style="padding: 12px 16px; font-size: 13px; color: #92400e; font-weight: 600; font-family: inherit; line-height: 1.4;">
                                        Aggregated Startup & Fintech Intelligence Report. Mentions resolved below.
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 10px 24px 30px 24px;">
                            <table border="0" cellpadding="0" cellspacing="0" width="100%">
    """
    
    # Loop over articles
    for art in articles:
        # Format metadata
        pub_dt = datetime.fromisoformat(art["published_at"].replace("Z", "+00:00"))
        pub_time_str = pub_dt.strftime("%b %d, %Y at %I:%M %p")
        
        headline = art["headline"]
        summary = art["summary"] or "No AI summary compiled."
        
        # Enforce maximum 150 words limit inside the email view
        summary_words = summary.split()
        if len(summary_words) > 150:
            summary = " ".join(summary_words[:150]) + "..."
            
        source = art["source"]
        source_url = art["source_url"]
        
        # Startups Mentioned Tags
        startups = art.get("startups_mentioned") or []
        startups_html = ""
        if startups:
            tags = []
            for s in startups:
                tags.append(f"""<span style="display: inline-block; background-color: #eff6ff; color: #2563eb; font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 4px; margin-right: 6px; text-transform: uppercase; margin-bottom: 4px; font-family: inherit;">🚀 {s.get("name")}</span>""")
            startups_html = f'<div style="margin-bottom: 12px; text-align: left;">{" ".join(tags)}</div>'
            
        # Similar Sources
        similar_sources = art.get("similar_sources") or []
        similar_html = ""
        if similar_sources:
            links = []
            for sim in similar_sources:
                links.append(f'<a href="{sim.get("url")}" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 600; font-family: inherit;">{sim.get("source")}</a>')
            similar_html = f"""
                <tr>
                    <td style="padding-top: 10px; font-size: 11px; color: #64748b; font-family: inherit; line-height: 1.4; text-align: left;">
                        Also reported by: {", ".join(links)}
                    </td>
                </tr>
            """

        html += f"""
                                <!-- Article Card -->
                                <tr>
                                    <td style="padding: 24px 0; border-bottom: 1px solid #e2e8f0;">
                                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td style="font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding-bottom: 8px; font-family: inherit; text-align: left;">
                                                    {pub_time_str}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding-bottom: 10px; text-align: left;">
                                                    <h2 style="font-size: 16px; font-weight: 700; margin: 0; line-height: 1.4; font-family: inherit;">
                                                        <a href="{source_url}" target="_blank" style="color: #0f172a; text-decoration: none;">{headline}</a>
                                                    </h2>
                                                </td>
                                            </tr>
                                            
                                            <!-- Startups Mentioned -->
                                            {"<tr><td style='padding-bottom: 4px;'>" + startups_html + "</td></tr>" if startups_html else ""}
                                            
                                            <tr>
                                                <td style="font-size: 13.5px; color: #334155; line-height: 1.5; padding-bottom: 14px; font-family: inherit; text-align: left;">
                                                    {summary}
                                                </td>
                                            </tr>
                                            
                                            <!-- Metadata Footer (Source + Button) -->
                                            <tr>
                                                <td>
                                                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                                        <tr>
                                                            <td align="left" style="vertical-align: middle;">
                                                                <span style="display: inline-block; background-color: #faf5ff; color: #7c3aed; font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 4px; text-transform: uppercase; font-family: inherit;">Source: {source}</span>
                                                            </td>
                                                            <td align="right" style="vertical-align: middle;">
                                                                <a href="{source_url}" target="_blank" style="display: inline-block; background-color: #0f172a; color: #ffffff !important; font-size: 12px; font-weight: 600; text-decoration: none; padding: 8px 16px; border-radius: 6px; text-align: center; font-family: inherit;">Read Full Article</a>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                            
                                            <!-- Similar Sources -->
                                            {similar_html}
                                        </table>
                                    </td>
                                </tr>
        """
        
    if not articles:
        html += """
                                <!-- Empty State -->
                                <tr>
                                    <td style="padding: 40px 0; text-align: center; color: #64748b; font-family: inherit; font-size: 14px;">
                                        No high-priority startup news articles ingested in this cycle.
                                    </td>
                                </tr>
        """

    # Footer Section
    html += """
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f1f5f9; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 11px; color: #64748b; font-family: inherit; line-height: 1.6;">
                            <p style="margin: 0 0 6px 0;">This email was automatically generated and sent to the ICICI Startup Engagement & Investments Team.</p>
                            <p style="margin: 0 0 6px 0;">&copy; 2026 ICICI Bank Ltd. All rights reserved.</p>
                            <p style="margin: 6px 0 0 0; font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Security Disclaimer: This information is for internal circulation only.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
    """
    return html


def dispatch_gmail_digest(edition: str = "Daily") -> bool:
    """
    Fetches the configured range of articles and dispatches the HTML digest.
    Reads credentials GMAIL_USER and GMAIL_APP_PASSWORD from env.
    """
    config = load_email_config()
    if not config.get("enabled", True):
        logger.info("Email digest is disabled in config.")
        return False
        
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pwd = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not gmail_user or not gmail_pwd:
        logger.error("GMAIL_USER and GMAIL_APP_PASSWORD environment variables must be set.")
        return False

    try:
        # 1. Fetch articles from Supabase in the past 12 hours (for twice_daily) or 24 hours (for daily)
        hours_lookback = 24 if config.get("frequency") == "daily" else 12
        since_time = (datetime.now(timezone.utc) - timedelta(hours=hours_lookback)).isoformat()
        
        # Fetch canonical news articles
        query = supabase.table("news_articles").select("*").gte("published_at", since_time)
        res = query.order("published_at", desc=True).limit(config.get("max_articles", 15)).execute()
        
        articles = res.data or []
        logger.info(f"Fetched {len(articles)} articles for {edition} digest.")

        # Post-filter in python by priority score if configured
        min_priority = config.get("filters", {}).get("priority_score_min", 0)
        filtered = []
        for art in articles:
            # If the article has resolved startups, check if any of them passes priority threshold
            startups = art.get("startups_mentioned") or []
            if min_priority > 0 and startups:
                # Find if any startup mentions match priority score in registry
                pass_gate = False
                for s in startups:
                    s_id = s.get("id")
                    if s_id:
                        st_res = supabase.table("startups").select("priority_score").eq("id", s_id).execute()
                        if st_res.data and (st_res.data[0].get("priority_score") or 0) >= min_priority:
                            pass_gate = True
                            break
                if not pass_gate:
                    continue
            filtered.append(art)

        # 2. Render HTML
        html_content = generate_html_digest(filtered, edition)
        
        # 3. Compile MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ICICI Startup Intelligence Digest - {edition} Edition"
        msg["From"] = config.get("sender") or gmail_user
        msg["To"] = ", ".join(config.get("recipient_list", [gmail_user]))
        
        if config.get("cc"):
            msg["Cc"] = ", ".join(config.get("cc", []))
        if config.get("bcc"):
            msg["Bcc"] = ", ".join(config.get("bcc", []))
            
        msg.attach(MIMEText(html_content, "html"))
        
        # 4. SMTP Send
        logger.info(f"Connecting to Gmail SMTP server for dispatching {edition} Edition...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        
        # All recipients list
        all_to = config.get("recipient_list", [gmail_user]) + config.get("cc", []) + config.get("bcc", [])
        
        server.sendmail(msg["From"], all_to, msg.as_string())
        server.quit()
        
        logger.info("✅ HTML Email digest successfully dispatched!")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch email digest: {e}", exc_info=True)
        return False
