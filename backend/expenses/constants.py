DEFAULT_EXPENSE_CATEGORIES = [
    "Software & Subscriptions",
    "Travel",
    "Professional Services",
    "Equipment",
    "Office Supplies",
    "Marketing",
    "Bank Fees & Charges",
    "Other",
]

# Simple keyword rules for CSV auto-categorization (PRD Phase 2: "simple
# keyword rules to start"). Matched case-insensitively against the imported
# transaction description; first match wins, "Other" is the fallback.
CATEGORY_KEYWORDS = {
    "Software & Subscriptions": [
        "aws", "google cloud", "azure", "github", "gitlab", "figma", "notion",
        "adobe", "canva", "slack", "zoom", "dropbox", "godaddy", "namecheap",
        "digitalocean", "vercel", "netlify", "openai", "anthropic",
    ],
    "Travel": [
        "uber", "ola", "irctc", "indigo", "spicejet", "air india", "makemytrip",
        "goibibo", "redbus", "railway", "airlines", "airways",
    ],
    "Professional Services": [
        "chartered accountant", "ca fees", "legal", "lawyer", "consultant", "advocate",
    ],
    "Equipment": [
        "amazon", "flipkart", "croma", "reliance digital", "apple store", "dell", "hp store",
    ],
    "Office Supplies": [
        "stationery", "office depot", "staples",
    ],
    "Marketing": [
        "google ads", "facebook ads", "meta ads", "linkedin ads", "mailchimp", "buffer",
    ],
    "Bank Fees & Charges": [
        "bank charges", "annual fee", "atm fee", "gst on charges", "processing fee", "neft charges",
    ],
}
