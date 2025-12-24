// ===========================================
// Reusable Tab Component
// ===========================================

/**
 * Tab component for creating horizontal pill-style tab interfaces.
 *
 * Usage:
 *   const tabs = createTabs({
 *     container: document.getElementById('tab-container'),
 *     tabs: [
 *       { id: 'general', label: 'General' },
 *       { id: 'midi', label: 'MIDI' },
 *       { id: 'dmx', label: 'DMX' }
 *     ],
 *     defaultTab: 'general',
 *     persistKey: 'configEditorTab',  // Optional: persist selection to localStorage
 *     onChange: (tabId) => { ... }    // Optional: callback when tab changes
 *   });
 *
 *   // Get current tab
 *   tabs.getActiveTab();  // 'general'
 *
 *   // Switch tab programmatically
 *   tabs.switchTab('midi');
 */

function createTabs(options) {
    const { container, tabs, defaultTab, persistKey, onChange } = options;

    if (!container || !tabs || tabs.length === 0) {
        console.error('Tabs: container and tabs array are required');
        return null;
    }

    let activeTab = defaultTab || tabs[0].id;

    // Restore persisted tab if available
    if (persistKey) {
        const saved = localStorage.getItem(persistKey);
        if (saved && tabs.some(t => t.id === saved)) {
            activeTab = saved;
        }
    }

    // Create tabs wrapper
    const tabsWrapper = document.createElement('div');
    tabsWrapper.className = 'tabs';

    // Create tab buttons
    tabs.forEach(tab => {
        const button = document.createElement('button');
        button.className = 'tab';
        button.dataset.tabId = tab.id;
        button.textContent = tab.label;

        if (tab.id === activeTab) {
            button.classList.add('active');
        }

        button.addEventListener('click', () => switchTab(tab.id));
        tabsWrapper.appendChild(button);
    });

    // Insert tabs into container
    container.appendChild(tabsWrapper);

    /**
     * Switch to a specific tab
     */
    function switchTab(tabId) {
        if (!tabs.some(t => t.id === tabId)) {
            console.warn(`Tabs: unknown tab id '${tabId}'`);
            return;
        }

        activeTab = tabId;

        // Update button states
        tabsWrapper.querySelectorAll('.tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tabId === tabId);
        });

        // Persist selection
        if (persistKey) {
            localStorage.setItem(persistKey, tabId);
        }

        // Call onChange callback
        if (onChange) {
            onChange(tabId);
        }
    }

    /**
     * Get the currently active tab id
     */
    function getActiveTab() {
        return activeTab;
    }

    // Initial onChange call to set up content
    if (onChange) {
        onChange(activeTab);
    }

    return {
        switchTab,
        getActiveTab
    };
}
