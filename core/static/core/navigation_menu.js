(() => {
    const initializeMenus = () => {
    const triggers = [...document.querySelectorAll("[data-menu-trigger]")];

    const closeMenu = (trigger, restoreFocus = false) => {
        const menu = document.getElementById(trigger.dataset.menuTrigger);
        if (!menu) return;
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        if (restoreFocus) trigger.focus();
    };

    const closeAll = (except) => {
        triggers.forEach((trigger) => {
            if (trigger !== except) closeMenu(trigger);
        });
    };

    triggers.forEach((trigger) => {
        const menu = document.getElementById(trigger.dataset.menuTrigger);
        if (!menu) return;
        trigger.addEventListener("click", () => {
            const isOpen = trigger.getAttribute("aria-expanded") === "true";
            closeAll(trigger);
            menu.hidden = isOpen;
            trigger.setAttribute("aria-expanded", String(!isOpen));
            if (!isOpen) menu.querySelector("a, button")?.focus();
        });
        menu.addEventListener("click", (event) => {
            if (event.target.closest("a, button")) closeMenu(trigger);
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-menu-trigger], [data-menu]")) closeAll();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            const openTrigger = triggers.find(
                (trigger) => trigger.getAttribute("aria-expanded") === "true"
            );
            if (openTrigger) closeMenu(openTrigger, true);
        }
    });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeMenus, { once: true });
    } else {
        initializeMenus();
    }
})();
