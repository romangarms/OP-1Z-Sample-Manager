function setupDragDrop(id, type) {
    const dropArea = document.getElementById(id);
    const samplePackBox = dropArea.parentElement;
    let dragCounter = 0;

    // Create hidden file input
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // When the user clicks the drop area, trigger the input
    dropArea.addEventListener('click', () => fileInput.click());

    // When files are selected via the file picker
    fileInput.addEventListener('change', async (event) => {
        await handleFiles(event.target.files, type);
    });

    // Drag & Drop behavior - use samplePackBox to avoid child element issues
    samplePackBox.addEventListener('dragenter', (event) => {
        event.preventDefault();
        dragCounter++;
        samplePackBox.classList.add('dragover');
    });

    samplePackBox.addEventListener('dragover', (event) => {
        event.preventDefault();
    });

    samplePackBox.addEventListener('dragleave', (event) => {
        event.preventDefault();
        dragCounter--;
        if (dragCounter === 0) {
            samplePackBox.classList.remove('dragover');
        }
    });

    samplePackBox.addEventListener('drop', async (event) => {
        event.preventDefault();
        dragCounter = 0;
        samplePackBox.classList.remove('dragover');
        await handleFiles(event.dataTransfer.files, type);
    });
}

function showConvertingProgress(current, total, filename) {
    const overlay = document.getElementById('converting-overlay');
    const status = document.getElementById('converting-status');
    const progress = document.getElementById('converting-progress');

    overlay.classList.remove('hidden');
    status.textContent = `Converting ${current} of ${total}: ${filename}`;
    progress.style.width = `${(current / total) * 100}%`;
}

function hideConvertingProgress() {
    document.getElementById('converting-overlay').classList.add('hidden');
    document.getElementById('converting-progress').style.width = '0%';
}

async function handleFiles(files, type) {
    const results = [];
    const total = files.length;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        showConvertingProgress(i + 1, total, file.name);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type); // "drum" or "synth"

        try {
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                results.push(`${file.name}: Error - ${result.error || 'Conversion failed'}`);
            } else {
                results.push(`${file.name}: ${result.message || 'Converted'}`);
            }
        } catch (err) {
            results.push(`${file.name}: Error - ${err.message}`);
        }
    }

    hideConvertingProgress();

    // Show results as toast
    const successCount = results.filter(r => r.includes('Success') || r.includes('Converted')).length;
    const errorCount = results.length - successCount;

    if (errorCount === 0) {
        toast.success(`${successCount} file(s) converted`, 'Conversion Complete');
    } else if (successCount === 0) {
        toast.error(`${errorCount} file(s) failed`, 'Conversion Failed');
    } else {
        toast.warning(`${successCount} converted, ${errorCount} failed`, 'Partial Conversion');
    }
}


function openExplorer() {
    fetch("/open-explorer", { method: "POST" })
        .then(response => {
            if (!response.ok) throw new Error("Request failed");
            return response.json();
        })
        .catch(err => {
            console.error("Error:", err);
        });
}

function deleteAllConverted() {
    showConfirmModal(
        'Delete All Converted Samples',
        'Are you sure you want to delete all converted samples? This cannot be undone.',
        () => {
            fetch("/delete-all-converted", { method: "DELETE" })
                .then(response => {
                    if (!response.ok) throw new Error("Request failed");
                    return response.json();
                })
                .then(data => {
                    if (data.count === 0) {
                        toast.info('No files to delete', 'Folder Empty');
                    } else {
                        toast.success(`Deleted ${data.count} file(s)`, 'Samples Deleted');
                    }
                })
                .catch(err => {
                    toast.error('Failed to delete samples');
                    console.error("Error:", err);
                });
        }
    );
}

document.addEventListener('DOMContentLoaded', () => {
    setupDragDrop('drum-samples', 'drum');
    setupDragDrop('synth-samples', 'synth');

    // Initialize Lucide icons
    lucide.createIcons();
});

// Prevent default drag-and-drop behavior on the whole page
window.addEventListener("dragover", (e) => {
    e.preventDefault();
});

window.addEventListener("drop", (e) => {
    e.preventDefault();
});