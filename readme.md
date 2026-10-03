# 🛡️ ThreatLens

### AI-Powered Multi-Signal Email Security & Phishing Awareness Platform

> **ThreatLens** helps users detect, analyze, and understand suspicious emails using multiple security signals and AI-powered explanations.

---

## 👥 Team Kaizen

**Team Name:** Team Kaizen

### Team Members

- **Khumbham Manicharan**
- **Govindula Srikar**
- **Dumpala Akshaya**

---
Demo Link :https://threatlens89.netlify.app/
<img width="1892" height="877" alt="image" src="https://github.com/user-attachments/assets/6b589579-02f3-4eda-844b-fbcad1b54e35" />

<img width="1917" height="881" alt="image" src="https://github.com/user-attachments/assets/3e1bb771-8149-4a00-a458-cd351ec295ff" />

<img width="1907" height="881" alt="image" src="https://github.com/user-attachments/assets/4bc2e0b8-ef83-4afe-842d-beaa14a94ee1" />
<img width="1917" height="875" alt="image" src="https://github.com/user-attachments/assets/1d4b9d8a-cb56-42ca-a9f9-266bff9070e0" />

<img width="1917" height="888" alt="image" src="https://github.com/user-attachments/assets/2d6f0f14-e155-4581-84cd-2b6b60a306d8" />

## 🚀 About the Project

ThreatLens is a cybersecurity platform designed to analyze suspicious emails using multiple security signals instead of relying on a simple phishing/not-phishing classification.

The platform combines machine learning, URL reputation, sender and IP analysis, email authentication checks, attachment analysis, and AI-generated explanations to provide a clearer understanding of email security risks.

---

## ✨ Key Features
# 🛡️ ThreatLens — AI-Powered Phishing Detection & Security Awareness Platform

ThreatLens is an AI-powered email security and phishing awareness platform designed to detect suspicious emails, URLs, domains, senders, IP addresses, and attachments while providing understandable security explanations and awareness training.

The platform combines **AI/ML detection, threat intelligence, email analysis, phishing simulations, security analytics, and user awareness** into a single security platform.

---

# 🚀 Feature Levels

ThreatLens features are organized into three levels:

- 🟢 **Level 0 — Foundation & Basic Security**
- 🟡 **Level 1 — Intelligent Detection & Analysis**
- 🔴 **Level 2 — Advanced AI, Automation & Phishing Awareness**

---

# 🟢 Level 0 — Foundation & Basic Security

Level 0 provides the basic platform infrastructure required to operate ThreatLens.

## 1. 🌐 Web-Based Security Platform

- ThreatLens web interface
- Responsive security dashboard
- Security-focused user interface
- Landing page and application navigation
- Security reports and analytics interface

## 2. 🔐 User Registration & Login

- User registration
- User login
- Demo authentication flow
- User account management foundation
- Secure authentication architecture

## 3. 💾 SQLite Database

- Local SQLite database support
- User information storage
- Security analysis data storage
- Detection history storage
- Application data persistence

## 4. ⚡ FastAPI Backend

- FastAPI-based backend
- REST API architecture
- API endpoints for security analysis
- Request validation
- Backend service orchestration

## 5. 📧 Email Input & Analysis Interface

Users can submit suspicious email information for analysis.

Supported information includes:

- Email content
- Email headers
- Sender information
- URLs contained in emails
- Attachments
- Suspicious indicators

## 6. 📊 Security Dashboard

The dashboard provides an overview of security activity.

Example metrics include:

- Emails analyzed
- Phishing detections
- User awareness score
- Active campaigns
- Detection history
- Security analytics

## 7. 📋 Security Reports

Generate understandable security reports containing:

- Threat classification
- Risk score
- Suspicious indicators
- Detection results
- Recommended security actions

---

# 🟡 Level 1 — Intelligent Detection & Analysis

Level 1 introduces automated security analysis and multiple detection signals.

## 1. 🔍 Multi-Signal Email Analysis

ThreatLens analyzes multiple security signals instead of relying on a single detection method.

Signals include:

- Email content
- Email headers
- Sender information
- URLs
- Domains
- IP addresses
- Attachments
- Reputation information

Combining multiple signals improves the ability to identify suspicious emails.

---

## 2. 📧 Sender & Email Header Analysis

Analyze email sender information and headers for suspicious indicators.

Analysis can include:

- Sender identity
- Sender domain
- Email routing information
- SPF indicators
- DKIM indicators
- DMARC indicators
- Header inconsistencies
- Suspicious sender patterns
- Possible spoofing indicators

---

## 3. 🌐 URL Analysis

Analyze URLs contained inside suspicious emails.

Detection can include:

- Suspicious URLs
- Malicious links
- Redirects
- URL reputation
- Domain reputation
- Typosquatting indicators
- Suspicious domain structures
- Phishing URLs

---

## 4. 🌍 Domain Reputation Analysis

Evaluate domains associated with suspicious messages.

Possible signals include:

- Domain reputation
- Suspicious domains
- Newly observed domains
- Domain similarity
- Typosquatting
- Reputation intelligence

---

## 5. 🖥️ IP Reputation Analysis

Analyze IP addresses associated with email infrastructure.

Possible analysis includes:

- IP reputation
- Threat intelligence
- Suspicious IP indicators
- Geographic information
- Known malicious infrastructure

---

## 6. 📎 Attachment Safety Analysis

Analyze email attachments for potentially dangerous content.

Supported security concepts include:

- Suspicious file detection
- File type analysis
- Malware indicators
- Risky attachment detection
- Suspicious attachment behavior

---

## 7. 🧠 Machine Learning Risk Scoring

Machine learning can be used to evaluate security indicators and produce a risk score.

Example:

```text
Risk Score: 85 / 100

Classification: HIGH RISK

Indicators:
✓ Suspicious URL
✓ Sender domain spoofing
✓ Suspicious attachment
✓ Credential theft indicators

---

## 🧠 How It Works

```text
                User
                 │
                 ▼
          ThreatLens Web UI
                 │
                 ▼
             FastAPI
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
      ML       Security     AI
   Analysis     Signals   Analysis
       │         │         │
       └─────────┼─────────┘
                 ▼
          Risk Assessment
                 │
                 ▼
       Explainable Security
              Report
