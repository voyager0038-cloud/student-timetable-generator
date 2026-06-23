import sqlite3

DATABASE = "timetable.db"

def create_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty TEXT,
        day TEXT,
        time_slot TEXT,
        section TEXT,
        subject TEXT
    )
    """)

    conn.commit()
    conn.close()

def save_entry(faculty, day, time_slot, section, subject):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO timetable
    (faculty, day, time_slot, section, subject)
    VALUES (?, ?, ?, ?, ?)
    """, (faculty, day, time_slot, section, subject))

    conn.commit()
    conn.close()

def faculty_busy(faculty, day, time_slot):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM timetable
    WHERE faculty = ?
    AND day = ?
    AND time_slot = ?
    """, (faculty, day, time_slot))

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