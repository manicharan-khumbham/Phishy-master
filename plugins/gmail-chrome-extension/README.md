# Phishy AI - Gmail Chrome Extension

🛡️ AI-powered email security for Gmail. Flag suspicious emails instantly and get real-time threat analysis.

## Features

- **One-Click Flagging**: Flag suspicious emails directly from Gmail interface
- **Real-time AI Analysis**: Get instant threat assessment with confidence scores
- **WebSocket Integration**: Real-time updates and notifications
- **Ngrok Support**: Seamlessly works with ngrok tunneled servers
- **Auto-Configuration**: QR code setup and automatic tunnel URL updates
- **Threat Intelligence**: Visual indicators for suspicious emails
- **Security Dashboard**: Access your security analytics from the extension

## Installation

### From Source (Development)

1. **Download the Extension**
   ```bash
   # Clone or download the Phishy AI repository
   git clone <repository-url>
   cd phishy/plugins/gmail-chrome-extension
   ```

2. **Load in Chrome**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (top right toggle)
   - Click "Load unpacked"
   - Select the `gmail-chrome-extension` folder

3. **Configure Extension**
   - Click the Phishy AI extension icon in your toolbar
   - Enter your Phishy AI server URL (e.g., `https://abc123.ngrok.io`)
   - Enter your email address
   - Click "Save Configuration"

### Quick Setup with QR Code

1. Start Phishy AI with ngrok:
   ```bash
   python start_with_plugins.py --auto-restart
   ```

2. Open the setup URL shown in the console
3. Scan the QR code with your phone or copy the configuration URL
4. Import settings into the Chrome extension

## Usage

### Flagging Emails

1. **Open any email in Gmail**
2. **Look for the "🚩 Flag Suspicious" button** in the email toolbar
3. **Click the button** and select:
   - Flag category (phishing, spam, malware, etc.)
   - Confidence level
   - Additional notes (optional)
4. **Submit** to get instant AI analysis

### Automatic Detection

The extension automatically:
- Scans new emails for suspicious indicators
- Highlights potentially dangerous emails with warning badges
- Provides real-time threat scores
- Connects to Phishy AI for advanced analysis

### Settings Management

Click the extension icon to:
- View connection status
- Update server URL
- Check flagging statistics
- Enable/disable protection
- Access security dashboard

## Configuration

### Required Settings

| Setting | Description | Example |
|---------|-------------|---------|
| Server URL | Your Phishy AI server endpoint | `https://abc123.ngrok.io` |
| User Email | Your email address for identification | `user@company.com` |
| Enable Protection | Turn on/off email scanning | `true` |

### Advanced Options

- **Auto-Reconnect**: Automatically reconnect when server restarts
- **Real-time Updates**: Receive live notifications about threats
- **Tunnel Sync**: Automatically update when ngrok URL changes

## Ngrok Integration

This extension is optimized for ngrok tunneling:

### Automatic URL Updates
- WebSocket connection detects tunnel changes
- Configuration updates automatically
- No manual reconfiguration needed

### SSL Certificate Handling
- Bypasses SSL verification for ngrok development tunnels
- Works with both free and paid ngrok accounts
- Supports custom subdomains

### Connection Management
- Auto-reconnect on tunnel restart
- Graceful handling of connection limits
- Fallback to polling if WebSocket fails

## API Endpoints

The extension communicates with these Phishy AI endpoints:

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/email-flagging/health` | Connection testing | GET |
| `/email-flagging/flag` | Flag suspicious emails | POST |
| `/email-flagging/stats` | Get flagging statistics | GET |
| `/email-flagging/ws/{plugin_id}` | WebSocket connection | WS |

## Security Features

### Data Protection
- No email content stored locally
- Encrypted communication with server
- Minimal data collection
- User-controlled data sharing

### Privacy Controls
- Optional email body analysis
- Configurable threat detection sensitivity
- User consent for data processing
- Local-first operation when possible

## Troubleshooting

### Common Issues

**Connection Failed**
- Verify Phishy AI server is running
- Check ngrok tunnel is active
- Ensure URL is correct and accessible
- Test connection using extension popup

**Flag Button Not Appearing**
- Refresh Gmail page
- Check if extension is enabled
- Verify permissions are granted
- Try disabling other Gmail extensions

**WebSocket Connection Issues**
- Check server logs for errors
- Verify ngrok WebSocket support
- Try refreshing the extension
- Check browser console for errors

### Debug Mode

Enable debug logging:
1. Open Chrome DevTools (F12)
2. Go to Console tab
3. Look for Phishy AI messages
4. Check Network tab for API calls

### Reset Extension

To completely reset:
1. Click extension icon
2. Click "Clear Configuration"
3. Reload Gmail page
4. Reconfigure with new settings

## Development

### Building from Source

```bash
# Install dependencies (if any)
npm install

# The extension is ready to load as-is
# No build process required for basic functionality
```

### File Structure

```
gmail-chrome-extension/
├── manifest.json          # Extension manifest
├── phishy-gmail.js        # Main content script
├── phishy-styles.css      # Extension styles
├── popup.html             # Settings popup
├── popup.js              # Popup functionality
├── background.js         # Background service worker
├── icons/                # Extension icons
└── README.md            # This file
```

### Adding Features

1. **Content Script**: Modify `phishy-gmail.js` for Gmail integration
2. **Background Tasks**: Update `background.js` for service worker features
3. **UI Changes**: Edit `popup.html` and `popup.js` for settings
4. **Styling**: Update `phishy-styles.css` for appearance

## Support

### Getting Help

1. **Check Server Status**: Ensure Phishy AI backend is running
2. **Review Logs**: Check browser console and server logs
3. **Test Connection**: Use the "Test Connection" button
4. **Documentation**: Refer to main Phishy AI documentation

### Reporting Issues

When reporting problems, include:
- Browser version and OS
- Extension version
- Server URL and configuration
- Error messages from console
- Steps to reproduce the issue

## Version History

- **v1.0.0**: Initial release with core flagging functionality
- Advanced AI analysis integration
- WebSocket real-time communication
- Ngrok optimization and auto-configuration
- Comprehensive security features

## License

Part of the Phishy AI security platform. See main project license for details.

---

**⚠️ Security Notice**: This extension is designed for security testing and training purposes. Always ensure you have proper authorization before testing email security systems.