/**
 * Phishy AI Gmail Extension - Popup Script
 * Manages extension settings and status
 */

class PhishyPopup {
    constructor() {
        this.config = {};
        this.init();
    }
    
    async init() {
        await this.loadConfig();
        this.setupEventListeners();
        this.updateUI();
        this.checkConnection();
    }
    
    async loadConfig() {
        try {
            this.config = await chrome.storage.sync.get([
                'phishyApiUrl',
                'phishyUserEmail',
                'phishyPluginId',
                'phishyEnabled',
                'phishyStats'
            ]);
        } catch (error) {
            console.error('Error loading config:', error);
        }
    }
    
    setupEventListeners() {
        // Test connection button
        document.getElementById('testConnection').addEventListener('click', () => {
            this.testConnection();
        });
        
        // Save configuration button
        document.getElementById('saveConfig').addEventListener('click', () => {
            this.saveConfiguration();
        });
        
        // Clear configuration button
        document.getElementById('clearConfig').addEventListener('click', () => {
            this.clearConfiguration();
        });
        
        // Open dashboard button
        document.getElementById('openDashboard').addEventListener('click', () => {
            this.openDashboard();
        });
        
        // Enable/disable toggle
        document.getElementById('enabledToggle').addEventListener('change', (e) => {
            this.toggleEnabled(e.target.checked);
        });
        
        // Auto-save on input changes
        document.getElementById('apiUrl').addEventListener('blur', () => {
            this.autoSave();
        });
        
        document.getElementById('userEmailInput').addEventListener('blur', () => {
            this.autoSave();
        });
    }
    
    updateUI() {
        // Update form fields
        document.getElementById('apiUrl').value = this.config.phishyApiUrl || '';
        document.getElementById('userEmailInput').value = this.config.phishyUserEmail || '';
        document.getElementById('enabledToggle').checked = this.config.phishyEnabled !== false;
        
        // Update status display
        document.getElementById('serverUrl').textContent = 
            this.config.phishyApiUrl || 'Not configured';
        document.getElementById('userEmail').textContent = 
            this.config.phishyUserEmail || 'Not configured';
        
        // Show/hide buttons based on configuration
        const isConfigured = this.config.phishyApiUrl && this.config.phishyUserEmail;
        document.getElementById('openDashboard').style.display = isConfigured ? 'block' : 'none';
        document.getElementById('clearConfig').style.display = isConfigured ? 'block' : 'none';
        
        // Update statistics if available
        if (this.config.phishyStats) {
            this.updateStats(this.config.phishyStats);
        }
    }
    
    updateStats(stats) {
        document.getElementById('flaggedCount').textContent = stats.flaggedCount || 0;
        document.getElementById('threatLevel').textContent = stats.threatLevel || 'Low';
        document.getElementById('statsGrid').style.display = 'grid';
    }
    
    async checkConnection() {
        if (!this.config.phishyApiUrl) {
            this.updateConnectionStatus('disconnected', 'Not configured');
            return;
        }
        
        this.updateConnectionStatus('checking', 'Checking...');
        
        try {
            const response = await fetch(`${this.config.phishyApiUrl}/email-flagging/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            
            if (response.ok) {
                const data = await response.json();
                this.updateConnectionStatus('connected', 'Connected');
                
                // Update stats if available
                if (data.connected_plugins !== undefined) {
                    const stats = {
                        flaggedCount: data.connected_plugins,
                        threatLevel: data.tunnel_active ? 'Active' : 'Local'
                    };
                    this.updateStats(stats);
                    await chrome.storage.sync.set({ phishyStats: stats });
                }
            } else {
                this.updateConnectionStatus('warning', 'Server error');
            }
        } catch (error) {
            console.error('Connection check failed:', error);
            this.updateConnectionStatus('disconnected', 'Connection failed');
        }
    }
    
    updateConnectionStatus(status, message) {
        const statusElement = document.getElementById('connectionStatus');
        const indicator = statusElement.querySelector('.status-indicator');
        
        // Remove all status classes
        indicator.classList.remove('status-connected', 'status-disconnected', 'status-warning');
        
        // Add appropriate class
        switch (status) {
            case 'connected':
                indicator.classList.add('status-connected');
                break;
            case 'warning':
                indicator.classList.add('status-warning');
                break;
            case 'checking':
                indicator.classList.add('status-warning');
                break;
            default:
                indicator.classList.add('status-disconnected');
        }
        
        // Update text
        statusElement.innerHTML = `
            <span class="status-indicator ${indicator.className}"></span>
            ${message}
        `;
    }
    
    async testConnection() {
        const apiUrl = document.getElementById('apiUrl').value.trim();
        
        if (!apiUrl) {
            this.showError('Please enter a server URL');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch(`${apiUrl}/email-flagging/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(10000)
            });
            
            if (response.ok) {
                const data = await response.json();
                this.showSuccess(`Connected successfully! Version: ${data.version || 'Unknown'}`);
                this.updateConnectionStatus('connected', 'Connected');
            } else {
                throw new Error(`Server returned ${response.status}`);
            }
        } catch (error) {
            console.error('Test connection failed:', error);
            this.showError('Connection failed. Check URL and server status.');
            this.updateConnectionStatus('disconnected', 'Connection failed');
        } finally {
            this.showLoading(false);
        }
    }
    
    async saveConfiguration() {
        const apiUrl = document.getElementById('apiUrl').value.trim();
        const userEmail = document.getElementById('userEmailInput').value.trim();
        const enabled = document.getElementById('enabledToggle').checked;
        
        if (!apiUrl || !userEmail) {
            this.showError('Please fill in all fields');
            return;
        }
        
        // Validate URL format
        try {
            new URL(apiUrl);
        } catch {
            this.showError('Please enter a valid URL');
            return;
        }
        
        // Validate email format
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(userEmail)) {
            this.showError('Please enter a valid email address');
            return;
        }
        
        this.showLoading(true);
        
        try {
            // Test connection first
            const response = await fetch(`${apiUrl}/email-flagging/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            
            if (!response.ok) {
                throw new Error('Server is not accessible');
            }
            
            // Save configuration
            const pluginId = this.config.phishyPluginId || this.generatePluginId();
            
            await chrome.storage.sync.set({
                phishyApiUrl: apiUrl,
                phishyUserEmail: userEmail,
                phishyPluginId: pluginId,
                phishyEnabled: enabled
            });
            
            // Update local config
            this.config = {
                ...this.config,
                phishyApiUrl: apiUrl,
                phishyUserEmail: userEmail,
                phishyPluginId: pluginId,
                phishyEnabled: enabled
            };
            
            this.updateUI();
            this.showSuccess('Configuration saved successfully!');
            
            // Notify content script about configuration update
            this.notifyContentScript();
            
        } catch (error) {
            console.error('Save configuration failed:', error);
            this.showError('Failed to save configuration. Check server connection.');
        } finally {
            this.showLoading(false);
        }
    }
    
    async clearConfiguration() {
        if (!confirm('Are you sure you want to clear all configuration? This will disable email protection.')) {
            return;
        }
        
        try {
            await chrome.storage.sync.clear();
            this.config = {};
            this.updateUI();
            this.updateConnectionStatus('disconnected', 'Configuration cleared');
            this.showSuccess('Configuration cleared successfully');
            
            // Notify content script
            this.notifyContentScript();
            
        } catch (error) {
            console.error('Clear configuration failed:', error);
            this.showError('Failed to clear configuration');
        }
    }
    
    async toggleEnabled(enabled) {
        try {
            await chrome.storage.sync.set({ phishyEnabled: enabled });
            this.config.phishyEnabled = enabled;
            
            this.showSuccess(enabled ? 'Protection enabled' : 'Protection disabled');
            
            // Notify content script
            this.notifyContentScript();
            
        } catch (error) {
            console.error('Toggle enabled failed:', error);
            this.showError('Failed to update settings');
        }
    }
    
    async autoSave() {
        // Auto-save configuration when user moves away from input fields
        if (this.config.phishyApiUrl || this.config.phishyUserEmail) {
            const apiUrl = document.getElementById('apiUrl').value.trim();
            const userEmail = document.getElementById('userEmailInput').value.trim();
            
            if (apiUrl && userEmail) {
                await chrome.storage.sync.set({
                    phishyApiUrl: apiUrl,
                    phishyUserEmail: userEmail
                });
                
                this.config.phishyApiUrl = apiUrl;
                this.config.phishyUserEmail = userEmail;
                this.updateUI();
            }
        }
    }
    
    async notifyContentScript() {
        // Notify all Gmail tabs about configuration changes
        try {
            const tabs = await chrome.tabs.query({ url: "https://mail.google.com/*" });
            
            for (const tab of tabs) {
                chrome.tabs.sendMessage(tab.id, {
                    type: 'configUpdated',
                    config: this.config
                }).catch(() => {
                    // Ignore errors - tab might not have content script loaded
                });
            }
        } catch (error) {
            console.debug('Failed to notify content script:', error);
        }
    }
    
    openDashboard() {
        if (this.config.phishyApiUrl) {
            chrome.tabs.create({ url: this.config.phishyApiUrl });
        }
    }
    
    generatePluginId() {
        return `gmail_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    showError(message) {
        const errorElement = document.getElementById('errorMessage');
        const successElement = document.getElementById('successMessage');
        
        successElement.style.display = 'none';
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
    
    showSuccess(message) {
        const errorElement = document.getElementById('errorMessage');
        const successElement = document.getElementById('successMessage');
        
        errorElement.style.display = 'none';
        successElement.textContent = message;
        successElement.style.display = 'block';
        
        setTimeout(() => {
            successElement.style.display = 'none';
        }, 3000);
    }
    
    showLoading(show) {
        const loadingElement = document.getElementById('loading');
        const configForm = document.getElementById('configForm');
        
        loadingElement.style.display = show ? 'block' : 'none';
        configForm.style.opacity = show ? '0.5' : '1';
        
        // Disable buttons while loading
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(btn => {
            btn.disabled = show;
        });
    }
}

// Initialize popup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PhishyPopup();
});

// Listen for storage changes to update UI
chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'sync') {
        // Reload and update UI when storage changes
        location.reload();
    }
});