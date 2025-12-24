/**
 * OP-Z Config Editor
 * Tabbed interface with auto-save functionality
 */

// ===========================================
// Constants
// ===========================================

const CONFIG_FRIENDLY_NAMES = {
    // General config
    backlit_keys: "Backlit Keys",
    disable_headphone_db_reduction: "Disable Headphone dB Reduction",
    disable_microphone_mode: "Disable Microphone Mode",
    disable_param_page_reset: "Disable Parameter Page Reset",
    disable_start_sound: "Disable Startup Sound",
    disable_track_preview: "Disable Track Preview",
    generous_chords: "Generous Chords",
    latch_notes_with_shift: "Latch Notes with Shift",
    legacy_input_select: "Legacy Input Select",
    temp_param_add_fx_a: "Temp Parameter Add FX A",

    // MIDI global config
    alt_program_change: "Alt Program Change",
    channel_one_to_active: "Channel 1 to Active Track",
    enable_program_change: "Enable Program Change",
    incoming_midi: "Incoming MIDI",
    midi_echo: "MIDI Echo",
    outgoing_midi: "Outgoing MIDI",
    timing_clock_in: "MIDI Clock In",
    timing_clock_out: "MIDI Clock Out"
};

const OPZ_TRACK_NAMES = [
    "Kick", "Snare", "Perc", "Sample",
    "Bass", "Lead", "Arp", "Chord",
    "FX1", "FX2", "Tape", "Master",
    "Perform", "Module", "Lights", "Motion"
];

const MIDI_GLOBAL_KEYS = [
    'incoming_midi', 'outgoing_midi', 'midi_echo',
    'timing_clock_in', 'timing_clock_out',
    'enable_program_change', 'alt_program_change', 'channel_one_to_active'
];

const CC_COLORS = ['green', 'blue', 'yellow', 'red'];

// ===========================================
// State
// ===========================================

let midiConfig = null;
let generalConfig = null;

// ===========================================
// Utility Functions
// ===========================================

function getFriendlyName(key) {
    if (CONFIG_FRIENDLY_NAMES[key]) {
        return CONFIG_FRIENDLY_NAMES[key];
    }
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function createCheckbox(name, checked, onChange) {
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = name;
    input.checked = checked;
    input.className = 'toggle-checkbox';
    if (onChange) {
        input.addEventListener('change', onChange);
    }
    return input;
}

function createNumberInput(name, value, onChange) {
    const input = document.createElement('input');
    input.type = 'number';
    input.name = name;
    input.value = value;
    input.className = 'channel-input';
    if (onChange) {
        input.addEventListener('change', onChange);
    }
    return input;
}

// ===========================================
// Tab Setup
// ===========================================

function initTabs() {
    const tabsContainer = document.getElementById('config-tabs-container');

    createTabs({
        container: tabsContainer,
        tabs: [
            { id: 'general', label: 'General' },
            { id: 'midi', label: 'MIDI' },
            { id: 'dmx', label: 'DMX' }
        ],
        defaultTab: 'general',
        persistKey: 'configEditorTab',
        onChange: (tabId) => {
            // Hide all tab content
            document.querySelectorAll('.tab-content').forEach(el => {
                el.hidden = true;
            });
            // Show selected tab content
            const activeContent = document.getElementById(`tab-${tabId}`);
            if (activeContent) {
                activeContent.hidden = false;
            }
        }
    });
}

// ===========================================
// General Config
// ===========================================

function renderGeneralForm(config) {
    const form = document.getElementById('general-form');
    form.innerHTML = '';

    for (const [key, value] of Object.entries(config)) {
        if (typeof value !== 'boolean') continue;

        const item = document.createElement('div');
        item.className = 'config-item';

        const label = document.createElement('label');
        label.className = 'config-label';
        label.textContent = getFriendlyName(key);

        const checkbox = createCheckbox(key, value, () => saveGeneralConfig());

        item.appendChild(label);
        item.appendChild(checkbox);
        form.appendChild(item);
    }
}

async function saveGeneralConfig() {
    try {
        const form = document.getElementById('general-form');
        const config = {};

        form.querySelectorAll('input[type="checkbox"]').forEach(input => {
            config[input.name] = input.checked;
        });

        await fetch('/save-config/general', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        toast.success('Settings saved');
    } catch (err) {
        console.error('Error saving general config:', err);
        toast.error('Failed to save settings');
    }
}

// ===========================================
// MIDI Config
// ===========================================

async function loadMidiConfig() {
    try {
        const res = await fetch('/get-config/midi');
        midiConfig = await res.json();
        renderMidiGlobalSettings(midiConfig);
        renderTrackAccordions(midiConfig);
    } catch (err) {
        console.error('Error loading MIDI config:', err);
        toast.error('Failed to load MIDI settings');
    }
}

function renderMidiGlobalSettings(config) {
    const form = document.getElementById('midi-global-form');
    form.innerHTML = '';

    MIDI_GLOBAL_KEYS.forEach(key => {
        if (!(key in config)) return;

        const item = document.createElement('div');
        item.className = 'config-item';

        const label = document.createElement('label');
        label.className = 'config-label';
        label.textContent = getFriendlyName(key);

        const checkbox = createCheckbox(key, config[key], () => saveMidiConfig());

        item.appendChild(label);
        item.appendChild(checkbox);
        form.appendChild(item);
    });
}

function renderTrackAccordions(config) {
    const container = document.getElementById('midi-track-sections');
    container.innerHTML = '';

    const trackEnable = config.track_enable || [];
    const trackChannels = config.track_channels || [];
    const parameterCcOut = config.parameter_cc_out || [];

    OPZ_TRACK_NAMES.forEach((trackName, idx) => {
        const accordion = createTrackAccordion(
            idx,
            trackName,
            trackEnable[idx] ?? true,
            trackChannels[idx] ?? idx,
            parameterCcOut[idx] || new Array(16).fill(0)
        );
        container.appendChild(accordion);
    });
}

function createTrackAccordion(trackIdx, trackName, enabled, channel, ccValues) {
    const accordion = document.createElement('div');
    accordion.className = 'track-accordion';
    accordion.dataset.trackIndex = trackIdx;

    // Header
    const header = document.createElement('div');
    header.className = 'track-accordion-header';
    header.innerHTML = `
        <div class="track-accordion-title">
            <span class="track-number">${trackIdx + 1}</span>
            <span class="track-name">${trackName}</span>
        </div>
        <svg class="track-accordion-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
    `;
    header.addEventListener('click', () => {
        accordion.classList.toggle('expanded');
    });

    // Content
    const content = document.createElement('div');
    content.className = 'track-accordion-content';

    // Track settings row (Enable + Channel)
    const settingsRow = document.createElement('div');
    settingsRow.className = 'track-settings-row';

    // Enable toggle
    const enableSetting = document.createElement('div');
    enableSetting.className = 'track-setting';
    const enableLabel = document.createElement('span');
    enableLabel.className = 'track-setting-label';
    enableLabel.textContent = 'Enable';
    const enableCheckbox = createCheckbox(`track_enable_${trackIdx}`, enabled, () => saveMidiConfig());
    enableCheckbox.dataset.trackIndex = trackIdx;
    enableCheckbox.dataset.field = 'track_enable';
    enableSetting.appendChild(enableLabel);
    enableSetting.appendChild(enableCheckbox);

    // Channel input
    const channelSetting = document.createElement('div');
    channelSetting.className = 'track-setting';
    const channelLabel = document.createElement('span');
    channelLabel.className = 'track-setting-label';
    channelLabel.textContent = 'MIDI Channel';
    const channelInput = createNumberInput(`track_channel_${trackIdx}`, channel, () => saveMidiConfig());
    channelInput.dataset.trackIndex = trackIdx;
    channelInput.dataset.field = 'track_channels';
    channelInput.min = 0;
    channelInput.max = 15;
    channelSetting.appendChild(channelLabel);
    channelSetting.appendChild(channelInput);

    settingsRow.appendChild(enableSetting);
    settingsRow.appendChild(channelSetting);
    content.appendChild(settingsRow);

    // CC Grid
    const ccContainer = document.createElement('div');
    ccContainer.className = 'cc-grid-container';

    const ccTitle = document.createElement('h4');
    ccTitle.textContent = 'CC Values';
    ccContainer.appendChild(ccTitle);

    const ccGrid = document.createElement('div');
    ccGrid.className = 'cc-grid';

    // Header row
    const headerRow = document.createElement('div');
    headerRow.className = 'cc-grid-header';
    headerRow.innerHTML = `<span></span>`; // Empty cell for row label column
    CC_COLORS.forEach(color => {
        const header = document.createElement('span');
        header.className = `cc-column-header ${color}`;
        header.textContent = color.charAt(0).toUpperCase() + color.slice(1);
        headerRow.appendChild(header);
    });
    ccGrid.appendChild(headerRow);

    // 4 rows (pages)
    for (let page = 0; page < 4; page++) {
        const row = document.createElement('div');
        row.className = 'cc-grid-row';

        const rowLabel = document.createElement('span');
        rowLabel.className = 'cc-row-label';
        rowLabel.textContent = `Page ${page + 1}`;
        row.appendChild(rowLabel);

        // 4 columns (knobs)
        for (let knob = 0; knob < 4; knob++) {
            const ccIndex = page * 4 + knob;
            const input = document.createElement('input');
            input.type = 'number';
            input.className = `cc-input ${CC_COLORS[knob]}`;
            input.value = ccValues[ccIndex] ?? 0;
            input.min = 0;
            input.max = 127;
            input.dataset.trackIndex = trackIdx;
            input.dataset.ccIndex = ccIndex;
            input.dataset.field = 'parameter_cc_out';
            input.addEventListener('change', () => saveMidiConfig());
            row.appendChild(input);
        }

        ccGrid.appendChild(row);
    }

    ccContainer.appendChild(ccGrid);
    content.appendChild(ccContainer);

    accordion.appendChild(header);
    accordion.appendChild(content);

    return accordion;
}

async function saveMidiConfig() {
    try {
        // Build config from form state
        const config = {
            track_enable: [],
            track_channels: [],
            parameter_cc_out: []
        };

        // Get global settings
        const globalForm = document.getElementById('midi-global-form');
        globalForm.querySelectorAll('input[type="checkbox"]').forEach(input => {
            config[input.name] = input.checked;
        });

        // Get track settings
        const accordions = document.querySelectorAll('.track-accordion');
        accordions.forEach((accordion, trackIdx) => {
            // Enable
            const enableCheckbox = accordion.querySelector('input[data-field="track_enable"]');
            config.track_enable[trackIdx] = enableCheckbox ? enableCheckbox.checked : true;

            // Channel
            const channelInput = accordion.querySelector('input[data-field="track_channels"]');
            config.track_channels[trackIdx] = channelInput ? parseInt(channelInput.value) : trackIdx;

            // CC values
            config.parameter_cc_out[trackIdx] = [];
            const ccInputs = accordion.querySelectorAll('input[data-field="parameter_cc_out"]');
            ccInputs.forEach(input => {
                const ccIndex = parseInt(input.dataset.ccIndex);
                config.parameter_cc_out[trackIdx][ccIndex] = parseInt(input.value) || 0;
            });
        });

        await fetch('/save-config/midi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        toast.success('Settings saved');
    } catch (err) {
        console.error('Error saving MIDI config:', err);
        toast.error('Failed to save settings');
    }
}

// ===========================================
// DMX Config
// ===========================================

async function loadDmxConfig() {
    try {
        const res = await fetch('/get-config/dmx');
        const data = await res.json();
        const textarea = document.getElementById('dmx-textarea');

        // Format JSON for readability
        if (data.content) {
            try {
                const parsed = JSON.parse(data.content);
                textarea.value = JSON.stringify(parsed, null, 2);
            } catch {
                textarea.value = data.content;
            }
        } else {
            textarea.value = '';
        }
    } catch (err) {
        console.error('Error loading DMX config:', err);
        toast.error('Failed to load DMX settings');
    }
}

function initDmxAutoSave() {
    const textarea = document.getElementById('dmx-textarea');
    textarea.addEventListener('blur', saveDmxConfig);
}

async function saveDmxConfig() {
    try {
        const textarea = document.getElementById('dmx-textarea');
        const content = textarea.value;

        await fetch('/save-config/dmx', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        toast.success('Settings saved');
    } catch (err) {
        console.error('Error saving DMX config:', err);
        toast.error('Failed to save settings');
    }
}

// ===========================================
// Initialization
// ===========================================

function showError() {
    document.getElementById('device-error-container').hidden = false;
    document.getElementById('main-content').hidden = true;
}

function hideError() {
    document.getElementById('device-error-container').hidden = true;
    document.getElementById('main-content').hidden = false;
}

async function loadAllConfigs() {
    try {
        const res = await fetch('/get-config/general');
        if (!res.ok) {
            showError();
            return false;
        }
        generalConfig = await res.json();
        renderGeneralForm(generalConfig);

        // Load remaining configs
        await Promise.all([
            loadMidiConfig(),
            loadDmxConfig()
        ]);

        hideError();
        return true;
    } catch (err) {
        console.error('Failed to load configs:', err);
        showError();
        return false;
    }
}

async function pollForMount(retries = 60, delay = 2000) {
    for (let i = 0; i < retries; i++) {
        const success = await loadAllConfigs();
        if (success) return;
        await new Promise(r => setTimeout(r, delay));
    }
    console.warn('OP-Z not found after polling.');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDmxAutoSave();
    loadAllConfigs();
    pollForMount();
});
