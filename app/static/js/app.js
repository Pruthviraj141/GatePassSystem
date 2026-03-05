/* ─── Campus GatePass — Client JS ─────────────────────────────────────── */

/**
 * Initialise WebSocket notifications for admin pages.
 * Call this from an Alpine x-data component on admin templates.
 */
function adminNotifications() {
    return {
        notifications: [],
        init() {
            const proto = location.protocol === "https:" ? "wss:" : "ws:";
            const ws = new WebSocket(`${proto}//${location.host}/ws/notifications`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const id = Date.now();
                this.notifications.push({ id, message: data.message, show: true });
                setTimeout(() => {
                    this.notifications = this.notifications.filter((n) => n.id !== id);
                }, 6000);
            };
            ws.onclose = () => {
                // Attempt reconnect after 5 s
                setTimeout(() => this.init(), 5000);
            };
        },
        dismiss(id) {
            this.notifications = this.notifications.filter((n) => n.id !== id);
        },
    };
}

/* HTMX global config */
document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener("htmx:afterSwap", (e) => {
        // Add fade-in animation to swapped elements
        if (e.detail.target) {
            e.detail.target.classList.add("animate-fade-in-up");
        }
    });
});
