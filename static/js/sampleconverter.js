function setupDragDrop(id, type) {
    const dropArea = document.getElementById(id);

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

    // Drag & Drop behavior
    dropArea.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropArea.classList.add('dragover');
    });

    dropArea.addEventListener('dragleave', (event) => {
        event.preventDefault();
        dropArea.classList.remove('dragover');
    });

    dropArea.addEventListener('drop', async (event) => {
        event.preventDefault();
        dropArea.classList.remove('dragover');
        await handleFiles(event.dataTransfer.files, type);
    });
}

async function handleFiles(files, type) {

    const results = [];

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type); // "drum" or "synth"

        try {
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            results.push(`${file.name}: ${result.message || "Success"}`);
        } catch (err) {
            results.push(`${file.name}: Error - ${err.message}`);
        }
    }

    // Show all results in one alert
    console.log("Conversion results:", results);
    alert(results.join('\n'));
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