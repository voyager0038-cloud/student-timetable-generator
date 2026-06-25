from flask import Flask, render_template, request, redirect, url_for
import json
import random
from datetime import datetime, timedelta

from database import (
    create_database,
    save_entries,
    faculty_busy,
    classroom_busy,
    list_saved_timetables,
    get_saved_timetable,
    delete_saved_timetable,
)

app = Flask(__name__)

create_database()

def draft_to_form_values(draft):
    form_values = {
        "college": draft.get("college", ""),
        "affiliation": draft.get("affiliation", ""),
        "department": draft.get("department", ""),
        "semester": draft.get("semester", ""),
        "section": draft.get("section", ""),
        "year": draft.get("year", ""),
        "classroom": draft.get("classroom", ""),
        "cycle": draft.get("cycle", ""),
        "classteacher": draft.get("class_teacher", ""),
        "effectivefrom": draft.get("effective_from", ""),
        "workingdays": str(len(draft.get("days", [])) or ""),
        "periods": str(len(draft.get("period_headers", [])) or ""),
        "starttime": draft.get("starttime", ""),
        "lunch": draft.get("lunch_break", ""),
        "firstbreak": draft.get("first_break", ""),
        "firstbreakafter": str(draft.get("first_break_index", "")),
        "lunchafter": str(draft.get("lunch_index", "")),
    }

    for index, subject in enumerate(draft.get("subjects", []), start=1):
        form_values[f"subject{index}"] = subject.get("name", "")
        form_values[f"code{index}"] = subject.get("code", "")
        form_values[f"faculty{index}"] = subject.get("faculty", "")
        form_values[f"hours{index}"] = str(subject.get("hours", ""))

    for index, lab in enumerate(draft.get("labs", []), start=1):
        form_values[f"labsubject{index}"] = lab.get("name", "")
        form_values[f"labfaculty{index}"] = lab.get("faculty", "")
        form_values[f"labduration{index}"] = str(lab.get("duration", ""))
        form_values[f"labroom{index}"] = lab.get("room", "")

    return form_values

def parse_lab_duration(duration):
    digits = "".join(char for char in (duration or "") if char.isdigit())
    return int(digits) if digits else 2

def make_theory_item(subject):
    return {
        "type": "theory",
        "name": subject["name"],
        "code": subject["code"],
        "faculty": subject["faculty"],
        "length": 1,
        "room": "",
        "display": subject["code"] or subject["name"]
    }

def make_lab_item(lab):
    room = lab.get("room", "")
    display = lab["name"]

    if room:
        display = f"{display} ({room})"

    return {
        "type": "lab",
        "name": lab["name"],
        "code": lab["name"],
        "faculty": lab["faculty"],
        "length": lab["duration"],
        "room": room,
        "display": display
    }

def build_clash_free_schedule(subjects, labs, slots, section, classroom, periods_per_day, break_indexes):
    assignments = {}
    local_faculty_slots = set()
    local_room_slots = set()
    requirements = [make_lab_item(lab) for lab in labs]
    failure_reason = ""

    for subject in subjects:
        for _ in range(subject["hours"]):
            requirements.append(make_theory_item(subject))

    for lab in labs:
        if lab["duration"] > periods_per_day:
            return None, (
                f"{lab['name']} needs {lab['duration']} continuous periods, but the day has "
                f"only {periods_per_day} periods."
            )

    required_periods = sum(item["length"] for item in requirements)

    if required_periods > len(slots):
        return None, (
            f"Required teaching periods are {required_periods}, but only "
            f"{len(slots)} timetable slots are available. Reduce weekly hours/lab durations "
            "or increase working days/periods."
        )

    faculty_load = {}

    for item in requirements:
        faculty_load[item["faculty"]] = faculty_load.get(item["faculty"], 0) + item["length"]

    requirements.sort(
        key=lambda item: (
            -item["length"],
            -faculty_load.get(item["faculty"], 0),
            item["faculty"].lower(),
            item["name"].lower()
        )
    )

    slots_by_day_period = {
        (slot["day"], slot["period"]): slot
        for slot in slots
    }

    def block_crosses_break(start_period, length):
        for period in range(start_period + 1, start_period + length):
            if period in break_indexes:
                return True

        return False

    def block_slots(start_slot, length):
        if start_slot["period"] + length > periods_per_day:
            return None

        if block_crosses_break(start_slot["period"], length):
            return None

        block = []

        for period in range(start_slot["period"], start_slot["period"] + length):
            slot = slots_by_day_period.get((start_slot["day"], period))

            if not slot:
                return None

            block.append(slot)

        return block

    def available_blocks(item):
        candidates = []

        for slot in slots:
            block = block_slots(slot, item["length"])

            if not block:
                continue

            room = item["room"] or classroom
            available = True

            for block_slot in block:
                slot_key = (block_slot["day"], block_slot["time"])
                faculty_slot = (item["faculty"].strip().lower(), block_slot["day"], block_slot["time"])
                room_slot = (room.strip().lower(), block_slot["day"], block_slot["time"])

                if slot_key in assignments:
                    available = False
                    break

                if faculty_slot in local_faculty_slots:
                    available = False
                    break

                if room and room_slot in local_room_slots:
                    available = False
                    break

                if faculty_busy(item["faculty"], block_slot["day"], block_slot["time"], section):
                    available = False
                    break

                if classroom_busy(room, block_slot["day"], block_slot["time"], section):
                    available = False
                    break

            if not available:
                continue

            candidates.append(block)

        return candidates

    def backtrack(index):
        nonlocal failure_reason

        if index == len(requirements):
            return True

        item = requirements[index]
        candidates = available_blocks(item)

        if not candidates and not failure_reason:
            room = item["room"] or classroom or "the selected room"

            if item["type"] == "lab":
                failure_reason = (
                    f"{item['name']} could not be placed as a {item['length']}-period continuous lab. "
                    f"Check that {item['faculty']} and {room} are free for a continuous block, and "
                    "that the block does not cross short break or lunch."
                )
            else:
                failure_reason = (
                    f"{item['name']} could not be placed because {item['faculty']} or {room} "
                    "is already busy in all available slots."
                )

        random.shuffle(candidates)

        for block in candidates:
            room = item["room"] or classroom
            applied_faculty_slots = []
            applied_room_slots = []

            for slot in block:
                slot_key = (slot["day"], slot["time"])
                faculty_slot = (item["faculty"].strip().lower(), slot["day"], slot["time"])
                room_slot = (room.strip().lower(), slot["day"], slot["time"])

                assignments[slot_key] = item
                local_faculty_slots.add(faculty_slot)
                applied_faculty_slots.append(faculty_slot)

                if room:
                    local_room_slots.add(room_slot)
                    applied_room_slots.append(room_slot)

            if backtrack(index + 1):
                return True

            for slot in block:
                assignments.pop((slot["day"], slot["time"]))

            for faculty_slot in applied_faculty_slots:
                local_faculty_slots.remove(faculty_slot)

            for room_slot in applied_room_slots:
                local_room_slots.remove(room_slot)

        return False

    if backtrack(0):
        return assignments, ""

    return None, failure_reason or (
        "The timetable could not be completed after checking all valid placements. "
        "Try reducing hours, changing faculty, changing lab rooms, or increasing periods/days."
    )


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
                    effective_from=request.form.get("effectivefrom", ""),
                    form_values=request.form
                )

            saved = save_entries(
                draft.get("entries", []),
                draft.get("section", ""),
                draft
            )

            return render_template(
                'index.html',
                timetable=draft.get("timetable", []),
                subjects=draft.get("subjects", []),
                labs=draft.get("labs", []),
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
                effective_from=draft.get("effective_from", ""),
                form_values=draft_to_form_values(draft)
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
                        approved=False,
                        form_values=request.form
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

                if any([lab_name, lab_faculty, lab_duration, lab_room]) and not all([lab_name, lab_faculty, lab_duration, lab_room]):
                    return render_template(
                        'index.html',
                        timetable=[],
                        subjects=[],
                        days=[],
                        period_headers=[],
                        first_break=first_break,
                        lunch_break=lunch_break,
                        error="Please complete lab subject, faculty, duration, and lab room for every lab row you start filling.",
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
                        approved=False,
                        form_values=request.form
                    )

                if lab_name:

                    labs.append({
                        "name": lab_name,
                        "faculty": lab_faculty,
                        "duration": parse_lab_duration(lab_duration),
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
                approved=False,
                form_values=request.form
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

        schedule, failure_reason = build_clash_free_schedule(
            subjects,
            labs,
            slots,
            section,
            request.form.get("classroom", ""),
            periods_per_day,
            {first_break_index, lunch_index}
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
                error=failure_reason,
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
                approved=False,
                form_values=request.form
            )

        for period in range(periods_per_day):

            row = {
                "time": period_headers[period]["time"]
            }

            for day in days:

                slot_key = (day, period_headers[period]["time"])
                selected_subject = schedule.get(slot_key)
                row[day] = selected_subject["display"] if selected_subject else "Library"

            timetable.append(row)

        entries = []

        for slot_key, subject in schedule.items():
            day, time_slot = slot_key
            room = subject["room"] or request.form.get("classroom", "")

            entries.append({
                "faculty": subject["faculty"],
                "day": day,
                "time_slot": time_slot,
                "section": section,
                "subject": subject["name"],
                "classroom": room
            })

        draft_payload = json.dumps({
            "entries": entries,
            "timetable": timetable,
            "subjects": subjects,
            "labs": labs,
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
            "effective_from": request.form.get("effectivefrom", ""),
            "starttime": start_time
        })

        # =========================
        # LUNCH BREAK
        # =========================

    return render_template(
        'index.html',
        timetable=timetable,
        subjects=subjects,
        labs=labs if request.method == 'POST' else [],
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
        approved=approved,
        form_values=request.form
    )

@app.route('/saved')
def saved_timetables():
    return render_template(
        'saved.html',
        saved_timetables=list_saved_timetables(),
        selected=None,
        message=request.args.get("message", "")
    )

@app.route('/saved/<section>')
def view_saved_timetable(section):
    selected = get_saved_timetable(section)

    return render_template(
        'saved.html',
        saved_timetables=list_saved_timetables(),
        selected=selected,
        message="" if selected else "Saved timetable not found."
    )

@app.route('/saved/<section>/delete', methods=['POST'])
def delete_saved(section):
    delete_saved_timetable(section)

    return redirect(
        url_for(
            'saved_timetables',
            message=f"Saved timetable for section {section} deleted."
        )
    )

@app.route('/saved/<section>/edit')
def edit_saved(section):
    saved = get_saved_timetable(section)

    if not saved:
        return redirect(
            url_for(
                'saved_timetables',
                message="Saved timetable not found."
            )
        )

    form_values = draft_to_form_values(saved)

    return render_template(
        'index.html',
        timetable=[],
        subjects=saved.get("subjects", []),
        labs=saved.get("labs", []),
        days=[],
        period_headers=[],
        first_break_index=None,
        lunch_index=None,
        first_break=saved.get("first_break", "10:50 AM - 11:00 AM"),
        lunch_break=saved.get("lunch_break", "1:00 PM - 2:00 PM"),
        error=None,
        college=saved.get("college", ""),
        affiliation=saved.get("affiliation", ""),
        department=saved.get("department", ""),
        semester=saved.get("semester", ""),
        section=saved.get("section", ""),
        year=saved.get("year", ""),
        classroom=saved.get("classroom", ""),
        cycle=saved.get("cycle", ""),
        class_teacher=saved.get("class_teacher", ""),
        effective_from=saved.get("effective_from", ""),
        draft_payload="",
        approved=False,
        form_values=form_values
    )


if __name__ == '__main__':
    app.run(
        debug=True,
        port=5001
    )
