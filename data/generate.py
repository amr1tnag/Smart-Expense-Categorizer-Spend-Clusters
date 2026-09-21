"""Regenerate the synthetic data files (deterministic, seed 42).

    python data/generate.py

Writes:
  data/seed_labeled.csv        training set: many merchants x several statement
                               formats, with a `merchant` column used for
                               merchant-grouped cross-validation.
  data/sample_statement.csv    six-month demo statement with ground-truth
                               `category`. Deliberately includes merchants that
                               never appear in the training set, so scoring it
                               measures generalisation rather than memorisation.
  public/sample_statement.csv  the same statement without labels, for download.

Everything here is synthetic. Merchant names are real brands, but amounts, dates
and reference numbers are random.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rng = random.Random(42)

BANKS = ["HDFC", "YESB", "ICIC", "SBIN", "UTIB", "KKBK", "PUNB", "BARB"]
HANDLES = ["ybl", "okhdfcbank", "paytm", "ibl", "oksbi", "axl"]
CITIES = ["BENGALURU", "MUMBAI", "DELHI", "HYDERABAD", "CHENNAI", "PUNE", "KOLKATA", "GURGAON"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def ref(n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


# --- statement formats ------------------------------------------------------
def upi(m: str) -> str:
    h = m.split()[0].lower()
    return rng.choice(
        [
            f"UPI/{m}/{ref(6)}",
            f"UPI/{m}/{ref(6)}/{rng.choice(BANKS)}",
            f"UPI/DR/{ref(12)}/{m}/{rng.choice(BANKS)}/{h}@{rng.choice(HANDLES)}",
            f"UPI-{m}-{h}@{rng.choice(HANDLES)}-{ref(12)}",
        ]
    )


def pos(m: str) -> str:
    c = rng.choice(CITIES)
    return rng.choice([f"POS {ref(4)} {m} {c}", f"POS/{m} {c}", f"{m} {c} IN", f"POS {m}"])


def ecom(m: str) -> str:
    return rng.choice([f"{m} ONLINE {ref(8)}", f"PG*{m}*{ref(8)}", f"{m} INTERNET {ref(6)}", f"{m}*{ref(7)}"])


def neft(m: str) -> str:
    return rng.choice([f"NEFT/{m}/{rng.choice(BANKS)}", f"NEFT-{ref(11)}-{m}-{rng.choice(BANKS)}"])


def imps(m: str) -> str:
    return f"IMPS/{ref(12)}/{m}/{rng.choice(BANKS)}"


def ach(m: str) -> str:
    return rng.choice(
        [f"ACH D- {m}-{ref(8)}", f"ACH DEBIT {m} {rng.choice(MONTHS)}", f"NACH/{m}/{ref(8)}", f"ECS {m} {ref(6)}"]
    )


def bbps(m: str) -> str:
    return rng.choice([f"BBPS/{m}/{ref(10)}", f"BILLPAY/{m}/{ref(8)}"])


CHANNELS = {"upi": upi, "pos": pos, "ecom": ecom, "neft": neft, "imps": imps, "ach": ach, "bbps": bbps}

# category -> channel weights (loose on purpose, so channel alone is a weak cue)
WEIGHTS = {
    "food": {"upi": 6, "pos": 3, "ecom": 1},
    "travel": {"upi": 5, "pos": 3, "ecom": 2},
    "shopping": {"upi": 2, "pos": 3, "ecom": 5},
    "entertainment": {"upi": 5, "pos": 2, "ecom": 3, "ach": 1},
    "health": {"upi": 4, "pos": 5, "ecom": 1},
    "bills": {"upi": 3, "ach": 4, "bbps": 3, "ecom": 1},
    "rent": {"neft": 4, "imps": 3, "upi": 3, "ach": 1},
    "other": {"upi": 1},
}


def describe(category: str, merchant: str) -> str:
    chans, w = zip(*WEIGHTS[category].items())
    return CHANNELS[rng.choices(chans, w)[0]](merchant)


# --- training merchants: name -> (lo, hi) amount range ------------------------
TRAIN = {
    "food": {
        "SWIGGY": (120, 900), "ZOMATO": (150, 1100), "DOMINOS PIZZA": (250, 1200), "MCDONALDS": (150, 700),
        "KFC": (200, 900), "BURGER KING": (150, 700), "STARBUCKS": (250, 900), "CAFE COFFEE DAY": (120, 600),
        "HALDIRAMS": (150, 900), "BARBEQUE NATION": (900, 3200), "PIZZA HUT": (300, 1400), "SUBWAY": (150, 650),
        "BIGBASKET": (400, 3200), "BLINKIT": (120, 1800), "ZEPTO": (100, 1500), "DMART": (600, 4500),
        "RELIANCE FRESH": (300, 2600), "NATURES BASKET": (500, 3500), "CHAI POINT": (60, 400),
        "BEHROUZ BIRYANI": (350, 1300), "FAASOS": (150, 700), "SHREE SAI SWEETS": (80, 900),
        "HOTEL SAGAR RESTAURANT": (200, 1400), "UDUPI GRAND": (120, 700), "MORE SUPERMARKET": (300, 2800),
        "LOCAL KIRANA STORE": (40, 700),
    },
    "travel": {
        "UBER INDIA": (90, 900), "OLA CABS": (80, 800), "IRCTC": (300, 3800), "INDIGO AIRLINES": (2500, 12000),
        "AIR INDIA": (3000, 15000), "MAKEMYTRIP": (1200, 14000), "GOIBIBO": (900, 12000), "REDBUS": (350, 2400),
        "INDIAN OIL PETROL PUMP": (500, 3500), "HP PETROL BUNK": (500, 3500), "BHARAT PETROLEUM": (500, 3500),
        "SHELL FUEL STATION": (600, 3600), "FASTAG RECHARGE": (500, 3000), "NAMMA METRO": (100, 800),
        "DELHI METRO SMART CARD": (100, 1000), "BMTC BUS PASS": (200, 1200), "OYO ROOMS": (700, 4500),
        "AIRPORT TAXI PREPAID": (400, 1800),
    },
    "shopping": {
        "AMAZON PAY INDIA": (250, 9000), "FLIPKART": (300, 12000), "MYNTRA": (500, 6000), "AJIO": (400, 5000),
        "NYKAA": (350, 4000), "CROMA ELECTRONICS": (1500, 60000), "RELIANCE DIGITAL": (1500, 55000),
        "DECATHLON SPORTS": (400, 8000), "IKEA": (800, 20000), "PUMA STORE": (1500, 7000), "NIKE STORE": (2000, 9000),
        "LIFESTYLE STORES": (700, 6000), "WESTSIDE": (600, 5000), "MAX FASHION": (400, 4000),
        "PANTALOONS": (600, 5000), "TATA CLIQ": (500, 9000), "MEESHO": (200, 2500), "LENSKART": (700, 6000),
        "VIJAY SALES": (1500, 45000), "PEPPERFRY": (2000, 30000),
    },
    "entertainment": {
        "NETFLIX": (149, 799), "HOTSTAR": (299, 1499), "SPOTIFY INDIA": (59, 199), "AMAZON PRIME": (179, 1499),
        "YOUTUBE PREMIUM": (129, 189), "SONYLIV": (299, 999), "ZEE5": (99, 999), "BOOKMYSHOW": (200, 2800),
        "PVR CINEMAS": (250, 2200), "INOX MOVIES": (250, 2200), "SMAAASH GAMING": (300, 2500),
        "STEAM GAMES": (200, 3000), "PLAYSTATION STORE": (300, 4000), "TIMEZONE ARCADE": (200, 1800),
        "WONDERLA": (900, 3500), "LOLLAPALOOZA TICKETS": (2000, 9000),
    },
    "health": {
        "APOLLO PHARMACY": (100, 3500), "MEDPLUS": (100, 3000), "PHARMEASY": (150, 3500), "1MG": (150, 3000),
        "NETMEDS": (150, 3000), "PRACTO CONSULTATION": (300, 1500), "MANIPAL HOSPITAL": (500, 25000),
        "FORTIS HOSPITAL": (500, 25000), "MAX HEALTHCARE": (500, 25000), "DR LAL PATHLABS": (300, 4500),
        "THYROCARE": (300, 4500), "CULT FIT": (700, 4500), "GOLDS GYM": (1200, 5000), "CLOVE DENTAL": (500, 12000),
        "ASTER CLINIC": (300, 3500), "VISION EYE CARE": (400, 6000),
    },
    "bills": {
        "AIRTEL POSTPAID": (399, 1499), "JIO RECHARGE": (199, 999), "VODAFONE IDEA": (199, 999), "BSNL": (150, 900),
        "ACT FIBERNET": (799, 1999), "BESCOM ELECTRICITY": (400, 5000), "TATA POWER": (500, 6000),
        "ADANI ELECTRICITY": (500, 6000), "MSEDCL": (400, 5500), "WATER BOARD BILL": (150, 1200),
        "INDANE GAS": (850, 1100), "HP GAS CYLINDER": (850, 1100), "LIC PREMIUM": (1500, 25000),
        "HDFC LIFE": (2000, 30000), "ICICI PRUDENTIAL": (2000, 30000), "CREDIT CARD BILL PAYMENT": (2000, 60000),
        "TATA PLAY": (250, 900), "PROPERTY TAX": (1500, 15000), "HDFC ERGO INSURANCE": (1500, 20000),
    },
    "rent": {
        "HOUSE RENT": (9000, 40000), "LANDLORD RENT": (9000, 40000), "NOBROKER RENT PAY": (9000, 40000),
        "CRED RENT PAYMENT": (9000, 40000), "SOCIETY MAINTENANCE": (800, 6000), "PG ACCOMMODATION FEE": (5000, 18000),
        "FLAT RENT": (9000, 40000), "HOSTEL FEE": (4000, 20000), "APARTMENT ASSOCIATION": (800, 6000),
        "OWNER RENT PAYMENT": (9000, 40000),
    },
    "other": {
        "ATM CASH WITHDRAWAL": (500, 20000), "NFS CASH WDL": (500, 20000), "SELF TRANSFER": (1000, 50000),
        "BANK CHARGES": (10, 600), "SMS ALERT CHARGES": (10, 60), "ANNUAL CARD FEE": (200, 3000),
        "GST ON CHARGES": (5, 120), "ZERODHA BROKING": (500, 30000), "GROWW SIP": (500, 25000),
        "MUTUAL FUND SIP": (500, 25000), "CHEQUE BOOK CHARGES": (30, 200), "FUND TRANSFER": (500, 30000),
    },
}

FIRST_TRAIN = ["RAHUL", "PRIYA", "AMIT", "NEHA", "VIKRAM", "ANJALI", "SURESH", "KAVITA", "ROHAN", "DIVYA",
               "MANOJ", "SNEHA", "ARJUN", "POOJA", "KARTHIK", "MEERA", "DEEPAK", "SWATI", "NITIN", "RITU"]
LAST_TRAIN = ["SHARMA", "NAIR", "PATEL", "REDDY", "IYER", "GUPTA", "SINGH", "KUMAR", "MENON", "JOSHI",
              "VERMA", "RAO", "DESAI", "BOSE", "PILLAI"]


DESCRIPTORS = {
    "food": ["RESTAURANT", "CAFE", "BAKERY", "SWEETS", "KITCHEN", "BIRYANI", "DHABA", "FOODS", "SUPERMARKET",
             "GROCERY", "DAIRY", "TIFFIN", "COFFEE", "JUICE"],
    "travel": ["CABS", "TAXI", "TRAVELS", "PETROL PUMP", "FUEL", "AIRLINES", "RAILWAY", "METRO", "BUS", "TOLL"],
    "shopping": ["FASHION", "ELECTRONICS", "MOBILES", "FURNITURE", "APPAREL", "FOOTWEAR", "JEWELLERS", "GIFTS"],
    "entertainment": ["CINEMAS", "MOVIES", "GAMES", "GAMING", "STREAMING", "MUSIC", "THEATRE", "CONCERT"],
    "health": ["PHARMACY", "HOSPITAL", "CLINIC", "DIAGNOSTICS", "DENTAL", "HEALTH", "MEDICALS", "LABS", "WELLNESS"],
    "bills": ["ELECTRICITY", "BROADBAND", "INSURANCE", "RECHARGE", "POSTPAID", "GAS", "WATER BILL", "TELECOM", "PREMIUM"],
    "rent": ["RENT", "MAINTENANCE", "HOSTEL", "LEASE", "PG RENT"],
    "other": ["CHARGES", "FEES", "CASH WITHDRAWAL", "TRANSFER", "INVESTMENTS", "SIP"],
}
AMOUNTS = {"food": (60, 2500), "travel": (80, 6000), "shopping": (300, 15000), "entertainment": (100, 2500),
           "health": (150, 8000), "bills": (200, 8000), "rent": (2000, 35000), "other": (50, 20000)}
_SYL = ["KA", "RA", "MI", "TO", "NE", "VA", "LU", "SO", "DA", "PE", "ZI", "HA", "BRI", "TEK", "SHA", "NO", "VI", "GAN", "PRA", "JO"]


def fake_brand() -> str:
    return "".join(rng.choice(_SYL) for _ in range(rng.choice([2, 3])))


def person(first: list[str], last: list[str]) -> str:
    return f"{rng.choice(first)} {rng.choice(last)}"


def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=rng.randrange((end - start).days + 1))


def amount(lo: float, hi: float) -> float:
    return round(lo + (hi - lo) * rng.random() ** 1.6, 2)


def build_seed(rows_per_merchant: int = 7):
    out = []
    start, end = date(2024, 1, 1), date(2024, 6, 30)
    for cat, merchants in TRAIN.items():
        for name, (lo, hi) in merchants.items():
            for _ in range(rows_per_merchant):
                out.append((rand_date(start, end), describe(cat, name), amount(lo, hi), cat, name))
    # Unknown brands are the norm on real statements, and a brand name alone says
    # nothing. Generic descriptors ("... PHARMACY", "... PETROL PUMP") do, so pair
    # them with made-up brand names to teach the model to lean on the descriptor.
    for cat, words in DESCRIPTORS.items():
        lo, hi = AMOUNTS[cat]
        for _ in range(16):
            brand = fake_brand()
            for _ in range(3):
                name = f"{brand} {rng.choice(words)}"
                out.append((rand_date(start, end), describe(cat, name), amount(lo, hi), cat, brand))
    # person-to-person transfers: the merchant is a name, unseen at test time
    for _ in range(90):
        p = person(FIRST_TRAIN, LAST_TRAIN)
        d = rng.choice([f"UPI/{p}/{ref(6)}", f"UPI/P2A/{ref(12)}/{p}/{rng.choice(BANKS)}", f"UPI/{p}/{rng.choice(['PAYMENT', 'SENT', 'DINNER SPLIT', 'GIFT'])}/{ref(6)}"])
        out.append((rand_date(start, end), d, amount(100, 8000), "other", "P2P"))
    rng.shuffle(out)
    return out


# --- demo statement -----------------------------------------------------------
# Merchants below are mostly NOT in TRAIN (marked *), so the score on this file
# measures how well the model handles brands and formats it has never seen.
def build_sample():
    rng.seed(20250101)  # independent of the training draw, so the test set never shifts
    rows = []

    def add(d, desc, amt, cat):
        rows.append((d, desc, round(amt, 2), cat))

    fixed = [  # (day of month, jitter days, description factory, amount, category)
        (2, 1, lambda: f"NEFT/SURESH REDDY RENT/{rng.choice(BANKS)}", 24000, "rent"),
        (5, 1, lambda: f"IMPS/{ref(12)}/PRESTIGE ORCHID MAINT/{rng.choice(BANKS)}", 2800, "rent"),
        (7, 1, lambda: f"ACH D- AIRTEL-{ref(8)}", 799, "bills"),
        (10, 2, lambda: f"BBPS/ACT BROADBAND/{ref(10)}", 1179, "bills"),
        (12, 1, lambda: f"UPI/NETFLIX COM/{ref(6)}/{rng.choice(BANKS)}", 649, "entertainment"),
        (18, 1, lambda: f"UPI/SPOTIFY/{ref(6)}", 119, "entertainment"),
        (6, 2, lambda: f"ACH D- CULTFIT-{ref(8)}", 1500, "health"),
        (4, 1, lambda: f"NACH/GROWW SIP/{ref(8)}", 5000, "other"),
        (20, 2, lambda: f"UPI/CRED CLUB CARD BILL/{ref(6)}", None, "bills"),
    ]
    for m in range(6):
        month_start = date(2025, 1 + m, 1)
        for day, jit, fn, amt, cat in fixed:
            d = month_start + timedelta(days=day - 1 + rng.randint(-jit, jit))
            if amt is None:
                amt = rng.uniform(6000, 22000)
            add(d, fn(), amt, cat)
        # electricity varies month to month
        add(month_start + timedelta(days=14 + rng.randint(-1, 2)), f"BBPS/BESCOM ELECTRICITY/{ref(10)}", rng.uniform(600, 2400), "bills")

        # discretionary spend: food and rides skew to weekends
        for _ in range(rng.randint(10, 14)):
            d = month_start + timedelta(days=rng.randrange(28))
            if d.weekday() < 5 and rng.random() < 0.45:
                d += timedelta(days=(5 - d.weekday()))
            name, lo, hi = rng.choice(
                [
                    ("SWIGGY", 150, 900), ("ZOMATO", 150, 1100), ("EATSURE", 200, 800), ("DUNZO", 100, 900),
                    ("BLINKIT", 150, 1400), ("SHIVAJI SWEETS AND SNACKS", 100, 600), ("THIRD WAVE COFFEE", 200, 700),
                ]
            )
            add(d, describe("food", name), amount(lo, hi), "food")
        for _ in range(rng.randint(4, 7)):
            d = month_start + timedelta(days=rng.randrange(28))
            name, lo, hi = rng.choice(
                [("UBER INDIA", 90, 700), ("RAPIDO", 40, 300), ("OLA CABS", 90, 700), ("BPCL PETROL PUMP", 600, 2500), ("CLEARTRIP", 2500, 9000), ("ABHIBUS", 400, 1500)]
            )
            add(d, describe("travel", name), amount(lo, hi), "travel")
        for _ in range(rng.randint(2, 4)):
            d = month_start + timedelta(days=rng.randrange(28))
            name, lo, hi = rng.choice(
                [("AMAZON PAY INDIA", 300, 6000), ("FLIPKART", 400, 9000), ("MYNTRA", 600, 4000), ("FIRSTCRY", 300, 3000), ("SHOPPERS STOP", 800, 6000), ("BEWAKOOF", 300, 2000)]
            )
            add(d, describe("shopping", name), amount(lo, hi), "shopping")
        if rng.random() < 0.7:
            d = month_start + timedelta(days=rng.randrange(28))
            name, lo, hi = rng.choice([("APOLLO PHARMACY", 150, 2500), ("NARAYANA HEALTH", 500, 6000), ("MEDIBUDDY", 200, 2000), ("TATA 1MG", 150, 2000)])
            add(d, describe("health", name), amount(lo, hi), "health")
        if rng.random() < 0.6:
            d = month_start + timedelta(days=rng.randrange(28))
            name, lo, hi = rng.choice([("JIOCINEMA", 99, 400), ("BOOKMYSHOW", 300, 1800), ("INOX MOVIES", 300, 1800), ("DISNEY PLUS HOTSTAR", 149, 1499)])
            add(d, describe("entertainment", name), amount(lo, hi), "entertainment")
        for _ in range(rng.randint(1, 2)):  # cash + transfers to people
            d = month_start + timedelta(days=rng.randrange(28))
            add(d, rng.choice([f"ATM WDL {ref(6)} {rng.choice(CITIES)}", f"NFS CASH WDL {ref(8)}"]), rng.choice([2000, 5000, 10000]), "other")
        for _ in range(rng.randint(1, 3)):
            p = person(["ADITYA", "ISHA", "TANVI", "HARSH", "LAKSHMI", "FARHAN", "GAURAV", "SIMRAN"], ["KAPOOR", "MALHOTRA", "CHOPRA", "SETHI", "AGARWAL", "KHAN"])
            d = month_start + timedelta(days=rng.randrange(28))
            add(d, f"UPI/{p}/{rng.choice(['PAYMENT', 'DINNER SPLIT', 'THANKS'])}/{ref(6)}", amount(200, 6000), "other")
    rows.sort(key=lambda r: r[0])
    return rows


def write(path: Path, header: list[str], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


if __name__ == "__main__":
    seed = build_seed()
    write(ROOT / "data" / "seed_labeled.csv", ["date", "description", "amount", "category", "merchant"],
          [(d.isoformat(), desc, amt, cat, mer) for d, desc, amt, cat, mer in seed])
    sample = build_sample()
    write(ROOT / "data" / "sample_statement.csv", ["date", "description", "amount", "category"],
          [(d.isoformat(), desc, amt, cat) for d, desc, amt, cat in sample])
    write(ROOT / "public" / "sample_statement.csv", ["date", "description", "amount"],
          [(d.isoformat(), desc, amt) for d, desc, amt, _ in sample])
    print(f"seed_labeled.csv: {len(seed)} rows | sample_statement.csv: {len(sample)} rows")
