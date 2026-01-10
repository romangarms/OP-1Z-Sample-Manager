/**
 * Update Checker - runs on page load
 * Backend handles cooldown (default: 1 hour between notices)
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const resp = await fetch('/display_update_notice');
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.display_update_notice) {
            toast.info(
                `New version ${data.github_version} available (you have ${data.current_version}).`,
                'Update Available',
                { duration: 8000 }
            );
        }
    } catch (err) {
        console.error('Update check failed:', err);
    }
});