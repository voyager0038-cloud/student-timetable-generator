import sqlite3

DATABASE = "timetable.db"

def normalize_faculty(faculty):
    return " ".join((faculty or "").strip().lower().split())

def normalize_text(value):
    return " ".join((value or "").strip().lower().split())

def create_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty TEXT,
        faculty_key TEXT,
        classroom TEXT,
        classroom_key TEXT,
        day TEXT,
        time_slot TEXT,
        section TEXT,
        subject TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(timetable)")
    columns = [column[1] for column in cursor.fetchall()]

    if "faculty_key" not in columns:
        cursor.execute("ALTER TABLE timetable ADD COLUMN faculty_key TEXT")

    if "classroom" not in columns:
        cursor.execute("ALTER TABLE timetable ADD COLUMN classroom TEXT")

    if "classroom_key" not in columns:
        cursor.execute("ALTER TABLE timetable ADD COLUMN classroom_key TEXT")

    cursor.execute("""
    UPDATE timetable
    SET faculty_key = LOWER(TRIM(faculty))
    WHERE faculty_key IS NULL
    """)

    cursor.execute("""
    UPDATE timetable
    SET classroom_key = LOWER(TRIM(classroom))
    WHERE classroom_key IS NULL
    """)

    cursor.execute("""
    DELETE FROM timetable
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM timetable
        GROUP BY faculty_key, day, time_slot
    )
    AND faculty_key IS NOT NULL
    AND faculty_key != ''
    """)

    cursor.execute("""
    DELETE FROM timetable
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM timetable
        GROUP BY classroom_key, day, time_slot
    )
    AND classroom_key IS NOT NULL
    AND classroom_key != ''
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS unique_faculty_time_slot
    ON timetable (faculty_key, day, time_slot)
    WHERE faculty_key IS NOT NULL
    AND faculty_key != ''
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS unique_classroom_time_slot
    ON timetable (classroom_key, day, time_slot)
    WHERE classroom_key IS NOT NULL
    AND classroom_key != ''
    """)

    conn.commit()
    conn.close()

def save_entry(faculty, day, time_slot, section, subject, classroom=""):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    faculty_key = normalize_faculty(faculty)
    classroom_key = normalize_text(classroom)

    try:
        cursor.execute("""
        INSERT INTO timetable
        (faculty, faculty_key, classroom, classroom_key, day, time_slot, section, subject)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (faculty, faculty_key, classroom, classroom_key, day, time_slot, section, subject))

        conn.commit()
        saved = True

    except sqlite3.IntegrityError:
        saved = False

    finally:
        conn.close()

    return saved

def save_entries(entries, section):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "DELETE FROM timetable WHERE section=?",
            (section,)
        )

        for entry in entries:
            faculty = entry.get("faculty", "")
            classroom = entry.get("classroom", "")
            faculty_key = normalize_faculty(faculty)
            classroom_key = normalize_text(classroom)

            cursor.execute("""
            INSERT INTO timetable
            (faculty, faculty_key, classroom, classroom_key, day, time_slot, section, subject)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                faculty,
                faculty_key,
                classroom,
                classroom_key,
                entry.get("day", ""),
                entry.get("time_slot", ""),
                section,
                entry.get("subject", "")
            ))

        conn.commit()
        saved = True

    except sqlite3.IntegrityError:
        conn.rollback()
        saved = False

    finally:
        conn.close()

    return saved

def faculty_busy(faculty, day, time_slot, ignore_section=""):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    faculty_key = normalize_faculty(faculty)

    query = """
    SELECT 1 FROM timetable
    WHERE faculty_key = ?
    AND day = ?
    AND time_slot = ?
    """
    params = [faculty_key, day, time_slot]

    if ignore_section:
        query += " AND section != ?"
        params.append(ignore_section)

    cursor.execute(query, params)

    result = cursor.fetchone()

    conn.close()

    return result is not None

def classroom_busy(classroom, day, time_slot, ignore_section=""):
    classroom_key = normalize_text(classroom)

    if not classroom_key:
        return False

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    query = """
    SELECT 1 FROM timetable
    WHERE classroom_key = ?
    AND day = ?
    AND time_slot = ?
    """
    params = [classroom_key, day, time_slot]

    if ignore_section:
        query += " AND section != ?"
        params.append(ignore_section)

    cursor.execute(query, params)

    result = cursor.fetchone()

    conn.close()

    return result is not None

def clear_section(section):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM timetable WHERE section=?",
        (section,)
    )

    conn.commit()
    conn.close()
