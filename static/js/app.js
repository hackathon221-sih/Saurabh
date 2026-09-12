document.addEventListener("DOMContentLoaded", () => {
    const today = document.getElementById("today");
    if (today) {
        today.textContent = new Date().toLocaleDateString("en-IN", {
            weekday:"short", day:"numeric", month:"short", year:"numeric"
        });
    }
    const search = document.getElementById("globalSearch");
    if (search) {
        search.addEventListener("keydown", async (e) => {
            if (e.key !== "Enter" || !search.value.trim()) return;
            const res = await fetch("/api/search?q=" + encodeURIComponent(search.value));
            const data = await res.json();
            if (data.length) window.location.href = "/events";
            else alert("No matching upcoming event found.");
        });
    }
});
