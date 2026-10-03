# Phishy Platform - Visual Walkthrough

This document provides a comprehensive visual tour of all Phishy platform features with detailed screenshots and explanations.

---

## Table of Contents

1. [Chat Interface](#chat-interface)
2. [AI Email Generator](#ai-email-generator)
3. [Email Analyzer](#email-analyzer)
4. [Overview Dashboard](#overview-dashboard)
5. [Analytics Reports](#analytics-reports)
6. [Email Tracking](#email-tracking)
7. [Activity Logs](#activity-logs)
8. [Risk Assessment](#risk-assessment)
9. [Chrome Extension](#chrome-extension)
10. [Detailed Security Analysis](#detailed-security-analysis)

---

## Chat Interface

![Chat Interface](docs/screenshots/chat-interface.png)

### Overview
The **Phishy AI Chat Interface** provides conversational access to security analytics through natural language queries. This intelligent interface allows security teams to quickly get insights without navigating complex dashboards.

### Features Shown
- **Real-time Security Status**: Current metrics including total click events (10), monitored users (4), and recent activity (9 in last 24h)
- **Risk Level Indicator**: Current risk level displayed as HIGH with assessment details
- **Natural Language Queries**: Users can ask questions like "what are click trends" to get instant analytics
- **Platform Health**: Shows "Platform Healthy • 10 modules" status at bottom
- **Navigation Menu**: Complete sidebar with all platform sections (AI Tools, Analytics & Insights, System Management)

### Use Case
Security administrators can quickly check campaign effectiveness, user vulnerability patterns, and risk trends through simple conversational queries instead of manual dashboard navigation.

---

## AI Email Generator

### Setup & Configuration

![Email Generator Setup](docs/screenshots/email-generator-setup.png)

### Overview
The **Email Generator** creates realistic phishing simulations for security awareness training using AI-powered content generation.

### Features Shown
- **Target Email Input**: Add recipient emails (supports multiple recipients)
- **Scenario Selection**: Pre-defined phishing scenarios like "account security"
- **Sender Customization**: Optional sender name field (e.g., "IT security team")
- **Tracking Options**: 1x1 tracking pixel checkbox for email open monitoring
- **Email Preview**: Generated subject line "Immediate Action Required for Enhanced Account Security at Abc Corporation"
- **Content Preview**: AI-generated phishing email content with realistic social engineering tactics

### Available Scenarios
- Account Security Alerts
- Payment Requests
- Package Delivery Notifications
- IT Support Requests
- Urgent Password Resets
- Prize/Reward Claims

---

### SMTP Configuration & Sending

![Email Generator SMTP](docs/screenshots/email-generator-smtp.png)

### Overview
Configure email delivery through SMTP with auto-detected server settings based on email provider.

### Features Shown
- **Your Email**: Sender email address (cyberphishytesting@gmail.com)
- **App Password**: Secure app password authentication (masked)
- **Auto-Detection**: SMTP server automatically detected from email domain
- **Action Buttons**:
  - **Send Email**: Dispatch to 1 recipient
  - **Test SMTP Connection**: Verify settings before sending
  - **Preview Campaign**: Review email before deployment

### Supported Email Providers
- Gmail (smtp.gmail.com:587)
- Outlook/Hotmail (smtp.office365.com:587)
- Yahoo Mail (smtp.mail.yahoo.com:587)
- AOL Mail (smtp.aol.com:587)
- ProtonMail Bridge
- Zoho Mail

### Security Note
Platform requires app-specific passwords (not regular account passwords) for enhanced security, especially for Gmail accounts with 2FA enabled.

---

## Email Analyzer

![Email Analyzer](docs/screenshots/email-analyzer.png)

### Overview
The **Email Analyzer** provides real-time phishing analysis using multi-signal detection powered by AI and machine learning.

### Features Shown
- **Content Input**: Large text area for pasting suspicious email content (headers, body, links)
- **Analyze Email Button**: Triggers comprehensive analysis
- **Clear Button**: Reset the analyzer

### How to Use the Email Analyzer
1. **Copy & Paste**: Copy entire suspicious email content including headers
2. **Include Headers**: Add From, To, Subject lines for better analysis
3. **Real-time Analysis**: Get instant results with confidence scores and risk levels
4. **Smart Detection**: AI detects URLs, social engineering, urgency tactics, and more
5. **Security Recommendations**: Receive specific actions to take based on analysis

### Detection Capabilities
- ML-based phishing classification
- URL reputation checking (Google Safe Browsing, URLScan.io)
- Sender IP reputation (AbuseIPDB)
- Header authentication (SPF, DKIM, DMARC)
- Social engineering pattern detection
- Urgency and pressure tactic identification
- Attachment safety analysis

### Pro Tip
The analyzer can also be accessed through the chat interface by pasting email content directly - Phishy will automatically detect and analyze it.

---

## Overview Dashboard

![Overview Dashboard](docs/screenshots/overview-dashboard.png)

### Overview
The **Analytics Dashboard** provides a comprehensive view of phishing campaign performance, user engagement, and security metrics.

### Key Metrics Displayed

#### Summary Cards
- **Total Clicks**: 10 clicks (9 in last 24h)
- **Unique Users**: 4 users (9 in last 7d)
- **Average Risk**: 25.0 (Low Risk indicator)
- **Training Success**: 50.0% (50.0% secure)
- **Total Email Opens**: 2 opens (2 unique openers)
- **Open Rate**: 50.0% (Good engagement)

#### Click Activity Over Time
- Time-series graph showing click trends from 7:00 to 14:00
- Steady increase in clicks visualized with line chart
- Helps identify peak vulnerability times

#### User Click Summary
Individual user breakdown with risk assessment:
- **risky.user@company.com**: 6 clicks • 0 opens • HIGH risk
- **test.user@company.com**: 2 clicks • 0 opens • LOW risk
- **thomasraisen122@gmail.com**: 1 click • 1 opens • LOW risk

### Use Case
Security teams can quickly assess campaign effectiveness, identify high-risk users requiring immediate training, and track engagement patterns over time.

---

## Analytics Reports

### Executive Summary

![Analytics Report 1](docs/screenshots/analytics-report-1.png)

### Overview
**Phishing Campaign Analytics Reports** provide executive-level summaries with key findings and risk assessments.

### Report Details
- **Generated**: 12/28/2025
- **Analysis Period**: Last 7 Days
- **Platform**: Phishy AI Platform

### Executive Summary Content
Analyzes phishing campaign activity targeting unique users over the monitoring period. Identifies total click events, flagged emails, and threat levels within the monitored environment.

### Key Metrics
- **Total Security Events**: 10
- **Users Monitored**: 4 individuals
- **Click Events**: 10 total interactions
- **Flagged Emails**: 0 suspicious messages identified
- **Recent Activity**: 9 events in the last 24 hours
- **Average Engagement**: 2.5 clicks per user

### Risk Assessment
Current risk level displayed as **HIGH** based on recent activity patterns. The organization shows a 0.0% flag-to-click ratio, indicating need for improvement in security awareness among users. Most active users requiring attention are identified (risky.user, test.user, thomasraisen122).

---

### Actionable Recommendations

![Analytics Report 2](docs/screenshots/analytics-report-2.png)

### Overview
Recommendations are categorized by timeline to provide clear action plans for security teams.

### Immediate Actions (0-30 days)
- **IMMEDIATE ACTION REQUIRED**: Conduct urgent security training for high-activity users
- Review and strengthen email security filters
- Focus on repeat-offender training programs
- Investigate recent activity patterns for potential threats
- Schedule weekly security awareness updates
- Enhance user reporting training programs

### Analysis Note
This analysis provides data-driven insights based on 134 days of monitoring data, enabling targeted security improvements.

### Risk Assessment Summary
- **Risk Level**: High
- **Training Priority**: 4 users require immediate attention

---

### High-Risk User Identification

![Analytics Report 3](docs/screenshots/analytics-report-3.png)

### Overview
Detailed breakdown of users demonstrating high susceptibility to phishing attempts.

### High-Risk Users Table

| Employee Email | Click Count | Risk Level | Recommended Action |
|----------------|-------------|------------|-------------------|
| risky.user@company.com | 6 | HIGH | Immediate 1-on-1 training |
| test.user@company.com | 2 | MEDIUM | Group training session |
| thomasraisen122@gmail.com | 1 | LOW | Standard awareness reminder |
| another.user@company.com | 1 | LOW | Standard awareness reminder |

### Strategic Recommendations

#### Immediate Actions (0-30 days)
- Schedule mandatory security training for high-risk users
- Implement email security reminders during peak hours (14:00 - 15:00)
- Deploy additional phishing simulations to test improvement

#### Medium-term Goals (1-3 months)
- Develop personalized training modules based on click patterns
- Establish monthly security awareness sessions
- Create gamified security training programs

#### Long-term Strategy (3+ months)
- Implement advanced email filtering and AI detection
- Establish security champion program
- Quarterly security posture assessments

---

### Key Performance Metrics

![Analytics Report 4](docs/screenshots/analytics-report-4.png)

### Overview
Comprehensive performance metrics showing campaign effectiveness and engagement rates.

### Metrics Breakdown

#### Campaign Metrics
- **Total Phishing Clicks**: 10 (Campaign interactions)
- **Unique Users Engaged**: 4 (Individual participants)
- **Recent Activity (7d)**: 9 (Weekly engagement)
- **Engagement Rate**: 225% (Click-through percentage)

### Report Information

#### Report Details
- **Report Type**: Detailed Security Analysis
- **Data Source**: Phishy AI Cybersecurity Platform
- **Analysis Period**: Last 7 Days
- **Report Generation**: 12/28/2025 via AI Analytics

#### Confidentiality Notice
⚠️ **CONFIDENTIAL**: This report contains sensitive security information and should be distributed only to authorized personnel.

---

## Email Tracking

![Email Tracking](docs/screenshots/email-tracking.png)

### Overview
The **Email Tracking** dashboard monitors email open events, helping measure campaign reach and user engagement.

### Key Metrics

#### Summary Cards
- **Total Opens**: 2 (2 total)
- **Unique Users**: 2 users (2 users)
- **Open Rate**: 0% (Active)
- **Recent Opens**: 0 (0 today)

### Email Open Activity Over Time
Time-series visualization showing email open patterns throughout the day:
- X-axis: Time (0:00 to 23:00)
- Y-axis: Open activity (0.0 to 1.0)
- Two distinct peaks visible around 5:00 and 7:00

### Users Who Opened Emails

Individual tracking data:
- **test@example.com**
  - 1 opens
  - Last: 8/21/2025, 4:14:45 AM

- **thomasraisen122@gmail.com**
  - 1 opens
  - Last: 8/16/2025, 7:35:06 AM

### Use Case
Security teams can correlate email opens with click events to understand user engagement patterns and identify the most effective times for security awareness campaigns.

### Tracking Mechanism
Uses 1x1 invisible tracking pixels embedded in emails (enabled during email generation) to detect when recipients open training emails.

---

## Activity Logs

![Activity Logs](docs/screenshots/activity-logs.png)

### Overview
**Activity Logs** provide detailed audit trails of all user interactions with phishing simulations.

### Summary Metrics
- **Total Clicks**: 10 (10 total)
- **Unique Users**: 4 (4 unique)
- **Unique IPs**: 2 (2 sources)
- **Last 24h**: 0 (Last 24h)

### Filters & Controls

#### Filter Options
- **Filter by User Email**: Search specific user activities (e.g., user@example.com)
- **Filter by Action ID**: Search by campaign identifier (e.g., action123)
- **Time Period**: Filter by date range (All time, Last 24h, Last 7d, Last 30d)

#### Action Buttons
- **Apply Filters**: Execute filter search
- **Clear Filters**: Reset all filters
- **Refresh**: Update data
- **Download CSV**: Export logs for analysis
- **Clear All Logs**: Remove all activity data (with confirmation)

### Activity Logs Data Table

Columns displayed:
- **Timestamp**: Exact date/time of interaction
- **User Email**: Recipient who clicked
- **Action ID**: Campaign identifier
- **IP Address**: Source IP of click
- **User Agent**: Browser/device information
- **Referer**: Source of navigation

#### Sample Log Entries

| Timestamp | User Email | Action ID | IP Address | User Agent | Referer |
|-----------|------------|-----------|------------|------------|---------|
| 8/16/2025, 10:34:54 AM | xxxxxxxxx@gmail.com | phish-ec55fc3f | 103.xxx.xxx.xxx | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb... | direct |
| 12/28/2025, 5:01:40 PM | test.user@company.com | campaign-001 | 127.0.0.1 | curl/8.12.1 | direct |
| 12/28/2025, 5:01:41 PM | test.user@company.com | campaign-001 | 127.0.0.1 | curl/8.12.1 | direct |
| 12/28/2025, 5:01:43 PM | another.user@company.com | campaign-002 | 127.0.0.1 | curl/8.12.1 | direct |

### Use Case
- **Forensic Analysis**: Investigate suspicious activity patterns
- **Compliance**: Maintain audit trails for security compliance
- **Behavioral Analysis**: Identify patterns in user clicks (time, frequency, device)
- **Campaign Tracking**: Monitor specific campaign performance by Action ID

---

## Risk Assessment

### Overall Risk Scoring

![Risk Assessment 1](docs/screenshots/risk-assessment-1.png)

### Overview
The **Risk Assessment** module calculates comprehensive security posture based on user behavior, engagement patterns, and activity trends.

### Overall Metrics

#### Primary Indicators
- **Overall Risk Score**: 95/100 (CRITICAL Risk)
- **High-Risk Users**: 1 (Requires attention)
- **Risk Trend**: INCREASING (Activity surge detected)
- **Training Priority**: IMMEDIATE (High-risk users need urgent attention)

### Risk Breakdown by Category

#### User Behavior Risk: 25%
- 1 high-risk user out of 4 total
- Indicates 25% of users demonstrate concerning click patterns

#### Engagement Risk: 100%
- 100% of users have clicked on simulations
- Shows universal susceptibility to phishing attempts

#### Frequency Risk: 50%
- Average 2.5 clicks per active user
- Moderate repeat-offender rate

#### Recent Activity Risk: 85%
- Recent activity surge detected
- Indicates increasing vulnerability or active campaign

### Interpretation
A **95/100 CRITICAL** risk score indicates severe organizational vulnerability to phishing attacks. Immediate intervention required for high-risk users, with comprehensive training needed across all user groups.

---

### Individual User Risk Profiles

![Risk Assessment 2](docs/screenshots/risk-assessment-2.png)

### Overview
Personalized risk assessments for each monitored user with tailored training recommendations.

### User Risk Cards

#### 1. risky.user (HIGH RISK)
- **Email**: risky.user@company.com
- **Risk Level**: HIGH RISK (Red badge)
- **Click Count**: 6 clicks
- **Recommendation**: Immediate training needed
- **Priority**: Highest priority for 1-on-1 security training

#### 2. test.user (MEDIUM RISK)
- **Email**: test.user@company.com
- **Risk Level**: MEDIUM RISK (Orange badge)
- **Click Count**: 2 clicks
- **Recommendation**: Schedule training session
- **Priority**: Group training suitable

#### 3. thomasraisen122 (LOW RISK)
- **Email**: thomasraisen122@gmail.com
- **Risk Level**: LOW RISK (Green badge)
- **Click Count**: 1 click
- **Recommendation**: Standard monitoring
- **Priority**: Standard awareness reminder sufficient

#### 4. another.user (LOW RISK)
- **Email**: another.user@company.com
- **Risk Level**: LOW RISK (Green badge)
- **Click Count**: 1 click
- **Recommendation**: Standard monitoring
- **Priority**: Standard awareness reminder sufficient

### Use Case
Security teams can prioritize training resources by focusing on high-risk individuals while maintaining awareness programs for lower-risk users.

---

### Security Risk Assessment Report

![Risk Assessment 3](docs/screenshots/risk-assessment-3.png)

### Overview
Downloadable security report with prioritized action items and timelines.

### Report Actions

- **Refresh Assessment**: Recalculate risk scores with latest data
- **Download Report**: Export PDF report for management review

### Recommended Actions

#### 1. Schedule immediate one-on-one security training (HIGH Priority)
- **Description**: 1 users have clicked 3+ phishing simulations
- **Timeline**: Within 24 hours
- **Priority Level**: HIGH (Red indicator)

#### 2. Investigate recent activity surge (HIGH Priority)
- **Description**: Unusual spike in phishing simulation clicks detected
- **Timeline**: Immediate
- **Priority Level**: HIGH (Red indicator)

#### 3. Organize group security awareness training (MEDIUM Priority)
- **Description**: 1 users showing moderate risk patterns
- **Timeline**: Within 1 week
- **Priority Level**: MEDIUM (Orange indicator)

#### 4. Review email security filters (Additional)
- **Description**: High engagement rate may indicate security gaps
- **Timeline**: Ongoing
- **Priority Level**: Standard

### Report Format
The downloadable report includes all risk assessments, user profiles, recommended actions with timelines, and compliance documentation suitable for management review and regulatory requirements.

---

## Chrome Extension

### Configuration Popup

![Chrome Extension Popup](docs/screenshots/chrome-extension-popup.png)

### Overview
The **Phishy Chrome Extension** integrates phishing detection directly into Gmail, providing real-time security analysis as users read their emails.

### Extension Popup Configuration

#### Setup Fields
- **Your Email Address**: User's Gmail address for improved detection accuracy
  - Example: abd@gmail.com
  - Helps the AI understand legitimate sender patterns

- **Phishy Backend URL**: ngrok tunnel URL for the Phishy backend
  - Example: https://fb9f247dcc4c.ngrok-free.app
  - Your ngrok tunnel URL for the Phishy backend
  - Must be HTTPS URL (no trailing slash)

#### Action Buttons
- **Save Settings**: Store configuration in Chrome storage
- **Test Connection**: Verify backend connectivity before use

### How it Works
1. Automatically scans emails when you open them in Gmail
2. Sends email content to Phishy backend for analysis
3. Displays inline security warnings directly in Gmail
4. Shows detailed multi-signal analysis results

### Requirements
- Phishy backend must be running (localhost:8080)
- ngrok tunnel active for external access
- Chrome browser with Developer Mode enabled
- Extension loaded from `chrome-extension/` folder

### Privacy Note
The extension only analyzes emails you actively open and sends data to your own Phishy backend instance, not third-party servers.

---

### Gmail Integration & Detection

![Chrome Extension Detection](docs/screenshots/chrome-extension-detection.png)

### Overview
Real-time phishing detection displayed directly in Gmail inbox with visual risk indicators.

### Detection Banner

#### Alert Display
- **Status**: "PHISHING DETECTED (HIGH RISK)"
- **Color Coding**: Red background for HIGH RISK threats
- **ML Confidence**: 83% confidence score
- **Analysis Summary**:
  - Smart Analysis: 43 URLs found, 3 trusted • API: 31 • Path#1: 0
  - Analysis complete
  - Phi AI: 8 suspicious patterns

### Quick Recommendations
Visual warnings with actionable items:
- ⚠️ DO NOT click any links or download attachments
- 📧 Report this email to your IT security team

### Email Context
The banner appears inline in Gmail between the sender information and email content, providing immediate context without disrupting the reading experience.

### Visual Indicators
- Red banner: HIGH RISK / CRITICAL
- Orange banner: MEDIUM RISK
- Yellow banner: LOW RISK / Suspicious
- Green banner: SAFE / Clean

### Detailed Analysis Access
Clicking on the banner or "Detailed Analysis" button opens a comprehensive modal with:
- ML phishing detection scores
- URL reputation checks
- Pattern intelligence analysis
- AI security summary

---

## Detailed Security Analysis

### Multi-Signal Detection Overview

![Detailed Analysis 1](docs/screenshots/detailed-analysis-1.png)

### Overview
**Detailed Security Analysis Modal** provides comprehensive breakdowns of all security signals analyzed for an email.

### Analysis Components

#### 1. ML Phishing Detection
- **Status**: ⚠️ PHISHING DETECTED
- **Confidence**: 82.5%
- **Risk Level**: HIGH
- **Method**: rule_based

**AI Recommendations**:
- 🚨 DO NOT click any links or download attachments
- 📧 Report this email to your IT security team
- 🗑️ Delete this email immediately
- ⚠️ Verify any URLs independently before visiting
- 🔒 Never provide personal information via email

#### 2. Google Safe Browsing
- **Status**: ✅ CLEAN
- **URLs Found**: 2 | Checked: 2
- **Details**: Checked 2 URLs with Google Safe Browsing
- **Database**: Google's URL reputation database

#### 3. URLScan.io Analysis
- **Status**: ✅ CLEAN
- **Malicious Score**: 0/100 (Continued in next screenshot)

#### 4. Path Intelligence Analysis
- **Status**: ⚠️ SUSPICIOUS PATTERNS DETECTED
- **URLs Analyzed**: 40 URLs with smart tiered analysis
- **Details**: (Visible in next screenshot)

### Modal Features
- **Close Button**: X in top right corner
- **Scrollable Content**: View all analysis sections
- **Real-time Results**: Analysis completes in seconds
- **Color-Coded Sections**: Easy visual scanning

---

### URL Security Analysis

![Detailed Analysis 2](docs/screenshots/detailed-analysis-2.png)

### Overview
Detailed URL reputation analysis from multiple security engines.

### URLScan.io Analysis (Continued)

#### Malicious Score
- **Score**: 0/100 (Clean)
- **URLs Found**: 31 | Scanned: 2

#### Scanned URLs
- `https://link.cnbc.com/click/42791016.224928/aH...` → 0/100
- `https://link.cnbc.com/click/42791016.224928/aH...` → 0/100

#### Security Engine Results
All engines returned clean results:
- ✅ URLVoid
- ✅ Phishtank
- ✅ OpenPhish
- ✅ Malware Domain List

**Status Message**: URLScan.io analysis completed - 2 URLs successfully scanned

**Note**: Real-time URL scanning & reputation analysis

---

### Path Intelligence Analysis

#### Suspicious Patterns Detected
**Analysis**: Analyzed 40 URLs with smart tiered analysis

#### Detected Suspicious Patterns
Multiple instances of random/generated path patterns detected with CRITICAL RISK level:

1. `https://link.cnbc.com/click/42791016.224...`
   - Risk Score: 100/100
   - Pattern: Random/generated path pattern

2. `https://link.cnbc.com/click/42791016.224...`
   - Risk Score: 100/100
   - Pattern: Random/generated path pattern

3. `https://link.cnbc.com/click/42791016.224...`
   - Risk Score: 100/100
   - Pattern: Random/generated path pattern

4. `https://link.cnbc.com/click/42791016.224...`
   - Risk Score: 100/100
   - Pattern: Random/generated path pattern

5. `https://link.cnbc.com/click/42791016.224...`
   - Risk Score: 100/100
   - Pattern: Random/generated path pattern

**Detection Methodology**: Phishy's Path Intelligence identifies obfuscated URLs, random path generation, and evasion techniques used by advanced phishing campaigns.

---

### AI Security Summary

![Detailed Analysis 3](docs/screenshots/detailed-analysis-3.png)

### Overview
Explainable AI analysis providing human-readable reasoning for the security assessment.

### AI Security Summary

#### Overall Assessment
**CRITICAL RISK**

This email is a phishing attempt using malicious links to steal personal information, employing sophisticated tactics like random path patterns for evasion.

### Key Findings

#### 1. High-Confidence Phishing Attack
- Phishing attack with high confidence score of over 80%
- Critical threat tier due to malicious links in attachments
- Designed to trick users into providing personal information

#### 2. Advanced Evasion Techniques
- Use of random path patterns for URLs
- Sign of advanced evasion techniques
- Aims to avoid detection by simple heuristic analysis tools like SafeURLs or SlimURL

#### 3. No Known Malware Payloads
- The phishing email does not contain any known malware payloads
- Designed with high-tier threats that could lead to credential theft

#### 4. Abuse of Legitimate Services
- Abuse of legitimate services such as cloud storage for hosting links
- May evade detection by SafeBrowsing

### What to Watch For

- **Do not click on any suspicious links or...**

### Intelligence Source
Powered by **Phi-3 Mini LLM** (Ollama) providing explainable AI reasoning that helps users understand *why* an email is dangerous, not just that it is.

### Use Case
The AI summary translates technical security findings into clear, actionable insights that non-technical users can understand and act upon.

---

## Platform Navigation

### Main Sections

#### Chat Interface
- Conversational AI analytics
- Natural language security queries
- Real-time metrics and insights

#### AI Tools
- **Email Generator**: Create phishing simulations
- **Email Analyzer**: Analyze suspicious emails

#### Analytics & Insights
- **Overview Dashboard**: Campaign performance metrics
- **Email Tracking**: Open rate monitoring
- **Activity Logs**: Detailed audit trails
- **Risk Assessment**: User vulnerability scoring

#### System Management
- **System Health**: Platform status monitoring
- **Flagged Emails**: Suspicious message review

---

## Getting Started

### Platform Access
1. Start Phishy backend: `python backend/app.py`
2. Start frontend: `python -m http.server 3001` in frontend/
3. Access web interface: `http://localhost:3001`

### Chrome Extension Setup
1. Start ngrok: `ngrok http 8080`
2. Load extension in Chrome (Developer Mode)
3. Configure with Gmail address and ngrok URL
4. Test connection
5. Open Gmail and view inline security analysis

### Creating Your First Campaign
1. Navigate to **Email Generator**
2. Add target email(s)
3. Select phishing scenario
4. Generate and review content
5. Configure SMTP settings
6. Send campaign
7. Monitor results in **Overview Dashboard**

### Analyzing Emails
1. Navigate to **Email Analyzer**
2. Paste suspicious email content
3. Click **Analyze Email**
4. Review multi-signal results
5. Follow security recommendations

---

## Best Practices

### Campaign Management
- Start with small test groups
- Use realistic scenarios relevant to your organization
- Monitor results in real-time
- Provide immediate feedback to users who click

### Training Programs
- Focus on high-risk users first
- Combine simulations with educational content
- Track improvement over time
- Celebrate security awareness victories

### Security Analysis
- Always verify URLs independently
- Check sender authentication headers
- Be suspicious of urgency tactics
- Report suspicious emails to IT security

---

## Platform Support

For detailed setup instructions, API documentation, and troubleshooting, refer to the main [README.md](README.md).

**Platform Version**: Phishy 1.0
**Last Updated**: December 2025
**Documentation**: Comprehensive visual walkthrough with 19 platform screenshots
