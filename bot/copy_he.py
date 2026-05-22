"""Hebrew UI copy for the Telegram bot."""

from __future__ import annotations

# ── תפריט ראשי (4 אפשרויות בלבד) ───────────────────────────────
BTN_CURRENT_ACTIVITY = "📊 כמה שחקנים מחוברים?"
BTN_TOP_ISLANDS = "🏆 האיים הכי פופולריים"
BTN_SHOP = "🛒 מה יש בחנות היום?"
BTN_ANOMALIES = "⚠️ חריגות פעילות"
BTN_HELP = "💬 עזרה ומדריך"
BTN_HOME = "🏠 חזרה לתפריט"

LOADING = "רגע, טוען נתונים…"
UNKNOWN_ACTION = "לא הצלחנו לזהות את הבחירה. לחצו על «חזרה לתפריט»."

# ── מסך פתיחה ─────────────────────────────────────────────────
WELCOME_TITLE = "Fortnite — מרכז הנתונים"
WELCOME_TAGLINE = "כל מה שצריך על איים, שחקנים וחנות — במקום אחד"
WELCOME_BODY = (
    "שלום! 👋\n"
    "שמחים שבאתם.\n\n"
    "כאן אפשר לבדוק בקלות:\n"
    "• כמה שחקנים מחוברים לאיים עכשיו\n"
    "• אילו איים הכי פופולריים\n"
    "• מה מוצע בחנות לפי נדירות\n\n"
    "לחצו על אחד הכפתורים למטה 👇"
)

MENU_PROMPT = "מה תרצו לראות?"

# ── עזרה ─────────────────────────────────────────────────────
HELP_TITLE = "איך משתמשים?"
HELP_BODY = (
    "פשוט לוחצים על כפתור בתפריט:\n\n"
    "📊 <b>כמה שחקנים מחוברים?</b>\n"
    "   האי הכי פעיל כרגע וסיכום שחקנים\n\n"
    "🏆 <b>האיים הכי פופולריים</b>\n"
    "   דירוג לפי מספר שחקנים מחוברים\n\n"
    "🛒 <b>מה יש בחנות היום?</b>\n"
    "   פירוט פריטים לפי נדירות\n\n"
    "אפשר גם לכתוב: <code>פעילות</code> · <code>איים</code> · <code>חנות</code>\n\n"
    "פקודות: /start · /menu"
)

# ── סטטוסים (שפה ידידותית, בלי ז׳רגון טכני) ─────────────────
NO_DATA_TITLE = "עדיין אין נתונים"
NO_DATA_HINT = "ייתכן שהנתונים עוד לא עודכנו. נסו שוב בעוד כמה דקות."

ERROR_TITLE = "משהו השתבש"
ERROR_HINT = "לא הצלחנו להביא את הנתונים כרגע. נסו שוב בעוד רגע."

UNKNOWN_INPUT = (
    "לא בטוחים מה לבחור? 😊\n"
    "לחצו «חזרה לתפריט» או שלחו /menu"
)

# ── כותרות מסכי תוצאה ────────────────────────────────────────
TITLE_ACTIVITY = "שחקנים מחוברים עכשיו"
TITLE_ACTIVITY_SUB = "האי הכי פעיל ברגע זה"
TITLE_TOP_ISLANDS = "האיים הכי פופולריים"
TITLE_TOP_ISLANDS_SUB = "מדורגים לפי שחקנים מחוברים"
TITLE_SHOP = "חנות היום"
TITLE_SHOP_SUB = "פירוט לפי נדירות"
TITLE_HEALTH = "בריאות מקורות הנתונים"
TITLE_ANOMALIES = "חריגות"
TITLE_AVG_TODAY = "ממוצע שחקנים היום"

LABEL_UPDATED = "עודכן לאחרונה"
LABEL_SNAPSHOT = "תאריך חנות"
LABEL_ISLAND = "אי"
LABEL_CODE = "קוד אי"
LABEL_PEAK_CCU = "שחקנים מחוברים (שיא)"
LABEL_TOTAL_CCU = 'סה"כ שחקנים מחוברים'
LABEL_PLAYERS = "שחקנים ייחודיים"
LABEL_PLAYS = "משחקים"
LABEL_RANK = "מקום"
LABEL_STATUS = "סטטוס"
LABEL_SUCCESS = "הצלחות"
LABEL_FAILURES = "כשלונות"
LABEL_SEVERITY = "חומרה"
LABEL_TIME = "זמן מדידה"

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

STATUS_LABELS = {
    "success": "תקין ✅",
    "failed": "כשל ❌",
    "failure": "כשל ❌",
}

ANOMALY_BODY = (
    "לא זוהתה פעילות חריגה כרגע. "
    "נדרשת היסטוריית מדדים נוספת כדי לזהות חריגות."
)
TOP_ISLANDS_FEW = "רק מעט איים עם נתוני שיא זמינים כרגע."
ANOMALY_SEVERITY_HIGH = "גבוהה"
ANOMALY_SEVERITY_MEDIUM = "בינונית"
