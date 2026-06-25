from flask import Flask, render_template, request
import json
import random
from datetime import datetime, timedelta

from database import (
    create_database,
    save_entries,
    faculty_busy,
    classroom_busy,
)

app = Flask(__name__)

create_database()

def build_clash_free_schedule(subjects, slots, section, classroom):
    assignments = {}
    local_faculty_slots = set()
    local_room_slots = set()
    requirements = []

    for subject in subjects:
        for _ in range(subject["hours"]):
            requirements.append(subject)

    if len(requirements) > len(slots):
        return None

    faculty_load = {}

    for subject in requirements:
        faculty_load[subject["faculty"]] = faculty_load.get(subject["faculty"], 0) + 1

    requirements.sort(
        key=lambda subject: (
            -faculty_load.get(subject["faculty"], 0),
            subject["faculty"].lower(),
            subject["name"].lower()
        )
    )

    def available_slots(subject):
        candidates = []

        for slot in slots:
            slot_key = (slot["day"], slot["time"])
            faculty_slot = (subject["faculty"].strip().lower(), slot["day"], slot["time"])
            room_slot = (classroom.strip().lower(), slot["day"], slot["time"])

            if slot_key in assignments:
                continue

            if faculty_slot in local_faculty_slots:
                continue

            if classroom and room_slot in local_room_slots:
                continue

            if faculty_busy(subject["faculty"], slot["day"], slot["time"], section):
                continue

            if classroom_busy(classroom, slot["day"], slot["time"], section):
                continue

            candidates.append(slot)

        return candidates

    def backtrack(index):
        if index == len(requirements):
            return True

        subject = requirements[index]
        candidates = available_slots(subject)

        random.shuffle(candidates)

        for slot in candidates:
            slot_key = (slot["day"], slot["time"])
            faculty_slot = (subject["faculty"].strip().lower(), slot["day"], slot["time"])
            room_slot = (classroom.strip().lower(), slot["day"], slot["time"])

            assignments[slot_key] = subject
            local_faculty_slots.add(faculty_slot)

            if classroom:
                local_room_slots.add(room_slot)

            if backtrack(index + 1):
                return True

            assignments.pop(slot_key)
            local_faculty_slots.remove(faculty_slot)

            if classroom:
                local_room_slots.remove(room_slot)

        return False

    if backtrack(0):
        return assignments

    return None


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
    draft_payload = ""
    approved = False

    if request.method == 'POST':

        if request.form.get("action") == "approve":
            draft_payload = request.form.get("draft_payload", "")

            try:
                draft = json.loads(draft_payload)
            except json.JSONDecodeError:
                draft = None

            if not draft:
                return render_template(
                    'index.html',
                    timetable=[],
                    subjects=[],
                    days=[],
                    period_headers=[],
                    error="Draft timetable could not be approved. Please generate it again.",
                    draft_payload="",
                    approved=False,
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

            saved = save_entries(
                draft.get("entries", []),
                draft.get("section", "")
            )

            return render_template(
                'index.html',
                timetable=draft.get("timetable", []),
                subjects=draft.get("subjects", []),
                days=draft.get("days", []),
                period_headers=draft.get("period_headers", []),
                first_break_index=draft.get("first_break_index"),
                lunch_index=draft.get("lunch_index"),
                first_break=draft.get("first_break", first_break),
                lunch_break=draft.get("lunch_break", lunch_break),
                error=None if saved else "This draft could not be saved because a faculty or classroom clash now exists. Please generate a fresh timetable.",
                draft_payload="" if saved else draft_payload,
                approved=saved,
                college=draft.get("college", ""),
                affiliation=draft.get("affiliation", ""),
                department=draft.get("department", ""),
                semester=draft.get("semester", ""),
                section=draft.get("section", ""),
                year=draft.get("year", ""),
                classroom=draft.get("classroom", ""),
                cycle=draft.get("cycle", ""),
                class_teacher=draft.get("class_teacher", ""),
                effective_from=draft.get("effective_from", "")
            )

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
                        effective_from=request.form.get("effectivefrom", ""),
                        draft_payload="",
                        approved=False
                    )

                if subject_name:

                    subjects.append({
                        "name": subject_name,
                        "code": subject_code,
                        "faculty": faculty_name,
                        "hours": int(hours) if hours else 1
                    })

        section = request.form.get("section", "")

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
                lunch_break=lunch_break,
                draft_payload="",
                approved=False
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

        first_break_index = max(
            0,
            min(first_break_after, periods_per_day)
        )

        lunch_index = max(
            first_break_index,
            min(lunch_after, periods_per_day)
        )

        slots = []

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

            for day in days:
                slots.append({
                    "day": day,
                    "period": period,
                    "time": time_slot
                })

        schedule = build_clash_free_schedule(
            subjects,
            slots,
            section,
            request.form.get("classroom", "")
        )

        if schedule is None:
            return render_template(
                'index.html',
                timetable=[],
                subjects=subjects,
                days=days,
                period_headers=period_headers,
                first_break_index=first_break_index,
                lunch_index=lunch_index,
                first_break=first_break,
                lunch_break=lunch_break,
                error="A clash-free timetable could not be generated with these inputs. Reduce weekly hours, change faculty assignments, increase periods/days, or check existing section schedules.",
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
                draft_payload="",
                approved=False
            )

        for period in range(periods_per_day):

            row = {
                "time": period_headers[period]["time"]
            }

            for day in days:

                slot_key = (day, period_headers[period]["time"])
                selected_subject = schedule.get(slot_key)
                row[day] = selected_subject["code"] if selected_subject else "Library"

            timetable.append(row)

        entries = []

        for slot_key, subject in schedule.items():
            day, time_slot = slot_key
            entries.append({
                "faculty": subject["faculty"],
                "day": day,
                "time_slot": time_slot,
                "section": section,
                "subject": subject["name"],
                "classroom": request.form.get("classroom", "")
            })

        draft_payload = json.dumps({
            "entries": entries,
            "timetable": timetable,
            "subjects": subjects,
            "days": days,
            "period_headers": period_headers,
            "first_break_index": first_break_index,
            "lunch_index": lunch_index,
            "first_break": first_break,
            "lunch_break": lunch_break,
            "college": request.form.get("college", ""),
            "affiliation": request.form.get("affiliation", ""),
            "department": request.form.get("department", ""),
            "semester": request.form.get("semester", ""),
            "section": section,
            "year": request.form.get("year", ""),
            "classroom": request.form.get("classroom", ""),
            "cycle": request.form.get("cycle", ""),
            "class_teacher": request.form.get("classteacher", ""),
            "effective_from": request.form.get("effectivefrom", "")
        })

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
        effective_from=request.form.get("effectivefrom", ""),
        draft_payload=draft_payload,
        approved=approved
    )


if __name__ == '__main__':
    app.run(
        debug=True,
        port=5001
    )
