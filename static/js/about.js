document.addEventListener('DOMContentLoaded', function() {
    var codeEl = document.getElementById('app-version');
    if (!codeEl) return;
    fetch('/get_app_version')
        .then(function(resp) {
            if (!resp.ok) throw new Error('Network response was not ok');
            return resp.json();
        })
        .then(function(data) {
            var version = (data && data.app_version) ? data.app_version : 'unknown';
            codeEl.textContent = version;
        })
        .catch(function() {
            codeEl.textContent = 'unknown';
        });
});