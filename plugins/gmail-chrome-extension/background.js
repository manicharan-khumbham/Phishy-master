/**
 * Phishy AI Gmail Extension - Background Service Worker
 * Handles extension lifecycle and background tasks
 */

class PhishyBackground {
    constructor() {
        this.config = {};
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }
    
    async init() {
        console.log('🛡️ Phishy AI Background Service Worker initialized');
        
        // Load configuration
        await this.loadConfig();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Connect WebSocket if configured
        if (this.config.phishyApiUrl && this.config.phishyEnabled !== false) {
            this.connectWebSocket();
        }
        
        // Start periodic health checks
        this.startHealthChecks();
    }
    
    async loadConfig() {
        try {
            this.config = await chrome.storage.sync.get([
                'phishyApiUrl',
                'phishyUserEmail',
                'phishyPluginId',
                'phishyEnabled'
            ]);
        } catch (error) {
            console.error('Error loading config:', error);
        }
    }
    
    setupEventListeners() {
        // Listen for storage changes
        chrome.storage.onChanged.addListener((changes, namespace) => {
            if (namespace === 'sync') {
                this.handleConfigChange(changes);
            }
        });
        
        // Listen for extension install/startup
        chrome.runtime.onStartup.addListener(() => {
            console.log('Extension startup');
            this.init();
        });
        
        chrome.runtime.onInstalled.addListener((details) => {
            console.log('Extension installed/updated:', details.reason);
            this.handleInstall(details);
        });
        
        // Listen for messages from content scripts
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // Keep message channel open for async response
        });
        
        // Listen for tab updates (Gmail navigation)
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            if (changeInfo.status === 'complete' && 
                tab.url && tab.url.includes('mail.google.com')) {
                this.handleGmailTabUpdate(tabId, tab);
            }
        });
    }
    
    async handleConfigChange(changes) {
        console.log('Configuration changed:', changes);
        
        // Reload configuration
        await this.loadConfig();
        
        // Reconnect WebSocket if URL changed
        if (changes.phishyApiUrl || changes.phishyEnabled) {
            this.disconnectWebSocket();
            
            if (this.config.phishyApiUrl && this.config.phishyEnabled !== false) {
                setTimeout(() => this.connectWebSocket(), 1000);
            }
        }
        
        // Notify all Gmail tabs about config changes
        this.notifyGmailTabs({
            type: 'configUpdated',
            config: this.config
        });
    }
    
    async handleInstall(details) {
        if (details.reason === 'install') {
            // First time installation
            await this.showWelcomeNotification();
            await this.openSetupPage();
        } else if (details.reason === 'update') {
            // Extension updated
            await this.showUpdateNotification();
        }
    }
    
    async handleMessage(message, sender, sendResponse) {
        try {
            switch (message.type) {
                case 'getConfig':
                    sendResponse({ config: this.config });
                    break;
                    
                case 'testConnection':
                    const result = await this.testConnection(message.url);
                    sendResponse(result);
                    break;
                    
                case 'flagEmail':
                    const flagResult = await this.flagEmail(message.emailData);
                    sendResponse(flagResult);
                    break;
                    
                case 'getStats':
                    const stats = await this.getStats();
                    sendResponse(stats);
                    break;
                    
                default:
                    console.log('Unknown message type:', message.type);
                    sendResponse({ error: 'Unknown message type' });
            }
        } catch (error) {
            console.error('Error handling message:', error);
            sendResponse({ error: error.message });
        }
    }
    
    async handleGmailTabUpdate(tabId, tab) {
        // Inject content script if needed (for dynamic loading)
        try {
            await chrome.tabs.sendMessage(tabId, { type: 'ping' });
        } catch {
            // Content script not loaded, inject it
            try {
                await chrome.scripting.executeScript({
                    target: { tabId },
                    files: ['phishy-gmail.js']
                });
                
                await chrome.scripting.insertCSS({
                    target: { tabId },
                    files: ['phishy-styles.css']
                });
            } catch (error) {
                console.debug('Failed to inject content script:', error);
            }
        }
    }
    
    connectWebSocket() {
        if (!this.config.phishyApiUrl || this.websocket) return;
        
        try {
            const wsUrl = this.config.phishyApiUrl
                .replace('https://', 'wss://')
                .replace('http://', 'ws://');
            
            const pluginId = this.config.phishyPluginId || 'background_service';
            
            this.websocket = new WebSocket(
                `${wsUrl}/email-flagging/ws/${pluginId}?plugin_type=gmail`
            );
            
            this.websocket.onopen = () => {
                console.log('🔗 Connected to Phishy AI WebSocket');
                this.reconnectAttempts = 0;
                this.showNotification('Connected to Phishy AI', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };
            
            this.websocket.onclose = (event) => {
                console.log('📡 Disconnected from Phishy AI WebSocket');
                this.websocket = null;
                
                if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                    setTimeout(() => this.connectWebSocket(), delay);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.showNotification('Connection error', 'error');
            };
            
        } catch (error) {
            console.error('Error connecting WebSocket:', error);
        }
    }
    
    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
    
    handleWebSocketMessage(message) {
        console.log('WebSocket message:', message);
        
        switch (message.type) {
            case 'connected':
                this.showNotification('Phishy AI Protection Active', 'success');
                break;
                
            case 'tunnel_updated':
                this.handleTunnelUpdate(message.data);
                break;
                
            case 'email_flagged':
                this.handleEmailFlagged(message.data);
                break;
                
            case 'threat_alert':
                this.handleThreatAlert(message.data);
                break;
                
            default:
                console.log('Unknown WebSocket message type:', message.type);
        }
    }
    
    async handleTunnelUpdate(data) {
        const newUrl = data.new_tunnel_url;
        console.log('Tunnel URL updated:', newUrl);
        
        // Update stored configuration
        await chrome.storage.sync.set({ phishyApiUrl: newUrl });
        this.config.phishyApiUrl = newUrl;
        
        // Show notification
        this.showNotification('Server URL updated automatically', 'info');
        
        // Notify Gmail tabs
        this.notifyGmailTabs({
            type: 'tunnelUpdated',
            newUrl: newUrl
        });
    }
    
    handleEmailFlagged(data) {
        const { flag_request, analysis } = data;
        
        // Show notification for high-threat emails
        if (analysis.threat_level === 'high' || analysis.threat_level === 'critical') {
            this.showNotification(
                `High threat email detected: ${flag_request.subject}`,
                'warning'
            );
        }
        
        // Update badge
        this.updateBadge();
    }
    
    handleThreatAlert(data) {
        this.showNotification(
            `Security Alert: ${data.message}`,
            'warning'
        );
    }
    
    async testConnection(url) {
        try {
            const response = await fetch(`${url}/email-flagging/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            
            if (response.ok) {
                const data = await response.json();
                return { success: true, data };
            } else {
                return { success: false, error: `HTTP ${response.status}` };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async flagEmail(emailData) {
        if (!this.config.phishyApiUrl) {
            return { success: false, error: 'Not configured' };
        }
        
        try {
            const response = await fetch(`${this.config.phishyApiUrl}/email-flagging/flag`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(emailData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.updateBadge();
                return { success: true, data: result };
            } else {
                return { success: false, error: `HTTP ${response.status}` };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async getStats() {
        if (!this.config.phishyApiUrl) {
            return { flaggedCount: 0, threatLevel: 'Unknown' };
        }
        
        try {
            const response = await fetch(`${this.config.phishyApiUrl}/email-flagging/stats`);
            
            if (response.ok) {
                const data = await response.json();
                return {
                    flaggedCount: data.stats?.total_flags || 0,
                    threatLevel: this.calculateOverallThreatLevel(data.stats)
                };
            }
        } catch (error) {
            console.error('Error getting stats:', error);
        }
        
        return { flaggedCount: 0, threatLevel: 'Unknown' };
    }
    
    calculateOverallThreatLevel(stats) {
        if (!stats || !stats.threat_levels) return 'Low';
        
        const { critical = 0, high = 0, medium = 0, low = 0 } = stats.threat_levels;
        const total = critical + high + medium + low;
        
        if (total === 0) return 'Low';
        
        const criticalPercent = (critical / total) * 100;
        const highPercent = (high / total) * 100;
        
        if (criticalPercent > 10) return 'Critical';
        if (highPercent > 20 || criticalPercent > 0) return 'High';
        if (medium > low) return 'Medium';
        
        return 'Low';
    }
    
    async updateBadge() {
        try {
            const stats = await this.getStats();
            
            if (stats.flaggedCount > 0) {
                await chrome.action.setBadgeText({
                    text: stats.flaggedCount.toString()
                });
                
                // Set badge color based on threat level
                const colors = {
                    'Low': '#28a745',
                    'Medium': '#ffc107',
                    'High': '#fd7e14',
                    'Critical': '#dc3545'
                };
                
                await chrome.action.setBadgeBackgroundColor({
                    color: colors[stats.threatLevel] || '#6c757d'
                });
            } else {
                await chrome.action.setBadgeText({ text: '' });
            }
        } catch (error) {
            console.error('Error updating badge:', error);
        }
    }
    
    startHealthChecks() {
        // Check health every 5 minutes
        setInterval(async () => {
            if (this.config.phishyApiUrl) {
                const result = await this.testConnection(this.config.phishyApiUrl);
                
                if (!result.success && this.websocket) {
                    console.log('Health check failed, reconnecting...');
                    this.disconnectWebSocket();
                    setTimeout(() => this.connectWebSocket(), 5000);
                }
            }
        }, 5 * 60 * 1000);
    }
    
    async notifyGmailTabs(message) {
        try {
            const tabs = await chrome.tabs.query({ url: "https://mail.google.com/*" });
            
            for (const tab of tabs) {
                chrome.tabs.sendMessage(tab.id, message).catch(() => {
                    // Ignore errors - tab might not have content script loaded
                });
            }
        } catch (error) {
            console.debug('Failed to notify Gmail tabs:', error);
        }
    }
    
    async showNotification(message, type = 'info') {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        
        try {
            await chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: 'Phishy AI',
                message: `${icons[type]} ${message}`
            });
        } catch (error) {
            console.debug('Notification failed:', error);
        }
    }
    
    async showWelcomeNotification() {
        await this.showNotification(
            'Welcome to Phishy AI! Click the extension icon to configure your email protection.',
            'info'
        );
    }
    
    async showUpdateNotification() {
        await this.showNotification(
            'Phishy AI has been updated with new security features!',
            'success'
        );
    }
    
    async openSetupPage() {
        // Open the extension popup or a setup page
        try {
            await chrome.tabs.create({
                url: chrome.runtime.getURL('popup.html')
            });
        } catch (error) {
            console.debug('Failed to open setup page:', error);
        }
    }
}

// Initialize background service
const phishyBackground = new PhishyBackground();