"""Generate a labeled synthetic Kotak-style UPI statement.

Description formats mirror a real Indian savings-account statement
(UPI/<payee>/<bank>/<ref>/<note>, PCI card swipes, NACH mandates, fee
entries), so a model trained here transfers to genuine exports.

    python scripts/generate_statement.py --rows 800 --out data/synthetic_statement.csv
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta

BANKS = ["YESB", "UTIB", "HDFC", "SBIN", "UBIN", "KKBK", "IBKL", "PPIW", "CNRB", "IDFB", "RATN", "SVCB"]

# merchant, category, (min, max), weekend_bias (1.0 = no bias)
MERCHANTS = [
    # --- food: delivery, cafes, street vendors ---
    ("Swiggy Ltd", "food", 120, 700, 1.8, "Pay for Inte"),
    ("Swiggy Limited", "food", 150, 900, 1.8, "UPI"),
    ("Zomato Ltd", "food", 140, 800, 1.8, "Pay via Razo"),
    ("Patil Vadapav", "food", 20, 80, 1.0, "UPI"),
    ("GAVDEVI WADAPA", "food", 15, 60, 1.0, "UPI"),
    ("Ganga Sagar Fa", "food", 10, 90, 1.0, "UPI"),
    ("Royal Bakery", "food", 20, 150, 1.2, "UPI"),
    ("New Daimond 2", "food", 30, 200, 1.3, "UPI"),
    ("CHENNAI EDALI", "food", 60, 250, 1.0, "UPI"),
    ("Krishna milk", "food", 20, 80, 1.0, "UPI"),
    ("Cafe Coffee Day", "food", 90, 400, 1.5, "UPI"),
    ("Starbucks India", "food", 200, 700, 1.6, "UPI"),
    # --- groceries: quick commerce ---
    ("BLINKIT", "groceries", 150, 1600, 1.2, "Pay via Razo"),
    ("Blinkit", "groceries", 120, 1200, 1.2, "Pay via Razo"),
    ("Zepto", "groceries", 100, 900, 1.2, "UPI"),
    ("BIGBASKET", "groceries", 200, 2200, 1.1, "Pay"),
    ("amazon pay gro", "groceries", 100, 1400, 1.1, "You are payi"),
    ("Amazon Pay Gro", "groceries", 120, 1500, 1.1, "You are payi"),
    ("SHIVAM SUPER M", "groceries", 30, 600, 1.0, "UPI"),
    ("Solanki Genera", "groceries", 15, 300, 1.0, "UPI"),
    ("DMart Avenue", "groceries", 400, 3200, 1.6, "UPI"),
    # --- travel: transit, fuel, rail ---
    ("NMMTGhansoli C", "travel", 10, 30, 0.5, "UPI"),
    ("NMMTTurbe C413", "travel", 10, 30, 0.5, "UPI"),
    ("Indian Railway", "travel", 15, 350, 1.0, "UPI"),
    ("VASHI FUEL CEN", "travel", 100, 1500, 1.0, "UPI"),
    ("HP PETROL PUMP", "travel", 200, 2000, 1.0, "UPI"),
    ("Uber India Sys", "travel", 60, 600, 1.4, "UPI"),
    ("Rapido Bike", "travel", 25, 200, 1.2, "UPI"),
    ("2 Wheeler nigh", "travel", 50, 200, 1.0, "UPI"),
    ("MAH Vashi Inor", "travel", 100, 500, 1.0, "UPI"),
    ("IRCTC Rail Con", "travel", 300, 2500, 1.0, "UPI"),
    # --- shopping ---
    ("Amazon Pay", "shopping", 100, 3000, 1.1, "Request from"),
    ("Flipkart Inter", "shopping", 200, 5000, 1.1, "UPI"),
    ("Myntra Designs", "shopping", 400, 3500, 1.3, "UPI"),
    ("Ugaoo", "shopping", 200, 900, 1.2, "Payment To U"),
    ("Impression sal", "shopping", 100, 600, 1.2, "UPI"),
    ("DECATHLON SPOR", "shopping", 500, 4000, 1.5, "UPI"),
    ("RELIANCE TREND", "shopping", 400, 2500, 1.4, "UPI"),
    # --- bills & subscriptions (recurring) ---
    ("ANTHROPIC* CLAUDE SUB", "bills", 2353, 2353, 1.0, None),
    ("Godaddy", "bills", 299, 1200, 1.0, "Pay"),
    ("NETFLIX.COM", "bills", 199, 649, 1.0, None),
    ("Spotify India", "bills", 119, 199, 1.0, "UPI"),
    ("Jio Recharge", "bills", 199, 899, 1.0, "UPI"),
    ("Airtel Postpai", "bills", 299, 999, 1.0, "UPI"),
    ("ACT Fibernet", "bills", 700, 1400, 1.0, "UPI"),
    ("MSEB Electrici", "bills", 400, 2500, 1.0, "UPI"),
    # --- entertainment ---
    ("ROLLING CUE", "entertainment", 40, 300, 1.7, "UPI"),
    ("BookMyShow", "entertainment", 150, 900, 1.9, "UPI"),
    ("PVR Cinemas", "entertainment", 200, 1200, 1.9, "UPI"),
    ("Smaaash Gaming", "entertainment", 300, 1500, 1.8, "UPI"),
    # --- health ---
    ("Apollo Pharmac", "health", 80, 1500, 1.0, "UPI"),
    ("PharmEasy", "health", 150, 1800, 1.0, "UPI"),
    ("Cult Fit", "health", 500, 2500, 1.0, "UPI"),
    ("Dr Lal PathLab", "health", 300, 2000, 0.7, "UPI"),
]

# Person-to-person UPI. Text alone cannot tell you what these were for -
# they get their own class rather than being forced into a spend category.
PEOPLE = [
    "MITALI NAG", "APURBA NAG", "ARPITA NAG", "AMRIT NAG", "NIRAJ KUMAR",
    "SHUBHAM CHANDR", "Ravi s Gowda", "Amey Nagesh", "UPENDRA SINGH",
    "Dwijesh Hemant", "Mitesh Mahendr", "SOURAV DHAR", "SHIVAM YADAV",
    "LONDHE VINOD S", "RAJESH KUMAR J", "Sharafat Ali", "Altaf Yamin Sh",
    "YAM LAL CHAPAG", "ARUNA HEMANT P", "V SUDALAI KONA", "Shubham Brahmd",
    "PRADEEP PAN SH", "DARNE SOHAM SU", "Avaneesh Sachi", "Shadmani Khato",
]
P2P_NOTES = ["UPI", "Payment from", "Paid securel", "NO REMARK"]

MONTHLY_BILLS = ["ANTHROPIC* CLAUDE SUB", "NETFLIX.COM", "Spotify India", "ACT Fibernet", "Jio Recharge"]


def ref() -> str:
    return str(random.randint(100000000000, 999999999999))


def describe(name: str, note: str | None) -> str:
    """Build a description in the bank's own wire format."""
    if name in ("ANTHROPIC* CLAUDE SUB", "NETFLIX.COM"):
        return f"PCI/{random.randint(1000, 9999)}/{name}/+{random.randint(10**11, 10**12 - 1)}/{random.randint(0, 23):02d}:{random.randint(0, 59):02d}"
    return f"UPI/{name}/{random.choice(BANKS)}/{ref()}/{note}"


def generate(rows: int, start: date, seed: int) -> list[dict]:
    random.seed(seed)
    out: list[dict] = []
    day_span = max(30, rows // 3)
    billed: set[tuple[str, int]] = set()

    for i in range(rows):
        when = start + timedelta(days=random.randint(0, day_span))
        weekend = when.weekday() >= 5
        roll = random.random()

        if roll < 0.22:  # person-to-person transfer, either direction
            who = random.choice(PEOPLE)
            amount = round(random.choice([20, 50, 100, 200, 500, 1000, 2000]) * random.uniform(0.5, 1.5), 2)
            out.append({
                "date": when, "description": describe(who, random.choice(P2P_NOTES)),
                "amount": amount, "type": random.choice(["debit", "credit"]), "category": "transfer",
            })
            continue

        if roll < 0.25:  # incoming money: salary, refunds, fees
            kind = random.random()
            if kind < 0.4:
                desc, amount, cat, typ = f"Recd:IMPS/{ref()}/Amazon Sel/KKBK/X{random.randint(1000,9999)}/PCXQJ", round(random.uniform(800, 4000), 2), "income", "credit"
            elif kind < 0.7:
                desc, amount, cat, typ = f"NEFT/SALARY CREDIT/{ref()}", round(random.uniform(15000, 45000), 2), "income", "credit"
            else:
                desc, amount, cat, typ = "CHRG:SMS ALERT FEE FOR THE MONTH", round(random.uniform(2, 25), 2), "bills", "debit"
            out.append({"date": when, "description": desc, "amount": amount, "type": typ, "category": cat})
            continue

        name, cat, lo, hi, bias, note = random.choice(MERCHANTS)
        # Weekend-biased merchants get resampled onto a weekend sometimes, which
        # is what gives K-Means a real "weekend splurge" cluster to find.
        if bias > 1.2 and not weekend and random.random() < 0.35:
            when += timedelta(days=(5 - when.weekday()) % 7)
        if name in MONTHLY_BILLS:
            key = (name, when.month)
            if key in billed:
                continue
            billed.add(key)
            when = when.replace(day=min(random.randint(1, 5), 28))

        out.append({
            "date": when,
            "description": describe(name, note),
            "amount": round(random.uniform(lo, hi), 2),
            "type": "debit",
            "category": cat,
        })

    out.sort(key=lambda r: r["date"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=800)
    ap.add_argument("--out", default="data/synthetic_statement.csv")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--opening", type=float, default=5000.0)
    args = ap.parse_args()

    records = generate(args.rows, date(2026, 3, 1), args.seed)

    balance = args.opening
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "description", "amount", "type", "balance", "category"])
        for r in records:
            balance += r["amount"] if r["type"] == "credit" else -r["amount"]
            w.writerow([
                r["date"].isoformat(), r["description"], f"{r['amount']:.2f}",
                r["type"], f"{balance:.2f}", r["category"],
            ])
    print(f"{len(records)} rows -> {args.out}")


if __name__ == "__main__":
    main()
