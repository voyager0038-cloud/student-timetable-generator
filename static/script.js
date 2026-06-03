/* ========================= */
/* DARK MODE */
/* ========================= */

function toggleDarkMode() {

    document.body.classList.toggle("dark-mode");

    if(document.body.classList.contains("dark-mode")){

        localStorage.setItem("theme", "dark");

    }

    else{

        localStorage.setItem("theme", "light");

    }

}


/* ========================= */
/* LOAD SAVED THEME */
/* ========================= */

window.onload = function(){

    let savedTheme =
    localStorage.getItem("theme");

    if(savedTheme === "dark"){

        document.body.classList.add("dark-mode");

    }

}


/* ========================= */
/* PRINT TIMETABLE */
/* ========================= */

function printTimetable(){

    window.print();

}


/* ========================= */
/* SUBJECT + LAB COUNTS */
/* ========================= */

let subjectCount = 8;
let labCount = 1;


/* ========================= */
/* PAGE LOAD */
/* ========================= */

document.addEventListener("DOMContentLoaded", function(){


    /* ========================= */
    /* ADD SUBJECT */
    /* ========================= */

    const addSubjectBtn =
    document.getElementById("addSubjectBtn");

    if(addSubjectBtn){

        addSubjectBtn.addEventListener("click", function(){

            subjectCount++;

            const table =
            document.getElementById("subjectTable");

            let row = table.insertRow();

            row.innerHTML = `

                <td>

                    <input type="text"
                    name="subject${subjectCount}"
                    placeholder="New Subject">

                </td>

                <td>

                    <input type="text"
                    name="code${subjectCount}"
                    placeholder="Subject Code">

                </td>

                <td>

                    <input type="text"
                    name="faculty${subjectCount}"
                    placeholder="Professor Name">

                </td>

                <td>

                    <input type="number"
                    name="hours${subjectCount}"
                    placeholder="Weekly Hours">

                </td>

            `;

        });

    }



    /* ========================= */
    /* ADD LAB */
    /* ========================= */

    const addLabBtn =
    document.getElementById("addLabBtn");

    if(addLabBtn){

        addLabBtn.addEventListener("click", function(){

            labCount++;

            const table =
            document.getElementById("labTable");

            let row = table.insertRow();

            row.innerHTML = `

                <td>

                    <input type="text"
                    name="labsubject${labCount}"
                    placeholder="New Lab">

                </td>

                <td>

                    <input type="text"
                    name="labfaculty${labCount}"
                    placeholder="Faculty Name">

                </td>

                <td>

                    <input type="text"
                    name="labduration${labCount}"
                    placeholder="Duration">

                </td>

                <td>

                    <input type="text"
                    name="labroom${labCount}"
                    placeholder="Lab Room">

                </td>

            `;

        });

    }

});