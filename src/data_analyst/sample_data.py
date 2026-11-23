"""Generates a synthetic e-commerce SQLite database (seeded, so results are reproducible).

Run:  python -m data_analyst.sample_data
"""
from __future__ import annotations

import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

BUSINESS_NOTES = (
    "Revenue = SUM(order_items.quantity * order_items.unit_price), counting only orders with status 'delivered' "
    "unless the user asks otherwise. An 'order' is a row in orders; a 'customer' is a row in customers."
)

SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    city TEXT,           -- Cairo, Giza, Alexandria, Mansoura, Tanta, Aswan, Luxor
    signup_date TEXT     -- YYYY-MM-DD
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,       -- Electronics, Groceries, Fashion, Home, Books, Sports
    price REAL           -- list price in EGP
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TEXT,     -- YYYY-MM-DD
    status TEXT          -- delivered, cancelled, pending
);
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER,
    unit_price REAL      -- price paid per unit in EGP
);
"""

CITIES = ["Cairo", "Giza", "Alexandria", "Mansoura", "Tanta", "Aswan", "Luxor"]
CITY_WEIGHTS = [30, 18, 20, 8, 8, 8, 8]
FIRST = ["Ahmed", "Mohamed", "Mahmoud", "Omar", "Youssef", "Ali", "Hassan", "Karim", "Sara", "Mona", "Nour", "Salma", "Hana", "Reem", "Dina", "Laila"]
LAST = ["Hassan", "Ibrahim", "Mostafa", "Farouk", "Saleh", "Nabil", "Adel", "Samir", "Fathy", "Khaled"]
PRODUCTS = {
    "Electronics": ["Wireless Mouse", "USB-C Cable", "Bluetooth Speaker", "Power Bank", "Smart Watch", "Earbuds"],
    "Groceries": ["Olive Oil 1L", "Basmati Rice 5kg", "Black Tea 250g", "Dates 500g", "Honey 500g", "Coffee 250g"],
    "Fashion": ["Cotton T-Shirt", "Denim Jeans", "Running Shoes", "Leather Belt", "Winter Jacket", "Backpack"],
    "Home": ["Table Lamp", "Cookware Set", "Bed Sheets", "Storage Box", "Wall Clock", "Vacuum Flask"],
    "Books": ["Python Basics", "Machine Learning Intro", "Data Structures", "Arabic Poetry", "History of Egypt", "Cookbook"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Football", "Jump Rope", "Water Bottle", "Cycling Gloves"],
}
PRICE_RANGE = {"Electronics": (150, 1800), "Groceries": (40, 350), "Fashion": (120, 1500), "Home": (80, 1200), "Books": (60, 400), "Sports": (70, 900)}


def create_sample_db(path: str | Path, seed: int = 42, n_customers: int = 200, n_orders: int = 1500) -> Path:
    rng = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    start, end = date(2025, 1, 1), date(2026, 10, 31)
    span = (end - start).days

    customers = []
    for i in range(1, n_customers + 1):
        signup = start + timedelta(days=rng.randint(0, span // 2))
        customers.append((i, f"{rng.choice(FIRST)} {rng.choice(LAST)}", rng.choices(CITIES, CITY_WEIGHTS)[0], signup.isoformat()))

    products = []
    pid = 1
    for category, names in PRODUCTS.items():
        lo, hi = PRICE_RANGE[category]
        for name in names:
            products.append((pid, name, category, round(rng.uniform(lo, hi), 2)))
            pid += 1

    orders, items = [], []
    item_id = 1
    for oid in range(1, n_orders + 1):
        cust = rng.choice(customers)
        signup = date.fromisoformat(cust[3])
        order_date = signup + timedelta(days=rng.randint(0, max(1, (end - signup).days)))
        status = rng.choices(["delivered", "cancelled", "pending"], [82, 12, 6])[0]
        if order_date < end - timedelta(days=14) and status == "pending":
            status = "delivered"
        orders.append((oid, cust[0], order_date.isoformat(), status))
        for p in rng.sample(products, rng.randint(1, 4)):
            items.append((item_id, oid, p[0], rng.randint(1, 3), round(p[3] * rng.uniform(0.9, 1.0), 2)))
            item_id += 1

    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)
        conn.executemany("INSERT INTO products VALUES (?,?,?,?)", products)
        conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
        conn.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)
        conn.commit()
    finally:
        conn.close()
    return path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "data/shop.db"
    print(f"Created {create_sample_db(target)}")
