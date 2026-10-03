chrome.runtime.onInstalled.addListener(() => {
  console.log('Phishy extension installed');
  
  chrome.storage.local.get(['userEmail', 'ngrokUrl']).then((result) => {
    if (!result.userEmail || !result.ngrokUrl) {
      chrome.action.setBadgeText({text: '!'});
      chrome.action.setBadgeBackgroundColor({color: '#ff4444'});
      chrome.action.setTitle({title: 'Phishy - Configuration Required'});
    } else {
      chrome.action.setBadgeText({text: ''});
      chrome.action.setTitle({title: 'Phishy - Active'});
    }
  });
});

chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'local' && (changes.userEmail || changes.ngrokUrl)) {
    chrome.storage.local.get(['userEmail', 'ngrokUrl']).then((result) => {
      if (result.userEmail && result.ngrokUrl) {
        chrome.action.setBadgeText({text: ''});
        chrome.action.setBadgeBackgroundColor({color: '#4CAF50'});
        chrome.action.setTitle({title: 'Phishy - Active'});
        
        chrome.tabs.query({url: "https://mail.google.com/*"}, (tabs) => {
          tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, {
              action: 'settingsUpdated',
              settings: result
            }).catch(() => {});
          });
        });
      } else {
        chrome.action.setBadgeText({text: '!'});
        chrome.action.setBadgeBackgroundColor({color: '#ff4444'});
        chrome.action.setTitle({title: 'Phishy - Configuration Required'});
      }
    });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'logPhishingResult') {
    console.log('Phishing detection result:', request.data);
    
    chrome.storage.local.get(['detectionHistory']).then((result) => {
      const history = result.detectionHistory || [];
      history.unshift({
        ...request.data,
        timestamp: Date.now(),
        tabId: sender.tab?.id
      });
      
      if (history.length > 100) {
        history.splice(100);
      }
      
      chrome.storage.local.set({ detectionHistory: history });
    });
  }
  
  sendResponse({success: true});
});