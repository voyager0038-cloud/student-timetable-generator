function addSubject() {

    let container = document.getElementById("subjects-container");

    let row = document.createElement("div");

    row.className = "subject-row";

    row.innerHTML = `
        <input type="text" placeholder="Subject Code">
        <input type="text" placeholder="Subject Name">
        <input type="text" placeholder="Faculty Name">
        <input type="number" placeholder="Hours/Week">
    `;

    container.appendChild(row);
}

function addLab() {

    let container = document.getElementById("labs-container");

    let row = document.createElement("div");

    row.className = "lab-row";

    row.innerHTML = `
        <input type="text" placeholder="Lab Code">
        <input type="text" placeholder="Lab Name">
        <input type="text" placeholder="Faculty Name">
        <input type="number" placeholder="Hours/Week">
    `;

    container.appendChild(row);
}

function printTimetable() {
    window.print();
}

function downloadTimetable() {

    let timetable = document.getElementById("timetable-section");

    if(!timetable){
        alert("Generate timetable first!");
        return;
    }

    let printWindow = window.open('', '', 'height=800,width=1200');

    printWindow.document.write(`
        <html>
        <head>
            <title>Student Timetable</title>
            <style>
                body{
                    font-family:Arial;
                    padding:20px;
                }

                table{
                    width:100%;
                    border-collapse:collapse;
                }

                th,td{
                    border:1px solid black;
                    padding:8px;
                    text-align:center;
                }

                th{
                    background:#1565c0;
                    color:white;
                }
            </style>
        </head>
        <body>
            ${timetable.innerHTML}
        </body>
        </html>
    `);

    printWindow.document.close();
    printWindow.print();
}