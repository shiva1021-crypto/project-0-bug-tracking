document.addEventListener("DOMContentLoaded", function () {
    const navToggle = document.querySelector(".nav-toggle");
    const navLinks = document.querySelector(".nav-links");
    const themeToggle = document.querySelector(".theme-toggle");
    const printReport = document.querySelector(".print-report");

    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark-mode");
    }

    if (navToggle && navLinks) {
        navToggle.addEventListener("click", function () {
            navLinks.classList.toggle("open");
        });
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            document.body.classList.toggle("dark-mode");
            localStorage.setItem("theme", document.body.classList.contains("dark-mode") ? "dark" : "light");
        });
    }

    if (printReport) {
        printReport.addEventListener("click", function () {
            window.print();
        });
    }

    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            let valid = true;

            form.querySelectorAll("[required]").forEach(function (field) {
                if (!field.value.trim()) {
                    valid = false;
                    field.classList.add("field-error");
                } else {
                    field.classList.remove("field-error");
                }
            });

            if (!valid) {
                event.preventDefault();
                alert("Please fill all required fields.");
            }
        });
    });
});
