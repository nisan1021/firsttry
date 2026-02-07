"""Application-wide constants."""

CATEGORIES = ["רכב", "קניות אוכל", "קניות ביגוד", "אחרים"]

PARTNERS = ["בן/בת זוג A", "בן/בת זוג B"]

# Fixed colour map for charts (category -> hex colour)
CATEGORY_COLORS = {
    "רכב": "#4e79a7",
    "קניות אוכל": "#f28e2b",
    "קניות ביגוד": "#e15759",
    "אחרים": "#76b7b2",
}

PARTNER_COLORS = {
    "בן/בת זוג A": "#59a14f",
    "בן/בת זוג B": "#edc948",
}

DATE_INPUT_FMT = "%Y-%m-%d %H:%M"
ISO_FMT = "%Y-%m-%dT%H:%M:%S"
