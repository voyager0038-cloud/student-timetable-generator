from flask import Flask, render_template, request
import random

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():

    timetable = []

    if request.method == 'POST':

        subjects = [s.strip() for s in request.form['subjects'].split(',')]

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

                row = {
                    "time": period,
                    "Monday": random.choice(subjects),
                    "Tuesday": random.choice(subjects),
                    "Wednesday": random.choice(subjects),
                    "Thursday": random.choice(subjects),
                    "Friday": random.choice(subjects)
                }

            timetable.append(row)

    return render_template('index.html', timetable=timetable)

if __name__ == '__main__':
    app.run(debug=True, port=5002)