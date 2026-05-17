"""
Application configuration and constants.
"""
import os

# ─── Company Info ─────────────────────────────────────────────────────────────
COMPANY_NAME    = "MAJ GOLD"
COMPANY_TAGLINE = "Inventory Management System"
APP_VERSION     = "1.0.0"

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("MAJ_GOLD_DB", "maj_gold.db")

# ─── Window ───────────────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH  = 1280
WINDOW_MIN_HEIGHT = 800
WINDOW_TITLE      = f"{COMPANY_NAME} — {COMPANY_TAGLINE}"

# ─── Color Palette ────────────────────────────────────────────────────────────
COLORS = {
    "bg_darkest":   "#07090F",
    "bg":           "#0A0C14",
    "surface":      "#111827",
    "surface2":     "#1A2035",
    "surface3":     "#1F2B45",
    "border":       "#2A3347",
    "border_light": "#3A4560",
    "accent":       "#F5A623",
    "accent2":      "#E8C547",
    "accent_dim":   "#A67215",
    "text_primary": "#F0F4FF",
    "text_secondary":"#8A9BB5",
    "text_muted":   "#4A5568",
    "danger":       "#FF4757",
    "danger_dim":   "#7F2130",
    "success":      "#2ED573",
    "success_dim":  "#1A6A3A",
    "info":         "#1E90FF",
    "info_dim":     "#0E4A80",
    "warning":      "#FFB347",
    "purple":       "#A855F7",
}

# ─── Sidebar Navigation Items ─────────────────────────────────────────────────
# (label, icon_text, page_key)
NAV_ITEMS = [
    ("Dashboard",      "⬡",  "dashboard"),
    ("─────────────", None,  None),          # separator
    ("Daybook",        "📒", "daybook"),
    ("─────────────", None,  None),
    ("Masters",        "🗂", "masters"),
    ("Gold Receipts",  "🏅", "gold_receipt"),
    ("Melt Batches",   "🔥", "melt"),
    ("─────────────", None,  None),
    ("Gold Box",       "📦", "gold_box"),
    ("Wire & Sheet",   "🔗", "wire_sheet"),
    ("Goldsmith",      "⚒",  "goldsmith"),
    ("Polish",         "✨", "polish"),
    ("Faceting",       "💎", "faceting"),
    ("Kambi",          "🔩", "kambi"),
    ("─────────────", None,  None),
    ("Finished Stock", "🏺", "finished_stock"),
    ("Tot Stock",      "📊", "tot_stock"),
    ("Stock Summary",  "📈", "stock_summary"),
    ("─────────────", None,  None),
    ("Ledger",         "📜", "ledger"),
    ("V Account",      "🔐", "v_account"),
    ("GS-PCS Report",  "📋", "gs_pcs"),
]

# ─── Process Types ─────────────────────────────────────────────────────────────
PROCESS_TYPES = ["MELTING", "SCRAP_MELTING", "WIRE_SHEET", "GOLDSMITH",
                 "POLISH", "FACETING", "KAMBI", "HALLMARKING", "GOLD_BOX"]

STOCK_CATEGORIES = ["CHAIN_22K", "BOX_22K", "FACTORY_22K", "999", "995", "PURSE"]
MELT_TYPES       = ["NG_MELTING", "SCRAP_MELTING"]
PURITY_OPTIONS   = ["999", "9999", "995", "996", "916", "22K"]
