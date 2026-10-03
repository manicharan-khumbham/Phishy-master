/**
 * Phishy AI Gmail Extension - Content Script
 * Adds email flagging capabilities to Gmail interface
 */

class PhishyGmail {
    constructor() {
        this.apiBaseUrl = null;
        this.websocket = null;
        this.userEmail = null;
        this.pluginId = null;
        this.isActive = false;
        
        this.init();
    }
    
    async init() {
        console.log('🛡️ Phishy AI Gmail Extension initializing...');
        
        // Load configuration
        await this.loadConfig();
        
        // Connect WebSocket if configured
        if (this.apiBaseUrl) {
            this.connectWebSocket();
        }
        
        // Monitor for new emails (no toolbar buttons)
        this.monitorNewEmails();
        
        console.log('✅ Phishy AI Gmail Extension initialized');
        
        // Add manual trigger for testing
        window.phishyAddFlag = () => this.forceAddFlagButton();
    }
    
    async loadConfig() {
        try {
            const result = await chrome.storage.sync.get([
                'phishyApiUrl', 
                'phishyUserEmail', 
                'phishyPluginId',
                'phishyEnabled'
            ]);
            
            this.apiBaseUrl = result.phishyApiUrl;
            this.userEmail = result.phishyUserEmail;
            this.pluginId = result.phishyPluginId || this.generatePluginId();
            this.isActive = result.phishyEnabled !== false; // Default to true
            
            if (!this.pluginId) {
                this.pluginId = this.generatePluginId();
                await chrome.storage.sync.set({ phishyPluginId: this.pluginId });
            }
            
        } catch (error) {
            console.error('Error loading Phishy config:', error);
        }
    }
    
    generatePluginId() {
        return `gmail_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    // No more toolbar buttons - flag option is now in warnings only!
    
    monitorNewEmails() {
        // IMMEDIATE email scanning - no delays!
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node.querySelector) {
                        // Prevent duplicate processing
                        if (node.hasAttribute('data-phishy-processed')) return;
                        
                        const emailRows = node.querySelectorAll('[jsaction*="click"]');
                        emailRows.forEach(row => this.scanEmailRow(row));
                        
                        // IMMEDIATE scan for opened email content
                        const emailContents = node.querySelectorAll('.ii.gt, .a3s.aiL, .adn.ads, .gs .a3s, .adP, .ii.gt .a3s');
                        emailContents.forEach(emailContent => {
                            if (emailContent && !emailContent.hasAttribute('data-phishy-scanned')) {
                                console.log('🚨 IMMEDIATE SCAN triggered for email content!');
                                // Scan immediately - no delays
                                this.scanOpenedEmailImmediate(emailContent);
                            }
                        });
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // DISABLED automatic scanning to prevent loops
        // setInterval(() => {
        //     this.scanVisibleEmailsImmediate();
        // }, 2000);
        
        // Scan immediately on load
        this.scanVisibleEmailsImmediate();
        
        // Listen for Gmail navigation/email opening
        this.setupGmailNavigationListener();
    }
    
    scanEmailRow(emailRow) {
        // Basic heuristic scanning for suspicious indicators
        try {
            const senderElement = emailRow.querySelector('[email]');
            const subjectElement = emailRow.querySelector('[data-thread-id]');
            
            if (senderElement && subjectElement) {
                const sender = senderElement.getAttribute('email') || senderElement.textContent;
                const subject = subjectElement.textContent;
                
                const suspiciousScore = this.calculateSuspiciousScore(sender, subject);
                
                if (suspiciousScore > 0.7) {
                    this.highlightSuspiciousEmail(emailRow, suspiciousScore);
                }
            }
        } catch (error) {
            console.debug('Error scanning email row:', error);
        }
    }
    
    calculateSuspiciousScore(sender, subject) {
        let score = 0;
        
        // Check for suspicious keywords
        const suspiciousWords = [
            'urgent', 'verify', 'suspended', 'click here', 'act now',
            'limited time', 'confirm', 'update payment', 'security alert'
        ];
        
        const text = (sender + ' ' + subject).toLowerCase();
        suspiciousWords.forEach(word => {
            if (text.includes(word)) score += 0.2;
        });
        
        // Check for suspicious sender patterns
        if (sender.includes('noreply') && subject.toLowerCase().includes('verify')) {
            score += 0.3;
        }
        
        return Math.min(score, 1.0);
    }
    
    highlightSuspiciousEmail(emailRow, score) {
        if (emailRow.querySelector('.phishy-warning')) return; // Already highlighted
        
        const warning = document.createElement('div');
        warning.className = 'phishy-warning';
        warning.innerHTML = `
            <span class="phishy-warning-icon">⚠️</span>
            <span class="phishy-warning-text">Potentially suspicious (${Math.round(score * 100)}%)</span>
        `;
        
        emailRow.style.position = 'relative';
        emailRow.appendChild(warning);
    }
    
    scanVisibleEmails() {
        // Regular scanning method (kept for compatibility)
        this.scanVisibleEmailsImmediate();
    }
    
    scanVisibleEmailsImmediate() {
        // PREVENT LOOPS - only scan if not recently scanned
        const now = Date.now();
        const lastScanKey = 'phishy_last_scan';
        const lastScan = parseInt(localStorage.getItem(lastScanKey) || '0');
        
        // Only scan if more than 5 seconds since last scan
        if (now - lastScan < 5000) {
            console.log('⏸️ Skipping scan - too recent (preventing loops)');
            return;
        }
        
        localStorage.setItem(lastScanKey, now.toString());
        console.log('🔍 Starting visible email scan...');
        
        const emailSelectors = [
            '.ii.gt',           // Gmail message body
            '.a3s.aiL',         // Gmail email content  
            '.adn.ads',         // Gmail conversation
            '.gs .a3s',         // Gmail thread content
            '[role="listitem"] .a3s', // Gmail inbox messages
            '.Ar.Au .adn',      // Gmail expanded messages
            '.adP',             // Gmail email container
            '.ii.gt .a3s',      // Nested content
            '.h7 .a3s'          // Thread messages
        ];
        
        const emailContents = document.querySelectorAll(emailSelectors.join(', '));
        let scannedCount = 0;
        
        emailContents.forEach((content) => {
            if (!content.hasAttribute('data-phishy-scanned') && content.offsetParent !== null) {
                console.log('⚡ ML scan triggered for email content');
                this.scanOpenedEmailImmediate(content);
                scannedCount++;
            }
        });
        
        console.log(`📊 Scan complete - processed ${scannedCount} new emails`);
    }
    
    setupGmailNavigationListener() {
        // REDUCED navigation listeners to prevent loops
        let lastNavigation = 0;
        
        // Listen for Gmail navigation changes (hash changes)
        window.addEventListener('hashchange', () => {
            const now = Date.now();
            if (now - lastNavigation > 2000) { // 2 second cooldown
                console.log('🔄 Gmail navigation detected');
                lastNavigation = now;
                setTimeout(() => this.scanVisibleEmailsImmediate(), 500);
            }
        });
        
        // REMOVED history listeners that cause loops
        
        // Listen for clicks that might open emails (with cooldown)
        let lastClick = 0;
        document.addEventListener('click', (e) => {
            const now = Date.now();
            if (now - lastClick < 1000) return; // 1 second cooldown
            
            const target = e.target.closest('[role="listitem"], .zA, .yW, tr[jsaction*="click"]');
            if (target) {
                console.log('📧 Email click detected');
                lastClick = now;
                setTimeout(() => this.scanVisibleEmailsImmediate(), 1000);
            }
        });
    }
    
    async scanOpenedEmail(emailContent) {
        if (!this.apiBaseUrl || !this.isActive) {
            console.log('⚠️ Skipping scan - API not configured or plugin disabled');
            return;
        }
        
        try {
            // Mark as scanned to prevent duplicate scans
            emailContent.setAttribute('data-phishy-scanned', 'true');
            
            console.log('📧 Starting email scan...');
            
            // Extract email data for analysis
            const emailData = this.extractEmailFromContent(emailContent);
            if (!emailData) {
                console.log('❌ Could not extract email data');
                return;
            }
            
            console.log('📊 Extracted email data:', {
                sender: emailData.sender,
                subject: emailData.subject,
                bodyLength: emailData.body.length,
                urlCount: emailData.urls.length
            });
            
            // Show loading indicator
            this.showScanningIndicator(emailContent);
            
            // Perform AI analysis
            const analysisResult = await this.performAIAnalysis(emailData);
            
            console.log('🔍 Analysis result:', {
                is_phishing: analysisResult.is_phishing,
                risk_level: analysisResult.risk_level,
                confidence: analysisResult.confidence_score
            });
            
            // Remove loading indicator
            this.hideScanningIndicator(emailContent);
            
            // Show warning if suspicious - LOWER the threshold for testing
            if (analysisResult.is_phishing || analysisResult.risk_level === 'HIGH' || analysisResult.risk_level === 'CRITICAL') {
                console.log('🚨 Showing HIGH risk warning');
                this.showSuspiciousEmailWarning(emailContent, analysisResult);
            } else if (analysisResult.risk_level === 'MEDIUM' || analysisResult.confidence_score > 30) {
                console.log('⚠️ Showing MEDIUM risk warning');
                this.showCautionWarning(emailContent, analysisResult);
            } else {
                console.log('✅ Email appears safe');
                // Show a brief "scanned" indicator for user feedback
                this.showSafeEmailIndicator(emailContent);
            }
            
        } catch (error) {
            console.error('❌ Error scanning email:', error);
            emailContent.removeAttribute('data-phishy-scanned');
            this.showErrorIndicator(emailContent, error);
        }
    }
    
    async scanOpenedEmailImmediate(emailContent) {
        // INSTANT scanning using YOUR ML MODEL - with proper duplicate prevention
        if (!this.isActive || !this.apiBaseUrl) {
            console.log('⚠️ Plugin disabled or API not configured');
            return;
        }
        
        try {
            // Create unique identifier for this email content
            const emailId = this.getEmailUniqueId(emailContent);
            
            // Check if this specific email is already being processed or was processed
            if (this.processingEmails?.has(emailId)) {
                console.log('📧 Email already being processed, skipping...');
                return;
            }
            
            // Initialize processing set if not exists
            if (!this.processingEmails) {
                this.processingEmails = new Set();
            }
            
            // Mark as being processed
            this.processingEmails.add(emailId);
            
            console.log('⚡ INSTANT ML SCAN starting for email:', emailId);
            
            // Extract email data quickly
            const emailData = this.extractEmailFromContent(emailContent);
            if (!emailData) {
                console.log('❌ Could not extract email data for ML scan');
                this.processingEmails.delete(emailId);
                return;
            }
            
            console.log('📊 ML scan data:', {
                sender: emailData.sender,
                subject: emailData.subject,
                bodyLength: emailData.body.length
            });
            
            // Use YOUR ML MODEL for analysis - FAST API call
            const analysisResult = await this.performMLAnalysisInstant(emailData);
            
            console.log('🤖 ML analysis result:', {
                is_phishing: analysisResult.is_phishing,
                risk_level: analysisResult.risk_level,
                confidence: analysisResult.confidence_score
            });
            
            // Remove from processing set
            this.processingEmails.delete(emailId);
            
            // Show warnings based on ML MODEL results
            if (analysisResult.is_phishing || analysisResult.risk_level === 'HIGH' || analysisResult.risk_level === 'CRITICAL') {
                console.log('🚨 ML MODEL DETECTED PHISHING - SHOWING WARNING!');
                this.showSuspiciousEmailWarning(emailContent, analysisResult, emailId);
            } else if (analysisResult.risk_level === 'MEDIUM') {
                console.log('⚠️ ML MODEL DETECTED MEDIUM RISK!');
                this.showCautionWarning(emailContent, analysisResult, emailId);
            } else {
                console.log('✅ ML MODEL: Email appears safe');
                this.showSafeEmailIndicator(emailContent);
            }
            
        } catch (error) {
            console.error('❌ Error in ML scan:', error);
            // Remove from processing set on error
            if (this.processingEmails) {
                const emailId = this.getEmailUniqueId(emailContent);
                this.processingEmails.delete(emailId);
            }
            
            // Fallback to basic analysis if ML fails
            console.log('🔄 Falling back to basic analysis...');
            const basicResult = this.performInstantAnalysis(emailData || {});
            if (basicResult.is_phishing) {
                this.showSuspiciousEmailWarning(emailContent, basicResult, this.getEmailUniqueId(emailContent));
            }
        }
    }
    
    getEmailUniqueId(emailContent) {
        // Create a unique ID for this email content to prevent duplicates
        const container = emailContent.closest('[data-message-id]') || emailContent.closest('.adn');
        const messageId = container?.getAttribute('data-message-id');
        
        if (messageId) {
            return messageId;
        }
        
        // Fallback: use content hash
        const text = (emailContent.textContent || '').substring(0, 200);
        return 'email_' + this.simpleHash(text);
    }
    
    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash).toString(36);
    }
    
    async performMLAnalysisInstant(emailData) {
        // Use YOUR ML MODEL via API - with timeout for speed
        try {
            const response = await fetch(`${this.apiBaseUrl}/detector/analyze-email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email_content: `Subject: ${emailData.subject}\n\nFrom: ${emailData.sender}\n\n${emailData.body}`,
                    include_detailed_analysis: true,
                    cache_results: true
                }),
                signal: AbortSignal.timeout(3000) // 3 second timeout for instant results
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('🤖 ML MODEL RESPONSE:', result);
                return result;
            } else {
                console.warn('ML API returned error, using fallback');
                throw new Error(`API returned ${response.status}`);
            }
            
        } catch (error) {
            console.warn('ML API failed, using fallback analysis:', error.message);
            // Fallback to instant rules
            return this.performInstantAnalysis(emailData);
        }
    }
    
    removeExistingWarnings(emailContent) {
        // Remove any existing Phishy warnings in the email container
        const container = emailContent.closest('.adn, .ii, [role="listitem"]') || emailContent.parentNode;
        if (container) {
            const existingWarnings = container.querySelectorAll('.phishy-email-warning, .phishy-safe-indicator, .phishy-error-indicator');
            existingWarnings.forEach(warning => {
                console.log('🗑️ Removing existing warning');
                warning.remove();
            });
        }
    }
    
    performInstantAnalysis(emailData) {
        // SUPER AGGRESSIVE instant analysis for immediate warnings
        let riskScore = 0;
        let riskFactors = [];
        
        console.log('⚡ Performing INSTANT analysis...');
        
        const text = (emailData.subject + ' ' + emailData.body).toLowerCase();
        
        // INSTANT phishing detection - very aggressive
        const highRiskWords = [
            'urgent', 'verify', 'suspended', 'expires', 'click here', 'act now',
            'phishy', 'simulation', 'training', 'security alert', 'account locked',
            'confirm', 'update', 'action required', 'limited time', 'immediate'
        ];
        
        const foundHighRisk = highRiskWords.filter(word => text.includes(word));
        if (foundHighRisk.length > 0) {
            riskScore += foundHighRisk.length * 25; // 25 points per word
            riskFactors.push(`High-risk keywords detected: ${foundHighRisk.join(', ')}`);
            console.log('🚨 HIGH-RISK WORDS FOUND:', foundHighRisk);
        }
        
        // URL analysis
        if (emailData.urls.length > 0) {
            riskScore += emailData.urls.length * 15;
            riskFactors.push(`${emailData.urls.length} URLs detected`);
            console.log('🔗 URLs found:', emailData.urls.length);
            
            // Check for tracking/suspicious URLs
            const suspiciousUrls = emailData.urls.filter(url => 
                url.includes('track') || url.includes('click') || url.includes('redirect') ||
                url.includes('bit.ly') || url.includes('tinyurl') || url.includes('t.co')
            );
            
            if (suspiciousUrls.length > 0) {
                riskScore += 40;
                riskFactors.push('Suspicious tracking/shortened URLs');
                console.log('🚨 SUSPICIOUS URLs:', suspiciousUrls);
            }
        }
        
        // Personal info requests
        const personalWords = ['password', 'login', 'credentials', 'ssn', 'social security', 'credit card'];
        const foundPersonal = personalWords.filter(word => text.includes(word));
        if (foundPersonal.length > 0) {
            riskScore += foundPersonal.length * 30;
            riskFactors.push(`Personal info requested: ${foundPersonal.join(', ')}`);
            console.log('🚨 PERSONAL INFO REQUESTS:', foundPersonal);
        }
        
        // Subject line analysis
        const suspiciousSubjectWords = ['urgent', 'verify', 'expired', 'suspended', 'alert'];
        const subjectScore = suspiciousSubjectWords.filter(word => 
            emailData.subject.toLowerCase().includes(word)
        ).length;
        
        if (subjectScore > 0) {
            riskScore += subjectScore * 20;
            riskFactors.push(`Suspicious subject line indicators: ${subjectScore}`);
        }
        
        // VERY LOW thresholds for instant detection
        let riskLevel = 'LOW';
        if (riskScore >= 40) riskLevel = 'CRITICAL';
        else if (riskScore >= 25) riskLevel = 'HIGH';  
        else if (riskScore >= 15) riskLevel = 'MEDIUM';
        
        const result = {
            is_phishing: riskScore >= 15, // Very low threshold!
            confidence_score: Math.min(riskScore * 2, 95),
            risk_level: riskLevel,
            analysis_details: {
                risk_factors: riskFactors,
                analysis_method: 'instant_rules',
                total_risk_score: riskScore
            },
            recommendations: riskScore >= 15 ? [
                '🚨 DO NOT CLICK any links in this email!',
                '📞 Verify sender through alternative means',
                '🛡️ Report to IT security team immediately'
            ] : ['✅ Email appears safe']
        };
        
        console.log('⚡ INSTANT analysis complete:', result);
        return result;
    }
    
    extractEmailFromContent(emailContent) {
        try {
            const emailContainer = emailContent.closest('[data-message-id]') || emailContent.closest('.adn');
            
            // Get sender info
            const senderElement = emailContainer?.querySelector('[email]') || 
                                 emailContainer?.querySelector('.go .gb') ||
                                 document.querySelector('.go .gb');
            
            const sender = senderElement ? 
                (senderElement.getAttribute('email') || senderElement.textContent.trim()) : 
                'unknown@example.com';
            
            // Get subject
            const subjectElement = emailContainer?.querySelector('h2') ||
                                 emailContainer?.querySelector('.hP') ||
                                 document.querySelector('h2');
            
            const subject = subjectElement ? subjectElement.textContent.trim() : 'No subject';
            
            // Get email body text
            const bodyText = emailContent.innerText || emailContent.textContent || '';
            
            // Extract URLs
            const urls = this.extractUrls(bodyText);
            
            return {
                sender: sender,
                subject: subject,
                body: bodyText,
                urls: urls,
                hasAttachments: this.checkForAttachments(emailContainer)
            };
            
        } catch (error) {
            console.error('Error extracting email data:', error);
            return null;
        }
    }
    
    extractUrls(text) {
        const urlRegex = /https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?/gi;
        return text.match(urlRegex) || [];
    }
    
    checkForAttachments(emailContainer) {
        if (!emailContainer) return false;
        return emailContainer.querySelector('[data-tooltip*="attachment"], .aZo') !== null;
    }
    
    async performAIAnalysis(emailData) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/phishing-detector/analyze-email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email_content: `Subject: ${emailData.subject}\n\nFrom: ${emailData.sender}\n\n${emailData.body}`,
                    include_detailed_analysis: true,
                    cache_results: true
                })
            });
            
            if (response.ok) {
                return await response.json();
            } else {
                // Fallback to basic analysis if AI fails
                return this.performBasicAnalysis(emailData);
            }
            
        } catch (error) {
            console.error('AI analysis failed:', error);
            return this.performBasicAnalysis(emailData);
        }
    }
    
    performBasicAnalysis(emailData) {
        let riskScore = 0;
        let riskFactors = [];
        
        console.log('🔍 Performing basic analysis on email data:', emailData);
        
        // Check for suspicious URLs
        if (emailData.urls.length > 3) {
            riskScore += 30;
            riskFactors.push('Multiple URLs detected');
            console.log('⚠️ Multiple URLs found:', emailData.urls.length);
        }
        
        const suspiciousUrls = emailData.urls.filter(url => 
            url.includes('bit.ly') || url.includes('tinyurl') || 
            url.includes('t.co') || /https?:\/\/\d+\.\d+\.\d+\.\d+/.test(url) ||
            url.includes('track') || url.includes('click') || url.includes('redirect')
        );
        
        if (suspiciousUrls.length > 0) {
            riskScore += 40;
            riskFactors.push('Suspicious URL shorteners or tracking links');
            console.log('🚨 Suspicious URLs found:', suspiciousUrls);
        }
        
        // Check for urgent language - MORE aggressive detection
        const urgentWords = ['urgent', 'immediate', 'expires', 'verify', 'suspended', 'act now', 
                            'click here', 'limited time', 'expire', 'security alert', 'account locked',
                            'confirm', 'update', 'action required', 'respond now'];
        const text = (emailData.subject + ' ' + emailData.body).toLowerCase();
        const urgentCount = urgentWords.filter(word => text.includes(word)).length;
        
        if (urgentCount > 0) { // Lowered threshold for testing
            riskScore += urgentCount * 15; // More points per urgent word
            riskFactors.push(`High urgency language detected (${urgentCount} indicators)`);
            console.log('⚠️ Urgent language detected:', urgentCount, 'words');
        }
        
        // Check for personal info requests
        const personalInfoWords = ['password', 'ssn', 'social security', 'credit card', 'bank account',
                                  'pin', 'social', 'account number', 'login', 'credentials'];
        const personalInfoCount = personalInfoWords.filter(word => text.includes(word)).length;
        
        if (personalInfoCount > 0) {
            riskScore += personalInfoCount * 25;
            riskFactors.push(`Requests personal information (${personalInfoCount} types)`);
            console.log('🚨 Personal info requests detected:', personalInfoCount);
        }
        
        // Check sender reputation
        if (emailData.sender && emailData.sender !== 'unknown@example.com') {
            const senderDomain = emailData.sender.split('@')[1];
            // Flag suspicious sender patterns
            if (senderDomain && (senderDomain.includes('temp') || senderDomain.includes('fake') || 
                               senderDomain.includes('noreply') || senderDomain.length < 4)) {
                riskScore += 20;
                riskFactors.push('Suspicious sender domain');
            }
        }
        
        // Check for phishing simulation markers (for testing)
        if (text.includes('phishy') || text.includes('simulation') || text.includes('training')) {
            riskScore += 50; // High score for testing
            riskFactors.push('Phishing simulation detected');
            console.log('🎯 Phishing simulation detected!');
        }
        
        // Determine risk level - LOWER thresholds for better detection
        let riskLevel = 'LOW';
        if (riskScore >= 50) riskLevel = 'CRITICAL';
        else if (riskScore >= 30) riskLevel = 'HIGH';
        else if (riskScore >= 15) riskLevel = 'MEDIUM';
        
        const result = {
            is_phishing: riskScore >= 20, // Lowered threshold
            confidence_score: Math.min(riskScore * 1.5, 95),
            risk_level: riskLevel,
            analysis_details: {
                risk_factors: riskFactors,
                analysis_method: 'enhanced_basic_rules',
                total_risk_score: riskScore
            },
            recommendations: riskScore >= 20 ? [
                'Do not click any links in this email',
                'Verify sender identity independently',
                'Report to IT security team'
            ] : ['Remain cautious with email requests']
        };
        
        console.log('📊 Analysis result:', result);
        return result;
    }
    
    showScanningIndicator(emailContent) {
        const indicator = document.createElement('div');
        indicator.className = 'phishy-scanning-indicator';
        indicator.innerHTML = `
            <div style="background: #17a2b8; color: white; padding: 8px; border-radius: 4px; 
                        position: relative; margin: 10px 0; font-size: 12px; text-align: center;">
                <span style="animation: spin 1s linear infinite; display: inline-block; margin-right: 5px;">⚡</span>
                Phishy AI is scanning this email...
            </div>
        `;
        
        emailContent.parentNode.insertBefore(indicator, emailContent);
    }
    
    hideScanningIndicator(emailContent) {
        const indicator = emailContent.parentNode.querySelector('.phishy-scanning-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    showSuspiciousEmailWarning(emailContent, analysisResult, emailId) {
        // Prevent multiple warnings using unique email ID
        const warningId = `phishy-warning-${emailId}`;
        
        // Check if warning already exists for this specific email
        if (document.getElementById(warningId)) {
            console.log('⚠️ Warning already exists for email:', emailId);
            return;
        }
        
        // Initialize shown warnings set
        if (!this.shownWarnings) {
            this.shownWarnings = new Set();
        }
        
        if (this.shownWarnings.has(emailId)) {
            console.log('⚠️ Warning already shown for email:', emailId);
            return;
        }
        
        // Mark as shown
        this.shownWarnings.add(emailId);
        
        const warning = document.createElement('div');
        warning.id = warningId; // Set unique ID
        warning.className = 'phishy-email-warning phishy-warning-high';
        warning.setAttribute('data-email-id', emailId); // Track which email this belongs to
        warning.style.cssText = `
            position: sticky !important;
            top: 0 !important;
            z-index: 99999 !important;
            width: 100% !important;
        `;
        warning.innerHTML = `
            <div style="background: linear-gradient(135deg, #dc3545, #a71e2a) !important; 
                        color: white !important; padding: 20px !important; 
                        border-radius: 8px !important; margin: 0 0 20px 0 !important; 
                        border: 3px solid #721c24 !important;
                        box-shadow: 0 8px 25px rgba(220, 53, 69, 0.5) !important;
                        animation: phishyPulse 2s infinite !important;">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <span style="font-size: 32px; margin-right: 15px; animation: phishyShake 0.5s infinite;">🚨</span>
                    <div>
                        <h4 style="margin: 0; font-size: 20px; font-weight: bold; text-transform: uppercase;">
                            ⚠️ DANGER: SUSPICIOUS EMAIL DETECTED!
                        </h4>
                        <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.95;">
                            🎯 Risk Level: <strong>${analysisResult.risk_level}</strong> | 
                            📊 Confidence: <strong>${Math.round(analysisResult.confidence_score)}%</strong>
                        </p>
                    </div>
                </div>
                <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <strong>🚨 THREAT INDICATORS DETECTED:</strong>
                    <ul style="margin: 8px 0; padding-left: 25px; font-size: 13px;">
                        ${(analysisResult.analysis_details.risk_factors || []).map(factor => 
                            `<li style="margin: 5px 0;"><strong>${factor}</strong></li>`
                        ).join('')}
                    </ul>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <strong>🛡️ IMMEDIATE ACTIONS REQUIRED:</strong>
                    <ul style="margin: 8px 0; padding-left: 25px; font-size: 13px;">
                        ${(analysisResult.recommendations || []).map(rec => 
                            `<li style="margin: 5px 0;"><strong>${rec}</strong></li>`
                        ).join('')}
                    </ul>
                </div>
                <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
                    <button class="phishy-btn phishy-btn-flag" 
                            style="background: #dc3545 !important; color: white !important; font-weight: bold !important; padding: 12px 20px !important; border-radius: 6px !important;"
                            onclick="window.phishyGmail.showFlagDialogFromWarning(this.closest('.phishy-email-warning'))">
                        🚩 FLAG AS PHISHING
                    </button>
                    <button class="phishy-btn phishy-btn-report" 
                            style="background: #28a745 !important; color: white !important; font-weight: bold !important; padding: 12px 20px !important; border-radius: 6px !important;"
                            onclick="window.phishyGmail.reportThreatToIT()">
                        📧 REPORT TO IT
                    </button>
                    <button class="phishy-btn phishy-btn-dismiss" 
                            style="background: #6c757d !important; color: white !important; font-weight: bold !important; padding: 12px 20px !important; border-radius: 6px !important;"
                            onclick="window.phishyGmail.dismissWarning('${warningId}')">
                        ✅ I UNDERSTAND - DISMISS
                    </button>
                </div>
            </div>
        `;
        
        // Insert at the very top of the email
        emailContent.parentNode.insertBefore(warning, emailContent.parentNode.firstChild);
        
        // Scroll to top to ensure warning is visible
        warning.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Add pulsing animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes phishyPulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.02); }
                100% { transform: scale(1); }
            }
            @keyframes phishyShake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }
        `;
        document.head.appendChild(style);
        
        // Play attention sound (if possible)
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmckBiGTzPDOez0FLYnS+OCeUBgLbbXr4s5zLgQihM32z4A8BxyG0QA=');
            audio.play().catch(() => {});
        } catch (e) {}
        
        // Log the detection
        this.logSuspiciousDetection(analysisResult);
        
        console.log('🚨🚨🚨 HIGH RISK WARNING DISPLAYED! 🚨🚨🚨');
    }
    
    showCautionWarning(emailContent, analysisResult, emailId) {
        // Prevent duplicate caution warnings
        const warningId = `phishy-caution-${emailId}`;
        
        if (document.getElementById(warningId)) {
            console.log('⚠️ Caution warning already exists for email:', emailId);
            return;
        }
        
        const warning = document.createElement('div');
        warning.id = warningId;
        warning.className = 'phishy-email-warning phishy-warning-medium';
        warning.setAttribute('data-email-id', emailId);
        warning.innerHTML = `
            <div style="background: linear-gradient(135deg, #fd7e14, #e55a00); color: white; padding: 15px; 
                        border-radius: 8px; margin: 10px 0; border-left: 4px solid #d73f00;
                        box-shadow: 0 4px 12px rgba(253, 126, 20, 0.3);">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; flex: 1;">
                        <span style="font-size: 24px; margin-right: 12px;">⚠️</span>
                        <div>
                            <strong style="font-size: 16px;">Exercise Caution</strong>
                            <p style="margin: 5px 0 0 0; font-size: 12px; opacity: 0.9;">
                                This email has suspicious characteristics (${Math.round(analysisResult.confidence_score)}% confidence)
                            </p>
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px; margin-left: 15px;">
                        <button class="phishy-btn" 
                                style="background: #28a745 !important; color: white !important; padding: 8px 15px !important; border-radius: 4px !important; font-size: 12px !important;"
                                onclick="window.phishyGmail.showFlagDialogFromWarning(this.closest('.phishy-email-warning'))">
                            🚩 Flag
                        </button>
                        <button style="background: rgba(255,255,255,0.2); border: none; color: white; font-size: 16px; 
                                       cursor: pointer; padding: 5px 10px; border-radius: 4px;" 
                                onclick="window.phishyGmail.dismissWarning('${warningId}')">
                            ✅ Dismiss
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        emailContent.parentNode.insertBefore(warning, emailContent);
    }
    
    logSuspiciousDetection(analysisResult) {
        console.log('🚨 Phishy AI Detection:', {
            riskLevel: analysisResult.risk_level,
            confidence: analysisResult.confidence_score,
            timestamp: new Date().toISOString()
        });
    }
    
    reportPhishing() {
        const currentEmail = this.getCurrentEmailData();
        if (currentEmail) {
            this.submitFlag(currentEmail, 'phishing', 0.9, 'Auto-detected as suspicious by AI analysis');
        }
    }
    
    showSafeEmailIndicator(emailContent) {
        const indicator = document.createElement('div');
        indicator.className = 'phishy-safe-indicator';
        indicator.innerHTML = `
            <div style="background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; 
                        margin: 5px 0; font-size: 11px; text-align: center; opacity: 0.9;">
                ✅ Scanned by Phishy AI - No threats detected
            </div>
        `;
        
        emailContent.parentNode.insertBefore(indicator, emailContent);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 3000);
    }
    
    showErrorIndicator(emailContent, error) {
        const indicator = document.createElement('div');
        indicator.className = 'phishy-error-indicator';
        indicator.innerHTML = `
            <div style="background: #dc3545; color: white; padding: 5px 10px; border-radius: 4px; 
                        margin: 5px 0; font-size: 11px; text-align: center;">
                ❌ Phishy AI scan failed: ${error.message || 'Connection error'}
                <button style="background: none; border: none; color: white; margin-left: 10px; cursor: pointer;" 
                        onclick="this.closest('.phishy-error-indicator').remove()">×</button>
            </div>
        `;
        
        emailContent.parentNode.insertBefore(indicator, emailContent);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 10000);
    }
    
    showFlagDialogFromWarning(warningElement) {
        // Extract email data from the current email context
        const emailContent = warningElement.parentNode.querySelector('.ii.gt, .a3s.aiL, .adn.ads');
        
        if (!emailContent) {
            console.error('Could not find email content for flagging');
            return;
        }
        
        // Close the warning
        warningElement.style.display = 'none';
        
        // Show the flag dialog
        this.showFlagDialog(emailContent);
    }
    
    reportThreatToIT() {
        // Generate a simplified threat report
        const emailData = this.getCurrentEmailData();
        
        if (!emailData) {
            alert('⚠️ Could not extract email data for reporting');
            return;
        }
        
        // Create report content
        const reportContent = `
SECURITY ALERT - PHISHING EMAIL DETECTED

Detected by: Phishy AI Security Extension
Time: ${new Date().toLocaleString()}
Risk Level: HIGH/CRITICAL

Email Details:
- From: ${emailData.sender}
- Subject: ${emailData.subject}
- Content Length: ${emailData.body.length} characters
- URLs Found: ${emailData.urls ? emailData.urls.length : 0}

Threat Indicators:
- Suspicious keywords detected
- Potential phishing patterns identified
- Automated security scan triggered alert

Recommended Actions:
1. Do not interact with this email
2. Do not click any links or attachments
3. Report to IT Security team
4. Consider blocking sender if external

Generated by Phishy AI - Cybersecurity Training Platform
        `.trim();
        
        // Try to open email client or copy to clipboard
        const mailtoLink = `mailto:security@company.com?subject=SECURITY ALERT - Phishing Email Detected&body=${encodeURIComponent(reportContent)}`;
        
        // Copy to clipboard as fallback
        navigator.clipboard.writeText(reportContent).then(() => {
            alert('🚩 Threat report copied to clipboard!\n\nPlease paste this into an email to your IT security team.\n\nFor immediate reporting, we attempted to open your email client.');
        }).catch(() => {
            alert('🚩 Threat detected! Please manually report this to your IT security team.');
        });
        
        // Try to open email client
        try {
            window.open(mailtoLink);
        } catch (e) {
            console.log('Could not open email client:', e);
        }
    }
    
    dismissWarning(warningId) {
        console.log('✅ Dismissing warning:', warningId);
        
        // Find and remove the warning element
        const warningElement = document.getElementById(warningId);
        if (warningElement) {
            // Add fade out animation
            warningElement.style.transition = 'opacity 0.3s ease-out';
            warningElement.style.opacity = '0';
            
            // Remove after animation
            setTimeout(() => {
                if (warningElement.parentNode) {
                    warningElement.remove();
                    console.log('✅ Warning dismissed and removed');
                }
            }, 300);
            
            // Log dismissal (optional - for training data)
            this.logWarningDismissal(warningId);
        } else {
            console.warn('⚠️ Warning element not found:', warningId);
        }
    }
    
    logWarningDismissal(warningId) {
        // Log that user dismissed the warning (useful for training)
        console.log('📊 User dismissed warning:', {
            warningId: warningId,
            timestamp: new Date().toISOString(),
            action: 'dismissed'
        });
        
        // Optional: Send to backend for analytics
        if (this.apiBaseUrl) {
            try {
                fetch(`${this.apiBaseUrl}/analytics/warning-dismissed`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        warningId: warningId,
                        userEmail: this.userEmail,
                        timestamp: new Date().toISOString(),
                        action: 'dismissed'
                    })
                }).catch(e => console.log('Analytics logging failed:', e));
            } catch (e) {
                // Ignore analytics errors
            }
        }
    }
    
    showFlagDialog() {
        if (!this.apiBaseUrl) {
            this.showConfigurationDialog();
            return;
        }
        
        const currentEmail = this.getCurrentEmailData();
        if (!currentEmail) {
            this.showNotification('Unable to extract email data', 'error');
            return;
        }
        
        this.showFlagCategoryDialog(currentEmail);
    }
    
    getCurrentEmailData() {
        try {
            // Extract email data from current Gmail view
            const emailContainer = document.querySelector('[role="main"]');
            if (!emailContainer) return null;
            
            // Get sender
            const senderElement = emailContainer.querySelector('[email]') ||
                                emailContainer.querySelector('.go .gb') ||
                                emailContainer.querySelector('.gD');
            
            const sender = senderElement ? 
                (senderElement.getAttribute('email') || senderElement.textContent.trim()) : 
                'unknown@example.com';
            
            // Get subject
            const subjectElement = emailContainer.querySelector('h2') ||
                                 emailContainer.querySelector('.hP');
            
            const subject = subjectElement ? subjectElement.textContent.trim() : 'No subject';
            
            // Get email body
            const bodyElement = emailContainer.querySelector('.a3s.aiL') ||
                              emailContainer.querySelector('.ii.gt .a3s');
            
            const body = bodyElement ? bodyElement.innerText : '';
            
            // Generate email ID
            const emailId = `gmail_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            return {
                email_id: emailId,
                sender_email: sender,
                subject: subject,
                body: body,
                headers: this.extractEmailHeaders(),
                client_info: {
                    plugin_type: 'gmail',
                    user_agent: navigator.userAgent,
                    url: window.location.href
                }
            };
            
        } catch (error) {
            console.error('Error extracting email data:', error);
            return null;
        }
    }
    
    extractEmailHeaders() {
        // Extract available headers from Gmail interface
        const headers = {};
        
        try {
            // Get date
            const dateElement = document.querySelector('.g3');
            if (dateElement) {
                headers['Date'] = dateElement.getAttribute('title') || dateElement.textContent;
            }
            
            // Add more header extraction logic as needed
            
        } catch (error) {
            console.debug('Error extracting headers:', error);
        }
        
        return headers;
    }
    
    showFlagCategoryDialog(emailData) {
        const dialog = document.createElement('div');
        dialog.className = 'phishy-dialog-overlay';
        dialog.innerHTML = `
            <div class="phishy-dialog">
                <div class="phishy-dialog-header">
                    <h3>🚩 Flag Suspicious Email</h3>
                    <button class="phishy-dialog-close">&times;</button>
                </div>
                <div class="phishy-dialog-content">
                    <p><strong>From:</strong> ${emailData.sender_email}</p>
                    <p><strong>Subject:</strong> ${emailData.subject}</p>
                    
                    <label for="phishy-category">Why is this email suspicious?</label>
                    <select id="phishy-category" class="phishy-select">
                        <option value="phishing">Phishing attempt</option>
                        <option value="spam">Spam/Unwanted</option>
                        <option value="malware">Contains malware/suspicious links</option>
                        <option value="suspicious">Generally suspicious</option>
                        <option value="other">Other</option>
                    </select>
                    
                    <label for="phishy-confidence">Confidence level:</label>
                    <select id="phishy-confidence" class="phishy-select">
                        <option value="0.9">Very confident (90%)</option>
                        <option value="0.7" selected>Confident (70%)</option>
                        <option value="0.5">Somewhat confident (50%)</option>
                        <option value="0.3">Low confidence (30%)</option>
                    </select>
                    
                    <label for="phishy-notes">Additional notes (optional):</label>
                    <textarea id="phishy-notes" class="phishy-textarea" 
                             placeholder="Describe why you think this email is suspicious..."></textarea>
                </div>
                <div class="phishy-dialog-footer">
                    <button id="phishy-flag-submit" class="phishy-btn phishy-btn-primary">
                        Flag Email
                    </button>
                    <button id="phishy-flag-cancel" class="phishy-btn phishy-btn-secondary">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Event handlers
        dialog.querySelector('.phishy-dialog-close').onclick = () => dialog.remove();
        dialog.querySelector('#phishy-flag-cancel').onclick = () => dialog.remove();
        dialog.onclick = (e) => {
            if (e.target === dialog) dialog.remove();
        };
        
        dialog.querySelector('#phishy-flag-submit').onclick = () => {
            const category = dialog.querySelector('#phishy-category').value;
            const confidence = parseFloat(dialog.querySelector('#phishy-confidence').value);
            const notes = dialog.querySelector('#phishy-notes').value;
            
            this.submitFlag(emailData, category, confidence, notes);
            dialog.remove();
        };
    }
    
    async submitFlag(emailData, category, confidence, notes) {
        try {
            this.showNotification('Flagging email...', 'info');
            
            const flagRequest = {
                ...emailData,
                flag_category: category,
                confidence_level: confidence,
                user_email: this.userEmail || 'user@gmail.com',
                plugin_version: '1.0.0',
                additional_context: notes
            };
            
            const response = await fetch(`${this.apiBaseUrl}/email-flagging/flag`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(flagRequest)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showNotification('Email flagged successfully!', 'success');
                this.showAnalysisResult(result.analysis);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
            
        } catch (error) {
            console.error('Error flagging email:', error);
            this.showNotification('Failed to flag email. Check your connection.', 'error');
        }
    }
    
    showAnalysisResult(analysis) {
        if (!analysis) return;
        
        const dialog = document.createElement('div');
        dialog.className = 'phishy-dialog-overlay';
        dialog.innerHTML = `
            <div class="phishy-dialog">
                <div class="phishy-dialog-header">
                    <h3>🤖 AI Analysis Result</h3>
                    <button class="phishy-dialog-close">&times;</button>
                </div>
                <div class="phishy-dialog-content">
                    <div class="phishy-analysis-result">
                        <div class="phishy-threat-level ${analysis.threat_level}">
                            Threat Level: <strong>${analysis.threat_level.toUpperCase()}</strong>
                        </div>
                        <div class="phishy-confidence">
                            AI Confidence: <strong>${Math.round(analysis.confidence_score * 100)}%</strong>
                        </div>
                        <div class="phishy-explanation">
                            <h4>Analysis:</h4>
                            <p>${analysis.explanation}</p>
                        </div>
                        ${analysis.recommendations.length > 0 ? `
                            <div class="phishy-recommendations">
                                <h4>Recommendations:</h4>
                                <ul>
                                    ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="phishy-dialog-footer">
                    <button class="phishy-btn phishy-btn-primary" onclick="this.closest('.phishy-dialog-overlay').remove()">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        dialog.querySelector('.phishy-dialog-close').onclick = () => dialog.remove();
        dialog.onclick = (e) => {
            if (e.target === dialog) dialog.remove();
        };
    }
    
    showConfigurationDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'phishy-dialog-overlay';
        dialog.innerHTML = `
            <div class="phishy-dialog">
                <div class="phishy-dialog-header">
                    <h3>⚙️ Configure Phishy AI</h3>
                    <button class="phishy-dialog-close">&times;</button>
                </div>
                <div class="phishy-dialog-content">
                    <p>Configure your Phishy AI connection to start flagging suspicious emails.</p>
                    
                    <label for="phishy-api-url">Phishy AI Server URL:</label>
                    <input type="url" id="phishy-api-url" class="phishy-input" 
                           placeholder="https://your-tunnel.ngrok.io" 
                           value="${this.apiBaseUrl || ''}">
                    
                    <label for="phishy-user-email">Your Email:</label>
                    <input type="email" id="phishy-user-email" class="phishy-input" 
                           placeholder="your.email@company.com" 
                           value="${this.userEmail || ''}">
                    
                    <div class="phishy-help">
                        <p><strong>Need help?</strong></p>
                        <p>1. Make sure Phishy AI server is running</p>
                        <p>2. Copy the ngrok tunnel URL from your server</p>
                        <p>3. Test connection by clicking "Test Connection"</p>
                    </div>
                </div>
                <div class="phishy-dialog-footer">
                    <button id="phishy-test-connection" class="phishy-btn phishy-btn-secondary">
                        Test Connection
                    </button>
                    <button id="phishy-save-config" class="phishy-btn phishy-btn-primary">
                        Save Configuration
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Event handlers
        dialog.querySelector('.phishy-dialog-close').onclick = () => dialog.remove();
        dialog.onclick = (e) => {
            if (e.target === dialog) dialog.remove();
        };
        
        dialog.querySelector('#phishy-test-connection').onclick = () => {
            const url = dialog.querySelector('#phishy-api-url').value;
            this.testConnection(url);
        };
        
        dialog.querySelector('#phishy-save-config').onclick = async () => {
            const url = dialog.querySelector('#phishy-api-url').value;
            const email = dialog.querySelector('#phishy-user-email').value;
            
            if (url && email) {
                await this.saveConfiguration(url, email);
                dialog.remove();
                this.showNotification('Configuration saved!', 'success');
            } else {
                this.showNotification('Please fill in all fields', 'error');
            }
        };
    }
    
    async testConnection(url) {
        try {
            this.showNotification('Testing connection...', 'info');
            
            const response = await fetch(`${url}/email-flagging/health`, {
                method: 'GET',
                timeout: 5000
            });
            
            if (response.ok) {
                this.showNotification('Connection successful!', 'success');
            } else {
                throw new Error('Connection failed');
            }
            
        } catch (error) {
            this.showNotification('Connection failed. Check URL and server status.', 'error');
        }
    }
    
    async saveConfiguration(url, email) {
        this.apiBaseUrl = url;
        this.userEmail = email;
        
        await chrome.storage.sync.set({
            phishyApiUrl: url,
            phishyUserEmail: email,
            phishyEnabled: true
        });
        
        this.connectWebSocket();
    }
    
    connectWebSocket() {
        if (!this.apiBaseUrl || this.websocket) return;
        
        try {
            const wsUrl = this.apiBaseUrl.replace('https://', 'wss://').replace('http://', 'ws://');
            this.websocket = new WebSocket(`${wsUrl}/email-flagging/ws/${this.pluginId}?plugin_type=gmail`);
            
            this.websocket.onopen = () => {
                console.log('🔗 Connected to Phishy AI WebSocket');
            };
            
            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };
            
            this.websocket.onclose = () => {
                console.log('📡 Disconnected from Phishy AI WebSocket');
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('Error connecting WebSocket:', error);
        }
    }
    
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'connected':
                this.showNotification('Connected to Phishy AI', 'success');
                break;
                
            case 'tunnel_updated':
                this.updateTunnelUrl(message.data.new_tunnel_url);
                break;
                
            case 'email_flagged':
                // Handle notifications about other flagged emails
                break;
                
            default:
                console.log('Unknown WebSocket message:', message);
        }
    }
    
    async updateTunnelUrl(newUrl) {
        this.apiBaseUrl = newUrl;
        await chrome.storage.sync.set({ phishyApiUrl: newUrl });
        this.showNotification('Server URL updated automatically', 'info');
        
        // Reconnect WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        this.connectWebSocket();
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `phishy-notification phishy-notification-${type}`;
        notification.innerHTML = `
            <div class="phishy-notification-content">
                <span class="phishy-notification-icon">
                    ${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}
                </span>
                <span class="phishy-notification-text">${message}</span>
                <button class="phishy-notification-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        notification.querySelector('.phishy-notification-close').onclick = () => {
            notification.remove();
        };
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize Phishy Gmail extension
const phishyGmail = new PhishyGmail();

// Add manual debug functions
window.phishyAddFlag = () => {
    console.log('🔧 Manually adding flag button...');
    
    // Try to find any likely button container
    const containers = document.querySelectorAll('.aAU, .ar9, .amn, [role="toolbar"], .T-I-J3');
    console.log('Found containers:', containers.length);
    
    containers.forEach((container, i) => {
        console.log(`Container ${i}:`, container);
        if (!container.querySelector('.phishy-flag-btn') && container.offsetParent !== null) {
            phishyGmail.addFlagButtonToToolbar(container);
            console.log('Added flag button to container', i);
        }
    });
    
    // Fallback: Add floating button
    if (!document.querySelector('.phishy-flag-btn')) {
        const flagButton = document.createElement('div');
        flagButton.className = 'phishy-flag-btn-floating';
        flagButton.innerHTML = `
            <div style="position: fixed; top: 100px; right: 20px; z-index: 10000; 
                        background: #dc3545; color: white; padding: 10px; border-radius: 5px; 
                        cursor: pointer; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">
                🚩 Flag Email
            </div>
        `;
        
        flagButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            phishyGmail.showFlagDialog();
        });
        
        document.body.appendChild(flagButton);
        console.log('Added floating flag button');
    }
};