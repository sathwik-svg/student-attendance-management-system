document.addEventListener("DOMContentLoaded", () => {

    /* Reveal cards when they enter viewport */

    const cards = document.querySelectorAll(
        ".feature-card, .role-card, .analytics-panel"
    );

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {

                if (entry.isIntersecting) {
                    entry.target.style.opacity = "1";
                    entry.target.style.transform = "translateY(0)";
                    observer.unobserve(entry.target);
                }

            });
        },
        {
            threshold: 0.15
        }
    );


    cards.forEach((card) => {

        card.style.opacity = "0";
        card.style.transform = "translateY(35px)";
        card.style.transition =
            "opacity .8s ease, transform .8s cubic-bezier(.2,.8,.2,1)";

        observer.observe(card);

    });


    /* Mouse movement effect */

    const dashboard = document.querySelector(".dashboard-card");

    if (dashboard) {

        dashboard.addEventListener("mousemove", (event) => {

            const rect = dashboard.getBoundingClientRect();

            const x =
                (event.clientX - rect.left) /
                rect.width - .5;

            const y =
                (event.clientY - rect.top) /
                rect.height - .5;

            dashboard.style.transform =
                `rotateY(${x * 12 - 4}deg)
                 rotateX(${y * -12 + 3}deg)
                 translateY(-5px)`;

        });


        dashboard.addEventListener("mouseleave", () => {

            dashboard.style.transform =
                "rotateY(-8deg) rotateX(5deg)";

        });

    }


    /* Smooth button feedback */

    document.querySelectorAll(".primary-button").forEach((button) => {

        button.addEventListener("mouseenter", () => {
            button.style.setProperty("--button-scale", "1.03");
        });

        button.addEventListener("mouseleave", () => {
            button.style.setProperty("--button-scale", "1");
        });

    });


    console.log(
        "%c ATTENDX ",
        "background:#fff;color:#000;padding:6px 12px;border-radius:20px;font-weight:bold;"
    );

    console.log(
        "Student Attendance Management System — home-server"
    );

});


/* =========================================================
   ATTENDX V2 — INTERACTION ENGINE
   ========================================================= */


/* Architecture node magnetic movement */

document.querySelectorAll(".architecture-node").forEach((node) => {

    node.addEventListener("mousemove", (event) => {

        const rect = node.getBoundingClientRect();

        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;

        node.style.transform =
            `perspective(700px)
             rotateX(${y * -6}deg)
             rotateY(${x * 6}deg)
             translateY(-5px)`;

    });

    node.addEventListener("mouseleave", () => {

        node.style.transform = "";

    });

});


/* VVIT logo mouse response */

const vvit = document.querySelector(".vvit-edge-brand");

if (vvit) {

    document.addEventListener("mousemove", (event) => {

        const x = event.clientX / window.innerWidth - 0.5;
        const y = event.clientY / window.innerHeight - 0.5;

        vvit.style.setProperty(
            "--mouse-x",
            `${x * 8}px`
        );

        vvit.style.setProperty(
            "--mouse-y",
            `${y * 8}px`
        );

    });

}


/* Architecture reveal */

const architectureElements =
    document.querySelectorAll(
        ".architecture-heading, .architecture-node, .database-core, .monitor-widget"
    );

const architectureObserver =
    new IntersectionObserver(
        (entries) => {

            entries.forEach((entry) => {

                if (!entry.isIntersecting) return;

                entry.target.classList.add("architecture-visible");

                architectureObserver.unobserve(entry.target);

            });

        },
        {
            threshold: 0.15
        }
    );


architectureElements.forEach((element) => {

    element.classList.add("architecture-hidden");

    architectureObserver.observe(element);

});


/* Live system clock */

function updateSystemTime() {

    const widget = document.querySelector(".widget-metric");

    if (!widget) return;

    const now = new Date();

    const time = now.toLocaleTimeString(
        [],
        {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }
    );

    widget.querySelector("span").textContent = time;

}

setInterval(updateSystemTime, 1000);
updateSystemTime();



/* =========================================================
   ATTENDX V4 — BRIGHT / DARK THEME ENGINE
   ========================================================= */

(function () {

    const root = document.documentElement;
    const toggle = document.getElementById("themeToggle");

    function setTheme(theme, animate = false) {

        if (animate) {

            document.body.classList.remove("theme-changing");

            void document.body.offsetWidth;

            document.body.classList.add("theme-changing");

        }

        root.setAttribute("data-theme", theme);

        if (toggle) {

            toggle.setAttribute(
                "aria-label",
                theme === "light"
                    ? "Switch to dark mode"
                    : "Switch to bright mode"
            );

        }

    }


    const savedTheme =
        localStorage.getItem("attendx-theme");


    const systemTheme =
        window.matchMedia(
            "(prefers-color-scheme: light)"
        ).matches
            ? "light"
            : "dark";


    setTheme(
        savedTheme || systemTheme,
        false
    );


    if (toggle) {

        toggle.addEventListener(
            "click",
            function () {

                const current =
                    root.getAttribute("data-theme");

                const next =
                    current === "light"
                        ? "dark"
                        : "light";


                setTheme(next, true);

                localStorage.setItem(
                    "attendx-theme",
                    next
                );

            }
        );

    }

})();


/* =========================================================
   VVIT PARALLAX
   ========================================================= */

(function () {

    const brand =
        document.querySelector(".vvit-edge-brand");

    if (!brand) return;


    window.addEventListener(
        "mousemove",
        function (event) {

            const x =
                (event.clientX /
                    window.innerWidth -
                    0.5) * 7;


            const y =
                (event.clientY /
                    window.innerHeight -
                    0.5) * 7;


            brand.style.setProperty(
                "--mouse-x",
                `${x}px`
            );

            brand.style.setProperty(
                "--mouse-y",
                `${y}px`
            );

        }
    );

})();

