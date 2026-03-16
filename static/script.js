function openImageModal(imageSrc) {
    document.getElementById("imageModal").style.display = "flex";
    document.getElementById("modalImage").src = imageSrc;
}

function closeImageModal() {
    document.getElementById("imageModal").style.display = "none";
}

function openNoteModal(button) {

    const eventId = button.getAttribute("data-event-id");
    const currentNote = button.getAttribute("data-note");

    document.getElementById("noteModal").style.display = "flex";
    document.getElementById("noteForm").action = "/add_note/" + eventId;

    document.getElementById("noteInput").value = currentNote || "";
}

function closeNoteModal() {
    document.getElementById("noteModal").style.display = "none";
}

function closeNoteModalOutside(event) {
    if (event.target.id === "noteModal") {
        closeNoteModal();
    }
}

window.addEventListener("DOMContentLoaded", function () {

    const chartData = document.getElementById("chart-data");

    const unreviewed = parseInt(chartData.dataset.unreviewed);
    const reviewed = parseInt(chartData.dataset.reviewed);
    const falseAlarm = parseInt(chartData.dataset.false);

    const ctx = document.getElementById("statusChart");

    if (ctx) {

        new Chart(ctx, {

            type: "doughnut",

            data: {

                labels: ["Unreviewed", "Reviewed", "False Alarm"],

                datasets: [{
                    data: [unreviewed, reviewed, falseAlarm],

                    backgroundColor: [
                        "#f59e0b",
                        "#16a34a",
                        "#dc2626"
                    ],

                    borderWidth: 0
                }]
            },

            options: {

                responsive: true,

                plugins: {
                    legend: {
                        labels: {
                            color: "white"
                        }
                    }
                }
            }
        });

    }

});