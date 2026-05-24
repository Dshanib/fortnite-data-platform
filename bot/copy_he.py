"""Hebrew UI copy for the Telegram bot."""

from __future__ import annotations

# ── תפריט ראשי ─────────────────────────────────────────────────
BTN_ACTIVITY_HUB = "📊 פעילות שחקנים"
BTN_TOP_ISLANDS = "🗺️ איים פעילים היום"
BTN_SHOP = "🛒 חנות לפי קטגוריה"
BTN_ANOMALIES = "⚠️ חריגות פעילות"
BTN_HELP = "💬 עזרה ומדריך"
BTN_HOME = "🏠 חזרה לתפריט"

# ── תת-תפריט פעילות ───────────────────────────────────────────
BTN_PLAYERS_NOW = "👥 כמה שחקנים היו היום?"
BTN_MOST_ACTIVE_ISLAND = "🥇 האי הכי פעיל עכשיו"
BTN_BACK_SHOP = "◀️ חזרה לקטגוריות"

LOADING = "רגע, טוען נתונים…"
UNKNOWN_ACTION = "לא הצלחנו לזהות את הבחירה. לחצו על «חזרה לתפריט»."

# ── מסך פתיחה ─────────────────────────────────────────────────
WELCOME_TITLE = "Fortnite — מרכז הנתונים"
WELCOME_BODY = (
    "שלום! 👋\n\n"
    "כאן אפשר לבדוק:\n"
    "• כמה שחקנים היו פעילים היום\n"
    "• מה האי הכי פעיל\n"
    "• אילו איים היו הכי פעילים היום\n"
    "• פריטים בחנות לפי קטגוריה\n\n"
    "לחצו על כפתור למטה 👇"
)

MENU_PROMPT = "מה תרצו לראות?"

ACTIVITY_HUB_TITLE = "פעילות שחקנים"
ACTIVITY_HUB_BODY = "בחרו מה לראות:"

SHOP_HUB_TITLE = "חנות היום"
SHOP_HUB_BODY = "בחרו קטגוריה:"

# ── עזרה ─────────────────────────────────────────────────────
HELP_TITLE = "איך משתמשים?"
HELP_BODY = (
    "לחצו על כפתור בתפריט:\n\n"
    "📊 <b>פעילות שחקנים</b> — שחקנים היום והאי הכי פעיל\n"
    "🗺️ <b>איים פעילים היום</b> — דירוג איים\n"
    "🛒 <b>חנות</b> — פריטים לפי קטגוריה\n"
    "⚠️ <b>חריגות</b> — פעילות חריגה\n\n"
    "פקודות: /start · /menu"
)

# ── סטטוסים ─────────────────────────────────────────────────
NO_DATA_TITLE = "עדיין אין נתונים"
NO_DATA_HINT = "אין נתונים כרגע. נסו שוב מאוחר יותר."

ERROR_TITLE = "משהו השתבש"
ERROR_HINT = "לא הצלחנו להביא את הנתונים כרגע. נסו שוב בעוד רגע."

UNKNOWN_INPUT = "לחצו «חזרה לתפריט» או שלחו /menu"

# ── כותרות מסכי תוצאה ────────────────────────────────────────
TITLE_PLAYERS_NOW = "שחקנים פעילים היום"
TITLE_MOST_ACTIVE = "האי הכי פעיל"
TITLE_TOP_ISLANDS = "איים פעילים היום"
LABEL_METRIC_DAY = "יום מדידה"
LABEL_ACTIVE_TODAY = 'סה"כ שחקנים פעילים היום'
LABEL_PLAYS_TODAY = 'סה"כ משחקים'
LABEL_ISLANDS_TOTAL = "מספר איים"
LABEL_PEAK_HOUR = "שיא מחוברים בשעה"
LABEL_UPDATED = "עודכן"
TITLE_SHOP_CATEGORY = "פריטים בחנות"
TITLE_SHOP = "חנות היום"
LABEL_SNAPSHOT = "תאריך חנות"
LABEL_ITEMS_TOTAL = 'סה"כ פריטים'
LABEL_ISLAND = "אי"
LABEL_CODE = "קוד"
LABEL_CREATOR = "יוצר"
LABEL_PLAYS = "משחקים"
LABEL_MINUTES = "דקות משחק"
LABEL_SEVERITY = "חומרה"
LABEL_TIME = "זמן"
TITLE_HEALTH = "בריאות מקורות הנתונים"
TITLE_ANOMALIES = "חריגות"
TITLE_AVG_TODAY = "ממוצע שחקנים היום"

LABEL_PEAK_CCU = "שחקנים מחוברים (שיא)"
LABEL_PLAYERS = "שחקנים ייחודיים"

UNKNOWN_ISLAND = "אי ללא שם"
UNKNOWN_RARITY = "לא ידוע"

RARITY_LABELS = {
    "common": "רגיל",
    "uncommon": "לא שכיח",
    "rare": "נדיר",
    "epic": "אפיק",
    "legendary": "אגדי",
    "marvel": "מארוול",
    "dc": "DC",
    "icon": "אייקון",
    "gaming": "גיימינג",
    "frozen": "קפוא",
    "lava": "לבה",
    "shadow": "צל",
    "slurp": "סלרפ",
    "dark": "אפל",
    "starwars": "מלחמת הכוכבים",
    "unknown": "לא ידוע",
}

CATEGORY_LABELS = {
    "outfit": "סקין / לבוש",
    "backpack": "תיק גב",
    "pickaxe": "מכוש",
    "glider": "גליידר",
    "emote": "אמוג׳י / ריקוד",
    "wrap": "עטיפת נשק",
    "loadingscreen": "מסך טעינה",
    "music": "מוזיקה",
    "contrail": "שובל",
    "spray": "ספריי",
    "emoji": "אמוג׳י",
    "banner": "באנר",
    "bundle": "חבילה",
    "unknown": "לא ידוע",
}

STATUS_LABELS = {
    "success": "תקין ✅",
    "failed": "כשל ❌",
    "failure": "כשל ❌",
}

ANOMALY_BODY = "לא זוהו חריגות פעילות כרגע."
SHOP_NO_CATEGORIES = "לא נמצאו קטגוריות בחנות."
TOP_ISLANDS_MORE = "איים נוספים"
SHOP_ITEMS_MORE = "פריטים נוספים"
ANOMALY_SEVERITY_HIGH = "גבוהה"
ANOMALY_SEVERITY_MEDIUM = "בינונית"
