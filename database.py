import hashlib
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_FILE = "xtreem.db"

DEFAULT_SERVICES = [
    ("Basic Wash", "Car", 499, "30-45 min"),
    ("Foam Wash", "Car", 699, "45-60 min"),
    ("Interior Cleaning", "Car", 999, "2-3 hrs"),
    ("Wax Polish", "Car", 1499, "2-3 hrs"),
    ("Deep Cleaning", "Car", 2999, "2-3 days"),
    ("Bike Foam Wash", "Bike", 199, "20-30 min"),
    ("Bike Deep Wash", "Bike", 299, "45-60 min"),
]

DEFAULT_MEMBERSHIPS = [
    ("Silver", 1999, "2 Basic Washes + 2 Foam Washes"),
    ("Gold", 3999, "2 Foam Washes + 1 Deep Cleaning"),
    ("Platinum", 5999, "4 Foam Washes + 1 Deep Cleaning + 1 Wax Polish"),
]

PAYMENT_METHODS = {"Cash", "UPI", "Card", "Bank Transfer", "Other"}
PAYMENT_STATUSES = {"unpaid", "paid", "partial", "refunded"}

VEHICLE_CATALOG = {
    "Car": {
        "Maruti Suzuki": ["Alto", "Alto K10", "S-Presso", "Celerio", "WagonR", "Swift", "Dzire", "Baleno", "Fronx", "Brezza", "Ertiga", "XL6", "Ciaz", "Grand Vitara", "Jimny", "Invicto"],
        "Hyundai": ["Santro", "Grand i10 Nios", "i20", "Aura", "Verna", "Exter", "Venue", "Creta", "Alcazar", "Tucson", "Kona Electric", "Ioniq 5"],
        "Tata": ["Tiago", "Tigor", "Altroz", "Punch", "Nexon", "Curvv", "Harrier", "Safari", "Tiago EV", "Tigor EV", "Punch EV", "Nexon EV"],
        "Mahindra": ["KUV100", "XUV 3XO", "Bolero", "Bolero Neo", "Scorpio", "Scorpio N", "Thar", "Thar Roxx", "XUV700", "Marazzo", "XUV400"],
        "Honda": ["Brio", "Jazz", "Amaze", "City", "City eHEV", "WR-V", "Elevate", "Civic", "Accord", "CR-V"],
        "Toyota": ["Glanza", "Urban Cruiser Taisor", "Rumion", "Urban Cruiser Hyryder", "Innova Crysta", "Innova Hycross", "Fortuner", "Hilux", "Camry", "Vellfire", "Land Cruiser"],
        "Kia": ["Sonet", "Seltos", "Carens", "Carnival", "EV6"],
        "Skoda": ["Kushaq", "Slavia", "Kylaq", "Octavia", "Superb", "Kodiaq"],
        "Volkswagen": ["Polo", "Ameo", "Taigun", "Virtus", "Tiguan"],
        "MG": ["Comet EV", "Astor", "Hector", "Hector Plus", "ZS EV", "Gloster"],
        "Renault": ["Kwid", "Triber", "Kiger", "Duster"],
        "Nissan": ["Magnite", "Kicks", "Terrano", "X-Trail"],
        "Citroen": ["C3", "eC3", "C3 Aircross", "Basalt", "C5 Aircross"],
        "Jeep": ["Compass", "Meridian", "Wrangler", "Grand Cherokee"],
        "Mercedes-Benz": ["A-Class", "C-Class", "E-Class", "S-Class", "GLA", "GLC", "GLE", "GLS"],
        "BMW": ["2 Series", "3 Series", "5 Series", "7 Series", "X1", "X3", "X5", "X7"],
        "Audi": ["A4", "A6", "Q3", "Q5", "Q7", "Q8", "e-tron"],
        "Force": ["Gurkha", "Trax", "Traveller"],
        "Isuzu": ["D-Max", "V-Cross", "MU-X"],
    },
    "Bike": {
        "Hero": ["Splendor Plus", "HF Deluxe", "Passion Plus", "Glamour", "Super Splendor", "Xtreme 125R", "Xtreme 160R", "Xtreme 200S", "Xpulse 200"],
        "Honda": ["Activa", "Dio", "Shine", "SP 125", "Unicorn", "Hornet 2.0", "CB200X", "CB350", "Hness CB350"],
        "TVS": ["XL100", "Jupiter", "Ntorq", "Radeon", "Raider", "Apache RTR 160", "Apache RTR 200", "Apache RR 310", "iQube"],
        "Bajaj": ["CT 110", "Platina", "Pulsar 125", "Pulsar 150", "Pulsar NS160", "Pulsar NS200", "Pulsar N250", "Avenger", "Dominar 400", "Chetak"],
        "Royal Enfield": ["Bullet 350", "Classic 350", "Hunter 350", "Meteor 350", "Himalayan", "Scram 411", "Guerrilla 450", "Interceptor 650", "Continental GT 650", "Super Meteor 650"],
        "Yamaha": ["Fascino", "RayZR", "FZ", "FZS", "FZ-X", "MT-15", "R15", "Aerox"],
        "Suzuki": ["Access 125", "Avenis", "Burgman Street", "Gixxer", "Gixxer SF", "V-Strom SX", "Hayabusa"],
        "KTM": ["125 Duke", "200 Duke", "250 Duke", "390 Duke", "RC 200", "RC 390", "390 Adventure"],
        "Jawa Yezdi": ["Jawa 350", "Jawa 42", "Perak", "Roadster", "Scrambler", "Adventure"],
        "Ather": ["450S", "450X", "450 Apex", "Rizta"],
        "Ola Electric": ["S1 X", "S1 Air", "S1 Pro"],
        "Revolt": ["RV400"],
        "Vespa": ["VXL", "SXL"],
        "Aprilia": ["SR 125", "SR 160", "SXR 160", "RS 457"],
        "Kawasaki": ["Ninja 300", "Ninja 500", "Ninja 650", "Z650", "Versys 650"],
        "Triumph": ["Speed 400", "Scrambler 400 X", "Trident 660", "Tiger Sport 660"],
        "Harley-Davidson": ["X440", "Nightster", "Sportster S"],
    },
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) >= 10:
        normalized = digits[-10:]
        return f"+91{normalized}"
    return digits


def _normalize_plate(plate: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (plate or "").upper())


def _looks_like_number_plate(value: str) -> bool:
    plate = _normalize_plate(value)
    return re.fullmatch(r"[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}", plate) is not None


def customer_token(phone: str) -> str:
    secret = os.getenv("QR_SECRET") or os.getenv("ADMIN_PASSWORD") or "xtreem-car-care"
    return hashlib.sha256(f"{secret}:{_normalize_phone(phone)}".encode("utf-8")).hexdigest()[:20]


def _customer_code(customer_id: int) -> str:
    return f"XSTCC{customer_id:03d}"


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        _move_legacy_bookings(conn)
        _create_tables(conn)
        _ensure_vehicle_brand_column(conn)
        _ensure_booking_payment_columns(conn)
        _ensure_customer_code_column(conn)
        _ensure_membership_payment_proof_column(conn)
        _seed_business_tables(conn)
        _seed_vehicle_catalog(conn)
        _migrate_legacy_data(conn)
        _backfill_booking_payments(conn)
        _cleanup_plate_only_vehicle_models(conn)
        _normalize_existing_number_plates(conn)
        _normalize_existing_phone_numbers(conn)
        _backfill_status_history(conn)


def _table_exists(conn, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _columns(conn, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _move_legacy_bookings(conn):
    cols = _columns(conn, "bookings")
    if cols and "customer_id" not in cols and not _table_exists(conn, "legacy_bookings"):
        conn.execute("ALTER TABLE bookings RENAME TO legacy_bookings")


def _create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            phone            TEXT NOT NULL UNIQUE,
            customer_code    TEXT NOT NULL UNIQUE,
            token            TEXT NOT NULL UNIQUE,
            whatsapp_opt_in  INTEGER NOT NULL DEFAULT 1,
            notes            TEXT NOT NULL DEFAULT '',
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id   INTEGER NOT NULL,
            vehicle_type  TEXT NOT NULL,
            vehicle_brand TEXT NOT NULL DEFAULT '',
            vehicle_model TEXT NOT NULL,
            number_plate  TEXT NOT NULL DEFAULT '',
            color         TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            UNIQUE(customer_id, number_plate, vehicle_model),
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_brands (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_type  TEXT NOT NULL,
            name          TEXT NOT NULL,
            active        INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL,
            UNIQUE(vehicle_type, name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_models (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id      INTEGER NOT NULL,
            name          TEXT NOT NULL,
            active        INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL,
            UNIQUE(brand_id, name),
            FOREIGN KEY(brand_id) REFERENCES vehicle_brands(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS service_catalog (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            category    TEXT NOT NULL,
            base_price  INTEGER NOT NULL DEFAULT 0,
            duration    TEXT NOT NULL DEFAULT '',
            active      INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL
        )
    """)


def _ensure_customer_code_column(conn):
    if "customer_code" not in _columns(conn, "customers"):
        conn.execute("ALTER TABLE customers ADD COLUMN customer_code TEXT NOT NULL DEFAULT ''")
    customers_missing_code = conn.execute(
        "SELECT id FROM customers WHERE customer_code = '' OR customer_code IS NULL"
    ).fetchall()
    for row in customers_missing_code:
        conn.execute(
            "UPDATE customers SET customer_code = ? WHERE id = ?",
            (_customer_code(row["id"]), row["id"]),
        )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_customer_code ON customers(customer_code)"
    )


def _ensure_vehicle_brand_column(conn):
    if "vehicle_brand" not in _columns(conn, "vehicles"):
        conn.execute("ALTER TABLE vehicles ADD COLUMN vehicle_brand TEXT NOT NULL DEFAULT ''")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER NOT NULL,
            vehicle_id      INTEGER NOT NULL,
            service_id      INTEGER,
            service_name    TEXT NOT NULL,
            preferred_date  TEXT NOT NULL,
            preferred_time  TEXT NOT NULL,
            pickup_address  TEXT NOT NULL DEFAULT '',
            payment_method  TEXT NOT NULL DEFAULT '',
            payment_status  TEXT NOT NULL DEFAULT 'unpaid',
            status          TEXT NOT NULL DEFAULT 'pending',
            booked_at       TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY(service_id) REFERENCES service_catalog(id)
        )
    """)


def _ensure_booking_payment_columns(conn):
    if "payment_method" not in _columns(conn, "bookings"):
        conn.execute("ALTER TABLE bookings ADD COLUMN payment_method TEXT NOT NULL DEFAULT ''")
    if "payment_status" not in _columns(conn, "bookings"):
        conn.execute("ALTER TABLE bookings ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'unpaid'")


def _ensure_membership_payment_proof_column(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_memberships (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id    INTEGER NOT NULL,
            customer_phone TEXT NOT NULL DEFAULT '',
            membership_id  INTEGER NOT NULL,
            starts_on      TEXT NOT NULL,
            ends_on        TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'active',
            payment_proof  TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(membership_id) REFERENCES memberships(id)
        )
    """)
    if "customer_phone" not in _columns(conn, "customer_memberships"):
        conn.execute("ALTER TABLE customer_memberships ADD COLUMN customer_phone TEXT NOT NULL DEFAULT ''")
    if "payment_proof" not in _columns(conn, "customer_memberships"):
        conn.execute("ALTER TABLE customer_memberships ADD COLUMN payment_proof TEXT NOT NULL DEFAULT ''")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wash_records (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id    INTEGER UNIQUE,
            customer_id   INTEGER NOT NULL,
            vehicle_id    INTEGER NOT NULL,
            service_id    INTEGER,
            service_name  TEXT NOT NULL,
            wash_date     TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'completed',
            notes         TEXT NOT NULL DEFAULT '',
            created_at    TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY(service_id) REFERENCES service_catalog(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id     INTEGER,
            customer_id    INTEGER NOT NULL,
            amount         INTEGER NOT NULL DEFAULT 0,
            method         TEXT NOT NULL DEFAULT '',
            payment_status TEXT NOT NULL DEFAULT 'unpaid',
            reference      TEXT NOT NULL DEFAULT '',
            paid_at        TEXT,
            created_at     TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id),
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON payments(booking_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_customer_id ON payments(customer_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memberships (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            monthly_price INTEGER NOT NULL,
            description   TEXT NOT NULL DEFAULT '',
            active        INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_memberships (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id    INTEGER NOT NULL,
            customer_phone TEXT NOT NULL DEFAULT '',
            membership_id  INTEGER NOT NULL,
            starts_on      TEXT NOT NULL,
            ends_on        TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'active',
            payment_proof  TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(membership_id) REFERENCES memberships(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS booking_status_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id  INTEGER NOT NULL,
            old_status  TEXT NOT NULL DEFAULT '',
            new_status  TEXT NOT NULL,
            changed_at  TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id)
        )
    """)


def _seed_business_tables(conn):
    for name, category, price, duration in DEFAULT_SERVICES:
        conn.execute("""
            INSERT OR IGNORE INTO service_catalog
              (name, category, base_price, duration, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, category, price, duration, _now()))

    for name, price, description in DEFAULT_MEMBERSHIPS:
        conn.execute("""
            INSERT OR IGNORE INTO memberships
              (name, monthly_price, description, created_at)
            VALUES (?, ?, ?, ?)
        """, (name, price, description, _now()))


def _seed_vehicle_catalog(conn):
    for vehicle_type, brands in VEHICLE_CATALOG.items():
        for brand_name, models in brands.items():
            cursor = conn.execute("""
                INSERT OR IGNORE INTO vehicle_brands
                  (vehicle_type, name, created_at)
                VALUES (?, ?, ?)
            """, (vehicle_type, brand_name, _now()))
            brand = conn.execute("""
                SELECT id FROM vehicle_brands
                WHERE vehicle_type = ? AND name = ?
            """, (vehicle_type, brand_name)).fetchone()
            brand_id = brand["id"] if brand else cursor.lastrowid
            for model_name in models:
                conn.execute("""
                    INSERT OR IGNORE INTO vehicle_models
                      (brand_id, name, created_at)
                    VALUES (?, ?, ?)
                """, (brand_id, model_name, _now()))


def _migrate_legacy_data(conn):
    sources = []
    if _table_exists(conn, "bookings_archive"):
        sources.append("bookings_archive")
    if _table_exists(conn, "legacy_bookings"):
        sources.append("legacy_bookings")

    for source in sources:
        cols = _columns(conn, source)
        if not {"id", "name", "phone", "vehicle_type", "vehicle_model", "service"}.issubset(cols):
            continue
        plate_expr = "vehicle_plate" if "vehicle_plate" in cols else "'' AS vehicle_plate"
        rows = conn.execute(f"""
            SELECT id, name, phone, vehicle_type, vehicle_model, {plate_expr}, service,
                   preferred_date, preferred_time, COALESCE(pickup_address, '') AS pickup_address,
                   COALESCE(status, 'pending') AS status, booked_at
            FROM {source}
            ORDER BY id
        """).fetchall()

        for row in rows:
            customer_id = _upsert_customer(conn, row["name"], row["phone"])
            vehicle_id = _upsert_vehicle(
                conn,
                customer_id,
                row["vehicle_type"],
                "",
                row["vehicle_model"],
                row["vehicle_plate"],
            )
            service_id = _service_id(conn, row["service"])
            conn.execute("""
                INSERT OR IGNORE INTO bookings
                  (id, customer_id, vehicle_id, service_id, service_name,
                   preferred_date, preferred_time, pickup_address, status, booked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["id"], customer_id, vehicle_id, service_id, row["service"],
                row["preferred_date"], row["preferred_time"], row["pickup_address"],
                row["status"], row["booked_at"],
            ))
            if row["status"] == "completed":
                _upsert_wash_record(conn, row["id"], row["status"])


def _backfill_status_history(conn):
    rows = conn.execute("""
        SELECT b.id, b.status, b.booked_at
        FROM bookings b
        LEFT JOIN booking_status_history h ON h.booking_id = b.id
        WHERE h.id IS NULL
    """).fetchall()
    for row in rows:
        conn.execute("""
            INSERT INTO booking_status_history
              (booking_id, old_status, new_status, changed_at)
            VALUES (?, '', ?, ?)
        """, (row["id"], row["status"], row["booked_at"]))


def _backfill_booking_payments(conn):
    rows = conn.execute("""
        SELECT b.id, b.customer_id, b.service_name, b.booked_at
        FROM bookings b
        LEFT JOIN payments p ON p.booking_id = b.id
        WHERE p.id IS NULL
    """).fetchall()
    for row in rows:
        conn.execute("""
            INSERT INTO payments
              (booking_id, customer_id, amount, method, payment_status, reference, paid_at, created_at)
            VALUES (?, ?, ?, '', 'unpaid', '', NULL, ?)
        """, (row["id"], row["customer_id"], _service_amount(conn, row["service_name"]), row["booked_at"]))
    conn.execute("""
        UPDATE bookings
        SET
          payment_method = COALESCE((
              SELECT method FROM payments
              WHERE booking_id = bookings.id
              ORDER BY id ASC
              LIMIT 1
          ), payment_method, ''),
          payment_status = COALESCE((
              SELECT payment_status FROM payments
              WHERE booking_id = bookings.id
              ORDER BY id ASC
              LIMIT 1
          ), payment_status, 'unpaid')
    """)


def _cleanup_plate_only_vehicle_models(conn):
    rows = conn.execute("""
        SELECT id, customer_id, vehicle_model, number_plate
        FROM vehicles
        WHERE COALESCE(number_plate, '') = ''
    """).fetchall()
    for row in rows:
        if _looks_like_number_plate(row["vehicle_model"]):
            number_plate = _normalize_plate(row["vehicle_model"])
            model = "Model not added"
            existing = conn.execute("""
                SELECT id FROM vehicles
                WHERE customer_id = ? AND number_plate = ? AND vehicle_model = ? AND id != ?
            """, (row["customer_id"], number_plate, model, row["id"])).fetchone()
            if existing:
                conn.execute("UPDATE bookings SET vehicle_id = ? WHERE vehicle_id = ?", (existing["id"], row["id"]))
                conn.execute("UPDATE wash_records SET vehicle_id = ? WHERE vehicle_id = ?", (existing["id"], row["id"]))
                conn.execute("DELETE FROM vehicles WHERE id = ?", (row["id"],))
                continue
            conn.execute("""
                UPDATE vehicles
                SET number_plate = ?, vehicle_model = 'Model not added', updated_at = ?
                WHERE id = ?
            """, (number_plate, _now(), row["id"]))


def _normalize_existing_number_plates(conn):
    rows = conn.execute("""
        SELECT id, customer_id, vehicle_model, number_plate
        FROM vehicles
        WHERE COALESCE(number_plate, '') != ''
    """).fetchall()
    for row in rows:
        normalized = _normalize_plate(row["number_plate"])
        if normalized == row["number_plate"]:
            continue

        existing = conn.execute("""
            SELECT id FROM vehicles
            WHERE customer_id = ? AND number_plate = ? AND vehicle_model = ? AND id != ?
        """, (row["customer_id"], normalized, row["vehicle_model"], row["id"])).fetchone()
        if existing:
            conn.execute("UPDATE bookings SET vehicle_id = ? WHERE vehicle_id = ?", (existing["id"], row["id"]))
            conn.execute("UPDATE wash_records SET vehicle_id = ? WHERE vehicle_id = ?", (existing["id"], row["id"]))
            conn.execute("DELETE FROM vehicles WHERE id = ?", (row["id"],))
            continue

        conn.execute("""
            UPDATE vehicles
            SET number_plate = ?, updated_at = ?
            WHERE id = ?
        """, (normalized, _now(), row["id"]))


def _normalize_existing_phone_numbers(conn):
    if not _table_exists(conn, "customers"):
        return

    for row in conn.execute("SELECT id, phone FROM customers").fetchall():
        normalized = _normalize_phone(row["phone"])
        if normalized and normalized != row["phone"]:
            conn.execute("UPDATE customers SET phone = ? WHERE id = ?", (normalized, row["id"]))

    if _table_exists(conn, "customer_memberships"):
        for row in conn.execute("SELECT id, customer_phone FROM customer_memberships").fetchall():
            normalized = _normalize_phone(row["customer_phone"])
            if normalized and normalized != row["customer_phone"]:
                conn.execute("UPDATE customer_memberships SET customer_phone = ? WHERE id = ?", (normalized, row["id"]))


def _upsert_customer(conn, name: str, phone: str) -> int:
    normalized_phone = _normalize_phone(phone) or phone.strip()
    token = customer_token(normalized_phone)
    existing = conn.execute("SELECT id, customer_code FROM customers WHERE phone = ?", (normalized_phone,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE customers SET name = ?, updated_at = ? WHERE id = ?",
            (name.strip(), _now(), existing["id"]),
        )
        if not existing["customer_code"]:
            conn.execute(
                "UPDATE customers SET customer_code = ? WHERE id = ?",
                (_customer_code(existing["id"]), existing["id"]),
            )
        return existing["id"]

    next_id = conn.execute("SELECT IFNULL(MAX(id), 0) + 1 AS next_id FROM customers").fetchone()["next_id"]
    customer_code = _customer_code(next_id)
    cursor = conn.execute("""
        INSERT INTO customers (name, phone, customer_code, token, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name.strip(), normalized_phone, customer_code, token, _now(), _now()))
    return cursor.lastrowid


def _upsert_vehicle(conn, customer_id: int, vehicle_type: str, vehicle_brand: str, vehicle_model: str, plate: str) -> int:
    number_plate = _normalize_plate(plate)
    brand = vehicle_brand.strip()
    model = vehicle_model.strip()
    if not number_plate and _looks_like_number_plate(model):
        number_plate = _normalize_plate(model)
        model = "Model not added"
    existing = conn.execute("""
        SELECT id FROM vehicles
        WHERE customer_id = ? AND number_plate = ? AND vehicle_model = ?
    """, (customer_id, number_plate, model)).fetchone()
    if existing:
        conn.execute("""
            UPDATE vehicles
            SET vehicle_type = ?, vehicle_brand = ?, updated_at = ?
            WHERE id = ?
        """, (vehicle_type, brand, _now(), existing["id"]))
        return existing["id"]

    cursor = conn.execute("""
        INSERT INTO vehicles
          (customer_id, vehicle_type, vehicle_brand, vehicle_model, number_plate, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (customer_id, vehicle_type, brand, model, number_plate, _now(), _now()))
    return cursor.lastrowid


def _service_id(conn, service_name: str) -> int | None:
    clean_name = service_name.strip()
    row = conn.execute("SELECT id FROM service_catalog WHERE name = ?", (clean_name,)).fetchone()
    if row:
        return row["id"]

    cursor = conn.execute("""
        INSERT INTO service_catalog (name, category, base_price, duration, created_at)
        VALUES (?, 'Custom', 0, '', ?)
    """, (clean_name, _now()))
    return cursor.lastrowid


def _clean_payment_method(method: str) -> str:
    value = (method or "").strip()
    if not value:
        return ""
    for allowed in PAYMENT_METHODS:
        if value.lower() == allowed.lower():
            return allowed
    return "Other"


def _clean_payment_status(status: str) -> str:
    value = (status or "unpaid").strip().lower()
    return value if value in PAYMENT_STATUSES else "unpaid"


def _service_amount(conn, service_name: str) -> int:
    clean_name = (service_name or "").strip()
    rows = conn.execute("""
        SELECT name, base_price
        FROM service_catalog
        WHERE base_price > 0
        ORDER BY LENGTH(name) DESC
    """).fetchall()
    for row in rows:
        if row["name"].lower() in clean_name.lower():
            return row["base_price"]

    amount_match = re.search(r"(?:rs\.?|inr|₹)\s*([0-9][0-9,]*)", clean_name, re.IGNORECASE)
    if amount_match:
        return int(amount_match.group(1).replace(",", ""))
    return 0


def _payment_paid_at(status: str, paid_at: str | None = None) -> str | None:
    clean_status = _clean_payment_status(status)
    if clean_status in {"paid", "partial"}:
        return paid_at or _now()
    return paid_at or None


def _upsert_booking_payment(conn, booking_id: int, method: str = "", status: str = "unpaid", amount: int | None = None, reference: str = "", paid_at: str | None = None):
    booking = conn.execute("""
        SELECT id, customer_id, service_name
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()
    if not booking:
        return False

    clean_status = _clean_payment_status(status)
    clean_method = _clean_payment_method(method)
    payment_amount = _service_amount(conn, booking["service_name"]) if amount is None else max(int(amount), 0)
    payment_paid_at = _payment_paid_at(clean_status, paid_at)
    existing = conn.execute("""
        SELECT id FROM payments
        WHERE booking_id = ?
        ORDER BY id ASC
        LIMIT 1
    """, (booking_id,)).fetchone()

    if existing:
        conn.execute("""
            UPDATE payments
            SET customer_id = ?, amount = ?, method = ?, payment_status = ?,
                reference = ?, paid_at = ?
            WHERE id = ?
        """, (
            booking["customer_id"], payment_amount, clean_method, clean_status,
            reference.strip(), payment_paid_at, existing["id"],
        ))
    else:
        conn.execute("""
            INSERT INTO payments
              (booking_id, customer_id, amount, method, payment_status, reference, paid_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            booking_id, booking["customer_id"], payment_amount, clean_method, clean_status,
            reference.strip(), payment_paid_at, _now(),
        ))
    conn.execute("""
        UPDATE bookings
        SET payment_method = ?, payment_status = ?
        WHERE id = ?
    """, (clean_method, clean_status, booking_id))
    return True


def insert_booking(data: dict):
    with _conn() as conn:
        customer_id = _upsert_customer(conn, data["name"], data["phone"])
        vehicle_id = _upsert_vehicle(
            conn,
            customer_id,
            data["vehicle_type"],
            data.get("vehicle_brand", ""),
            data["vehicle_model"],
            data.get("vehicle_plate", ""),
        )
        service_id = _service_id(conn, data["service"])
        booked_at = _now()
        cursor = conn.execute("""
            INSERT INTO bookings
              (customer_id, vehicle_id, service_id, service_name,
               preferred_date, preferred_time, pickup_address, payment_method,
               payment_status, status, booked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unpaid', 'pending', ?)
        """, (
            customer_id,
            vehicle_id,
            service_id,
            data["service"],
            data["preferred_date"],
            data["preferred_time"],
            data.get("pickup_address", ""),
            _clean_payment_method(data.get("payment_method", "")),
            booked_at,
        ))
        booking_id = cursor.lastrowid
        conn.execute("""
            INSERT INTO booking_status_history
              (booking_id, old_status, new_status, changed_at)
            VALUES (?, '', 'pending', ?)
        """, (booking_id, booked_at))
        _upsert_booking_payment(
            conn,
            booking_id,
            method=data.get("payment_method", ""),
            status=data.get("payment_status", "unpaid"),
        )


def insert_customer_membership(name: str, phone: str, membership_id: int, duration_days: int = 30, payment_proof: str = '') -> int:
    starts_on = datetime.now().strftime("%Y-%m-%d")
    ends_on = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d")
    normalized_phone = _normalize_phone(phone) or phone.strip()
    with _conn() as conn:
        customer_id = _upsert_customer(conn, name, phone)
        cursor = conn.execute("""
            INSERT INTO customer_memberships
              (customer_id, customer_phone, membership_id, starts_on, ends_on, status, payment_proof, created_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        """, (customer_id, normalized_phone, membership_id, starts_on, ends_on, payment_proof, _now()))
        return cursor.lastrowid


def get_active_memberships() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT id, name, monthly_price, description
            FROM memberships
            WHERE active = 1
            ORDER BY monthly_price ASC
        """).fetchall()
        return [dict(row) for row in rows]


def _booking_rows(conn, where_clause: str = "", params: tuple = ()) -> list[dict]:
    rows = conn.execute(f"""
        SELECT
          b.id,
          c.name,
          c.phone,
          c.customer_code,
          c.token AS customer_token,
          v.vehicle_type,
          v.vehicle_brand,
          v.vehicle_model,
          v.number_plate AS vehicle_plate,
          b.service_name AS service,
          b.preferred_date,
          b.preferred_time,
          b.pickup_address,
          b.payment_method,
          b.payment_status,
          b.status,
          b.booked_at,
          b.customer_id,
          b.vehicle_id,
          b.service_id,
          p.id AS payment_id,
          p.amount AS payment_amount,
          p.method AS linked_payment_method,
          p.payment_status AS linked_payment_status,
          p.reference AS payment_reference,
          p.paid_at AS payment_paid_at
        FROM bookings b
        JOIN customers c ON c.id = b.customer_id
        JOIN vehicles v ON v.id = b.vehicle_id
        LEFT JOIN payments p ON p.id = (
            SELECT id FROM payments
            WHERE booking_id = b.id
            ORDER BY id ASC
            LIMIT 1
        )
        {where_clause}
        ORDER BY b.id DESC
    """, params).fetchall()
    return [dict(row) for row in rows]


def get_all_bookings() -> list[dict]:
    with _conn() as conn:
        return _booking_rows(conn)


def get_vehicle_catalog() -> dict:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT
              b.vehicle_type,
              b.name AS brand,
              m.name AS model
            FROM vehicle_brands b
            JOIN vehicle_models m ON m.brand_id = b.id
            WHERE b.active = 1 AND m.active = 1
            ORDER BY b.vehicle_type, b.name, m.name
        """).fetchall()

    catalog: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        catalog.setdefault(row["vehicle_type"], {}).setdefault(row["brand"], []).append(row["model"])
    return catalog


def get_business_stats() -> dict:
    with _conn() as conn:
        bookings = conn.execute("SELECT status, COUNT(*) AS count FROM bookings GROUP BY status").fetchall()
        stats = {row["status"]: row["count"] for row in bookings}
        today = datetime.now().strftime("%Y-%m-%d")
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")

        def revenue_total(where_clause: str = "", params: tuple = ()) -> int:
            row = conn.execute(f"""
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM payments
                WHERE payment_status IN ('paid', 'partial')
                {where_clause}
            """, params).fetchone()
            return int(row["total"] or 0)

        revenue = {
            "today": revenue_total("AND DATE(COALESCE(paid_at, created_at)) = ?", (today,)),
            "week": revenue_total("AND DATE(COALESCE(paid_at, created_at)) >= ?", (week_start,)),
            "month": revenue_total("AND DATE(COALESCE(paid_at, created_at)) >= ?", (month_start,)),
            "total": revenue_total(),
        }
        collected_count = conn.execute("""
            SELECT COUNT(*)
            FROM payments
            WHERE payment_status IN ('paid', 'partial')
        """).fetchone()[0]
        pending_revenue = conn.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE payment_status = 'unpaid'
        """).fetchone()[0]
        return {
            "total": sum(stats.values()),
            "pending": stats.get("pending", 0),
            "confirmed": stats.get("confirmed", 0),
            "completed": stats.get("completed", 0),
            "cancelled": stats.get("cancelled", 0),
            "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "vehicles": conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],
            "washes": conn.execute("SELECT COUNT(*) FROM wash_records").fetchone()[0],
            "revenue": revenue,
            "pending_revenue": int(pending_revenue or 0),
            "collected_payments": collected_count,
        }


def _upsert_wash_record(conn, booking_id: int, status: str):
    booking = conn.execute("""
        SELECT customer_id, vehicle_id, service_id, service_name, preferred_date
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()
    if not booking:
        return

    if status == "completed":
        conn.execute("""
            INSERT INTO wash_records
              (booking_id, customer_id, vehicle_id, service_id, service_name, wash_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'completed', ?)
            ON CONFLICT(booking_id) DO UPDATE SET
              service_id = excluded.service_id,
              service_name = excluded.service_name,
              wash_date = excluded.wash_date,
              status = 'completed'
        """, (
            booking_id,
            booking["customer_id"],
            booking["vehicle_id"],
            booking["service_id"],
            booking["service_name"],
            booking["preferred_date"],
            _now(),
        ))
    else:
        conn.execute("DELETE FROM wash_records WHERE booking_id = ?", (booking_id,))


def update_booking_status(booking_id: int, status: str):
    with _conn() as conn:
        row = conn.execute("SELECT status FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return
        old_status = row["status"]
        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
        conn.execute("""
            INSERT INTO booking_status_history
              (booking_id, old_status, new_status, changed_at)
            VALUES (?, ?, ?, ?)
        """, (booking_id, old_status, status, _now()))
        _upsert_wash_record(conn, booking_id, status)


def get_booking_status(booking_id: int) -> str | None:
    with _conn() as conn:
        row = conn.execute("SELECT status FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return row["status"] if row else None


def get_booking_payment_info(booking_id: int) -> dict | None:
    with _conn() as conn:
        payment = conn.execute(
            "SELECT amount, method, payment_status, reference, paid_at"
            " FROM payments WHERE booking_id = ?"
            " ORDER BY id DESC LIMIT 1",
            (booking_id,),
        ).fetchone()
        if payment:
            return {
                "amount": payment["amount"],
                "method": payment["method"],
                "payment_status": payment["payment_status"],
                "reference": payment["reference"],
                "paid_at": payment["paid_at"],
            }
        row = conn.execute(
            "SELECT payment_status, payment_method FROM bookings WHERE id = ?",
            (booking_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "amount": 0,
            "method": row["payment_method"],
            "payment_status": row["payment_status"],
            "reference": "",
            "paid_at": None,
        }


def update_booking_vehicle(booking_id: int, vehicle_id: int):
    with _conn() as conn:
        booking = conn.execute("SELECT customer_id, vehicle_id FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not booking:
            return False
        vehicle = conn.execute("SELECT customer_id FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
        if not vehicle or vehicle["customer_id"] != booking["customer_id"]:
            return False
        conn.execute("UPDATE bookings SET vehicle_id = ? WHERE id = ?", (vehicle_id, booking_id))
        return True


def delete_booking(booking_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM booking_status_history WHERE booking_id = ?", (booking_id,))
        conn.execute("DELETE FROM payments WHERE booking_id = ?", (booking_id,))
        conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))


def insert_payment(booking_id: int | None, customer_id: int | None, amount: int = 0, method: str = "", payment_status: str = "unpaid", reference: str = "", paid_at: str | None = None) -> int:
    with _conn() as conn:
        resolved_customer_id = customer_id
        if booking_id:
            booking = conn.execute("SELECT customer_id FROM bookings WHERE id = ?", (booking_id,)).fetchone()
            if not booking:
                return 0
            resolved_customer_id = booking["customer_id"]

        if not resolved_customer_id:
            return 0

        customer = conn.execute("SELECT id FROM customers WHERE id = ?", (resolved_customer_id,)).fetchone()
        if not customer:
            return 0

        clean_status = _clean_payment_status(payment_status)
        cursor = conn.execute("""
            INSERT INTO payments
              (booking_id, customer_id, amount, method, payment_status, reference, paid_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            booking_id,
            resolved_customer_id,
            max(int(amount), 0),
            _clean_payment_method(method),
            clean_status,
            reference.strip(),
            _payment_paid_at(clean_status, paid_at),
            _now(),
        ))
        if booking_id:
            conn.execute("""
                UPDATE bookings
                SET payment_method = ?, payment_status = ?
                WHERE id = ?
            """, (_clean_payment_method(method), clean_status, booking_id))
        return cursor.lastrowid


def update_payment(payment_id: int, booking_id: int | None, customer_id: int | None, amount: int = 0, method: str = "", payment_status: str = "unpaid", reference: str = "", paid_at: str | None = None) -> bool:
    with _conn() as conn:
        existing = conn.execute("SELECT id, booking_id FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if not existing:
            return False

        resolved_customer_id = customer_id
        if booking_id:
            booking = conn.execute("SELECT customer_id FROM bookings WHERE id = ?", (booking_id,)).fetchone()
            if not booking:
                return False
            resolved_customer_id = booking["customer_id"]

        if not resolved_customer_id:
            return False

        customer = conn.execute("SELECT id FROM customers WHERE id = ?", (resolved_customer_id,)).fetchone()
        if not customer:
            return False

        clean_status = _clean_payment_status(payment_status)
        conn.execute("""
            UPDATE payments
            SET booking_id = ?, customer_id = ?, amount = ?, method = ?,
                payment_status = ?, reference = ?, paid_at = ?
            WHERE id = ?
        """, (
            booking_id,
            resolved_customer_id,
            max(int(amount), 0),
            _clean_payment_method(method),
            clean_status,
            reference.strip(),
            _payment_paid_at(clean_status, paid_at),
            payment_id,
        ))
        if existing["booking_id"] and existing["booking_id"] != booking_id:
            conn.execute("""
                UPDATE bookings
                SET payment_method = '', payment_status = 'unpaid'
                WHERE id = ?
            """, (existing["booking_id"],))
        if booking_id:
            conn.execute("""
                UPDATE bookings
                SET payment_method = ?, payment_status = ?
                WHERE id = ?
            """, (_clean_payment_method(method), clean_status, booking_id))
        return True


def update_booking_payment(booking_id: int, amount: int = 0, method: str = "", payment_status: str = "unpaid", reference: str = "", paid_at: str | None = None) -> bool:
    with _conn() as conn:
        return _upsert_booking_payment(
            conn,
            booking_id,
            amount=amount,
            method=method,
            status=payment_status,
            reference=reference,
            paid_at=paid_at,
        )


def delete_payment(payment_id: int) -> bool:
    with _conn() as conn:
        existing = conn.execute("SELECT booking_id FROM payments WHERE id = ?", (payment_id,)).fetchone()
        cursor = conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        if existing and existing["booking_id"]:
            conn.execute("""
                UPDATE bookings
                SET payment_method = '', payment_status = 'unpaid'
                WHERE id = ?
            """, (existing["booking_id"],))
        return cursor.rowcount > 0


def insert_customer(name: str, phone: str, whatsapp_opt_in: int = 1, notes: str = "") -> int:
    normalized_phone = _normalize_phone(phone) or phone.strip()
    token = customer_token(normalized_phone)
    with _conn() as conn:
        next_id = conn.execute("SELECT IFNULL(MAX(id), 0) + 1 AS next_id FROM customers").fetchone()["next_id"]
        customer_code = _customer_code(next_id)
        cursor = conn.execute("""
            INSERT INTO customers
              (name, phone, customer_code, token, whatsapp_opt_in, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name.strip(), normalized_phone, customer_code, token,
            1 if whatsapp_opt_in else 0, notes.strip(), _now(), _now(),
        ))
        return cursor.lastrowid


def update_customer(customer_id: int, name: str, phone: str, whatsapp_opt_in: int = 1, notes: str = ""):
    normalized_phone = _normalize_phone(phone) or phone.strip()
    token = customer_token(normalized_phone)
    with _conn() as conn:
        conn.execute("""
            UPDATE customers
            SET name = ?, phone = ?, token = ?, whatsapp_opt_in = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (
            name.strip(), normalized_phone, token,
            1 if whatsapp_opt_in else 0, notes.strip(), _now(), customer_id,
        ))


def delete_customer(customer_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM booking_status_history WHERE booking_id IN (SELECT id FROM bookings WHERE customer_id = ?)", (customer_id,))
        conn.execute("DELETE FROM payments WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM customer_memberships WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM wash_records WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM bookings WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM vehicles WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))


def insert_vehicle(customer_id: int, vehicle_type: str, vehicle_brand: str, vehicle_model: str, number_plate: str = "", color: str = "") -> int:
    with _conn() as conn:
        cursor = conn.execute("""
            INSERT INTO vehicles
              (customer_id, vehicle_type, vehicle_brand, vehicle_model, number_plate, color, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id, vehicle_type.strip(), vehicle_brand.strip(), vehicle_model.strip(),
            _normalize_plate(number_plate), color.strip(), _now(), _now(),
        ))
        return cursor.lastrowid


def update_vehicle(vehicle_id: int, vehicle_type: str, vehicle_brand: str, vehicle_model: str, number_plate: str = "", color: str = ""):
    with _conn() as conn:
        conn.execute("""
            UPDATE vehicles
            SET vehicle_type = ?, vehicle_brand = ?, vehicle_model = ?, number_plate = ?, color = ?, updated_at = ?
            WHERE id = ?
        """, (
            vehicle_type.strip(), vehicle_brand.strip(), vehicle_model.strip(),
            _normalize_plate(number_plate), color.strip(), _now(), vehicle_id,
        ))


def delete_vehicle(vehicle_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM booking_status_history WHERE booking_id IN (SELECT id FROM bookings WHERE vehicle_id = ?)", (vehicle_id,))
        conn.execute("DELETE FROM payments WHERE booking_id IN (SELECT id FROM bookings WHERE vehicle_id = ?)", (vehicle_id,))
        conn.execute("DELETE FROM wash_records WHERE vehicle_id = ?", (vehicle_id,))
        conn.execute("DELETE FROM bookings WHERE vehicle_id = ?", (vehicle_id,))
        conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))


def insert_service(name: str, category: str, base_price: int = 0, duration: str = "", active: int = 1) -> int:
    with _conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO service_catalog
              (name, category, base_price, duration, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name.strip(), category.strip(), base_price, duration.strip(), 1 if active else 0, _now()))
        row = conn.execute("SELECT id FROM service_catalog WHERE name = ?", (name.strip(),)).fetchone()
        return row["id"] if row else 0


def update_service(service_id: int, name: str, category: str, base_price: int = 0, duration: str = "", active: int = 1):
    with _conn() as conn:
        conn.execute("""
            UPDATE service_catalog
            SET name = ?, category = ?, base_price = ?, duration = ?, active = ?
            WHERE id = ?
        """, (name.strip(), category.strip(), base_price, duration.strip(), 1 if active else 0, service_id))


def delete_service(service_id: int):
    with _conn() as conn:
        conn.execute("UPDATE bookings SET service_id = NULL WHERE service_id = ?", (service_id,))
        conn.execute("UPDATE wash_records SET service_id = NULL WHERE service_id = ?", (service_id,))
        conn.execute("DELETE FROM service_catalog WHERE id = ?", (service_id,))


def insert_membership(name: str, monthly_price: int, description: str = "", active: int = 1) -> int:
    with _conn() as conn:
        cursor = conn.execute("""
            INSERT INTO memberships
              (name, monthly_price, description, active, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), monthly_price, description.strip(), 1 if active else 0, _now()))
        return cursor.lastrowid


def update_membership(membership_id: int, name: str, monthly_price: int, description: str = "", active: int = 1):
    with _conn() as conn:
        conn.execute("""
            UPDATE memberships
            SET name = ?, monthly_price = ?, description = ?, active = ?
            WHERE id = ?
        """, (name.strip(), monthly_price, description.strip(), 1 if active else 0, membership_id))


def delete_membership(membership_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM customer_memberships WHERE membership_id = ?", (membership_id,))
        conn.execute("DELETE FROM memberships WHERE id = ?", (membership_id,))


def get_customer_by_id(customer_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None


def get_customer_by_phone(phone: str) -> dict | None:
    normalized_phone = _normalize_phone(phone) or phone.strip()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM customers WHERE phone = ?", (normalized_phone,)).fetchone()
        return dict(row) if row else None


def get_customer_vehicles(customer_id: int | None = None, phone: str | None = None) -> list[dict]:
    with _conn() as conn:
        if customer_id is not None:
            customer = conn.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
            if not customer:
                return []
            cust_id = customer_id
        elif phone is not None:
            customer = get_customer_by_phone(phone)
            if not customer:
                return []
            cust_id = customer["id"]
        else:
            return []

        rows = conn.execute("""
            SELECT
              id,
              vehicle_type,
              vehicle_brand,
              vehicle_model,
              COALESCE(NULLIF(number_plate, ''), '') AS number_plate,
              color
            FROM vehicles
            WHERE customer_id = ?
            ORDER BY created_at DESC
        """, (cust_id,)).fetchall()
        return [dict(row) for row in rows]


def get_vehicle_by_id(vehicle_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
        return dict(row) if row else None


def get_customer_history(token: str) -> dict | None:
    with _conn() as conn:
        customer = conn.execute("SELECT * FROM customers WHERE token = ?", (token,)).fetchone()
        if not customer:
            return None

        vehicles = conn.execute("""
            SELECT
              v.id,
              v.vehicle_type,
              v.vehicle_brand,
              v.vehicle_model,
              COALESCE(NULLIF(v.number_plate, ''), 'Plate not added') AS plate,
              COUNT(DISTINCT w.id) AS completed,
              COUNT(DISTINCT b.id) AS total
            FROM vehicles v
            LEFT JOIN bookings b ON b.vehicle_id = v.id
            LEFT JOIN wash_records w ON w.vehicle_id = v.id
            WHERE v.customer_id = ?
            GROUP BY v.id
            ORDER BY v.id DESC
        """, (customer["id"],)).fetchall()

        records = conn.execute("""
            SELECT
              b.id,
              b.preferred_date,
              b.preferred_time,
              b.service_name AS service,
              b.status,
              b.booked_at,
              v.vehicle_type,
              v.vehicle_brand,
              v.vehicle_model,
              v.number_plate AS vehicle_plate
            FROM bookings b
            JOIN vehicles v ON v.id = b.vehicle_id
            WHERE b.customer_id = ?
            ORDER BY b.preferred_date DESC, b.id DESC
        """, (customer["id"],)).fetchall()

        completed_count = conn.execute(
            "SELECT COUNT(*) FROM wash_records WHERE customer_id = ?",
            (customer["id"],),
        ).fetchone()[0]

        return {
            "name": customer["name"],
            "phone": customer["phone"],
            "customer_code": customer["customer_code"],
            "total_records": len(records),
            "completed_count": completed_count,
            "vehicles": [dict(row) for row in vehicles],
            "records": [dict(row) for row in records],
        }


def get_table_summary() -> list[dict]:
    business_tables = [
        "customers",
        "vehicles",
        "vehicle_brands",
        "vehicle_models",
        "service_catalog",
        "bookings",
        "wash_records",
        "payments",
        "memberships",
        "customer_memberships",
        "booking_status_history",
    ]
    with _conn() as conn:
        summary = []
        for table in business_tables:
            if _table_exists(conn, table):
                summary.append({
                    "table": table,
                    "rows": conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                    "columns": sorted(_columns(conn, table)),
                })
        return summary


def get_admin_dashboard_data() -> dict:
    with _conn() as conn:
        customers = conn.execute("""
            SELECT
              c.id,
              c.name,
              c.phone,
              c.customer_code,
              c.whatsapp_opt_in,
              c.notes,
              c.created_at,
              c.updated_at,
              c.token AS customer_token,
              COUNT(DISTINCT v.id) AS vehicle_count,
              COUNT(DISTINCT b.id) AS booking_count,
              COUNT(DISTINCT w.id) AS wash_count
            FROM customers c
            LEFT JOIN vehicles v ON v.customer_id = c.id
            LEFT JOIN bookings b ON b.customer_id = c.id
            LEFT JOIN wash_records w ON w.customer_id = c.id
            GROUP BY c.id
            ORDER BY c.id DESC
        """).fetchall()

        vehicles = conn.execute("""
            SELECT
              v.id,
              v.customer_id,
              c.name AS customer_name,
              c.phone,
              c.customer_code,
              c.token AS customer_token,
              v.vehicle_type,
              v.vehicle_brand,
              v.vehicle_model,
              v.number_plate,
              v.color,
              v.created_at,
              v.updated_at,
              COUNT(DISTINCT b.id) AS booking_count,
              COUNT(DISTINCT w.id) AS wash_count
            FROM vehicles v
            JOIN customers c ON c.id = v.customer_id
            LEFT JOIN bookings b ON b.vehicle_id = v.id
            LEFT JOIN wash_records w ON w.vehicle_id = v.id
            GROUP BY v.id
            ORDER BY v.id DESC
        """).fetchall()

        services = conn.execute("""
            SELECT
              s.id,
              s.name,
              s.category,
              s.base_price,
              s.duration,
              s.active,
              s.created_at,
              COUNT(DISTINCT b.id) AS booking_count,
              COUNT(DISTINCT w.id) AS wash_count
            FROM service_catalog s
            LEFT JOIN bookings b ON b.service_id = s.id
            LEFT JOIN wash_records w ON w.service_id = s.id
            GROUP BY s.id
            ORDER BY s.category, s.base_price, s.name
        """).fetchall()

        wash_records = conn.execute("""
            SELECT
              w.id,
              w.booking_id,
              c.name AS customer_name,
              c.phone,
              v.vehicle_type,
              v.vehicle_brand,
              v.vehicle_model,
              v.number_plate,
              w.service_name,
              w.wash_date,
              w.status,
              w.notes,
              w.created_at
            FROM wash_records w
            JOIN customers c ON c.id = w.customer_id
            JOIN vehicles v ON v.id = w.vehicle_id
            ORDER BY w.id DESC
        """).fetchall()

        payments = conn.execute("""
            SELECT
              p.id,
              p.booking_id,
              p.customer_id,
              c.name AS customer_name,
              c.phone,
              b.service_name,
              p.amount,
              p.method,
              p.payment_status,
              p.reference,
              p.paid_at,
              p.created_at
            FROM payments p
            JOIN customers c ON c.id = p.customer_id
            LEFT JOIN bookings b ON b.id = p.booking_id
            ORDER BY p.id DESC
        """).fetchall()

        memberships = conn.execute("""
            SELECT
              m.id,
              m.name,
              m.monthly_price,
              m.description,
              m.active,
              m.created_at,
              COUNT(cm.id) AS subscriber_count
            FROM memberships m
            LEFT JOIN customer_memberships cm ON cm.membership_id = m.id
            GROUP BY m.id
            ORDER BY m.monthly_price
        """).fetchall()

        customer_memberships = conn.execute("""
            SELECT
              cm.id,
              cm.customer_phone AS phone,
              cm.membership_id,
              c.name AS customer_name,
              m.name AS membership_name,
              m.monthly_price,
              cm.starts_on,
              cm.ends_on,
              cm.status,
              cm.payment_proof,
              cm.created_at
            FROM customer_memberships cm
            JOIN customers c ON c.id = cm.customer_id
            JOIN memberships m ON m.id = cm.membership_id
            ORDER BY cm.id DESC
        """).fetchall()

        status_history = conn.execute("""
            SELECT
              h.id,
              h.booking_id,
              c.name AS customer_name,
              c.phone,
              b.service_name,
              h.old_status,
              h.new_status,
              h.changed_at
            FROM booking_status_history h
            JOIN bookings b ON b.id = h.booking_id
            JOIN customers c ON c.id = b.customer_id
            ORDER BY h.id DESC
            LIMIT 200
        """).fetchall()

        return {
            "customers": [dict(row) for row in customers],
            "vehicles": [dict(row) for row in vehicles],
            "services": [dict(row) for row in services],
            "wash_records": [dict(row) for row in wash_records],
            "payments": [dict(row) for row in payments],
            "memberships": [dict(row) for row in memberships],
            "customer_memberships": [dict(row) for row in customer_memberships],
            "status_history": [dict(row) for row in status_history],
        }
