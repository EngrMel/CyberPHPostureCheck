# ================================================================================================
# PH Cybersecurity & Data Privacy Posture Assessment Tool - Complete Production Version
# Developed by CyberPH | https://facebook.com/LearnCyberPH
# ================================================================================================

import os
import io
import json
import re
import html
import datetime as dt
import urllib.parse
from typing import Optional, Tuple
import streamlit as st
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF package

# ================================================================================================
# PAGE CONFIGURATION
# ================================================================================================
st.set_page_config(
    page_title="PH Cybersecurity & Data Privacy Posture",
    layout="wide",
    page_icon="🔐",
    menu_items={
        'Get Help': 'https://facebook.com/LearnCyberPH',
        'Report a bug': 'https://facebook.com/LearnCyberPH',
        'About': 'Developed by CyberPH - Free cybersecurity assessment tool'
    }
)

# ================================================================================================
# COLORS & STYLING
# ================================================================================================
BLACK = "#000000"
DARK_GRAY = "#1F2937"
GRAY = "#6B7280"
LIGHT_GRAY = "#E5E7EB"
SOFT_BG = "#F8FAFC"
WHITE = "#FFFFFF"
ACCENT_GRAY = "#9CA3AF"
SUCCESS_GREEN = "#10B981"
WARNING_ORANGE = "#F59E0B"
ERROR_RED = "#EF4444"
BORDER_COLOR = "#D1D5DB"

SPACING = {'section': 25, 'paragraph': 15, 'element': 10, 'tight': 5}

FONTS = {
    'title': ('hebo', 16),
    'header': ('hebo', 12),
    'subheader': ('hebo', 10),
    'body': ('helv', 9),
    'caption': ('helv', 8)
}

st.markdown(f"""
<style>
    .main .block-container {{
        padding-top: 0.75rem;
        padding-bottom: 1rem;
        color: {DARK_GRAY};
    }}
    .card {{
        background: {WHITE};
        border: 1px solid {LIGHT_GRAY};
        border-radius: .6rem;
        padding: .7rem .8rem;
        margin: .4rem 0 .8rem 0;
        box-shadow: 0 1px 4px rgba(15,23,42,.06);
    }}
    .domain-title {{
        color: {DARK_GRAY};
        font-weight: 700;
        margin-bottom: .2rem;
    }}
    .small-muted {{
        color: {GRAY};
        font-size: .9rem;
    }}
    .verdict-chip {{
        display:inline-block;
        padding:.18rem .5rem;
        border-radius:999px;
        font-weight:600;
        color:white;
    }}
    .verdict-pass {{ background:{SUCCESS_GREEN}; }}
    .verdict-warn {{ background:{WARNING_ORANGE}; }}
    .verdict-fail {{ background:{ERROR_RED}; }}
    .risk-box {{
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
        margin: 20px 0;
    }}
    .risk-low {{ background: {SUCCESS_GREEN}; }}
    .risk-medium {{ background: {WARNING_ORANGE}; }}
    .risk-high {{ background: {ERROR_RED}; }}
    .stat-box {{
        background: {SOFT_BG};
        border: 1px solid {LIGHT_GRAY};
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
    }}
    .stat-number {{
        font-size: 2rem;
        font-weight: bold;
        color: {DARK_GRAY};
    }}
    .stat-label {{
        font-size: 0.9rem;
        color: {GRAY};
    }}
</style>
""", unsafe_allow_html=True)

# ================================================================================================
# REAL NPC DATA (CITED SOURCES)
# ================================================================================================
NPC_INSIGHTS = {
    "total_breaches_reported": "6,847,611,386",
    "breach_period": "2018-2023",
    "ph_email_breaches_2023": "705,470",
    "lifetime_breaches": "124 million",
    "trust_rating": "36%",
    "believe_data_will_leak": "64%",
    "sources": [
        "NPC Data Breach Notification Monitoring System (2024)",
        "Surfshark Data Breach Statistics (2023)",
        "Inquiro.ph Comparative Analysis (2025)"
    ]
}


# ================================================================================================
# LOAD FUNCTIONS
# ================================================================================================
@st.cache_data
def load_questions(path: str = "questions_ph.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_image(path: str) -> Optional[Image.Image]:
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGBA")
        except:
            return None
    return None


qdata = load_questions()
logo = load_image("logo.png")
sns.set_theme(style="whitegrid", font_scale=0.9)

# ================================================================================================
# SIDEBAR
# ================================================================================================
with st.sidebar:
    if logo is not None:
        st.image(logo, use_container_width=True)

    st.header("⚙️ Assessment Options")
    org_name = st.text_input("**Company Name (required)**", placeholder="e.g., ACME Corp")
    assessor = st.text_input("**Assessor (required)**", placeholder="Your name")
    today = st.date_input("Date", value=dt.date.today())

    with st.expander("📊 Scoring Settings"):
        show_na = st.toggle("Allow N/A", value=True)
        weight_critical = st.slider("Critical weight ×", 1.0, 2.0, 1.3, 0.1)
        st.help("Critical controls weighted more heavily")
        colA, colB = st.columns(2)
        with colA:
            pass_thr = st.slider("PASS ≥", 60, 100, 85, 1)
        with colB:
            improve_thr = st.slider("Improve ≥", 40, 95, 60, 1)

    st.divider()

    st.subheader("💾 Save/Load Progress")
    if st.button("📥 Save Progress", use_container_width=True):
        if org_name and assessor:
            progress_data = {
                "org_name": org_name,
                "assessor": assessor,
                "date": today.isoformat(),
                "answers": st.session_state.answers,
                "idx": st.session_state.idx,
                "version": "1.0"
            }
            json_str = json.dumps(progress_data, indent=2)
            st.download_button("⬇️ Download Progress", data=json_str,
                               file_name=f"progress_{org_name.replace(' ', '_')}.json",
                               mime="application/json", use_container_width=True)
        else:
            st.warning("Fill Company Name first")

    uploaded_file = st.file_uploader("📤 Load Previous Progress", type="json")
    if uploaded_file:
        try:
            progress_data = json.load(uploaded_file)
            st.session_state.answers = progress_data["answers"]
            st.session_state.idx = progress_data["idx"]
            st.success("✅ Progress loaded!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    with st.expander("✍️ Signatures (optional)"):
        sig_company_file = st.file_uploader("Company signature", type=["png", "jpg", "jpeg"])
        sig_assessor_file = st.file_uploader("Assessor signature", type=["png", "jpg", "jpeg"])

    sig_company_img = Image.open(sig_company_file).convert("RGBA") if sig_company_file else None
    sig_assessor_img = Image.open(sig_assessor_file).convert("RGBA") if sig_assessor_file else None

# ================================================================================================
# MAIN NAVIGATION
# ================================================================================================
st.title("🔐 PH Cybersecurity & Data Privacy Posture")
st.caption("Free compliance assessment tool | Developed by CyberPH")

tab_overview, tab_questions, tab_results, tab_resources = st.tabs(
    ["📋 Overview", "❓ Questions", "📊 Results", "📚 Resources"]
)


# ================================================================================================
# HELPER FUNCTIONS
# ================================================================================================
def verdict_text_color(score: float, pass_t: int, improve_t: int) -> Tuple[str, str]:
    if score >= pass_t:
        return "PASS", "verdict-pass"
    elif score >= improve_t:
        return "NEEDS IMPROVEMENT", "verdict-warn"
    return "FAIL", "verdict-fail"


def calculate_risk_level(overall_score: float, critical_failures: int) -> Tuple[str, str]:
    if overall_score >= 85 and critical_failures == 0:
        return "LOW", "risk-low"
    elif overall_score >= 60 and critical_failures <= 2:
        return "MEDIUM", "risk-medium"
    else:
        return "HIGH", "risk-high"


def ensure_state():
    if "q_list" not in st.session_state:
        q_list = []
        for domain in qdata["domains"]:
            for q in domain["questions"]:
                q_list.append({
                    "id": q["id"],
                    "domain": domain["name"],
                    "desc": domain.get("desc", ""),
                    "text": q["text"],
                    "ref": q.get("ref", []),
                    "weight": q.get("weight", 1.0),
                    "critical": q.get("critical", False),
                    "tip": q.get("tip", ""),
                    "control": q.get("control", "")
                })
        st.session_state.q_list = q_list
        st.session_state.answers = {q["id"]: None for q in q_list}
        st.session_state.idx = 0


ensure_state()


# ================================================================================================
# SOCIAL SHARING - BADGE GENERATOR
# ================================================================================================
def generate_share_badge(org: str, score: float, date_str: str) -> bytes:
    """Generate professional branded badge with LARGER text for social media."""
    width, height = 1200, 630
    
    # Create base with gradient
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # Gradient background (green)
    for y in range(height):
        ratio = y / height
        r = int(16 + (10 - 16) * ratio)
        g = int(185 + (150 - 185) * ratio)
        b = int(129 + (100 - 129) * ratio)
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Load logo (if exists)
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            logo_ratio = logo_img.width / logo_img.height
            logo_width = 200
            logo_height = int(logo_width / logo_ratio)
            logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            img.paste(logo_img, (50, 40), logo_img)
        except:
            pass
    
    # Load fonts with BIGGER sizes
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)  # Increased from 65
        subtitle_font = ImageFont.truetype("arial.ttf", 52)  # Increased from 48
        score_font = ImageFont.truetype("arialbd.ttf", 160)  # Increased from 140
        org_font = ImageFont.truetype("arialbd.ttf", 48)  # Increased from 42, made bold
        caption_font = ImageFont.truetype("arial.ttf", 32)  # Increased from 28
        brand_font = ImageFont.truetype("arialbd.ttf", 36)  # Increased from 32
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        score_font = ImageFont.load_default()
        org_font = ImageFont.load_default()
        caption_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()
    
    # Main title
    title_text = "🎉 ACHIEVED"
    draw.text((600, 110), title_text, anchor="mm", fill="white", font=title_font)
    
    # Subtitle
    subtitle_text = "PH Data Privacy Compliance"
    draw.text((600, 185), subtitle_text, anchor="mm", fill="white", font=subtitle_font)
    
    # Score (large)
    score_text = f"{score:.1f}%"
    draw.text((600, 310), score_text, anchor="mm", fill="white", font=score_font)
    
    # Organization name (BOLD and BIGGER)
    org_text = org if len(org) <= 35 else org[:32] + "..."
    draw.text((600, 420), org_text, anchor="mm", fill="white", font=org_font)
    
    # Date (BIGGER)
    info_text = f"Assessed: {date_str}"
    draw.text((600, 480), info_text, anchor="mm", fill="white", font=caption_font)
    
    # Branding footer
    footer_overlay = Image.new('RGBA', (width, 90), (0, 0, 0, 180))
    img.paste(footer_overlay, (0, height - 90), footer_overlay)
    
    # CyberPH branding
    brand_text = "CyberPH"
    draw.text((100, height - 55), brand_text, anchor="lm", fill="white", font=brand_font)
    
    # Tagline
    tagline_text = "Free PH Cybersecurity & Data Privacy Assessment"
    draw.text((100, height - 25), tagline_text, anchor="lm", fill="white", font=caption_font)
    
    # Social handle
    social_text = "fb.com/LearnCyberPH"
    draw.text((width - 100, height - 40), social_text, anchor="rm", fill="white", font=caption_font)
    
    # Checkmark decoration
    circle_x, circle_y = width - 150, 100
    circle_radius = 60
    draw.ellipse([circle_x - circle_radius, circle_y - circle_radius,
                  circle_x + circle_radius, circle_y + circle_radius],
                 fill=(255, 255, 255, 200), outline="white", width=4)
    
    check_points = [
        (circle_x - 20, circle_y),
        (circle_x - 5, circle_y + 15),
        (circle_x + 20, circle_y - 20)
    ]
    draw.line(check_points, fill=(16, 185, 129), width=8, joint="curve")
    
    # Save
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return buf.getvalue()


# ================================================================================================
# PDF HELPER FUNCTIONS
# ================================================================================================
def pdf_color(hexcode: str):
    hexcode = hexcode.lstrip("#")
    r, g, b = int(hexcode[0:2], 16), int(hexcode[2:4], 16), int(hexcode[4:6], 16)
    return (r / 255.0, g / 255.0, b / 255.0)


def add_image_fit(page, img_bytes, x0, y0, x1, y1):
    rect = fitz.Rect(x0, y0, x1, y1)
    page.insert_image(rect, stream=img_bytes, keep_proportion=True)


def add_footer(page, page_num, total_pages, date_str, is_last_page=False, margin=35):
    footer_y = page.rect.height - 25
    if is_last_page:
        cyberph_text = "Developed by CyberPH | fb.com/LearnCyberPH"
        cyberph_width = fitz.get_text_length(cyberph_text, fontname='helv', fontsize=6)
        page.insert_text(((page.rect.width - cyberph_width) / 2, footer_y), cyberph_text,
                         fontsize=6, fontname='helv', color=pdf_color(GRAY))
    page_text = f"Page {page_num} of {total_pages}"
    text_width = fitz.get_text_length(page_text, fontname='helv', fontsize=8)
    page.insert_text(((page.rect.width - text_width) / 2, footer_y + 12), page_text,
                     fontsize=8, fontname='helv', color=pdf_color(GRAY))


def add_section_divider(page, y, title, margin=35):
    page.insert_text((margin, y + 15), title, fontsize=12, fontname='hebo', color=pdf_color(DARK_GRAY))
    return y + 25


def write_table_row(page, y, widths, contents, height=55, header=False, zebra=False, margin=35):
    x = margin
    if header:
        fill_color = pdf_color(DARK_GRAY)
        text_color = (1, 1, 1)
        font_name = 'hebo'
        font_size = 10
    else:
        fill_color = pdf_color(SOFT_BG if zebra else WHITE)
        text_color = pdf_color(DARK_GRAY)
        font_name = 'helv'
        font_size = 9

    for i, (w, text) in enumerate(zip(widths, contents)):
        rect = fitz.Rect(x, y, x + w, y + height)
        page.draw_rect(rect, fill=fill_color, color=pdf_color(BORDER_COLOR), width=0.3)
        text_rect = fitz.Rect(x + 6, y + 6, x + w - 6, y + height - 6)
        page.insert_textbox(text_rect, str(text), fontsize=font_size, fontname=font_name,
                            color=text_color, align=fitz.TEXT_ALIGN_LEFT)
        x += w
    return y + height


def new_page_with_header(doc, title: str, logo_img=None, margin=35):
    p = doc.new_page()
    p.draw_rect(fitz.Rect(0, 0, p.rect.width, 70), fill=pdf_color(DARK_GRAY))
    if logo_img:
        try:
            b = io.BytesIO()
            logo_img.save(b, format='PNG')
            add_image_fit(p, b.getvalue(), margin, 12, margin + 100, 58)
            logo_width = 110
        except:
            logo_width = 0
    else:
        logo_width = 0
    p.insert_text((margin + logo_width + 10, 42), title, fontsize=16, fontname='hebo', color=(1, 1, 1))
    return p


def create_cover_page(doc, org: str, assessor_name: str, date_str: str, logo_img, margin=35):
    p = doc.new_page()
    page_width = p.rect.width
    page_height = p.rect.height
    p.draw_rect(fitz.Rect(0, 0, page_width, 200), fill=pdf_color(DARK_GRAY))
    if logo_img:
        try:
            b = io.BytesIO()
            logo_img.save(b, format='PNG')
            logo_x = (page_width - 200) / 2
            add_image_fit(p, b.getvalue(), logo_x, 50, logo_x + 200, 130)
        except:
            pass
    title_y = 280
    title_text = "Cybersecurity & Data Privacy"
    title_width = fitz.get_text_length(title_text, fontname='hebo', fontsize=24)
    p.insert_text(((page_width - title_width) / 2, title_y), title_text, fontsize=24, fontname='hebo',
                  color=pdf_color(DARK_GRAY))
    subtitle_text = "Posture Assessment Report"
    subtitle_width = fitz.get_text_length(subtitle_text, fontname='hebo', fontsize=24)
    p.insert_text(((page_width - subtitle_width) / 2, title_y + 30), subtitle_text, fontsize=24, fontname='hebo',
                  color=pdf_color(DARK_GRAY))
    info_y = 400
    info_box = fitz.Rect(margin + 50, info_y, page_width - margin - 50, info_y + 120)
    p.draw_rect(info_box, color=pdf_color(LIGHT_GRAY), width=1.5)
    p.insert_text((margin + 70, info_y + 35), "Organization:", fontsize=10, fontname='hebo', color=pdf_color(GRAY))
    p.insert_text((margin + 70, info_y + 55), org, fontsize=14, fontname='hebo', color=pdf_color(DARK_GRAY))
    p.insert_text((margin + 70, info_y + 80), f"Date: {date_str}", fontsize=10, fontname='helv', color=pdf_color(GRAY))
    p.insert_text((margin + 70, info_y + 100), f"Assessor: {assessor_name}", fontsize=10, fontname='helv',
                  color=pdf_color(GRAY))
    return p


def add_verdict_box(page, y, verdict, score, margin=35):
    """FIXED: Adaptive width for long verdict text"""
    colors = {"PASS": SUCCESS_GREEN, "NEEDS IMPROVEMENT": WARNING_ORANGE, "FAIL": ERROR_RED}
    color = colors.get(verdict, GRAY)

    text = f"{verdict}: {score:.1f}%"
    text_width = fitz.get_text_length(text, fontname='hebo', fontsize=14)
    box_width = max(250, text_width + 60)

    verdict_rect = fitz.Rect(margin, y, margin + box_width, y + 40)
    shadow_rect = fitz.Rect(margin + 2, y + 2, margin + box_width + 2, y + 42)

    page.draw_rect(shadow_rect, fill=pdf_color(BORDER_COLOR))
    page.draw_rect(verdict_rect, fill=pdf_color(color))
    page.insert_text((margin + 15, y + 25), text, fontsize=14, fontname='hebo', color=(1, 1, 1))

    return y + 50


def add_signature_box(page, y, label, sig_img=None, margin=35):
    box_width, box_height = 240, 90
    sig_rect = fitz.Rect(margin, y, margin + box_width, y + box_height)
    page.draw_rect(sig_rect, fill=pdf_color(WHITE), color=pdf_color(GRAY), width=1.5)
    if sig_img:
        try:
            b = io.BytesIO()
            sig_img.save(b, format='PNG')
            add_image_fit(page, b.getvalue(), margin + 10, y + 10, margin + box_width - 10, y + box_height - 25)
        except:
            pass
    page.insert_text((margin + 10, y + box_height - 8), label, fontsize=8, fontname='helv', color=pdf_color(GRAY))
    return y + box_height + 15


# ================================================================================================
# ACTION CHECKLIST PDF - FIXED DOMAIN POPULATION
# ================================================================================================
def generate_action_checklist(improvements, org: str, date_str: str):
    """Final bulletproof version with manual text wrapping"""
    doc = fitz.open()
    p = doc.new_page(width=612, height=792)
    margin = 40
    y = 40

    # Header
    p.draw_rect(fitz.Rect(0, 0, 612, 80), fill=pdf_color(DARK_GRAY))
    p.insert_text((margin, 35), "COMPLIANCE ACTION CHECKLIST",
                  fontsize=18, fontname='hebo', color=(1, 1, 1))
    p.insert_text((margin, 55), f"{org} | {date_str}",
                  fontsize=10, fontname='helv', color=(1, 1, 1))
    y = 100

    p.insert_text((margin, y), "Track compliance improvements:",
                  fontsize=9, fontname='hebo', color=pdf_color(DARK_GRAY))
    y += 20

    # Table setup - Fixed widths
    col_widths = [22, 88, 295, 75]
    x = margin
    header_y = y

    # Draw header
    p.draw_rect(fitz.Rect(x, header_y, x + sum(col_widths), header_y + 25),
                fill=pdf_color(DARK_GRAY))

    headers = ["✓", "Domain", "Action Required", "Timeline"]
    x_pos = x
    for width, text in zip(col_widths, headers):
        p.insert_text((x_pos + 3, header_y + 15), text, fontsize=7.5,
                      fontname='hebo', color=(1, 1, 1))
        x_pos += width

    y = header_y + 25

    # Helper function to wrap text manually
    def wrap_text(text, max_width, fontsize=6.5, fontname='helv'):
        """Manually wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width = fitz.get_text_length(test_line, fontname=fontname, fontsize=fontsize)

            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    # Process improvements
    zebra = False
    items_processed = 0

    for imp in improvements:
        # Extract domain
        domain_text = None
        if isinstance(imp, dict) and 'domain' in imp and imp['domain']:
            raw_domain = str(imp['domain'])
            domain_text = raw_domain.split('(')[0].strip()

            # Shorten common names
            replacements = {
                "Governance & Compliance": "Governance",
                "Privacy Impact Assessment": "Privacy Impact",
                "Data Subject Rights": "Data Subject",
                "Security Measures": "Security",
                "Breach Management": "Breach Mgmt",
                "Physical & Organizational": "Physical/Org"
            }
            for old, new in replacements.items():
                if old in domain_text:
                    domain_text = new
                    break

        if not domain_text:
            qid = str(imp.get('id', '')).lower()
            if 'pia' in qid:
                domain_text = "Privacy Impact"
            elif any(x in qid for x in ['gov', 'dpo', 'pmp']):
                domain_text = "Governance"
            elif 'dsr' in qid:
                domain_text = "Data Subject"
            elif any(x in qid for x in ['sec', 'mfa', 'encrypt', 'access', 'policy', 'train']):
                domain_text = "Security"
            elif any(x in qid for x in ['breach', 'incident']):
                domain_text = "Breach Mgmt"
            elif any(x in qid for x in ['phys', 'org', 'ret', 'disposal', 'asset', 'log']):
                domain_text = "Physical/Org"
            elif 'vuln' in qid or 'cyber' in qid:
                domain_text = "Cybersecurity"
            else:
                domain_text = "Compliance"

        if not domain_text:
            domain_text = "N/A"

        # Extract action
        tip_text = str(imp.get('tip', imp.get('text', 'Complete requirement')))

        # Wrap domain text (max 2 lines)
        domain_lines = wrap_text(domain_text, col_widths[1] - 6, fontsize=6.5, fontname='hebo')[:2]

        # Wrap action text (max 5 lines)
        action_lines = wrap_text(tip_text, col_widths[2] - 6, fontsize=6.5, fontname='helv')[:5]

        # Calculate row height based on max lines
        max_lines = max(len(domain_lines), len(action_lines), 2)
        action_row_height = max(max_lines * 9 + 6, 30)
        comments_height = 26
        total_height = action_row_height + comments_height + 2

        # Page break check
        if y + total_height > 742:
            p = doc.new_page(width=612, height=792)
            y = 40
            zebra = False

        # Draw row background
        fill_color = pdf_color(SOFT_BG if zebra else WHITE)
        row_rect = fitz.Rect(x, y, x + sum(col_widths), y + action_row_height)
        p.draw_rect(row_rect, fill=fill_color, color=pdf_color(BORDER_COLOR), width=0.4)

        # Draw vertical separators
        sep_positions = [x + col_widths[0],
                         x + col_widths[0] + col_widths[1],
                         x + col_widths[0] + col_widths[1] + col_widths[2]]

        for sep_x in sep_positions:
            p.draw_line((sep_x, y), (sep_x, y + action_row_height),
                        color=pdf_color(BORDER_COLOR), width=0.4)

        # Checkbox
        p.insert_text((x + 7, y + (action_row_height / 2) + 2), "[ ]",
                      fontsize=8, fontname='helv', color=pdf_color(DARK_GRAY))

        # Domain - FIXED: Direct text insertion with manual wrapping
        domain_x = x + col_widths[0] + 3
        domain_y_start = y + 10
        for i, line in enumerate(domain_lines):
            p.insert_text((domain_x, domain_y_start + (i * 8)), line,
                          fontsize=6.5, fontname='hebo', color=pdf_color(DARK_GRAY))

        # Action - FIXED: Direct text insertion with manual wrapping
        action_x = x + col_widths[0] + col_widths[1] + 3
        action_y_start = y + 10
        for i, line in enumerate(action_lines):
            p.insert_text((action_x, action_y_start + (i * 8)), line,
                          fontsize=6.5, fontname='helv', color=pdf_color(DARK_GRAY))

        # Timeline box
        time_rect = fitz.Rect(x + col_widths[0] + col_widths[1] + col_widths[2] + 2,
                              y + 2, x + sum(col_widths) - 2, y + action_row_height - 2)
        p.draw_rect(time_rect, color=pdf_color(BORDER_COLOR), width=0.3)

        y += action_row_height

        # Comments row
        comments_fill = pdf_color("#FAFAFA" if zebra else "#F5F5F5")
        comments_rect = fitz.Rect(x, y, x + sum(col_widths), y + comments_height)
        p.draw_rect(comments_rect, fill=comments_fill, color=pdf_color(BORDER_COLOR), width=0.4)

        p.draw_line((sep_positions[0], y), (sep_positions[0], y + comments_height),
                    color=pdf_color(BORDER_COLOR), width=0.4)

        p.insert_text((x + col_widths[0] + 3, y + 8), "Comments:",
                      fontsize=6, fontname='hebo', color=pdf_color(GRAY))

        line_x1 = x + col_widths[0] + 2
        line_x2 = x + sum(col_widths) - 2
        p.draw_line((line_x1, y + 14), (line_x2, y + 14),
                    color=pdf_color(LIGHT_GRAY), width=0.2)
        p.draw_line((line_x1, y + 20), (line_x2, y + 20),
                    color=pdf_color(LIGHT_GRAY), width=0.2)

        y += comments_height + 2
        zebra = not zebra
        items_processed += 1

    # Footer
    p.insert_text((margin, 770), f"CyberPH | {items_processed} actions | fb.com/LearnCyberPH",
                  fontsize=6, fontname='helv', color=pdf_color(GRAY))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ================================================================================================
# FULL PDF GENERATION
# ================================================================================================
def generate_pdf(org, assessor_name, date_str, q_list, answers, pass_threshold, improve_threshold,
                 weight_crit, verdict, overall_score, domain_scores, improvements, logo_img,
                 sig_company, sig_assessor, fig_overall, fig_domain):
    doc = fitz.open()
    margin = 35
    page_numbers = []

    total_controls = len(q_list)
    critical_controls = sum(1 for q in q_list if q["critical"])
    compliant = len([q for q in q_list if answers[q["id"]] == "Yes"])
    non_compliant = len([q for q in q_list if answers[q["id"]] == "No"])

    # Cover
    create_cover_page(doc, org, assessor_name, date_str, logo_img, margin)
    page_numbers.append(None)

    # Executive Summary
    p = new_page_with_header(doc, "Executive Summary", logo_img, margin)
    page_numbers.append(1)
    y = 90

    y = add_section_divider(p, y, "Assessment Overview", margin)

    box_width, box_height = 130, 70
    boxes = [
        (f"{overall_score:.1f}%", "Overall", SUCCESS_GREEN if verdict == "PASS" else WARNING_ORANGE),
        (f"{total_controls}", "Total Controls", SOFT_BG),
        (f"{critical_controls}", "Critical", SOFT_BG)
    ]

    x_offset = margin
    for val, label, color in boxes:
        box_rect = fitz.Rect(x_offset, y, x_offset + box_width, y + box_height)
        p.draw_rect(box_rect, fill=pdf_color(color), color=pdf_color(BORDER_COLOR), width=1)
        text_color = (1, 1, 1) if color in [SUCCESS_GREEN, WARNING_ORANGE] else pdf_color(DARK_GRAY)
        p.insert_text((x_offset + 15, y + 30), label, fontsize=9, fontname='helv', color=text_color)
        p.insert_text((x_offset + 15, y + 52), val, fontsize=18, fontname='hebo', color=text_color)
        x_offset += box_width + 15

    y += box_height + 25

    y = add_section_divider(p, y, "Compliance Status", margin)
    status_text = f"Compliant: {compliant} ({(compliant / total_controls * 100):.1f}%)\n"
    status_text += f"Non-Compliant: {non_compliant} ({(non_compliant / total_controls * 100):.1f}%)\n"
    status_text += f"Verdict: {verdict}"
    p.insert_textbox(fitz.Rect(margin, y, p.rect.width - margin, y + 60), status_text,
                     fontsize=9, fontname='helv', color=pdf_color(DARK_GRAY))
    y += 70

    y = add_section_divider(p, y, "Scoring Methodology", margin)
    method_text = f"- Critical controls weighted x{weight_crit:.1f}\n"
    method_text += f"- PASS threshold: >={pass_threshold}%\n"
    method_text += f"- NEEDS IMPROVEMENT: >={improve_threshold}%"
    p.insert_textbox(fitz.Rect(margin, y, p.rect.width - margin, y + 60), method_text,
                     fontsize=9, fontname='helv', color=pdf_color(GRAY))
    y += 70

    y = add_section_divider(p, y, "Key Findings", margin)
    weakest = sorted(domain_scores.items(), key=lambda x: x[1])[:3]
    findings_text = "Priority Areas:\n"
    for i, (dom, score) in enumerate(weakest, 1):
        findings_text += f"{i}. {dom}: {score:.1f}%\n"
    p.insert_textbox(fitz.Rect(margin, y, p.rect.width - margin, y + 70), findings_text,
                     fontsize=9, fontname='helv', color=pdf_color(DARK_GRAY))

    # Results Page
    p = new_page_with_header(doc, "Results", logo_img, margin)
    page_numbers.append(2)
    y = 90

    y = add_section_divider(p, y, "Overall Result", margin)
    y = add_verdict_box(p, y, verdict, overall_score, margin)

    if fig_overall or fig_domain:
        y = add_section_divider(p, y, "Visual Summary", margin)
        chart_y = y

        if fig_overall and fig_domain:
            chart_width = 220
            if fig_overall:
                p.draw_rect(fitz.Rect(margin, chart_y, margin + chart_width, chart_y + chart_width),
                            color=pdf_color(LIGHT_GRAY), width=0.3)
                add_image_fit(p, fig_overall, margin + 3, chart_y + 3, margin + chart_width - 3,
                              chart_y + chart_width - 3)
                p.insert_text((margin, chart_y + chart_width + 12), "Overall Score",
                              fontsize=8, fontname='helv', color=pdf_color(GRAY))

            if fig_domain:
                x_offset = margin + chart_width + 25
                p.draw_rect(fitz.Rect(x_offset, chart_y, x_offset + chart_width, chart_y + chart_width),
                            color=pdf_color(LIGHT_GRAY), width=0.3)
                add_image_fit(p, fig_domain, x_offset + 3, chart_y + 3, x_offset + chart_width - 3,
                              chart_y + chart_width - 3)
                p.insert_text((x_offset, chart_y + chart_width + 12), "Domain Scores",
                              fontsize=8, fontname='helv', color=pdf_color(GRAY))
            y = chart_y + chart_width + 30

    # Domain Scores
    p = new_page_with_header(doc, "Domain Breakdown", logo_img, margin)
    page_numbers.append(3)
    y = 90

    y = add_section_divider(p, y, "Scores by Domain", margin)
    col_widths = [280, 80, 80]
    y = write_table_row(p, y, col_widths, ["Domain", "Score (%)", "Status"], height=45, header=True, margin=margin)

    zebra = False
    for domain_name, dscore in sorted(domain_scores.items(), key=lambda x: x[1]):
        status = "PASS" if dscore >= pass_threshold else "IMPROVE" if dscore >= improve_threshold else "FAIL"
        y = write_table_row(p, y, col_widths, [domain_name, f"{dscore:.1f}", status], height=50, zebra=zebra,
                            margin=margin)
        zebra = not zebra
        if y > p.rect.height - 100:
            p = new_page_with_header(doc, "Domain Breakdown (cont.)", logo_img, margin)
            page_numbers.append(len(page_numbers))
            y = 90

    # Improvements
    if improvements:
        p = new_page_with_header(doc, "Recommended Improvements", logo_img, margin)
        page_numbers.append(len(page_numbers))
        y = 90

        y = add_section_divider(p, y, "Priority Actions", margin)
        col_widths = [35, 165, 240]
        y = write_table_row(p, y, col_widths, ["ID", "Domain", "Action"], height=45, header=True, margin=margin)

        zebra = False
        for imp in improvements:
            qid = imp["id"]
            domain = imp["domain"]
            rec = imp.get("tip", imp["text"])
            rec_short = rec[:350] + "..." if len(rec) > 350 else rec
            y = write_table_row(p, y, col_widths, [qid, domain, rec_short], height=95, zebra=zebra, margin=margin)
            zebra = not zebra
            if y > p.rect.height - 120:
                p = new_page_with_header(doc, "Improvements (cont.)", logo_img, margin)
                page_numbers.append(len(page_numbers))
                y = 90
                y = write_table_row(p, y, col_widths, ["ID", "Domain", "Action"], height=45, header=True, margin=margin)

    # Signatures
    if y > p.rect.height - 250:
        p = new_page_with_header(doc, "Approvals", logo_img, margin)
        page_numbers.append(len(page_numbers))
        y = 90

    y = add_section_divider(p, y, "Signatures", margin)
    y_sig = y
    add_signature_box(p, y_sig, f"{org} Rep", sig_company, margin)
    add_signature_box(p, y_sig, f"Assessor: {assessor_name}", sig_assessor, margin + 280)

    # Footers
    total_numbered = len([p for p in page_numbers if p is not None])
    for i, page in enumerate(doc):
        if page_numbers[i] is not None:
            add_footer(page, page_numbers[i], total_numbered, date_str, page_numbers[i] == total_numbered, margin)

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ================================================================================================
# OVERVIEW TAB
# ================================================================================================
with tab_overview:
    col1, col2 = st.columns([1, 2])

    with col1:
        if logo is not None:
            st.image(logo, use_container_width=True)

    with col2:
        st.markdown("""
<div class="card">
<div class="domain-title">🎯 About This Tool</div>
<div class="small-muted">
Free assessment for <b>Philippine Data Privacy Act (R.A. 10173)</b>, 
<b>NPC Circulars</b>, and <b>NIST CSF 2.0</b>. Guidance only, not legal advice.
</div>
</div>
        """, unsafe_allow_html=True)

    st.markdown("### 🚀 How to Use")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### Step 1: Setup
        - Fill company details
        - Adjust thresholds
        - Upload signatures
        """)

    with col2:
        st.markdown("""
        #### Step 2: Assess
        - Answer 17 questions
        - Use implementation tips
        - Save progress anytime
        """)

    with col3:
        st.markdown("""
        #### Step 3: Report
        - View scores & risk
        - Download professional PDF
        - Get actionable steps
        """)

    st.divider()

    st.markdown("### 📊 PH Data Privacy Landscape")
    st.info(f"""
    **NPC Official Data:**
    - **{NPC_INSIGHTS['total_breaches_reported']}** incidents ({NPC_INSIGHTS['breach_period']})
    - **{NPC_INSIGHTS['trust_rating']}** trust in data protection
    - **{NPC_INSIGHTS['believe_data_will_leak']}** expect data leakage

    Sources: {', '.join(NPC_INSIGHTS['sources'][:2])}
    """)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{NPC_INSIGHTS['trust_rating']}</div>
            <div class="stat-label">Trust Rating</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{NPC_INSIGHTS['believe_data_will_leak']}</div>
            <div class="stat-label">Expect Leakage</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-number">6.8B+</div>
            <div class="stat-label">Incidents</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-number">5M₱</div>
            <div class="stat-label">Max Fine</div>
        </div>
        """, unsafe_allow_html=True)

# ================================================================================================
# QUESTIONS TAB
# ================================================================================================
with tab_questions:
    q_list = st.session_state.q_list
    answers = st.session_state.answers
    idx = st.session_state.idx
    total = len(q_list)

    # Progress indicator
    progress = (idx + 1) / total
    st.progress(progress)
    st.caption(f"Question **{idx + 1}** of **{total}** ({progress * 100:.0f}% complete)")

    if idx < total:
        q = q_list[idx]

        # Domain card (unchanged - working fine)
        st.markdown(f"""
<div style="background: linear-gradient(135deg, {DARK_GRAY} 0%, #374151 100%); border-left: 4px solid {SUCCESS_GREEN}; border-radius: 8px; padding: 16px 20px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <div style="color: {SUCCESS_GREEN}; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">📂 {html.escape(q['domain'])}</div>
    <div style="color: {LIGHT_GRAY}; font-size: 0.9rem; line-height: 1.4;">{html.escape(q.get('desc', ''))}</div>
</div>
        """, unsafe_allow_html=True)

        # FIXED: Question card with proper critical badge placement
        if q["critical"]:
            # Show critical badge ABOVE the question
            st.markdown(f"""
<div style="margin: 20px 0 -10px 0;">
    <span style="background: {ERROR_RED}; color: white; padding: 6px 14px; border-radius: 16px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; display: inline-block;">
        🔴 CRITICAL CONTROL
    </span>
</div>
            """, unsafe_allow_html=True)

        # Question card
        st.markdown(f"""
<div style="background: white; border: 2px solid {SUCCESS_GREEN}; border-radius: 12px; padding: 24px; margin: 12px 0 24px 0; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);">
    <span style="background: {SUCCESS_GREEN}; color: white; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; display: inline-block; margin-bottom: 12px;">Q{idx + 1}</span>
    <div style="color: {DARK_GRAY}; font-size: 1.2rem; font-weight: 600; line-height: 1.7;">
        {html.escape(q['text'])}
    </div>
</div>
        """, unsafe_allow_html=True)

        # Tip and References
        col1, col2 = st.columns([2, 1])

        with col1:
            if q.get("tip"):
                with st.expander("💡 Implementation Tip"):
                    st.info(q["tip"])

        with col2:
            if q.get("ref"):
                with st.expander("📚 References"):
                    for r in q["ref"]:
                        st.caption(f"• {r}")

        st.markdown("---")

        # Answer section
        st.subheader("Your Answer")

        options = ["Yes", "No"]
        if show_na:
            options.append("N/A")

        current_ans = answers[q["id"]]
        sel_idx = 0 if current_ans == "Yes" else 1 if current_ans == "No" else 2 if current_ans == "N/A" else 0

        choice = st.radio(
            "Select compliance status:",
            options,
            index=sel_idx,
            horizontal=True,
            key=f"radio_{q['id']}",
            help="Select Yes if compliant, No if not compliant, or N/A if not applicable"
        )
        answers[q["id"]] = choice

        st.markdown("---")

        # Navigation buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button("◀ Previous", disabled=(idx == 0), use_container_width=True):
                st.session_state.idx = max(0, idx - 1)
                st.rerun()

        with col2:
            if idx == total - 1:
                if st.button("✓ Finish Assessment", use_container_width=True, type="primary"):
                    st.success("✅ Assessment Complete! Go to **Results** tab.")
                    st.balloons()
            else:
                if st.button("Next ▶", use_container_width=True, type="primary"):
                    st.session_state.idx = min(total - 1, idx + 1)
                    st.rerun()

# ================================================================================================
# RESULTS TAB
# ================================================================================================
with tab_results:
    answers = st.session_state.answers
    q_list = st.session_state.q_list

    if not org_name or not assessor:
        st.warning("⚠️ Fill **Company Name** and **Assessor** in sidebar first.")
        st.stop()

    answered = [a for a in answers.values() if a]
    if len(answered) < len(q_list):
        st.info(f"📝 Answered **{len(answered)}**/**{len(q_list)}** questions.")
        st.stop()

    # Calculate scores
    domain_scores = {}
    domain_weights = {}
    domain_earned = {}

    for q in q_list:
        dom = q["domain"]
        ans = answers[q["id"]]
        w = q["weight"]
        if q["critical"]:
            w *= weight_critical

        if dom not in domain_scores:
            domain_scores[dom] = 0.0
            domain_weights[dom] = 0.0
            domain_earned[dom] = 0.0

        if ans == "Yes":
            domain_earned[dom] += w
        domain_weights[dom] += w

    for dom in domain_scores:
        if domain_weights[dom] > 0:
            domain_scores[dom] = 100.0 * domain_earned[dom] / domain_weights[dom]

    total_weight = sum(domain_weights.values())
    total_earned = sum(domain_earned.values())
    overall_score = 100.0 * total_earned / total_weight if total_weight > 0 else 0.0
    verdict, vclass = verdict_text_color(overall_score, pass_thr, improve_thr)

    critical_failures = len([q for q in q_list if q["critical"] and answers[q["id"]] == "No"])
    risk_level, risk_class = calculate_risk_level(overall_score, critical_failures)

    # Display
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
<div class="card">
<div class="domain-title">Overall Score: {overall_score:.1f}%</div>
<span class="{vclass} verdict-chip">{verdict}</span>
</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
<div class="{risk_class} risk-box">
    <h3 style="margin:0;">Risk: {risk_level}</h3>
    <p style="margin:5px 0 0 0;font-size:0.9em;">{critical_failures} critical failure(s)</p>
</div>
        """, unsafe_allow_html=True)

    # Social Sharing
    if overall_score >= 85:
        st.balloons()
        st.success("🎉 Congratulations! You achieved PH Data Privacy Compliance!")

        badge_bytes = generate_share_badge(org_name, overall_score, today.strftime("%B %Y"))

        st.markdown("### 🔗 Share Your Achievement")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button("📥 Download Badge", data=badge_bytes,
                               file_name=f"badge_{org_name.replace(' ', '_')}.png",
                               mime="image/png", use_container_width=True)

        with col2:
            linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote('https://facebook.com/LearnCyberPH')}"
            st.markdown(
                f'<a href="{linkedin_url}" target="_blank"><button style="width:100%;padding:10px;background:#0077B5;color:white;border:none;border-radius:5px;">📱 LinkedIn</button></a>',
                unsafe_allow_html=True)

        with col3:
            facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote('https://facebook.com/LearnCyberPH')}"
            st.markdown(
                f'<a href="{facebook_url}" target="_blank"><button style="width:100%;padding:10px;background:#1877F2;color:white;border:none;border-radius:5px;">📘 Facebook</button></a>',
                unsafe_allow_html=True)

        st.caption("💡 Download badge and upload when sharing!")

    # Charts
    st.markdown("### 📊 Domain Performance")

    col1, col2 = st.columns(2)

    with col1:
        fig1, ax1 = plt.subplots(figsize=(5, 5))
        ax1.pie([overall_score, 100 - overall_score], labels=["Score", "Gap"],
                autopct='%1.1f%%', colors=[DARK_GRAY, LIGHT_GRAY], startangle=90)
        ax1.set_title(f"Overall: {overall_score:.1f}%")
        st.pyplot(fig1)
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format='png', dpi=150, bbox_inches='tight')
        buf1.seek(0)
        fig_overall_bytes = buf1.getvalue()
        plt.close(fig1)

    with col2:
        fig2, ax2 = plt.subplots(figsize=(10, 8))
        domains_sorted = sorted(domain_scores.items(), key=lambda x: x[1])
        ax2.barh([d[0] for d in domains_sorted], [d[1] for d in domains_sorted], color=DARK_GRAY)
        ax2.set_xlabel("Score (%)", fontsize=13)
        ax2.set_title("Domain Scores", fontsize=14)
        ax2.set_xlim(0, 100)
        ax2.tick_params(labelsize=11)
        plt.tight_layout()
        st.pyplot(fig2)
        buf2 = io.BytesIO()
        fig2.savefig(buf2, format='png', dpi=250, bbox_inches='tight')
        buf2.seek(0)
        fig_domain_bytes = buf2.getvalue()
        plt.close(fig2)

    # Improvements - FIXED: Ensure domain is included
    improvements = []
    for q in q_list:
        if answers[q["id"]] == "No":
            improvements.append({
                "id": q["id"],
                "domain": q["domain"],  # Explicitly include domain
                "text": q["text"],
                "tip": q.get("tip", ""),
                "control": q.get("control", "")
            })

    if improvements:
        st.markdown(f"### 🎯 {len(improvements)} Improvements Needed")
        for imp in improvements:
            with st.expander(f"{imp['id']} – {imp['domain']}"):
                if imp['tip']:
                    st.success(f"✅ **Action:** {imp['tip']}")
                if imp['control']:
                    st.info(f"📋 **Control:** {imp['control']}")

    # Reports
    st.markdown("---")
    st.markdown("### 📄 Download Reports")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Full PDF Report", type="primary", use_container_width=True):
            with st.spinner("Generating..."):
                pdf_bytes = generate_pdf(org_name, assessor, today.strftime("%Y-%m-%d"),
                                         q_list, answers, pass_thr, improve_thr, weight_critical,
                                         verdict, overall_score, domain_scores, improvements,
                                         logo, sig_company_img, sig_assessor_img,
                                         fig_overall_bytes, fig_domain_bytes)

                st.download_button("⬇️ Download PDF", data=pdf_bytes,
                                   file_name=f"Report_{org_name.replace(' ', '_')}.pdf",
                                   mime="application/pdf", use_container_width=True)
                st.success("✅ Generated!")

    with col2:
        if improvements and st.button("📋 Action Checklist", use_container_width=True):
            with st.spinner("Generating..."):
                checklist_bytes = generate_action_checklist(improvements, org_name, today.strftime("%Y-%m-%d"))

                st.download_button("⬇️ Download Checklist", data=checklist_bytes,
                                   file_name=f"Checklist_{org_name.replace(' ', '_')}.pdf",
                                   mime="application/pdf", use_container_width=True)
                st.success("✅ Generated!")

# ================================================================================================
# RESOURCES TAB
# ================================================================================================
with tab_resources:
    st.markdown("### 📚 Philippine Data Privacy Resources")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🇵🇭 Official NPC Resources
        - [National Privacy Commission](https://www.privacy.gov.ph)
        - [Data Privacy Act (R.A. 10173)](https://www.privacy.gov.ph/data-privacy-act/)
        - [NPC Circulars & Advisories](https://www.privacy.gov.ph/advisories/)
        - [DPO Registration Portal](https://npcregistration.privacy.gov.ph/login)
        - [Breach Notification System](https://privacy.gov.ph/dbnmslivestats/)
        """)

    with col2:
        st.markdown("""
        #### 🛡️ Standards & Frameworks
        - [NIST CSF 2.0](https://www.nist.gov/cyberframework)
        - [ISO 27001](https://www.iso.org/isoiec-27001-information-security.html)
        - [DICT NCSP](https://dict.gov.ph/cybersecurity/)
        """)

    st.divider()

    st.markdown("### ❓ Frequently Asked Questions")

    with st.expander("📊 How is the score calculated?"):
        st.markdown("Weighted average: Critical controls × 1.3x, Yes = full weight, No = 0, N/A excluded.")

    with st.expander("🔒 Is my data stored?"):
        st.markdown("No. All data stays in your browser. Use 'Save Progress' for local backup.")

    with st.expander("⏱️ How long does it take?"):
        st.markdown("10-15 minutes for quick assessment, 20-30 minutes for thorough review.")

    with st.expander("👥 Who should complete this?"):
        st.markdown("DPO, IT Manager, CISO, Compliance Officer, or Business Owner familiar with data practices.")

# ================================================================================================
# FOOTER
# ================================================================================================
st.divider()
st.caption("© 2025 CyberPH | fb.com/LearnCyberPH | Free Assessment Tool | Not legal advice")

# ================================================================================================
# END OF FILE
# ================================================================================================
