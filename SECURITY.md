# Security Policy

## 🔒 Security Overview

Phishy is a cybersecurity training platform designed with security in mind. This document outlines security considerations, best practices, and vulnerability reporting procedures.

---

## 🛡️ Security Features

### Multi-Signal Analysis Architecture

Phishy doesn't rely on binary classification. Instead, it:
- Evaluates emails across **6+ security dimensions**
- Provides **explainable risk assessments**
- Uses **multiple independent data sources**
- Implements **defense in depth** principles

### Authentication & Authorization

- **No user authentication by design** - Training platform focused on email analysis
- **API key management** for external services (URLScan.io, AbuseIPDB, Google Safe Browsing)
- **Environment-based configuration** - Secrets stored in `.env` files (not in code)
- **SMTP app passwords** - No regular passwords stored

### Data Protection

- **PII Handling**: Click logs contain email addresses and IP addresses
  - NOT committed to version control (see `.gitignore`)
  - Encrypted in transit
  - Should be anonymized for production use
- **Sensitive Data** excluded from git:
  - `.env` files
  - `click_logs.csv`
  - Log files
  - Any files containing API keys or credentials

### CORS Configuration

**Environment-Based CORS Security:**

```python
# Development Mode (DEBUG=True)
- Wildcard CORS enabled (*)
- Required for ngrok and Chrome extension
- Shows warning in logs

# Production Mode (DEBUG=False)
- Restricted CORS only
- Explicit origin whitelist required
- API documentation disabled
```

**Production Setup:**
```env
DEBUG=False
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### API Security

- **Rate Limiting**: ⚠️ Not implemented - should be added for production
- **Input Validation**: Pydantic models for all inputs
- **No SQL Injection**: No SQL database used (CSV-based logging)
- **XSS Prevention**: Content-Type headers properly set
- **HTTPS Required**: For production deployment and Chrome extension

---

## ⚠️ Known Limitations

### 1. **No Built-in Rate Limiting**
**Risk**: API endpoints can be abused
**Mitigation**:
- Deploy behind reverse proxy (nginx, Cloudflare)
- Implement rate limiting at infrastructure level
- Consider adding `slowapi` or FastAPI rate limiting middleware

### 2. **Debug Mode Enabled by Default**
**Risk**: API documentation exposed, verbose error messages
**Mitigation**:
```env
DEBUG=False  # For production
```

### 3. **Click Logs Contain PII**
**Risk**: GDPR/CCPA compliance issues
**Mitigation**:
- Anonymize IP addresses (hash or truncate)
- Implement data retention policies
- Provide opt-out mechanisms
- Consider using UUID instead of email addresses

### 4. **No Authentication**
**Risk**: Anyone with URL can access API
**Mitigation**:
- Deploy in controlled environment
- Use firewall rules
- Add API key authentication if needed
- VPN for production deployments

### 5. **External API Dependencies**
**Risk**: Third-party service failures or compromise
**Mitigation**:
- Graceful degradation (works without external APIs)
- API key rotation policies
- Monitor API usage
- Validate all external responses

---

## 🔐 Deployment Security Checklist

### Before Production Deployment

- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure `ALLOWED_ORIGINS` with specific domains
- [ ] Review and anonymize click logs
- [ ] Remove or rotate any test API keys
- [ ] Enable HTTPS (required)
- [ ] Implement rate limiting (nginx, Cloudflare, WAF)
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Review SMTP credentials security
- [ ] Implement monitoring and alerting
- [ ] Add security headers:
  - `Strict-Transport-Security`
  - `X-Content-Type-Options`
  - `X-Frame-Options`
  - `Content-Security-Policy`
- [ ] Conduct penetration testing
- [ ] Review data retention policies
- [ ] Ensure GDPR/CCPA compliance
- [ ] Document incident response procedures

### Recommended nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🔍 Security Best Practices

### For Developers

1. **Never commit secrets**
   - Use `.env` files
   - Review changes before committing
   - Use `git diff` before push

2. **Validate all inputs**
   - Use Pydantic models
   - Sanitize user-provided data
   - Validate email formats

3. **Handle errors securely**
   - Don't expose stack traces in production
   - Log errors without sensitive data
   - Use generic error messages for users

4. **Keep dependencies updated**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

5. **Review third-party integrations**
   - Validate API responses
   - Handle failures gracefully
   - Monitor API usage

### For Administrators

1. **Protect API keys**
   - Rotate regularly
   - Use read-only keys where possible
   - Monitor usage

2. **Secure the server**
   - Keep OS updated
   - Use firewall
   - Disable unnecessary services
   - Use non-root user

3. **Monitor logs**
   - Regular log reviews
   - Set up alerts for anomalies
   - Implement SIEM if available

4. **Backup data**
   - Regular backups of click logs
   - Test restore procedures
   - Secure backup storage

5. **Incident response**
   - Document procedures
   - Have rollback plan
   - Contact information ready

---

## 🐛 Vulnerability Reporting

### Reporting a Security Issue

If you discover a security vulnerability, please report it responsibly:

**DO NOT** create a public GitHub issue for security vulnerabilities.

**Instead:**
1. Email: [Your contact email - UPDATE THIS]
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **24 hours**: Initial acknowledgment
- **7 days**: Preliminary assessment
- **30 days**: Fix and disclosure (if valid)

### Security Hall of Fame

We appreciate responsible disclosure. Contributors will be acknowledged here (with permission).

---

## 📋 Compliance Considerations

### GDPR (European Union)

**PII Collected:**
- Email addresses (click tracking)
- IP addresses (click tracking)
- User agent strings (click tracking)

**Requirements:**
- [ ] Legal basis for processing (legitimate interest for training)
- [ ] Data minimization (collect only necessary data)
- [ ] Purpose limitation (only for training analytics)
- [ ] Storage limitation (implement retention policies)
- [ ] Right to erasure (implement deletion mechanisms)
- [ ] Data portability (export functionality)
- [ ] Privacy by design (anonymization options)

### CCPA (California)

**Consumer Rights:**
- [ ] Right to know (disclose data collected)
- [ ] Right to delete (implement deletion)
- [ ] Right to opt-out (provide opt-out mechanism)
- [ ] Non-discrimination (no penalties for opt-out)

### Data Retention

**Recommended Policies:**
- Click logs: 90 days maximum
- Email content: Not stored
- API logs: 30 days
- Training data: Anonymized indefinitely

---

## 🔄 Security Update Policy

### Dependency Updates

- Monthly security patch reviews
- Critical vulnerabilities: Immediate patching
- Regular `pip audit` checks

### Security Advisories

Subscribe to security advisories for:
- FastAPI
- Uvicorn
- All ML/AI dependencies
- Python security announcements

---

## 📚 Security Resources

### Recommended Reading

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

### Tools

- `pip-audit` - Scan for vulnerable dependencies
- `bandit` - Python security linter
- `safety` - Check dependencies for known vulnerabilities
- `gitleaks` - Scan git history for secrets

### Running Security Scans

```bash
# Install security tools
pip install pip-audit bandit safety

# Scan for vulnerable dependencies
pip-audit

# Security linting
bandit -r backend/

# Check dependencies
safety check

# Scan git history for secrets
# Install: https://github.com/gitleaks/gitleaks
gitleaks detect --source . --verbose
```

---

## ✅ Security Certifications

This platform was developed as part of a Master's in Cybersecurity application, demonstrating:

- ✓ Secure coding practices
- ✓ Defense in depth architecture
- ✓ Multi-signal security analysis
- ✓ Privacy-conscious design
- ✓ Explainable AI for security decisions
- ✓ Comprehensive documentation

---

## 📞 Contact

For security-related questions:
- **GitHub Issues**: [Report here](https://github.com/rachuzzzz/Phishy/issues) (non-sensitive only)
- **Security Email**: cyberphishytesting@gmail.com
- **Project**: [Phishy on GitHub](https://github.com/rachuzzzz/Phishy)

---

**Last Updated**: December 2025
**Version**: 2.1.0
