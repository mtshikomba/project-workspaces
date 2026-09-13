(() => {
    const focusFirstInvalidField = () => {
        document.querySelector("[aria-invalid='true']")?.focus();
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", focusFirstInvalidField, {
            once: true,
        });
    } else {
        focusFirstInvalidField();
    }
})();