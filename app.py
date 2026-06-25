from flask import Flask, render_template, request
import random
from datetime import datetime, timedelta

from database import (
    create_database,
    save_entry,
    faculty_busy,
    clear_section
)

app = Flask(__name__)

create_database()


@app.route('/', methods=['GET', 'POST'])
def home():

    timetable = []
    subjects = []
    days = []
    period_headers = []
    first_break_index = None
    lunch_index = None
    first_break = "10:50 AM - 11:00 AM"
    lunch_break = "1:00 PM - 2:00 PM"

    if request.method == 'POST':

        # =========================
        # SUBJECT COLLECTION
        # =========================

        for key in request.form:

            if key.startswith("subject"):

                number = key.replace("subject", "")

                subject_name = request.form.get(f"subject{number}")
                subject_code = request.form.get(f"code{number}")
                faculty_name = request.form.get(f"faculty{number}")
                hours = request.form.get(f"hours{number}")

                if any([subject_name, subject_code, faculty_name, hours]) and not all([subject_name, subject_code, faculty_name, hours]):
                    return render_template(
                        'index.html',
                        timetable=[],
                        subjects=[],
                        days=[],
                        period_headers=[],
                        first_break=first_break,
                        lunch_break=lunch_break,
                        error="Please complete subject name, code, professor, and weekly hours for every subject row you start filling.",
                        college=request.form.get("college", ""),
                        affiliation=request.form.get("affiliation", ""),
                        department=request.form.get("department", ""),
                        semester=request.form.get("semester", ""),
                        section=request.form.get("section", ""),
                        year=request.form.get("year", ""),
                        classroom=request.form.get("classroom", ""),
                        cycle=request.form.get("cycle", ""),
                        class_teacher=request.form.get("classteacher", ""),
                        effective_from=request.form.get("effectivefrom", "")
                    )

                if subject_name:

                    subjects.append({
                        "name": subject_name,
                        "code": subject_code,
                        "faculty": faculty_name,
                        "hours": int(hours) if hours else 1
                    })

        section = request.form.get("section", "")

        if section:
            clear_section(section)

        # =========================
        # LAB COLLECTION
        # =========================

        labs = []

        for key in request.form:

            if key.startswith("labsubject"):

                number = key.replace("labsubject", "")

                lab_name = request.form.get(f"labsubject{number}")
                lab_faculty = request.form.get(f"labfaculty{number}")
                lab_duration = request.form.get(f"labduration{number}")
                lab_room = request.form.get(f"labroom{number}")

                if lab_name:

                    labs.append({
                        "name": lab_name,
                        "faculty": lab_faculty,
                        "duration": lab_duration,
                        "room": lab_room
                    })

        # =========================
        # SETTINGS
        # =========================

        working_days = int(
            request.form.get("workingdays", 5) or 5
        )

        periods_per_day = int(
            request.form.get("periods", 7) or 7
        )

        lunch_break = request.form.get(
            "lunch",
            "1:00 PM - 2:00 PM"
        ) or "1:00 PM - 2:00 PM"

        start_time = request.form.get(
            "starttime",
            "09:00"
        ) or "09:00"

        period_duration = 1
        first_break_after = int(request.form.get("firstbreakafter", 2) or 2)
        lunch_after = int(request.form.get("lunchafter", 4) or 4)
        first_break = request.form.get(
            "firstbreak",
            "10:50 AM - 11:00 AM"
        )

        if not subjects:
            return render_template(
                'index.html',
                timetable=[],
                subjects=[],
                days=[],
                period_headers=[],
                error="Please enter at least one subject before generating the timetable.",
                college=request.form.get("college", ""),
                affiliation=request.form.get("affiliation", ""),
                department=request.form.get("department", ""),
                semester=request.form.get("semester", ""),
                section=request.form.get("section", ""),
                year=request.form.get("year", ""),
                classroom=request.form.get("classroom", ""),
                cycle=request.form.get("cycle", ""),
                class_teacher=request.form.get("classteacher", ""),
                effective_from=request.form.get("effectivefrom", ""),
                first_break=first_break,
                lunch_break=lunch_break
            )

        # =========================
        # DAYS
        # =========================

        all_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday"
        ]

        days = all_days[:working_days]

        # =========================
        # TIMETABLE GENERATION
        # =========================

        start = datetime.strptime(
            start_time,
            "%H:%M"
        )

        roman_periods = [
            "I",
            "II",
            "III",
            "IV",
            "V",
            "VI",
            "VII",
            "VIII",
            "IX",
            "X"
        ]

        subject_pool = []

        for subject in subjects:
            subject_pool.extend([subject] * subject["hours"])

        if not subject_pool:
            subject_pool = subjects[:]

        first_break_index = max(
            0,
            min(first_break_after, periods_per_day)
        )

        lunch_index = max(
            first_break_index,
            min(lunch_after, periods_per_day)
        )

        for period in range(periods_per_day):

            current = start + timedelta(
                hours=period
            )

            next_time = current + timedelta(
                hours=period_duration
            )

            time_slot = (
                f"{current.strftime('%I:%M %p')} - "
                f"{next_time.strftime('%I:%M %p')}"
            )

            period_headers.append({
                "number": roman_periods[period] if period < len(roman_periods) else str(period + 1),
                "time": time_slot
            })

            row = {
                "time": time_slot
            }

            for day in days:

                assigned = False
                attempts = 0

                while not assigned and attempts < 20:

                    selected_subject = random.choice(subject_pool)

                    faculty = selected_subject["faculty"]

                    if not faculty_busy(
                        faculty,
                        day,
                        time_slot
                    ):

                        save_entry(
                            faculty,
                            day,
                            time_slot,
                            section,
                            selected_subject["name"]
                        )

                        content = selected_subject['code'] or selected_subject['name']

                        row[day] = content

                        assigned = True

                    attempts += 1

                if not assigned:

                    row[day] = "NO FACULTY AVAILABLE"

            timetable.append(row)

        # =========================
        # LUNCH BREAK
        # =========================

    return render_template(
        'index.html',
        timetable=timetable,
        subjects=subjects,
        days=days,
        period_headers=period_headers,
        first_break_index=first_break_index,
        lunch_index=lunch_index,
        first_break=first_break if request.method == 'POST' else "10:50 AM - 11:00 AM",
        lunch_break=lunch_break if request.method == 'POST' else "1:00 PM - 2:00 PM",
        error=None,
        college=request.form.get("college", ""),
        affiliation=request.form.get("affiliation", ""),
        department=request.form.get("department", ""),
        semester=request.form.get("semester", ""),
        section=request.form.get("section", ""),
        year=request.form.get("year", ""),
        classroom=request.form.get("classroom", ""),
        cycle=request.form.get("cycle", ""),
        class_teacher=request.form.get("classteacher", ""),
        effective_from=request.form.get("effectivefrom", "")
    )


if __name__ == '__main__':
    app.run(
        debug=True,
        port=5001
    )
