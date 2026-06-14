from flask import Flask, render_template, request
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():

    timetable = []

    department = ""
    semester = ""

    if request.method == 'POST':

        department = request.form['department']
        semester = request.form['semester']

        subjects = []
        faculty = []

        for i in range(1, 6):

            sub = request.form.get(f'subject{i}')
            fac = request.form.get(f'faculty{i}')

            if sub and fac:
                subjects.append(sub)
                faculty.append(fac)

        subject_faculty = list(zip(subjects, faculty))

        periods = [
            "9:00 - 10:00",
            "10:00 - 11:00",
            "11:00 - 12:00",
            "12:00 - 1:00",
            "LUNCH BREAK",
            "2:00 - 3:00",
            "3:00 - 4:00"
        ]

        for period in periods:

            if period == "LUNCH BREAK":

                row = {
                    "time": period,
                    "Monday": "BREAK",
                    "Tuesday": "BREAK",
                    "Wednesday": "BREAK",
                    "Thursday": "BREAK",
                    "Friday": "BREAK"
                }

            else:

                def random_subject():
                    sub, fac = random.choice(subject_faculty)
                    return f"{sub}<br><small>{fac}</small>"

                row = {
                    "time": period,
                    "Monday": random_subject(),
                    "Tuesday": random_subject(),
                    "Wednesday": random_subject(),
                    "Thursday": random_subject(),
                    "Friday": random_subject()
                }

            timetable.append(row)

    return render_template(
        'index.html',
        timetable=timetable,
        department=department,
        semester=semester,
        subject_faculty=subject_faculty if request.method == 'POST' else []
    )

if __name__ == '__main__':
    app.run(debug=True, port=5001)