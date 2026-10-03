class PhishyDetector {
  constructor() {
    this.ngrokUrl = null;
    this.userEmail = null;
    this.processedEmails = new Set();
    this.init();
  }

  async init() {
    await this.loadSettings();
    this.setupEmailDetection();
  }

  async loadSettings() {
    try {
      const result = await chrome.storage.local.get(['ngrokUrl', 'userEmail']);
      this.ngrokUrl = result.ngrokUrl;
      this.userEmail = result.userEmail;
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  }

  setupEmailDetection() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              this.checkForNewEmails(node);
            }
          });
        }
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    this.checkForNewEmails(document.body);
  }

  checkForNewEmails(container) {
    const emailElements = container.querySelectorAll('[data-message-id]:not([data-phishy-processed])');
    
    emailElements.forEach(async (emailElement) => {
      const messageId = emailElement.getAttribute('data-message-id');
      
      if (!this.processedEmails.has(messageId)) {
        this.processedEmails.add(messageId);
        emailElement.setAttribute('data-phishy-processed', 'true');
        await this.analyzeEmail(emailElement, messageId);
      }
    });

    const conversationViews = container.querySelectorAll('[role="main"] [data-message-id]:not([data-phishy-processed])');
    conversationViews.forEach(async (emailElement) => {
      const messageId = emailElement.getAttribute('data-message-id') || Date.now().toString();
      
      if (!this.processedEmails.has(messageId)) {
        this.processedEmails.add(messageId);
        emailElement.setAttribute('data-phishy-processed', 'true');
        await this.analyzeEmail(emailElement, messageId);
      }
    });
  }

  async analyzeEmail(emailElement, messageId) {
    if (!this.ngrokUrl || !this.userEmail) {
      this.showConfigurationNeeded(emailElement);
      return;
    }

    try {
      const emailContent = this.extractEmailContent(emailElement);
      
      if (!emailContent.subject && !emailContent.body && !emailContent.sender) {
        return;
      }

      // Extract all URLs from DOM structure and intelligently filter
      const allUrls = this.extractAllUrls(emailElement);
      const urlAnalysis = this.filterAndRankUrls(allUrls);
      
      // Store comprehensive analysis data
      emailContent.urls = allUrls;
      emailContent.urlAnalysis = urlAnalysis;
      this.lastAnalyzedContent = `Subject: ${emailContent.subject}\nFrom: ${emailContent.sender}\n\n${emailContent.body}`;
      this.lastAnalyzedElement = emailElement;
      this.lastFoundUrls = allUrls;
      this.lastUrlAnalysis = urlAnalysis;

      this.showAnalyzingBanner(emailElement);

      // Step 1: Get INSTANT ML verdict (no API calls)
      const mlResponse = await this.getInstantMLVerdict(emailContent);
      
      // Step 2: Display ML result immediately
      this.displayInstantMLResult(emailElement, mlResponse, emailContent, urlAnalysis);

      // Step 3: Asynchronously run API checks on top risky URLs only (if any)
      if (urlAnalysis.topRiskyUrls.length > 0) {
        this.runAsyncAPIChecks(emailElement, emailContent, urlAnalysis);
      }

    } catch (error) {
      console.error('Error analyzing email:', error);
      this.showErrorBanner(emailElement, error.message);
    }
  }

  async getInstantMLVerdict(emailContent) {
    // Call backend for ML-only analysis (no external APIs)
    const payload = {
      email_content: `Subject: ${emailContent.subject}\nFrom: ${emailContent.sender}\n\n${emailContent.body}`,
      ml_only: true, // New flag to skip external APIs
      include_detailed_analysis: false
    };

    const response = await fetch(`${this.ngrokUrl}/detector/analyze-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    return await response.json();
  }

  displayInstantMLResult(emailElement, mlResult, emailContent, urlAnalysis) {
    this.removeExistingBanners(emailElement);

    const isPhishing = mlResult.is_phishing;
    const confidence = mlResult.confidence_score / 100;
    
    const banner = this.createInstantResultBanner(isPhishing, confidence, mlResult, urlAnalysis);
    this.insertBanner(emailElement, banner);

    this.logResult(emailContent, mlResult);
  }

  createInstantResultBanner(isPhishing, confidence, result, urlAnalysis) {
    const bannerId = `phishy-banner-${Date.now()}`;
    const banner = document.createElement('div');
    banner.className = `phishy-banner ${isPhishing ? 'phishy-danger' : 'phishy-safe'}`;
    banner.id = bannerId;
    
    const confidencePercent = Math.round(confidence * 100);
    const status = isPhishing ? 'PHISHING DETECTED' : 'SAFE EMAIL';
    const emoji = isPhishing ? '⚠️' : '✅';
    const riskLevel = result.risk_level || '';
    
    // Enhanced URL analysis summary with tiered breakdown
    const metrics = urlAnalysis.analysisMetrics;
    const urlSummary = urlAnalysis.allUrls.length > 0 ? 
      `📊 Smart Analysis: ${urlAnalysis.allUrls.length} URLs found, ${urlAnalysis.whitelistedCount} trusted • API: ${metrics.apiAnalysis} • PathAI: ${metrics.pathIntelligence}` :
      '📊 No URLs found';
    
    banner.innerHTML = `
      <div class="phishy-banner-content">
        <div class="phishy-banner-header">
          <div class="phishy-status">
            ${emoji} <strong>${status} ${riskLevel ? `(${riskLevel} RISK)` : ''}</strong>
          </div>
          <div class="phishy-confidence">
            ML Confidence: ${confidencePercent}%
          </div>
        </div>
        <div class="phishy-url-summary">
          ${urlSummary}
        </div>
        ${urlAnalysis.topRiskyUrls.length > 0 ? 
          `<div class="phishy-api-status" id="api-status-${bannerId}">
            🔍 Checking ${urlAnalysis.topRiskyUrls.length} risky URLs...
          </div>` : ''}
        ${result.recommendations && result.recommendations.length > 0 ? 
          `<div class="phishy-reasoning">
            <strong>Quick Recommendations:</strong><br>
            ${result.recommendations.slice(0, 2).join('<br>')}
          </div>` : ''}
        <div class="phishy-actions">
          <button class="phishy-detailed-btn" data-banner-id="${bannerId}">
            🔍 Detailed Analysis
          </button>
        </div>
      </div>
    `;

    // Add click event for detailed analysis
    const detailBtn = banner.querySelector('.phishy-detailed-btn');
    detailBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.showDetailedAnalysis(banner, result);
    });

    return banner;
  }

  async runAsyncAPIChecks(emailElement, emailContent, urlAnalysis) {
    const banner = emailElement.querySelector('.phishy-banner');
    const apiStatusElement = banner?.querySelector('[id^="api-status-"]');
    
    if (!apiStatusElement) return;

    try {
      // Only send top risky URLs to APIs
      const payload = {
        email_content: `Subject: ${emailContent.subject}\nFrom: ${emailContent.sender}\n\n${emailContent.body}`,
        urls: urlAnalysis.topRiskyUrls, // Only top 2-3 risky URLs
        api_only: true // New flag to run only API checks
      };

      // Update status to show which APIs are running
      apiStatusElement.innerHTML = `🛡️ Google Safe Browsing & 🌐 URLScan.io checking ${urlAnalysis.topRiskyUrls.length} URLs...`;

      const response = await fetch(`${this.ngrokUrl}/comprehensive/detailed-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const apiResults = await response.json();
        this.updateBannerWithAPIResults(emailElement, apiResults, urlAnalysis);
      } else {
        apiStatusElement.innerHTML = `❌ API checks failed`;
      }

    } catch (error) {
      console.error('API checks failed:', error);
      if (apiStatusElement) {
        apiStatusElement.innerHTML = `❌ API checks timed out`;
      }
    }
  }

  updateBannerWithAPIResults(emailElement, apiResults, urlAnalysis) {
    const banner = emailElement.querySelector('.phishy-banner');
    const apiStatusElement = banner?.querySelector('[id^="api-status-"]');
    
    if (!apiStatusElement) return;

    // Combine API results with our path intelligence
    const hybridAnalysis = this.combineAPIWithPathIntelligence(apiResults, urlAnalysis);

    let statusText = hybridAnalysis.overallWarning ? '⚠️ ' : '✅ ';
    statusText += 'Analysis complete: ';
    const results = [];
    let hasErrors = false;
    let hasThreats = hybridAnalysis.hasPathThreats;

    // Google Safe Browsing results
    if (apiResults.safe_browsing) {
      const gsb = apiResults.safe_browsing;
      if (gsb.status === 'threat') {
        results.push(`🛡️ GSB: ${gsb.threats?.length || 0} threats`);
        hasThreats = true;
      } else if (gsb.status === 'clean') {
        results.push(`🛡️ GSB: Clean`);
      } else if (gsb.status === 'error') {
        results.push(`🛡️ GSB: Error`);
        hasErrors = true;
      } else {
        results.push(`🛡️ GSB: ${gsb.status}`);
      }
    }

    // URLScan.io results with path intelligence overlay
    if (apiResults.urlscan_io) {
      const urlscan = apiResults.urlscan_io;
      if (urlscan.status === 'malicious') {
        results.push(`🌐 URLScan: Malicious (${urlscan.verdicts?.overall?.score || 0}%)`);
        hasThreats = true;
      } else if (urlscan.status === 'clean') {
        // Add path intelligence warning even if API says clean
        if (hybridAnalysis.hasPathThreats) {
          results.push(`🌐 URLScan: Clean, ⚠️ Suspicious paths detected`);
        } else {
          results.push(`🌐 URLScan: Clean`);
        }
      } else if (urlscan.status === 'error') {
        results.push(`🌐 URLScan: Error`);
        hasErrors = true;
      } else {
        results.push(`🌐 URLScan: ${urlscan.status}`);
      }
    }

    // Add path intelligence summary
    if (hybridAnalysis.pathWarnings.length > 0) {
      results.push(`🧠 Path AI: ${hybridAnalysis.pathWarnings.length} suspicious patterns`);
    }

    statusText += results.join(', ');
    apiStatusElement.innerHTML = statusText;

    // Update CSS class based on hybrid analysis
    apiStatusElement.classList.remove('phishy-api-status');
    if (hasErrors) {
      apiStatusElement.classList.add('error');
    } else if (hasThreats || hybridAnalysis.hasPathThreats) {
      apiStatusElement.classList.add('error'); // Path threats are also concerning
    } else {
      apiStatusElement.classList.add('completed');
    }

    // Store updated results for detailed analysis
    this.lastAPIResults = apiResults;
    this.lastHybridAnalysis = hybridAnalysis;
  }

  combineAPIWithPathIntelligence(apiResults, urlAnalysis) {
    const pathWarnings = [];
    let hasPathThreats = false;
    
    if (!urlAnalysis || !urlAnalysis.pathIntelligenceUrls) {
      return { overallWarning: false, hasPathThreats: false, pathWarnings: [] };
    }

    // Use the enhanced pathIntelligenceUrls (up to 8 URLs) for comprehensive analysis
    const urlsToAnalyze = urlAnalysis.pathIntelligenceUrls || urlAnalysis.filteredUrls?.slice(0, 8) || [];
    
    urlsToAnalyze.forEach(urlRisk => {
      // Look for specific concerning patterns that APIs might miss
      const concerningFactors = urlRisk.riskFactors?.filter(factor => 
        factor.includes('Suspicious path on trusted domain') ||
        factor.includes('Random/generated path pattern') ||
        factor.includes('Suspicious path keywords') ||
        factor.includes('Untrusted subdomain') ||
        factor.includes('URL shortener') ||
        factor.includes('Suspicious domain structure')
      ) || [];

      // Include medium-risk patterns that might be overlooked
      if (concerningFactors.length > 0 || urlRisk.riskScore >= 15) {
        if (concerningFactors.length > 0) {
          hasPathThreats = true;
          pathWarnings.push({
            url: urlRisk.url,
            score: urlRisk.riskScore,
            factors: concerningFactors,
            tier: urlRisk.riskScore >= 60 ? 'CRITICAL' : urlRisk.riskScore >= 30 ? 'HIGH' : 'MEDIUM'
          });
        }
      }
    });

    console.log(`🧠 PathIntelligence analyzed ${urlsToAnalyze.length} URLs, found ${pathWarnings.length} suspicious patterns`);

    return {
      overallWarning: hasPathThreats,
      hasPathThreats: hasPathThreats,
      pathWarnings: pathWarnings,
      analysisMetrics: {
        urlsAnalyzed: urlsToAnalyze.length,
        patternsDetected: pathWarnings.length,
        highestThreatTier: pathWarnings.length > 0 ? pathWarnings[0].tier : 'NONE'
      }
    };
  }

  extractEmailContent(emailElement) {
    const subject = this.extractSubject(emailElement);
    const sender = this.extractSender(emailElement);
    const body = this.extractBody(emailElement);
    const urls = this.extractUrls(body);

    return {
      subject: subject || '',
      sender: sender || '',
      body: body || '',
      urls: urls || [],
      recipient: this.userEmail
    };
  }

  extractSubject(emailElement) {
    const subjectSelectors = [
      'h2[data-legacy-thread-id]',
      '[data-subject]',
      '.hP',
      '.bog'
    ];

    for (const selector of subjectSelectors) {
      const element = emailElement.querySelector(selector);
      if (element && element.textContent.trim()) {
        return element.textContent.trim();
      }
    }

    const subjectInConversation = document.querySelector('h2[data-legacy-thread-id]');
    return subjectInConversation ? subjectInConversation.textContent.trim() : '';
  }

  extractSender(emailElement) {
    const senderSelectors = [
      '.go .qu',
      '.yW span[email]',
      '.yW .qu',
      '.gD',
      '[email]'
    ];

    for (const selector of senderSelectors) {
      const element = emailElement.querySelector(selector);
      if (element) {
        const email = element.getAttribute('email') || element.textContent.trim();
        if (email && email.includes('@')) {
          return email;
        }
      }
    }
    return '';
  }

  extractBody(emailElement) {
    const bodySelectors = [
      '.ii.gt .a3s.aiL',
      '.ii.gt',
      '.aHn .a3s.aiL',
      '.a3s.aiL',
      '.ii.gt div[dir="ltr"]'
    ];

    for (const selector of bodySelectors) {
      const elements = emailElement.querySelectorAll(selector);
      if (elements.length > 0) {
        return Array.from(elements)
          .map(el => el.textContent.trim())
          .filter(text => text.length > 0)
          .join('\n');
      }
    }
    return '';
  }

  extractUrls(text) {
    const urlRegex = /https?:\/\/[^\s<>"{}|\\^`[\]]+/g;
    return text.match(urlRegex) || [];
  }

  extractAllUrls(emailElement) {
    const urls = new Set();
    
    // 1. Extract from text content
    const textUrls = this.extractUrls(emailElement.textContent || '');
    textUrls.forEach(url => urls.add(url));
    
    // 2. Extract from href attributes (links)
    const links = emailElement.querySelectorAll('a[href]');
    links.forEach(link => {
      const href = link.getAttribute('href');
      if (href && href.startsWith('http')) {
        urls.add(href);
      }
    });
    
    // 3. Extract from img src attributes
    const images = emailElement.querySelectorAll('img[src]');
    images.forEach(img => {
      const src = img.getAttribute('src');
      if (src && src.startsWith('http')) {
        urls.add(src);
      }
    });
    
    // 4. Extract from background-image CSS
    const elementsWithBg = emailElement.querySelectorAll('*');
    elementsWithBg.forEach(el => {
      const style = window.getComputedStyle(el);
      const bgImage = style.backgroundImage;
      if (bgImage && bgImage !== 'none') {
        const urlMatch = bgImage.match(/url\(['"]?(https?:\/\/[^'"]+)['"]?\)/);
        if (urlMatch) {
          urls.add(urlMatch[1]);
        }
      }
    });
    
    // 5. Extract from data attributes
    const dataElements = emailElement.querySelectorAll('[data-src], [data-url], [data-href]');
    dataElements.forEach(el => {
      ['data-src', 'data-url', 'data-href'].forEach(attr => {
        const dataUrl = el.getAttribute(attr);
        if (dataUrl && dataUrl.startsWith('http')) {
          urls.add(dataUrl);
        }
      });
    });
    
    // 6. Extract from iframe src
    const iframes = emailElement.querySelectorAll('iframe[src]');
    iframes.forEach(iframe => {
      const src = iframe.getAttribute('src');
      if (src && src.startsWith('http')) {
        urls.add(src);
      }
    });
    
    // 7. Extract from form actions
    const forms = emailElement.querySelectorAll('form[action]');
    forms.forEach(form => {
      const action = form.getAttribute('action');
      if (action && action.startsWith('http')) {
        urls.add(action);
      }
    });
    
    // 8. Extract from style attributes (inline styles)
    const styledElements = emailElement.querySelectorAll('[style*="url("]');
    styledElements.forEach(el => {
      const style = el.getAttribute('style');
      const urlMatches = style.match(/url\(['"]?(https?:\/\/[^'"]+)['"]?\)/g);
      if (urlMatches) {
        urlMatches.forEach(match => {
          const url = match.match(/https?:\/\/[^'"]+/)[0];
          if (url) urls.add(url);
        });
      }
    });
    
    // 9. Extract from tracking pixels and hidden elements
    const trackingElements = emailElement.querySelectorAll('img[width="1"], img[height="1"], [style*="display:none"], [style*="visibility:hidden"]');
    trackingElements.forEach(el => {
      const src = el.getAttribute('src');
      if (src && src.startsWith('http')) {
        urls.add(src);
      }
    });
    
    return Array.from(urls);
  }

  // Advanced URL Triage System with domain-level whitelisting and path-level analysis
  filterAndRankUrls(urls) {
    console.log("🔍 Smart URL Triage System: Analyzing", urls.length, "URLs");
    
    const urlRisks = urls.map(url => this.analyzeURLRisk(url));
    
    // Filter out whitelisted URLs and sort by risk score
    const filteredUrls = urlRisks.filter(item => !item.skip);
    const sortedUrls = filteredUrls.sort((a, b) => b.riskScore - a.riskScore);
    
    // Tiered Analysis System with Risk Thresholds
    const criticalRiskUrls = sortedUrls.filter(item => item.riskScore >= 60);  // Always get API analysis
    const highRiskUrls = sortedUrls.filter(item => item.riskScore >= 30 && item.riskScore < 60);
    const mediumRiskUrls = sortedUrls.filter(item => item.riskScore >= 15 && item.riskScore < 30);
    const lowRiskUrls = sortedUrls.filter(item => item.riskScore < 15);
    
    // Smart API Analysis Selection
    // Always analyze critical risk URLs + fill remaining slots (up to 5) with high risk URLs
    const maxApiAnalysis = 5;
    const apiAnalysisUrls = [
      ...criticalRiskUrls,
      ...highRiskUrls.slice(0, Math.max(0, maxApiAnalysis - criticalRiskUrls.length))
    ];
    
    // PathIntelligence analyzes more URLs (critical + high + medium, up to 8)
    const pathIntelligenceUrls = [
      ...criticalRiskUrls,
      ...highRiskUrls,
      ...mediumRiskUrls
    ].slice(0, 8);
    
    console.log("📊 Smart URL Analysis Results:");
    console.log("- Total URLs:", urls.length);
    console.log("- Whitelisted/Skipped:", urlRisks.filter(item => item.skip).length);
    console.log("- Critical Risk (≥60):", criticalRiskUrls.length);
    console.log("- High Risk (30-59):", highRiskUrls.length);
    console.log("- Medium Risk (15-29):", mediumRiskUrls.length);
    console.log("- Low Risk (<15):", lowRiskUrls.length);
    console.log("- API Analysis URLs:", apiAnalysisUrls.length, "→", apiAnalysisUrls.map(item => item.url));
    console.log("- PathIntelligence URLs:", pathIntelligenceUrls.length);
    console.log("- Top Risk Breakdown:", sortedUrls.slice(0, 5).map(item => ({url: item.url, score: item.riskScore, tier: item.riskScore >= 60 ? 'CRITICAL' : item.riskScore >= 30 ? 'HIGH' : item.riskScore >= 15 ? 'MEDIUM' : 'LOW'})));

    return {
      allUrls: urls,
      filteredUrls: sortedUrls,
      whitelistedCount: urlRisks.filter(item => item.skip).length,
      // Enhanced URL categorization
      criticalRiskUrls: criticalRiskUrls,
      highRiskUrls: highRiskUrls,
      mediumRiskUrls: mediumRiskUrls,
      lowRiskUrls: lowRiskUrls,
      // Smart analysis selection
      topRiskyUrls: apiAnalysisUrls.map(item => item.url), // Smart API selection (up to 5)
      pathIntelligenceUrls: pathIntelligenceUrls, // Expanded PathIntelligence coverage (up to 8)
      // Analysis metrics
      analysisMetrics: {
        totalAnalyzed: filteredUrls.length,
        apiAnalysis: apiAnalysisUrls.length,
        pathIntelligence: pathIntelligenceUrls.length,
        highestRiskScore: sortedUrls[0]?.riskScore || 0
      }
    };
  }

  analyzeURLRisk(url) {
    const parsed = this.parseURL(url);
    const domain = parsed.domain.toLowerCase();
    const path = parsed.path.toLowerCase();
    const fullURL = url.toLowerCase();
    
    let riskScore = 0;
    let riskFactors = [];
    
    // 1. DOMAIN-LEVEL WHITELISTING with suspicious subdomain detection
    const domainAnalysis = this.analyzeDomainRisk(parsed);
    if (domainAnalysis.skip) {
      return { url, riskScore: -100, riskFactors: domainAnalysis.riskFactors, skip: true };
    }
    riskScore += domainAnalysis.riskScore;
    riskFactors.push(...domainAnalysis.riskFactors);
    
    // 2. PATH-LEVEL ANALYSIS
    const pathAnalysis = this.analyzePathRisk(parsed);
    riskScore += pathAnalysis.riskScore;
    riskFactors.push(...pathAnalysis.riskFactors);
    
    // 3. URL STRUCTURE ANALYSIS
    const structureAnalysis = this.analyzeURLStructure(url, parsed);
    riskScore += structureAnalysis.riskScore;
    riskFactors.push(...structureAnalysis.riskFactors);
    
    // 4. ML-ASSISTED SCORING (heuristic-based)
    const mlScore = this.calculateMLScore(url, parsed, riskFactors);
    riskScore += mlScore.riskScore;
    riskFactors.push(...mlScore.riskFactors);
    
    return { url, riskScore: Math.min(riskScore, 100), riskFactors, skip: false };
  }

  parseURL(url) {
    try {
      const urlObj = new URL(url);
      const domainParts = urlObj.hostname.split('.');
      const rootDomain = domainParts.slice(-2).join('.');
      
      return {
        protocol: urlObj.protocol,
        hostname: urlObj.hostname,
        domain: urlObj.hostname,
        rootDomain: rootDomain,
        subdomain: domainParts.length > 2 ? domainParts.slice(0, -2).join('.') : '',
        path: urlObj.pathname,
        query: urlObj.search,
        fragment: urlObj.hash,
        port: urlObj.port
      };
    } catch (e) {
      return {
        protocol: 'unknown', hostname: url, domain: url, rootDomain: url,
        subdomain: '', path: '', query: '', fragment: '', port: ''
      };
    }
  }

  analyzeDomainRisk(parsed) {
    const { hostname, rootDomain, subdomain, path } = parsed;
    
    // Trusted root domains with path-level analysis
    const trustedDomains = {
      // Google ecosystem
      'google.com': { legitimatePaths: ['/help', '/support', '/policies', '/intl', '/search', '/maps'], 
                     suspiciousPaths: ['/redirect', '/url?', '/amp/'], 
                     trustedSubdomains: ['www', 'support', 'developers', 'policies', 'accounts'] },
      'googleapis.com': { legitimatePaths: ['/auth', '/oauth2', '/discovery'], 
                         suspiciousPaths: ['/storage/', '/drive/'], 
                         trustedSubdomains: ['www', 'accounts', 'oauth2'] },
      'gstatic.com': { legitimatePaths: ['/images/', '/charts/', '/fonts/'], 
                      suspiciousPaths: ['/file/', '/download/'], 
                      trustedSubdomains: ['ssl', 'www', 'fonts', 'maps'] },
      
      // Microsoft ecosystem  
      'microsoft.com': { legitimatePaths: ['/support', '/docs', '/download', '/security'], 
                        suspiciousPaths: ['/redirect', '/link'], 
                        trustedSubdomains: ['www', 'support', 'docs', 'account'] },
      'office.com': { legitimatePaths: ['/launch', '/apps', '/help'], 
                     suspiciousPaths: ['/redirect', '/external'], 
                     trustedSubdomains: ['www', 'portal', 'login'] },
      
      // Amazon ecosystem
      'amazon.com': { legitimatePaths: ['/gp/', '/dp/', '/help/', '/your-account/'], 
                     suspiciousPaths: ['/redirect', '/ref='], 
                     trustedSubdomains: ['www', 'smile', 'music', 'prime'] },
      'amazonaws.com': { legitimatePaths: ['/'], 
                        suspiciousPaths: ['/temp/', '/tmp/', '/uploads/'], 
                        trustedSubdomains: ['s3', 'ec2', 'cloudfront'] }
    };

    // Check if this is a trusted domain
    if (trustedDomains[rootDomain]) {
      const domainConfig = trustedDomains[rootDomain];
      
      // Check for suspicious subdomains
      if (subdomain && !domainConfig.trustedSubdomains.includes(subdomain)) {
        // Unknown subdomain on trusted domain - requires analysis
        return { 
          riskScore: 40, 
          riskFactors: [`Untrusted subdomain '${subdomain}' on ${rootDomain}`], 
          skip: false 
        };
      }
      
      // Check for suspicious paths
      if (domainConfig.suspiciousPaths.some(suspPath => path.includes(suspPath))) {
        // Suspicious path on trusted domain - requires analysis
        return { 
          riskScore: 50, 
          riskFactors: [`Suspicious path on trusted domain ${rootDomain}`], 
          skip: false 
        };
      }
      
      // Check for legitimate paths
      if (domainConfig.legitimatePaths.some(legPath => path.startsWith(legPath)) || path === '/') {
        // Legitimate path on trusted domain - skip analysis
        return { 
          riskScore: 0, 
          riskFactors: [`Trusted domain ${rootDomain} with legitimate path`], 
          skip: true 
        };
      }
      
      // Unknown path on trusted domain - low risk but check
      return { 
        riskScore: 20, 
        riskFactors: [`Unknown path on trusted domain ${rootDomain}`], 
        skip: false 
      };
    }
    
    // Check for obviously malicious domains
    const maliciousDomains = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'short.link'];
    if (maliciousDomains.some(malicious => hostname.includes(malicious))) {
      return { riskScore: 80, riskFactors: ['URL shortener service'], skip: false };
    }
    
    // Unknown domain - requires analysis
    return { riskScore: 30, riskFactors: ['Unknown domain'], skip: false };
  }

  analyzePathRisk(parsed) {
    const { path, query } = parsed;
    const fullPath = (path + query).toLowerCase();
    
    let riskScore = 0;
    let riskFactors = [];
    
    // High-risk path patterns
    const highRiskPaths = [
      '/login', '/signin', '/auth', '/verify', '/confirm', '/validate', '/update',
      '/account', '/banking', '/paypal', '/security', '/urgent', '/suspend'
    ];
    
    // High-risk query parameters
    const highRiskParams = [
      'redirect', 'url=', 'link=', 'goto=', 'return_to=', 'continue=', 'next='
    ];
    
    // Suspicious file types
    const suspiciousFiles = ['.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.zip'];
    
    // Check for high-risk paths
    if (highRiskPaths.some(riskPath => fullPath.includes(riskPath))) {
      riskScore += 40;
      riskFactors.push('Suspicious path keywords');
    }
    
    // Check for high-risk parameters
    if (highRiskParams.some(riskParam => fullPath.includes(riskParam))) {
      riskScore += 35;
      riskFactors.push('Redirect/suspicious parameters');
    }
    
    // Check for suspicious file types
    if (suspiciousFiles.some(fileType => fullPath.includes(fileType))) {
      riskScore += 60;
      riskFactors.push('Suspicious file type');
    }
    
    // Random/suspicious path patterns
    if (/\/[a-z0-9]{8,}\//.test(fullPath) || /\/[0-9]+\.html?$/.test(fullPath)) {
      riskScore += 25;
      riskFactors.push('Random/generated path pattern');
    }
    
    return { riskScore, riskFactors };
  }

  analyzeURLStructure(url, parsed) {
    let riskScore = 0;
    let riskFactors = [];
    
    // IP address instead of domain
    if (/^https?:\/\/\d+\.\d+\.\d+\.\d+/.test(url)) {
      riskScore += 70;
      riskFactors.push('IP address instead of domain');
    }
    
    // Suspicious TLDs
    const suspiciousTlds = ['.tk', '.ml', '.ga', '.cf', '.click', '.download', '.top'];
    if (suspiciousTlds.some(tld => parsed.hostname.endsWith(tld))) {
      riskScore += 40;
      riskFactors.push('Suspicious TLD');
    }
    
    // Very long URLs
    if (url.length > 150) {
      riskScore += 25;
      riskFactors.push('Unusually long URL');
    }
    
    // Multiple subdomains
    const subdomainCount = parsed.hostname.split('.').length - 2;
    if (subdomainCount > 3) {
      riskScore += 15 * (subdomainCount - 3);
      riskFactors.push(`Many subdomains (${subdomainCount})`);
    }
    
    // Non-standard ports
    if (parsed.port && !['80', '443', '8080', '8443'].includes(parsed.port)) {
      riskScore += 30;
      riskFactors.push('Non-standard port');
    }
    
    return { riskScore, riskFactors };
  }

  calculateMLScore(url, parsed, existingFactors) {
    let riskScore = 0;
    let riskFactors = [];
    
    // Combine multiple risk factors for higher confidence
    if (existingFactors.length >= 3) {
      riskScore += 20;
      riskFactors.push('Multiple risk indicators');
    }
    
    // Domain age heuristic (newer domains are riskier)
    // This would typically use an ML model or external API
    
    // Character entropy (random-looking domains are suspicious)
    const domainEntropy = this.calculateStringEntropy(parsed.hostname);
    if (domainEntropy > 3.5) {
      riskScore += 15;
      riskFactors.push('High domain entropy (random-looking)');
    }
    
    return { riskScore, riskFactors };
  }

  calculateStringEntropy(str) {
    const freq = {};
    for (let char of str) {
      freq[char] = (freq[char] || 0) + 1;
    }
    
    let entropy = 0;
    const length = str.length;
    for (let char in freq) {
      const p = freq[char] / length;
      entropy -= p * Math.log2(p);
    }
    
    return entropy;
  }

  extractDomain(url) {
    try {
      return new URL(url).hostname;
    } catch (e) {
      return url.split('/')[2] || url;
    }
  }

  async sendToBackend(emailContent) {
    const payload = {
      email_content: `Subject: ${emailContent.subject}\nFrom: ${emailContent.sender}\n\n${emailContent.body}`,
      include_detailed_analysis: true,
      cache_results: true
    };

    const response = await fetch(`${this.ngrokUrl}/detector/analyze-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    return await response.json();
  }

  displayResult(emailElement, result, emailContent) {
    this.removeExistingBanners(emailElement);

    const isPhishing = result.is_phishing;
    const confidence = result.confidence_score / 100; // Backend returns percentage, normalize to 0-1
    
    const banner = this.createResultBanner(isPhishing, confidence, result);
    this.insertBanner(emailElement, banner);

    this.logResult(emailContent, result);
  }

  createResultBanner(isPhishing, confidence, result) {
    const bannerId = `phishy-banner-${Date.now()}`;
    const banner = document.createElement('div');
    banner.className = `phishy-banner ${isPhishing ? 'phishy-danger' : 'phishy-safe'}`;
    banner.id = bannerId;
    
    const confidencePercent = Math.round(confidence * 100);
    const status = isPhishing ? 'PHISHING DETECTED' : 'SAFE EMAIL';
    const emoji = isPhishing ? '⚠️' : '✅';
    const riskLevel = result.risk_level || '';
    
    banner.innerHTML = `
      <div class="phishy-banner-content">
        <div class="phishy-banner-header">
          <div class="phishy-status">
            ${emoji} <strong>${status} ${riskLevel ? `(${riskLevel} RISK)` : ''}</strong>
          </div>
          <div class="phishy-confidence">
            Confidence: ${confidencePercent}%
          </div>
        </div>
        ${result.recommendations && result.recommendations.length > 0 ? 
          `<div class="phishy-reasoning">
            <strong>Quick Recommendations:</strong><br>
            ${result.recommendations.slice(0, 2).join('<br>')}
          </div>` : ''}
        <div class="phishy-actions">
          <button class="phishy-detailed-btn" data-banner-id="${bannerId}">
            🔍 Detailed Analysis
          </button>
        </div>
      </div>
    `;

    // Add click event for detailed analysis
    const detailBtn = banner.querySelector('.phishy-detailed-btn');
    detailBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.showDetailedAnalysis(banner, result);
    });

    return banner;
  }

  insertBanner(emailElement, banner) {
    const insertionPoint = emailElement.querySelector('.ii.gt') || 
                          emailElement.querySelector('.a3s') || 
                          emailElement.firstElementChild;
    
    if (insertionPoint) {
      insertionPoint.parentNode.insertBefore(banner, insertionPoint);
    } else {
      emailElement.prepend(banner);
    }
  }

  showAnalyzingBanner(emailElement) {
    this.removeExistingBanners(emailElement);
    
    const banner = document.createElement('div');
    banner.className = 'phishy-banner phishy-analyzing';
    banner.innerHTML = `
      <div class="phishy-banner-content">
        <div class="phishy-status">
          🔍 <strong>ANALYZING EMAIL...</strong>
        </div>
      </div>
    `;
    
    this.insertBanner(emailElement, banner);
  }

  showConfigurationNeeded(emailElement) {
    this.removeExistingBanners(emailElement);
    
    const banner = document.createElement('div');
    banner.className = 'phishy-banner phishy-config';
    banner.innerHTML = `
      <div class="phishy-banner-content">
        <div class="phishy-status">
          ⚙️ <strong>PHISHY CONFIGURATION NEEDED</strong>
        </div>
        <div class="phishy-reasoning">
          Click the Phishy extension icon to configure your settings
        </div>
      </div>
    `;
    
    this.insertBanner(emailElement, banner);
  }

  showErrorBanner(emailElement, errorMessage) {
    this.removeExistingBanners(emailElement);
    
    const banner = document.createElement('div');
    banner.className = 'phishy-banner phishy-error';
    banner.innerHTML = `
      <div class="phishy-banner-content">
        <div class="phishy-status">
          ❌ <strong>ANALYSIS ERROR</strong>
        </div>
        <div class="phishy-reasoning">
          ${errorMessage}
        </div>
      </div>
    `;
    
    this.insertBanner(emailElement, banner);
  }

  removeExistingBanners(emailElement) {
    const existingBanners = emailElement.querySelectorAll('.phishy-banner');
    existingBanners.forEach(banner => banner.remove());
  }

  async showDetailedAnalysis(banner, result) {
    const existingModal = document.querySelector('.phishy-detailed-modal');
    if (existingModal) {
      existingModal.remove();
    }

    // Show loading state VERY briefly (just visual feedback)
    const detailBtn = banner.querySelector('.phishy-detailed-btn');
    const originalText = detailBtn.textContent;
    detailBtn.textContent = '🔄 Loading...';
    detailBtn.disabled = true;

    // Create modal immediately with ML results and loading placeholders
    const modal = this.createDetailedModalWithLoadingStates(result);
    document.body.appendChild(modal);
    
    // Animate in immediately
    setTimeout(() => modal.classList.add('phishy-modal-show'), 10);
    
    // Reset button immediately (don't wait for anything)
    setTimeout(() => {
      detailBtn.textContent = originalText;
      detailBtn.disabled = false;
    }, 200);

    // Load external API results asynchronously (fire and forget)
    this.loadExternalAPIResultsAsync(modal, result).catch(error => {
      console.error('Background API loading failed:', error);
      // Don't show error to user, just log it
    });
  }

  async getComprehensiveAnalysis(result) {
    // Get the original email content for API analysis
    const emailContent = this.lastAnalyzedContent;
    
    // Use the pre-filtered risky URLs from Chrome extension intelligence
    const topRiskyUrls = this.lastUrlAnalysis ? this.lastUrlAnalysis.topRiskyUrls : [];
    
    console.log("Detailed Analysis Debug:");
    console.log("- lastUrlAnalysis exists:", !!this.lastUrlAnalysis);
    console.log("- topRiskyUrls:", topRiskyUrls);
    console.log("- topRiskyUrls length:", topRiskyUrls.length);
    if (this.lastUrlAnalysis) {
      console.log("- URL Analysis data:", this.lastUrlAnalysis);
    }
    
    const response = await fetch(`${this.ngrokUrl}/comprehensive/detailed-analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      body: JSON.stringify({
        email_content: emailContent,
        urls: topRiskyUrls, // Send pre-filtered risky URLs
        api_only: true, // Use API-only mode to avoid duplicate URL extraction
        ml_result: {
          is_phishing: result.is_phishing,
          confidence_score: result.confidence_score,
          risk_level: result.risk_level,
          recommendations: result.recommendations
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to get comprehensive analysis: ${response.status}`);
    }

    return await response.json();
  }

  createDetailedModalWithLoadingStates(result) {
    const modal = document.createElement('div');
    modal.className = 'phishy-detailed-modal';
    
    // Use ORIGINAL ML analysis results from the initial detection
    const mlData = {
      is_phishing: result.is_phishing,
      confidence_score: result.confidence_score,
      risk_level: result.risk_level,
      analysis_details: result.analysis_details,
      recommendations: result.recommendations
    };
    
    modal.innerHTML = `
      <div class="phishy-modal-overlay">
        <div class="phishy-modal-content">
          <div class="phishy-modal-header">
            <h3>🔍 Detailed Security Analysis</h3>
            <button class="phishy-modal-close">&times;</button>
          </div>
          
          <div class="phishy-analysis-cards">
            ${this.createMLAnalysisCard(mlData)}
            ${this.createLoadingSafeBrowsingCard()}
            ${this.createLoadingURLScanCard()}
            ${this.createLoadingPathIntelligenceCard()}
            ${this.createLoadingAISummaryCard()}
          </div>
          
          <div class="phishy-modal-footer">
            <div class="phishy-timestamp">
              Analysis started: ${new Date().toLocaleString()}
            </div>
          </div>
        </div>
      </div>
    `;

    // Add close handlers
    const closeBtn = modal.querySelector('.phishy-modal-close');
    const overlay = modal.querySelector('.phishy-modal-overlay');
    
    closeBtn.addEventListener('click', () => this.closeModal(modal));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.closeModal(modal);
    });

    return modal;
  }

  async loadExternalAPIResultsAsync(modal, result) {
    try {
      // Load PathIntelligence immediately (no external API needed)
      const pathIntelligenceResult = this.loadPathIntelligenceAsync(modal);

      console.log('🔄 Starting external API calls - waiting for completion before LLM...');
      
      // Load external APIs in parallel with extended timeouts
      const [safeBrowsingResult, urlScanResult] = await Promise.allSettled([
        this.loadGoogleSafeBrowsingAsync(result),
        this.loadURLScanAsync(result)
      ]);

      console.log('✅ All external APIs completed, now preparing comprehensive data for LLM...');

      // Build complete analysis results for AI Summary
      const analysisResults = {
        ml_analysis: result,
        path_intelligence: pathIntelligenceResult
      };

      // Update Safe Browsing card and store results
      if (safeBrowsingResult.status === 'fulfilled') {
        this.updateSafeBrowsingCard(modal, safeBrowsingResult.value);
        analysisResults.safe_browsing = safeBrowsingResult.value;
        console.log('📊 Safe Browsing data ready for LLM:', safeBrowsingResult.value.status);
      } else {
        const errorResult = { 
          status: 'error', 
          message: 'Failed to load Google Safe Browsing results',
          error: safeBrowsingResult.reason?.message || 'Unknown error'
        };
        this.updateSafeBrowsingCard(modal, errorResult);
        analysisResults.safe_browsing = errorResult;
        console.log('❌ Safe Browsing failed, including error in LLM data');
      }

      // Update URLScan card and store results
      if (urlScanResult.status === 'fulfilled') {
        this.updateURLScanCard(modal, urlScanResult.value);
        analysisResults.urlscan_io = urlScanResult.value;
        console.log('📊 URLScan data ready for LLM:', urlScanResult.value.status);
      } else {
        const errorResult = { 
          status: 'error', 
          message: 'Failed to load URLScan.io results',
          error: urlScanResult.reason?.message || 'Unknown error'
        };
        this.updateURLScanCard(modal, errorResult);
        analysisResults.urlscan_io = errorResult;
        console.log('❌ URLScan failed, including error in LLM data');
      }

      // IMPORTANT: Generate AI Summary ONLY after ALL API results are available
      console.log('🤖 All security data ready - generating comprehensive LLM summary...');
      await this.generateAISummaryAsync(modal, analysisResults);

      // Update final timestamp
      const timestampEl = modal.querySelector('.phishy-timestamp');
      if (timestampEl) {
        timestampEl.textContent = `Complete analysis finished: ${new Date().toLocaleString()}`;
      }
      
      console.log('🎉 Full security analysis pipeline completed with LLM summary');

    } catch (error) {
      console.error('Error in analysis pipeline:', error);
    }
  }

  loadPathIntelligenceAsync(modal) {
    try {
      // Generate path intelligence data from already-analyzed URLs
      const pathData = this.combineAPIWithPathIntelligence({}, this.lastUrlAnalysis);
      this.updatePathIntelligenceCard(modal, pathData);
      return pathData; // Return for AI summary
    } catch (error) {
      console.error('Error loading path intelligence:', error);
      const errorData = { 
        hasPathThreats: false,
        pathWarnings: [],
        error: 'Failed to analyze URL patterns'
      };
      this.updatePathIntelligenceCard(modal, errorData);
      return errorData;
    }
  }

  updatePathIntelligenceCard(modal, pathData) {
    const cardElement = modal.querySelector('.phishy-pathintelligence-card');
    if (!cardElement) return;

    // Replace the loading card with the actual results
    cardElement.outerHTML = this.createPathIntelligenceCard(pathData);
  }

  async generateAISummaryAsync(modal, analysisResults) {
    try {
      console.log('🤖 Starting AI security summary generation...');
      console.log('📊 Analysis data being sent to LLM:', JSON.stringify({
        ml_phishing: analysisResults.ml_analysis?.is_phishing,
        ml_confidence: analysisResults.ml_analysis?.confidence_score,
        safe_browsing_status: analysisResults.safe_browsing?.status,
        urlscan_status: analysisResults.urlscan_io?.status,
        path_threats: analysisResults.path_intelligence?.hasPathThreats,
        path_warnings_count: analysisResults.path_intelligence?.pathWarnings?.length
      }, null, 2));
      
      // Check if LLM service is available first
      console.log('🔍 Checking LLM service availability...');
      await this.checkLLMServiceStatus();
      
      // Prepare comprehensive data for LLM
      const summaryData = await this.callLocalLLMForSummary(modal, analysisResults);
      
      console.log('✅ LLM returned summary data:', summaryData);
      this.updateAISummaryCard(modal, summaryData);
      
    } catch (error) {
      console.error('❌ AI Summary generation failed:', error);
      console.error('❌ Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      
      // Provide specific error guidance based on error type
      let keyFindings = [];
      let recommendations = [];
      
      if (error.message.includes('ngrok URL returning HTML')) {
        keyFindings = [
          'ngrok tunnel is returning HTML instead of API responses',
          'This usually means ngrok is not properly forwarding to the backend',
          'Backend is running but not accessible through the tunnel'
        ];
        recommendations = [
          'Check if ngrok is running: ngrok http 8080',
          'Verify ngrok URL in extension settings',
          `Test ngrok health: ${this.ngrokUrl}/health`,
          'Restart ngrok tunnel if needed'
        ];
      } else if (error.message.includes('Cannot connect to backend')) {
        keyFindings = [
          'Unable to establish connection to backend through ngrok',
          'Network connectivity issue or backend not running',
          'ngrok tunnel may be inactive'
        ];
        recommendations = [
          'Ensure backend is running on port 8080',
          'Start/restart ngrok tunnel: ngrok http 8080',
          'Update ngrok URL in extension settings',
          'Check firewall/network restrictions'
        ];
      } else {
        keyFindings = [
          'Local LLM service (Ollama) may not be running',
          'Check backend logs for detailed error information',
          'Verify Ollama is installed and phi3:mini model is available'
        ];
        recommendations = [
          'Start Ollama service with: ollama serve',
          'Install model with: ollama pull phi3:mini',
          'Check backend server logs',
          'Review individual security analysis cards above for assessment'
        ];
      }
      
      // Show detailed error in card for debugging
      this.updateAISummaryCard(modal, {
        summary: `AI Summary service unavailable. ${error.message}`,
        overall_risk_level: 'UNKNOWN',
        key_findings: keyFindings,
        recommendations: recommendations
      });
    }
  }

  async checkLLMServiceStatus() {
    try {
      const response = await fetch(`${this.ngrokUrl}/llm/health`, {
        method: 'GET',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (!response.ok) {
        throw new Error(`LLM health check failed: ${response.status}`);
      }

      const health = await response.json();
      console.log('✅ LLM service status:', health);
      
      if (!health.ollama_service || !health.ollama_service.service_available) {
        throw new Error('Ollama service is not available');
      }
      
      return health;
    } catch (error) {
      console.error('❌ LLM service check failed:', error);
      
      let errorMessage = `LLM service unavailable: ${error.message}`;
      
      // Provide specific guidance based on error type
      if (error.message.includes('<!DOCTYPE') || error.message.includes('Unexpected token')) {
        errorMessage = `ngrok URL returning HTML instead of API response. Please check:
        1. Is ngrok running? Run: ngrok http 8080
        2. Is the ngrok URL correct in extension settings?
        3. Does the URL work: ${this.ngrokUrl}/health`;
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMessage = `Cannot connect to backend through ngrok. Please check:
        1. Is ngrok tunnel active?
        2. Is backend running on port 8080?
        3. Is the ngrok URL correct: ${this.ngrokUrl}`;
      }
      
      throw new Error(errorMessage);
    }
  }

  async callLocalLLMForSummary(modal, analysisResults) {
    // Prepare structured prompt for the local LLM
    const prompt = this.buildLLMPrompt(analysisResults);
    
    console.log('🤖 Calling local LLM for comprehensive security explanation...');
    
    // Show progress indicator in the AI Summary card
    const aiCard = modal.querySelector('.phishy-ai-summary-card');
    if (aiCard) {
      const statusEl = aiCard.querySelector('.phishy-card-status');
      if (statusEl) {
        statusEl.textContent = '🤖 AI analyzing security data... (may take 30-60 seconds)';
      }
    }
    
    // Shorter timeout for ngrok requests - ngrok free tier has limitations
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.error('⏰ LLM generation timed out after 60 seconds (ngrok timeout)');
      controller.abort();
    }, 60000); // 1 minute - ngrok free tier timeout limit
    
    try {
      // Validate ngrok URL is working before making LLM request
      console.log('🔍 Validating backend connection to:', `${this.ngrokUrl}/health`);
      try {
        const healthCheck = await fetch(`${this.ngrokUrl}/health`, {
          method: 'GET',
          timeout: 5000,
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        
        if (!healthCheck.ok) {
          throw new Error(`Backend health check failed: ${healthCheck.status} ${healthCheck.statusText}`);
        }
        
        const healthData = await healthCheck.json();
        console.log('✅ Backend health confirmed:', healthData.status);
      } catch (healthError) {
        console.error('❌ Backend health check failed:', healthError.message);
        throw new Error(`Backend unreachable via ngrok URL ${this.ngrokUrl}. Please check ngrok is running and URL is correct.`);
      }
      
      console.log('📡 Sending request to LLM endpoint:', `${this.ngrokUrl}/llm/explain-security-analysis`);
      console.log('📊 Request payload size:', JSON.stringify({
        analysis_results: analysisResults,
        email_content: this.lastAnalyzedContent,
        user_id: this.userEmail
      }).length, 'characters');
      
      const response = await fetch(`${this.ngrokUrl}/llm/explain-security-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          analysis_results: analysisResults,
          email_content: this.lastAnalyzedContent,
          prompt: prompt,
          user_id: this.userEmail
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      console.log('📡 LLM API response status:', response.status, response.statusText);

      if (!response.ok) {
        // Try to get error details from response
        let errorDetails = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorBody = await response.text();
          console.error('❌ LLM API error response:', errorBody);
          errorDetails = errorBody || errorDetails;
        } catch (e) {
          console.error('❌ Could not read error response:', e);
        }
        throw new Error(`LLM API failed: ${errorDetails}`);
      }

      const result = await response.json();
      console.log('✅ LLM generated comprehensive security explanation');
      console.log('📋 LLM response structure:', Object.keys(result));
      return result;
      
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        // Generate a simple summary from the analysis data instead of full LLM
        console.warn('⏰ LLM timed out due to ngrok limitations - providing quick summary from analysis data');
        return this.generateQuickSummaryFromData(analysisResults);
      }
      console.error('❌ LLM call failed with error:', error);
      throw error;
    }
  }

  generateQuickSummaryFromData(analysisResults) {
    // Generate a structured summary from analysis data when LLM times out
    const mlData = analysisResults.ml_analysis || {};
    const safeBrowsingData = analysisResults.safe_browsing || {};
    const urlScanData = analysisResults.urlscan_io || {};
    const pathData = analysisResults.path_intelligence || {};
    
    // Determine overall risk level based on analysis results
    let overallRisk = 'LOW';
    let summary = '';
    let keyFindings = [];
    let recommendations = [];
    
    // ML Analysis assessment
    if (mlData.is_phishing && mlData.confidence_score > 80) {
      overallRisk = 'CRITICAL';
      summary = 'This email has been identified as a phishing attempt with high confidence by our machine learning model.';
      keyFindings.push(`ML model detected phishing with ${mlData.confidence_score}% confidence`);
      recommendations.push('Do not click any links or download attachments from this email');
      recommendations.push('Report this email to your IT security team immediately');
    } else if (mlData.is_phishing && mlData.confidence_score > 50) {
      overallRisk = 'HIGH';
      summary = 'This email shows suspicious characteristics that suggest it may be a phishing attempt.';
      keyFindings.push(`ML model flagged potential phishing (${mlData.confidence_score}% confidence)`);
      recommendations.push('Exercise extreme caution with links and attachments');
    } else {
      summary = 'This email appears to be legitimate based on machine learning analysis.';
      keyFindings.push('ML analysis suggests this is not a phishing email');
    }
    
    // Path Intelligence assessment
    if (pathData.hasPathThreats && pathData.pathWarnings && pathData.pathWarnings.length > 0) {
      if (overallRisk === 'LOW') overallRisk = 'MEDIUM';
      if (overallRisk === 'MEDIUM' && pathData.pathWarnings.length >= 2) overallRisk = 'HIGH';
      
      keyFindings.push(`Advanced pattern analysis detected ${pathData.pathWarnings.length} suspicious URL patterns`);
      keyFindings.push('URLs may use evasion techniques not caught by traditional security services');
      recommendations.push('Be extra cautious with cloud storage links from unknown sources');
    }
    
    // API Status assessment
    const apiClean = (safeBrowsingData.status === 'clean' || safeBrowsingData.status === 'success') && 
                     (urlScanData.status === 'clean' || urlScanData.malicious_score === 0);
    
    if (apiClean && (overallRisk === 'HIGH' || overallRisk === 'CRITICAL')) {
      keyFindings.push('Traditional security APIs report clean, but advanced analysis suggests threats');
      summary += ' This email may use sophisticated evasion techniques that bypass standard security filters.';
    }
    
    // Ensure we have recommendations
    if (recommendations.length === 0) {
      recommendations = [
        'Verify sender identity before taking any action',
        'Be cautious with unexpected emails requesting sensitive information',
        'When in doubt, contact your IT security team'
      ];
    }
    
    return {
      summary: summary,
      overall_risk_level: overallRisk,
      key_findings: keyFindings,
      recommendations: recommendations,
      note: 'Quick analysis generated due to network timeout - full AI analysis unavailable'
    };
  }

  buildLLMPrompt(analysisResults) {
    return `You are an expert cybersecurity analyst providing clear explanations to end users. 

Analyze these comprehensive security results and provide an explainable AI summary:

ML ANALYSIS: ${JSON.stringify(analysisResults.ml_analysis, null, 2)}
SAFE BROWSING: ${JSON.stringify(analysisResults.safe_browsing, null, 2)}  
URLSCAN.IO: ${JSON.stringify(analysisResults.urlscan_io, null, 2)}
PATH INTELLIGENCE: ${JSON.stringify(analysisResults.path_intelligence, null, 2)}

Provide a response in this exact JSON format:
{
  "summary": "2-3 sentence plain English explanation of what this email is and the main security concerns",
  "overall_risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "key_findings": ["bullet point list of 2-4 specific security issues found"],
  "recommendations": ["bullet point list of 2-4 specific actions the user should take"]
}

Focus on:
1. Explaining WHY different security tools gave different results (if they disagree)
2. What specific attack techniques are being used
3. Clear, actionable advice for the end user
4. Highlight any sophisticated evasion techniques (like cloud storage abuse)

Keep language simple and avoid technical jargon. Be direct about the risk level.`;
  }

  updateAISummaryCard(modal, summaryData) {
    const cardElement = modal.querySelector('.phishy-aisummary-card');
    if (!cardElement) return;

    // Replace the loading card with the actual AI summary
    cardElement.outerHTML = this.createAISummaryCard(summaryData);
  }

  removeAISummaryCard(modal) {
    const cardElement = modal.querySelector('.phishy-aisummary-card');
    if (cardElement) {
      cardElement.remove();
      console.log('🗑️ AI Summary card removed due to LLM unavailability');
    }
  }

  createMLAnalysisCard(mlData) {
    const riskLevel = mlData.risk_level || 'UNKNOWN';
    const confidence = mlData.confidence_score || 0;
    const isPhishing = mlData.is_phishing;
    
    return `
      <div class="phishy-analysis-card phishy-ml-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🤖</div>
          <h4>ML Phishing Detection</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-prediction">
            <div class="phishy-prediction-result ${isPhishing ? 'phishing' : 'safe'}">
              ${isPhishing ? '⚠️ PHISHING DETECTED' : '✅ SAFE EMAIL'}
            </div>
            <div class="phishy-confidence-meter">
              <div class="phishy-confidence-bar">
                <div class="phishy-confidence-fill" style="width: ${confidence}%"></div>
              </div>
              <span class="phishy-confidence-text">${confidence}% Confidence</span>
            </div>
          </div>
          <div class="phishy-risk-level">
            Risk Level: <span class="phishy-risk-badge ${riskLevel.toLowerCase()}">${riskLevel}</span>
          </div>
          <div class="phishy-analysis-method">
            Method: ${mlData.analysis_details?.analysis_method || 'XGBoost ML Model'}
          </div>
          ${mlData.recommendations ? `
            <div class="phishy-recommendations">
              <strong>AI Recommendations:</strong>
              <ul>
                ${mlData.recommendations.map(rec => `<li>${rec}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  createSafeBrowsingCard(safeBrowsingData) {
    const status = safeBrowsingData.status || 'unavailable';
    const isClean = status === 'clean';
    const isThreat = status === 'threat';
    
    return `
      <div class="phishy-analysis-card phishy-safebrowsing-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🛡️</div>
          <h4>Google Safe Browsing</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-prediction">
            <div class="phishy-prediction-result ${isThreat ? 'phishing' : isClean ? 'safe' : 'unknown'}">
              ${isThreat ? '⚠️ THREAT DETECTED' : isClean ? '✅ CLEAN' : '❓ UNAVAILABLE'}
            </div>
          </div>
          ${safeBrowsingData.threats ? `
            <div class="phishy-threats">
              <strong>Detected Threats:</strong>
              <ul>
                ${safeBrowsingData.threats.map(threat => `
                  <li>${threat.threatType}: ${threat.platformType}</li>
                `).join('')}
              </ul>
            </div>
          ` : ''}
          ${safeBrowsingData.message ? `
            <div class="phishy-status-message">
              ${safeBrowsingData.message}
            </div>
          ` : ''}
          <div class="phishy-analysis-method">
            Google's URL reputation database
          </div>
        </div>
      </div>
    `;
  }

  createLoadingSafeBrowsingCard() {
    return `
      <div class="phishy-analysis-card phishy-safebrowsing-card phishy-loading-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🛡️</div>
          <h4>Google Safe Browsing</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-loading-state">
            <div class="phishy-loading-spinner"></div>
            <div class="phishy-loading-text">Checking URLs against Google's threat database...</div>
          </div>
          <div class="phishy-analysis-method">
            Google's URL reputation database
          </div>
        </div>
      </div>
    `;
  }

  createLoadingURLScanCard() {
    return `
      <div class="phishy-analysis-card phishy-urlscan-card phishy-loading-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🌐</div>
          <h4>URLScan.io Analysis</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-loading-state">
            <div class="phishy-loading-spinner"></div>
            <div class="phishy-loading-text">Scanning URLs with multiple security engines...</div>
          </div>
          <div class="phishy-analysis-method">
            Real-time URL scanning & reputation
          </div>
        </div>
      </div>
    `;
  }

  createLoadingPathIntelligenceCard() {
    return `
      <div class="phishy-analysis-card phishy-pathintelligence-card phishy-loading-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🧠</div>
          <h4>Path Intelligence Analysis</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-loading-state">
            <div class="phishy-loading-spinner"></div>
            <div class="phishy-loading-text">Analyzing URL patterns and path structures...</div>
          </div>
          <div class="phishy-analysis-method">
            Advanced pattern recognition for suspicious URLs
          </div>
        </div>
      </div>
    `;
  }

  createPathIntelligenceCard(pathData) {
    const hasThreats = pathData.hasPathThreats || false;
    const pathWarnings = pathData.pathWarnings || [];
    const urlsAnalyzed = this.lastUrlAnalysis?.filteredUrls?.length || 0;
    
    return `
      <div class="phishy-analysis-card phishy-pathintelligence-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🧠</div>
          <h4>Path Intelligence Analysis</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-prediction">
            <div class="phishy-prediction-result ${hasThreats ? 'warning' : 'safe'}">
              ${hasThreats ? '⚠️ SUSPICIOUS PATTERNS DETECTED' : '✅ NO SUSPICIOUS PATTERNS'}
            </div>
            <div class="phishy-urls-analyzed">
              Analyzed ${urlsAnalyzed} URLs with smart tiered analysis
            </div>
          </div>
          
          ${pathWarnings.length > 0 ? `
            <div class="phishy-path-warnings">
              <div class="phishy-section-header">
                <strong>Detected Suspicious Patterns:</strong>
              </div>
              ${pathWarnings.map(warning => `
                <div class="phishy-path-warning-item">
                  <div class="phishy-warning-url">
                    ${this.truncateUrl(warning.url, 40)}
                    <span class="phishy-tier-badge ${warning.tier?.toLowerCase()}">${warning.tier} RISK</span>
                  </div>
                  <div class="phishy-warning-score">Risk Score: ${warning.score}/100</div>
                  <div class="phishy-warning-factors">
                    ${warning.factors.map(factor => `<span class="phishy-factor-tag">${factor}</span>`).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
            
            <div class="phishy-path-recommendation">
              <strong>⚠️ Analysis:</strong> These URLs show patterns that external security APIs may not detect. 
              Exercise caution with unusual subdomains, suspicious paths, and cloud storage links from untrusted sources.
            </div>
          ` : `
            <div class="phishy-clean-result">
              <div class="phishy-clean-message">
                All detected URLs appear to follow normal patterns and structures.
              </div>
            </div>
          `}
          
          <div class="phishy-analysis-method">
            Advanced pattern recognition for suspicious URLs
          </div>
        </div>
      </div>
    `;
  }

  createLoadingAISummaryCard() {
    return `
      <div class="phishy-analysis-card phishy-aisummary-card phishy-loading-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🤖</div>
          <h4>AI Security Summary</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-loading-state">
            <div class="phishy-loading-spinner"></div>
            <div class="phishy-loading-text">Generating explainable AI summary...</div>
          </div>
          <div class="phishy-analysis-method">
            Combining all security analysis results with local LLM
          </div>
        </div>
      </div>
    `;
  }

  createAISummaryCard(summaryData) {
    const summary = summaryData.summary || 'Analysis summary unavailable';
    const riskLevel = summaryData.overall_risk_level || 'UNKNOWN';
    const keyFindings = summaryData.key_findings || [];
    const recommendations = summaryData.recommendations || [];
    
    return `
      <div class="phishy-analysis-card phishy-aisummary-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🤖</div>
          <h4>AI Security Summary</h4>
        </div>
        <div class="phishy-card-content">
          <div class="phishy-prediction">
            <div class="phishy-prediction-result ${riskLevel.toLowerCase()}">
              Overall Assessment: ${riskLevel} RISK
            </div>
          </div>
          
          <div class="phishy-ai-summary">
            <div class="phishy-summary-text">
              ${summary}
            </div>
          </div>
          
          ${keyFindings.length > 0 ? `
            <div class="phishy-key-findings">
              <div class="phishy-section-header">
                <strong>🔍 Key Findings:</strong>
              </div>
              <ul class="phishy-findings-list">
                ${keyFindings.map(finding => `<li>${finding}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
          
          ${recommendations.length > 0 ? `
            <div class="phishy-ai-recommendations">
              <div class="phishy-section-header">
                <strong>💡 What to Watch For:</strong>
              </div>
              <ul class="phishy-recommendations-list">
                ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
          
          <div class="phishy-analysis-method">
            Explainable AI combining ML, API, and pattern analysis
          </div>
        </div>
      </div>
    `;
  }

  async loadGoogleSafeBrowsingAsync(result) {
    try {
      // Use the pre-filtered risky URLs from Chrome extension intelligence
      const topRiskyUrls = this.lastUrlAnalysis ? this.lastUrlAnalysis.topRiskyUrls : [];
      
      console.log("loadGoogleSafeBrowsingAsync Debug:");
      console.log("- Using filtered risky URLs:", topRiskyUrls);
      console.log("- NOT using all URLs:", this.lastFoundUrls?.length || 0);
      
      // Extended timeout for thorough Safe Browsing API analysis
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000); // 90 seconds
      
      const response = await fetch(`${this.ngrokUrl}/comprehensive/safe-browsing`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          email_content: this.lastAnalyzedContent,
          urls: topRiskyUrls // Send the pre-filtered risky URLs instead of all URLs
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        console.error('Google Safe Browsing API timed out');
        return { status: 'error', message: 'Request timed out' };
      }
      console.error('Google Safe Browsing API failed:', error);
      return { status: 'error', message: error.message };
    }
  }

  async loadURLScanAsync(result) {
    try {
      // Use the pre-filtered risky URLs from Chrome extension intelligence
      const topRiskyUrls = this.lastUrlAnalysis ? this.lastUrlAnalysis.topRiskyUrls : [];
      
      console.log("loadURLScanAsync Debug:");
      console.log("- Using filtered risky URLs:", topRiskyUrls);
      console.log("- NOT using all URLs:", this.lastFoundUrls?.length || 0);
      
      // Extended timeout for comprehensive URLScan analysis
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 seconds (2 minutes)
      
      const response = await fetch(`${this.ngrokUrl}/comprehensive/urlscan`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          email_content: this.lastAnalyzedContent,
          urls: topRiskyUrls // Send the pre-filtered risky URLs instead of all URLs
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        console.error('URLScan.io API timed out');
        return { status: 'error', message: 'URLScan.io request timed out - scanning multiple URLs can take time', urls_found: this.lastFoundUrls?.length || 0, urls_scanned: 0 };
      }
      console.error('URLScan.io API failed:', error);
      return { status: 'error', message: error.message, urls_found: this.lastFoundUrls?.length || 0, urls_scanned: 0 };
    }
  }

  updateSafeBrowsingCard(modal, data) {
    const card = modal.querySelector('.phishy-safebrowsing-card');
    if (!card) return;

    card.classList.remove('phishy-loading-card');
    card.innerHTML = `
      <div class="phishy-card-header">
        <div class="phishy-card-icon">🛡️</div>
        <h4>Google Safe Browsing</h4>
      </div>
      <div class="phishy-card-content">
        ${this.createSafeBrowsingCardContent(data)}
      </div>
    `;
  }

  updateURLScanCard(modal, data) {
    const card = modal.querySelector('.phishy-urlscan-card');
    if (!card) return;

    card.classList.remove('phishy-loading-card');
    
    card.innerHTML = `
      <div class="phishy-card-header">
        <div class="phishy-card-icon">🌐</div>
        <h4>URLScan.io Analysis</h4>
      </div>
      <div class="phishy-card-content">
        ${this.createURLScanCardContent(data)}
      </div>
    `;
  }


  truncateUrl(url, maxLength = 60) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
  }

  createSafeBrowsingCardContent(safeBrowsingData) {
    const status = safeBrowsingData.status || 'unavailable';
    const isClean = status === 'clean';
    const isThreat = status === 'threat';
    const isError = status === 'error';
    const urlsFound = safeBrowsingData.urls_found || 0;
    const urlsChecked = safeBrowsingData.urls_checked || 0;
    
    return `
      <div class="phishy-prediction">
        <div class="phishy-prediction-result ${isThreat ? 'phishing' : isClean ? 'safe' : 'unknown'}">
          ${isThreat ? '⚠️ THREAT DETECTED' : isClean ? '✅ CLEAN' : isError ? '❌ ERROR' : '❓ UNAVAILABLE'}
        </div>
        ${(urlsFound > 0 || urlsChecked > 0) ? `
          <div class="phishy-url-stats">
            <div class="phishy-url-count">
              📊 URLs Found: <strong>${urlsFound}</strong> | Checked: <strong>${urlsChecked}</strong>
            </div>
          </div>
        ` : ''}
      </div>
      ${safeBrowsingData.threats && safeBrowsingData.threats.length > 0 ? `
        <div class="phishy-threats">
          <strong>Detected Threats:</strong>
          <ul>
            ${safeBrowsingData.threats.map(threat => `
              <li>${threat.threatType}: ${threat.platformType}</li>
            `).join('')}
          </ul>
        </div>
      ` : ''}
      ${safeBrowsingData.message ? `
        <div class="phishy-status-message">
          ${safeBrowsingData.message}
        </div>
      ` : ''}
      <div class="phishy-analysis-method">
        Google's URL reputation database
      </div>
    `;
  }

  createURLScanCardContent(urlScanData) {
    const status = urlScanData.status || 'unavailable';
    const score = urlScanData.verdicts?.overall?.score || 0;
    const malicious = urlScanData.verdicts?.overall?.malicious || false;
    const isError = status === 'error';
    const urlsFound = urlScanData.urls_found || 0;
    const urlsScanned = urlScanData.urls_scanned || 0;
    
    return `
      <div class="phishy-prediction">
        <div class="phishy-prediction-result ${malicious ? 'phishing' : score === -1 || isError ? 'unknown' : 'safe'}">
          ${malicious ? '⚠️ MALICIOUS' : score === -1 || isError ? (isError ? '❌ ERROR' : '❓ UNAVAILABLE') : '✅ CLEAN'}
        </div>
        ${score > -1 && !isError ? `
          <div class="phishy-urlscan-score">
            Malicious Score: <span class="phishy-score">${score}/100</span>
          </div>
        ` : ''}
        <div class="phishy-url-stats">
          <div class="phishy-url-count">
            📊 URLs Found: <strong>${urlsFound}</strong> | Scanned: <strong>${urlsScanned}</strong>
          </div>
        </div>
      </div>
      ${urlScanData.scanned_urls && urlScanData.scanned_urls.length > 0 ? `
        <div class="phishy-scanned-urls">
          <strong>Scanned URLs:</strong>
          <div class="phishy-url-list">
            ${urlScanData.scanned_urls.map(urlData => `
              <div class="phishy-url-item">
                <div class="phishy-url-text">${urlData.url}</div>
                <div class="phishy-url-score ${urlData.score >= 50 ? 'dangerous' : 'safe'}">
                  ${urlData.score}/100
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
      ${urlScanData.verdicts?.engines ? `
        <div class="phishy-engines">
          <strong>Security Engine Results:</strong>
          <div class="phishy-engine-grid">
            ${Object.entries(urlScanData.verdicts.engines).map(([engine, result]) => `
              <div class="phishy-engine-result">
                <span class="phishy-engine-name">${engine}</span>
                <span class="phishy-engine-verdict ${result.malicious ? 'malicious' : 'clean'}">
                  ${result.malicious ? '⚠️' : '✅'}
                </span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
      ${urlScanData.message ? `
        <div class="phishy-status-message">
          ${urlScanData.message}
        </div>
      ` : ''}
      <div class="phishy-analysis-method">
        Real-time URL scanning & reputation analysis
      </div>
      ${urlScanData.scan_url && urlScanData.scan_url !== '#' ? `
        <div class="phishy-external-link">
          <a href="${urlScanData.scan_url}" target="_blank" rel="noopener">
            View Full Report ↗
          </a>
        </div>
      ` : ''}
    `;
  }

  createURLScanCard(urlScanData) {
    const status = urlScanData.status || 'unavailable';
    const score = urlScanData.verdicts?.overall?.score || 0;
    const malicious = urlScanData.verdicts?.overall?.malicious || false;
    
    return `
      <div class="phishy-analysis-card phishy-urlscan-card">
        <div class="phishy-card-header">
          <div class="phishy-card-icon">🌐</div>
          <h4>URLScan.io Analysis</h4>
        </div>
        <div class="phishy-card-content">
          ${this.createURLScanCardContent(urlScanData)}
        </div>
      </div>
    `;
  }

  closeModal(modal) {
    modal.classList.remove('phishy-modal-show');
    setTimeout(() => modal.remove(), 300);
  }

  showErrorModal(message) {
    const modal = document.createElement('div');
    modal.className = 'phishy-error-modal';
    modal.innerHTML = `
      <div class="phishy-modal-overlay">
        <div class="phishy-modal-content phishy-error-content">
          <div class="phishy-modal-header">
            <h3>❌ Error</h3>
            <button class="phishy-modal-close">&times;</button>
          </div>
          <div class="phishy-error-message">${message}</div>
        </div>
      </div>
    `;

    const closeBtn = modal.querySelector('.phishy-modal-close');
    closeBtn.addEventListener('click', () => this.closeModal(modal));
    
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('phishy-modal-show'), 10);
  }

  logResult(emailContent, result) {
    console.log('Phishy Analysis Result:', {
      subject: emailContent.subject,
      sender: emailContent.sender,
      result: result,
      timestamp: new Date().toISOString()
    });
  }
}

if (window.location.hostname === 'mail.google.com') {
  let phishyDetector;
  
  const initPhishy = () => {
    if (!phishyDetector) {
      phishyDetector = new PhishyDetector();
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPhishy);
  } else {
    initPhishy();
  }

  chrome.storage.onChanged.addListener((changes) => {
    if (changes.ngrokUrl || changes.userEmail) {
      if (phishyDetector) {
        phishyDetector.loadSettings();
      }
    }
  });
}