document.addEventListener("DOMContentLoaded", () => {

    // =====================================
    // SIDEBAR MENU
    // =====================================

    const toggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");

    if (toggle && sidebar) {

        toggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
        });

        document.addEventListener("click", (event) => {

            if (
                window.innerWidth <= 760 &&
                sidebar.classList.contains("open") &&
                !sidebar.contains(event.target) &&
                !toggle.contains(event.target)
            ) {
                sidebar.classList.remove("open");
            }

        });
    }


    // =====================================
    // DASHBOARD PROGRESS CHART
    // =====================================

    const chartCanvas = document.getElementById("progressChart");

    if (chartCanvas && window.Chart) {

        const chartData = window.progressChartData || {
            completed: 0,
            inProgress: 0,
            notStarted: 0
        };

        new Chart(chartCanvas, {

            type: "doughnut",

            data: {

                labels: [
                    "Completed",
                    "In progress",
                    "Not started"
                ],

                datasets: [{

                    data: [
                        chartData.completed,
                        chartData.inProgress,
                        chartData.notStarted
                    ],

                    backgroundColor: [
                        "#9b7bff",
                        "#566079",
                        "#30384b"
                    ],

                    borderWidth: 0,
                    hoverOffset: 7,
                    borderRadius: 5,
                    spacing: 4

                }]

            },

            options: {

                responsive: true,
                maintainAspectRatio: false,
                cutout: "78%",

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        backgroundColor: "#20263a",
                        titleColor: "#fff",
                        bodyColor: "#c8cde0",
                        padding: 11,
                        displayColors: true

                    }

                },

                animation: {
                    animateRotate: true,
                    duration: 1000
                }

            }

        });

    }


    // =====================================
    // AUTOMATIC SKILL PROGRESS SAVING
    // =====================================

    document.querySelectorAll(".status-select").forEach((select) => {

        select.addEventListener("change", async() => {

            const hint = document.getElementById("saveHint");

            if (hint) {
                hint.textContent = "Saving your progress…";
            }

            select.disabled = true;

            try {

                const response = await fetch("/progress/update", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({

                        career_title: select.dataset.career,
                        skill_name: select.dataset.skill,
                        status: select.value

                    })

                });

                const result = await response.json();

                if (!response.ok || !result.ok) {

                    throw new Error(
                        result.message || "Could not save."
                    );

                }

                if (hint) {

                    hint.textContent =
                        "✓ Progress saved to your account.";

                }

            } catch (error) {

                console.error("Progress saving error:", error);

                if (hint) {

                    hint.textContent =
                        "Save failed. Please refresh and try again.";

                }

            } finally {

                select.disabled = false;

            }

        });

    });

});