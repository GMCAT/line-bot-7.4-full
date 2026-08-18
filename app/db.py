"""
คิวรีและเขียนข้อมูลผู้ติดต่อใน PostgreSQL ฐานหลักเพียงฐานเดียว
ใช้โครงสร้างเดียวกับ Prisma: primary key เป็น Int autoincrement และชื่อคอลัมน์เป็น snake_case

โครงสร้างตาราง:
  organizations(id Int, name, code, created_at, updated_at)
  contacts(id Int, organization_id Int, name, phone, email, line_id, position,
           contact_role, contact_type, is_available_24h, note, created_at, updated_at)

  contact_role: PRIMARY | SECONDARY
  contact_type: GENERAL | EMERGENCY | MAINTENANCE | IT_SUPPORT | LAB_SUPPORT | VENDOR | OTHER

"""
import os
import re
import psycopg
from psycopg.rows import dict_row

def _connect():
    # DATABASE_URL_MAIN เป็น fallback ชั่วคราวเพื่อให้ migration จากรุ่นเก่าไม่ดับทันที
    dsn = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_MAIN")
    if not dsn:
        raise RuntimeError("ยังไม่ได้ตั้ง DATABASE_URL สำหรับฐานข้อมูลหลัก")
    sslmode = os.getenv("DB_SSLMODE", "require")
    return psycopg.connect(dsn, connect_timeout=10, sslmode=sslmode, row_factory=dict_row)


def _normalize(s: str) -> str:
    """ตัดช่องว่าง/จุด/ขีด ออก แล้วแปลงเป็นตัวพิมพ์เล็ก กันคนพิมพ์เว้นวรรคเพี้ยน"""
    return re.sub(r"[\s.\-]+", "", s or "").lower()


def _levenshtein(a: str, b: str) -> int:
    """ระยะห่างของคำ (Levenshtein distance) ใช้วัดว่าสะกดผิดไปกี่ตัวอักษร"""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[n]


def _fuzzy_best_ids(candidates: list[tuple], query: str, threshold_ratio: float = 0.4) -> list:
    """
    candidates: list ของ (id, ข้อความที่จะเทียบ) — id ซ้ำกันได้ (เช่นชื่อ+ตัวย่อของหน่วยงานเดียวกัน)
    คืนค่า list ของ id ที่ระยะห่างน้อยที่สุด (อาจมีหลาย id ถ้าใกล้เคียงเท่ากัน) ภายใต้เกณฑ์ที่ยอมรับได้
    """
    q = _normalize(query)
    if not q:
        return []

    best_dist = None
    best_ids: list = []
    seen_ids: set = set()
    for cid, text in candidates:
        c = _normalize(text)
        if not c:
            continue
        dist = _levenshtein(q, c)
        threshold = max(1, round(len(c) * threshold_ratio))
        if dist <= threshold and (best_dist is None or dist < best_dist):
            best_dist = dist
            best_ids = [cid]
            seen_ids = {cid}
        elif dist == best_dist and cid not in seen_ids:
            best_ids.append(cid)
            seen_ids.add(cid)
    return best_ids


_BASE_SELECT = """
    SELECT
        c.id, c.name, c.phone, c.email, c.line_id, c.position,
        c.contact_role, c.contact_type, c.is_available_24h, c.note,
        o.name AS organization_name
    FROM contacts c
    LEFT JOIN organizations o ON o.id = c.organization_id
"""


def _find_organization(cur, query: str) -> dict | None:
    """
    หาหน่วยงานที่ตรงกับคำค้น เช็คแบบตรงเป๊ะก่อน (ชื่อเต็ม หรือตัวย่อ/code)
    แล้วค่อย fallback เป็นแบบ partial match (เช่น "ป่าไม้" match "กรมป่าไม้")
    """
    cur.execute(
        "SELECT id, name FROM organizations WHERE LOWER(name) = LOWER(%s) OR LOWER(code) = LOWER(%s) LIMIT 1",
        (query, query),
    )
    org = cur.fetchone()
    if org:
        return org

    like = f"%{query}%"
    cur.execute(
        "SELECT id, name FROM organizations WHERE name ILIKE %s OR code ILIKE %s ORDER BY name LIMIT 1",
        (like, like),
    )
    return cur.fetchone()


def search_contacts(query: str, limit: int = 20) -> tuple[str | None, list[dict], bool]:
    """
    ค้นหาผู้ติดต่อจากฐานหลัก
    3 ขั้นเรียงลำดับ:
      1. หน่วยงานตรงเป๊ะ/บางส่วน (ชื่อเต็ม/ตัวย่อ) -> คืนผู้ติดต่อทั้งหมดของหน่วยงานนั้น
      2. ชื่อคน/เบอร์/อีเมล/ตำแหน่งตรงบางส่วน -> คืนตามเงื่อนไขนั้น
      3. ถ้าทั้งสองขั้นบนไม่เจอเลย (สงสัยว่าพิมพ์ผิด) -> ลองหาหน่วยงาน/คนที่ใกล้เคียงที่สุดแทน (fuzzy)

    คืนค่าเป็น (ชื่อหน่วยงานที่ match หรือ None, list ของผู้ติดต่อ, เป็นการเดาแบบ fuzzy หรือไม่)
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            org = _find_organization(cur, query)
            if org:
                cur.execute(
                    _BASE_SELECT + " WHERE c.organization_id = %s ORDER BY c.contact_role, c.name LIMIT %s",
                    (org["id"], limit),
                )
                return org["name"], cur.fetchall(), False

            like = f"%{query}%"
            cur.execute(
                _BASE_SELECT + """
                WHERE c.name ILIKE %s OR c.phone ILIKE %s OR c.email ILIKE %s OR c.position ILIKE %s
                ORDER BY c.contact_role, c.name
                LIMIT %s
                """,
                (like, like, like, like, limit),
            )
            direct_hits = cur.fetchall()
            if direct_hits:
                return None, direct_hits, False

            cur.execute("SELECT id, name, code FROM organizations")
            org_rows = cur.fetchall()
            org_candidates = []
            for r in org_rows:
                org_candidates.append((r["id"], r["name"]))
                if r["code"]:
                    org_candidates.append((r["id"], r["code"]))
            org_ids = _fuzzy_best_ids(org_candidates, query)
            if org_ids:
                matched = next(r for r in org_rows if r["id"] == org_ids[0])
                cur.execute(
                    _BASE_SELECT + " WHERE c.organization_id = %s ORDER BY c.contact_role, c.name LIMIT %s",
                    (matched["id"], limit),
                )
                return matched["name"], cur.fetchall(), True

            cur.execute("SELECT id, name FROM contacts")
            contact_rows = cur.fetchall()
            contact_candidates = [(r["id"], r["name"]) for r in contact_rows]
            contact_ids = _fuzzy_best_ids(contact_candidates, query)
            if contact_ids:
                cur.execute(
                    _BASE_SELECT + " WHERE c.id = ANY(%s) ORDER BY c.contact_role, c.name",
                    (contact_ids,),
                )
                return None, cur.fetchall(), True

            return None, [], False


def list_emergency_contacts(limit: int = 10) -> list[dict]:
    """ดึงผู้ติดต่อฉุกเฉินจากฐานหลัก เรียงคนที่ติดต่อได้ 24 ชม. ขึ้นก่อน"""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _BASE_SELECT + """
                WHERE c.contact_type = 'EMERGENCY'
                ORDER BY c.is_available_24h DESC, c.contact_role, c.name
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def dump_all(limit: int = 500) -> list[dict]:
    """ดึงผู้ติดต่อทั้งหมดจากฐานหลัก เรียงตามหน่วยงาน"""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _BASE_SELECT + " ORDER BY o.name NULLS LAST, c.contact_role, c.name LIMIT %s",
                (limit,),
            )
            return cur.fetchall()


def _find_or_create_organization(cur, name: str, code: str | None = None) -> int:
    """
    หาหน่วยงานจากชื่อ (ตรงเป๊ะ ไม่สนตัวพิมพ์เล็กใหญ่) ถ้าไม่มีให้สร้างใหม่
    id ให้ PostgreSQL สร้างด้วย autoincrement ตาม Prisma schema
    """
    code = code.strip().upper() if code else None
    cur.execute("SELECT id, name, code FROM organizations WHERE LOWER(name) = LOWER(%s) LIMIT 1", (name,))
    row = cur.fetchone()
    if row:
        if code:
            cur.execute(
                "SELECT id, name FROM organizations WHERE LOWER(code) = LOWER(%s) AND id <> %s LIMIT 1",
                (code, row["id"]),
            )
            owner = cur.fetchone()
            if owner:
                raise ValueError(f'ตัวย่อ "{code}" ถูกใช้โดยหน่วยงาน "{owner["name"]}" แล้ว')
            if row["code"] and row["code"].lower() != code.lower():
                raise ValueError(
                    f'หน่วยงาน "{name}" มีตัวย่อ "{row["code"]}" อยู่แล้ว '
                    f'จึงไม่เปลี่ยนเป็น "{code}" อัตโนมัติ'
                )
            if not row["code"]:
                cur.execute("UPDATE organizations SET code = %s WHERE id = %s", (code, row["id"]))
        return row["id"]

    if code:
        cur.execute("SELECT name FROM organizations WHERE LOWER(code) = LOWER(%s) LIMIT 1", (code,))
        owner = cur.fetchone()
        if owner:
            raise ValueError(f'ตัวย่อ "{code}" ถูกใช้โดยหน่วยงาน "{owner["name"]}" แล้ว')

    cur.execute("INSERT INTO organizations (name, code) VALUES (%s, %s) RETURNING id", (name, code))
    return cur.fetchone()["id"]


def _insert_contact(cur, org_id: int, fields: dict) -> int:
    cur.execute(
        """
        INSERT INTO contacts
          (organization_id, name, phone, email, line_id, position,
           contact_role, contact_type, is_available_24h, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            org_id, fields["name"], fields.get("phone"), fields.get("email"),
            fields.get("line_id"), fields.get("position"),
            fields.get("contact_role", "SECONDARY"), fields.get("contact_type", "GENERAL"),
            fields.get("is_available_24h", False), fields.get("note"),
        ),
    )
    return cur.fetchone()["id"]


def add_contact(fields: dict) -> int:
    """
    เพิ่มผู้ติดต่อใหม่ลงฐานหลักเพียงฐานเดียว
    fields ต้องมี: name, organization (ชื่อหน่วยงาน — สร้างหน่วยงานใหม่อัตโนมัติถ้ายังไม่มี)
    fields อื่นที่รับได้ (optional): phone, email, line_id, position,
      contact_role ("PRIMARY"/"SECONDARY"), contact_type (ดู enum ด้านบน),
      is_available_24h (bool), note, organization_code

    คืนค่า id ของผู้ติดต่อที่ฐานข้อมูลสร้างให้
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            org_id = _find_or_create_organization(
                cur, fields["organization"], fields.get("organization_code")
            )
            return _insert_contact(cur, org_id, fields)


def database_status() -> dict:
    """ตรวจการเชื่อมต่อและจำนวนข้อมูลในฐานหลัก"""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM organizations")
            organization_count = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) AS count FROM contacts")
            contact_count = cur.fetchone()["count"]
    return {"organization_count": organization_count, "contact_count": contact_count}
