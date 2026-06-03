from flask import Flask, render_template, request
import random
from datetime import datetime, timedelta

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def home():

    timetable = []

    if request.method == 'POST':

        # =========================
        # SUBJECT COLLECTION
        # =========================

        subjects = []

        for key in request.form:

            if key.startswith("subject"):

                number = key.replace("subject", "")

                subject_name = request.form.get(
                    f"subject{number}"
                )

                subject_code = request.form.get(
                    f"code{number}"
                )

                faculty_name = request.form.get(
                    f"faculty{number}"
                )

                hours = request.form.get(
                    f"hours{number}"
                )

                if subject_name:

                    subjects.append({

                        "name": subject_name,

                        "code": subject_code,

                        "faculty": faculty_name,

                        "hours": int(hours) if hours else 1

                    })



        # =========================
        # LAB COLLECTION
        # =========================

        labs = []

        for key in request.form:

            if key.startswith("labsubject"):

                number = key.replace(
                    "labsubject",
                    ""
                )

                lab_name = request.form.get(
                    f"labsubject{number}"
                )

                lab_faculty = request.form.get(
                    f"labfaculty{number}"
                )

                lab_duration = request.form.get(
                    f"labduration{number}"
                )

                lab_room = request.form.get(
                    f"labroom{number}"
                )

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
            request.form.get("workingdays", 5)
        )

        periods_per_day = int(
            request.form.get("periods", 7)
        )

        lunch_break = request.form.get(
            "lunch",
            "1:00 PM - 2:00 PM"
        )

        start_time = request.form.get(
            "starttime",
            "09:00"
        )

        period_duration = 1



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


        for period in range(periods_per_day):

            current = start + timedelta(
                hours=period
            )

            next_time = current + timedelta(
                hours=period_duration
            )

            time_slot = (
                f"{current.strftime('%I:%M %p')} "
                f"- "
                f"{next_time.strftime('%I:%M %p')}"
            )

            row = {

                "time": time_slot

            }


            for day in days:

                selected_subject = random.choice(
                    subjects
                )

                content = f"""

                <b>{selected_subject['name']}</b><br>

                {selected_subject['code']}<br>

                {selected_subject['faculty']}

                """

                row[day] = content


            timetable.append(row)



        # =========================
        # LUNCH BREAK
        # =========================

        lunch_row = {

            "time": lunch_break

        }

        for day in days:

            lunch_row[day] = "🍴 Lunch Break"

        insert_position = len(timetable) // 2

        timetable.insert(
            insert_position,
            lunch_row
        )



    return render_template(

        'index.html',

        timetable=timetable

    )



if __name__ == '__main__':

    app.run(
        debug=True,
        port=5001
    )