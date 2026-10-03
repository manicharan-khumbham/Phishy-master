class PopupManager {
  constructor() {
    this.userEmailInput = document.getElementById('userEmail');
    this.ngrokUrlInput = document.getElementById('ngrokUrl');
    this.saveButton = document.getElementById('saveSettings');
    this.testButton = document.getElementById('testConnection');
    this.statusMessage = document.getElementById('statusMessage');
    
    this.init();
  }

  async init() {
    await this.loadSettings();
    this.setupEventListeners();
  }

  async loadSettings() {
    try {
      const result = await chrome.storage.local.get(['userEmail', 'ngrokUrl']);
      
      if (result.userEmail) {
        this.userEmailInput.value = result.userEmail;
      }
      
      if (result.ngrokUrl) {
        this.ngrokUrlInput.value = result.ngrokUrl;
      }
      
      if (result.userEmail && result.ngrokUrl) {
        this.showStatus('Settings loaded successfully', 'success');
      }
    } catch (error) {
      this.showStatus('Error loading settings: ' + error.message, 'error');
    }
  }

  setupEventListeners() {
    this.saveButton.addEventListener('click', () => this.saveSettings());
    this.testButton.addEventListener('click', () => this.testConnection());
    
    this.userEmailInput.addEventListener('input', () => this.validateForm());
    this.ngrokUrlInput.addEventListener('input', () => this.validateForm());
    
    this.userEmailInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.saveSettings();
    });
    
    this.ngrokUrlInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.saveSettings();
    });
  }

  validateForm() {
    const email = this.userEmailInput.value.trim();
    const url = this.ngrokUrlInput.value.trim();
    
    const emailValid = this.isValidEmail(email);
    const urlValid = this.isValidUrl(url);
    
    this.saveButton.disabled = !emailValid || !urlValid;
    this.testButton.disabled = !urlValid;
    
    if (email && !emailValid) {
      this.showStatus('Please enter a valid email address', 'warning');
    } else if (url && !urlValid) {
      this.showStatus('Please enter a valid URL (must start with https://)', 'warning');
    } else if (emailValid && urlValid) {
      this.showStatus('Ready to save settings', 'info');
    }
  }

  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  isValidUrl(url) {
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'https:' && (
        urlObj.hostname.includes('ngrok.io') || 
        urlObj.hostname.includes('ngrok-free.app') ||
        urlObj.hostname.includes('localhost') ||
        urlObj.hostname.includes('127.0.0.1')
      );
    } catch {
      return false;
    }
  }

  async saveSettings() {
    const email = this.userEmailInput.value.trim();
    const url = this.ngrokUrlInput.value.trim();
    
    if (!this.isValidEmail(email)) {
      this.showStatus('Please enter a valid email address', 'error');
      return;
    }
    
    if (!this.isValidUrl(url)) {
      this.showStatus('Please enter a valid HTTPS URL', 'error');
      return;
    }
    
    try {
      this.saveButton.disabled = true;
      this.saveButton.textContent = 'Saving...';
      
      await chrome.storage.local.set({
        userEmail: email,
        ngrokUrl: url.replace(/\/$/, '')
      });
      
      this.showStatus('Settings saved successfully! 🎉', 'success');
      
      setTimeout(() => {
        this.showStatus('Phishy is now active and monitoring your emails', 'info');
      }, 2000);
      
    } catch (error) {
      this.showStatus('Error saving settings: ' + error.message, 'error');
    } finally {
      this.saveButton.disabled = false;
      this.saveButton.textContent = 'Save Settings';
    }
  }

  async testConnection() {
    const url = this.ngrokUrlInput.value.trim();
    
    if (!this.isValidUrl(url)) {
      this.showStatus('Please enter a valid URL first', 'error');
      return;
    }
    
    try {
      this.testButton.disabled = true;
      this.testButton.textContent = 'Testing...';
      this.showStatus('Testing connection to backend...', 'info');
      
      const testUrl = url.replace(/\/$/, '') + '/health';
      const response = await fetch(testUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        this.showStatus(`✅ Connection successful! Backend is running (${data.status || 'healthy'})`, 'success');
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
    } catch (error) {
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        this.showStatus('❌ Cannot connect to backend. Make sure ngrok is running and the URL is correct.', 'error');
      } else {
        this.showStatus(`❌ Connection failed: ${error.message}`, 'error');
      }
    } finally {
      this.testButton.disabled = false;
      this.testButton.textContent = 'Test Connection';
    }
  }

  showStatus(message, type) {
    this.statusMessage.textContent = message;
    this.statusMessage.className = `status-message ${type}`;
    
    this.statusMessage.style.display = 'block';
    
    if (type === 'success' || type === 'info') {
      setTimeout(() => {
        this.statusMessage.style.display = 'none';
      }, 5000);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new PopupManager();
});