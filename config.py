"""
Resilient Pocket - Configuration & System Constants
Comprehensive Universal Keyword Dictionaries for Real-Time NLP Categorization
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "resilient_pocket.db")

# Default User Profile Settings
DEFAULT_PROFILE = {
    "name": "Alex Vance",
    "initial_balance": 150000.0,
    "current_cushion": 150000.0,
    "monthly_income": 85000.0,
    "target_daily_budget": 1800.0
}

# Comprehensive Real-Time NLP Tagging Dictionaries
TAG_DICTIONARY = {
    "shopping": [
        # Electronics & Gadgets
        "television", "tv", "television", "fridge", "refrigerator", "washing machine", "ac", "air conditioner",
        "cooler", "microwave", "oven", "heater", "geyser", "fan", "appliance", "appliances",
        "phone", "mobile", "smartphone", "iphone", "samsung", "oneplus", "realme", "xiaomi", "redmi",
        "laptop", "computer", "pc", "macbook", "ipad", "tablet", "monitor", "keyboard", "mouse",
        "headphone", "headphones", "earphone", "earphones", "earbuds", "airpods", "speaker", "soundbar",
        "charger", "cable", "powerbank", "adapter", "camera", "drone", "smartwatch", "watch",
        "croma", "reliance digital", "vijay sales", "poorvika", "sangeetha", "electronics",
        
        # E-Commerce & Retail Stores
        "amazon", "flipkart", "myntra", "meesho", "ajio", "tata cliq", "nykaa", "lenskart",
        
        # Clothing, Apparel & Footwear
        "clothes", "clothing", "shirt", "pant", "tshirt", "jeans", "dress", "saree", "kurti",
        "shoes", "footwear", "sneakers", "sandals", "boots", "fashion", "apparel", "wear",
        "zara", "h&m", "hnm", "uniqlo", "nike", "adidas", "puma", "trends", "pantaloons", "max",
        "mall", "store", "shop", "shopping", "bag", "wallet", "jewelry", "gold", "silver"
    ],
    "food": [
        # Chips, Snacks & Munchies
        "lays", "lay", "chips", "chip", "kurkure", "bingo", "doritos", "pringles", "wafers", "wafer",
        "biscuit", "biscuits", "maggi", "noodles", "namkeen", "munchies", "popcorn", "snack", "snacks",
        "chocolate", "chocolates", "cadbury", "kitkat", "snickers", "oreo", "ice cream", "sweets", "mithai",
        "halwa", "jalebi", "gulab jamun", "laddu", "ladoo", "kaju katli",
        
        # Indian Meals & Dishes
        "curd", "curd rice", "dahi", "dahi rice", "lemon rice", "fried rice", "jeera rice", "dal rice", "dal chawal",
        "rajma chawal", "chole chawal", "paneer rice", "veg rice", "egg rice", "biryani", "pulao", "puliyogare",
        "sambar rice", "rasam rice", "paneer", "milk", "butter", "ghee", "cheese", "doodh", "chass", "lassi",
        "dosa", "idli", "roti", "naan", "paratha", "puri", "poori", "pav", "bhature", "chole", "sabzi", "sabji",
        "curry", "thali", "samosa", "chaat", "panipuri", "golgappa", "bhelpuri", "vada", "vada pav", "pav bhaji",
        "kachaori", "pakoda", "pakora", "tiffin", "mess", "canteen", "bhookh", "khana", "khaana", "nasta", "nashta",
        
        # Quick Commerce & Delivery Platforms
        "swiggy", "zomato", "blinkit", "zepto", "instamart", "bigbasket", "bbnow",
        "uber eats", "dunzo", "licious", "country delight", "milkbasket",
        
        # Dining & Groceries
        "food", "restaurant", "hotel", "dhaba", "cafe", "coffee", "tea", "chai", "bakery", "kitchen",
        "lunch", "dinner", "breakfast", "supper", "bistro", "pizza", "burger", "subway", "dominos",
        "kfc", "mcdonalds", "starbucks", "grocery", "groceries", "supermarket", "vegetables", "veggies",
        "fruits", "meat", "chicken", "mutton", "fish", "egg", "eggs", "mart", "provision"
    ],
    "travel": [
        "uber", "ola", "rapido", "namma yatri", "flight", "airline", "irctc", "railway", "metro",
        "fuel", "petrol", "diesel", "shell", "cab", "taxi", "toll", "hpcl", "bpcl", "iocl", "parking",
        "bus", "train", "auto", "flight", "indigo", "air india", "vistara", "fastag", "subway pass"
    ],
    "bills": [
        "electricity", "water", "wifi", "broadband", "act", "airtel", "jio", "vi", "bsnl", "rent",
        "recharge", "utility", "gas", "bescom", "tata play", "dth", "dish tv", "maintenance", "society"
    ],
    "entertainment": [
        "netflix", "spotify", "prime", "movie", "bookmyshow", "cinema", "gaming", "steam", "hotstar",
        "youtube", "playstation", "xbox", "concert", "event", "show", "pvr", "inox"
    ],
    "health": [
        "pharmacy", "apollo", "hospital", "doctor", "medicine", "gym", "fitness", "cult.fit",
        "pharmeasy", "1mg", "clinic", "medical", "lab", "netmeds", "test", "consultation"
    ],
    "income": [
        "salary", "stipend", "freelance", "dividend", "interest", "refund", "cashback", "credit",
        "payout", "deposit", "bonus", "reward"
    ]
}

# Shock Detection Thresholds
SHOCK_THRESHOLD_RATIO = 0.05  # Transaction > 5% of liquid cushion triggers shock warning
SHOCK_BUDGET_MULTIPLIER = 2.5 # Single tx > 2.5x daily budget triggers shock warning

# Health Score Weights
HEALTH_WEIGHTS = {
    "cushion_ratio": 0.35,  # Cushion / 3-month income
    "runway_days": 0.35,    # Runway days (>90 days is ideal)
    "shock_penalty": 0.15,  # Active shock deficit impact
    "spending_vol": 0.15   # Volatility of daily burn
}
