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
                {
                    duration: 8000,
                    actions: [
                        //Open latest release page
                        {
                            text: 'View Release',
                            type: 'primary',
                            onClick: () => {
                                //latest: https://github.com/romangarms/OP-1Z-Sample-Manager/releases/latest
                                window.open('https://github.com/romangarms/OP-1Z-Sample-Manager/releases/latest');
                            }
                        },
                        //Set this tag as ignored version
                        {
                            text: 'Ignore',
                            type: 'secondary',
                            onClick: () => {
                                fetch("/set-config-setting", {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({
                                        config_option: "UPDATE_CHECKER_IGNORED_VERSION",
                                        config_value: data.github_version
                                    })
                                })
                            }
                        }
                    ]
                }
            );
        }
    } catch (err) {
        console.error('Update check failed:', err);
    }
});