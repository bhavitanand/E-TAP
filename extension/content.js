// E-TAP Gmail prototype. Change this URL when deploying the frontend.
const ETAP_APP_BASE_URL = 'http://127.0.0.1:5173';

// Keep track of emails we've already scanned to prevent infinite loops
const scannedEmails = new Set();

function extractEmailData(emailContainer) {
    // Gmail uses specific obfuscated classes, but generally elements can be found by standard selectors within the email pane
    const subjectEl = document.querySelector('h2[data-thread-perm-id]');
    const senderEl = emailContainer.querySelector('span[email]');
    const bodyEl = emailContainer.querySelector('.ii.gt');
    
    if (!bodyEl) return null;

    return {
        subject: subjectEl ? subjectEl.innerText : 'No Subject',
        sender: senderEl ? senderEl.getAttribute('email') : 'Unknown Sender',
        body: bodyEl.innerText,
    };
}

function injectBanner(emailContainer, reportData) {
    if (emailContainer.querySelector('.etap-banner')) {
        return; // Banner already exists
    }

    const banner = document.createElement('div');
    banner.className = 'etap-banner';

    // Parse the report from the backend (API returns risk_score at top level, and final_assessment inside ai_analysis)
    const riskScore = reportData.risk_score || 0;
    const verdict = reportData.verdict || 'Unknown';
    
    // Explanation is nested deeply inside ai_analysis
    let explanation = 'No explanation provided.';
    if (reportData.ai_analysis && reportData.ai_analysis.final_assessment && reportData.ai_analysis.final_assessment.supporting_evidence) {
        explanation = reportData.ai_analysis.final_assessment.supporting_evidence[0] || explanation;
    }

    // Traffic light styling
    const reportLink = reportData.email_id 
        ? `${ETAP_APP_BASE_URL}/?dossier=${encodeURIComponent(reportData.email_id)}` 
        : ETAP_APP_BASE_URL;

    const heading = document.createElement('strong');
    if (riskScore >= 65) {
        banner.classList.add('banner-red');
        heading.textContent = `🚨 High-Risk: ${verdict}`;
    } else if (riskScore >= 40) {
        banner.classList.add('banner-yellow');
        heading.textContent = '⚠️ Suspicious';
    } else {
        banner.classList.add('banner-green');
        heading.textContent = '✅ No high-risk signals detected';
    }
    const detail = document.createElement('span');
    detail.textContent = ` — ${explanation || 'No explanation provided.'} `;
    const link = document.createElement('a');
    link.href = reportLink;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'etap-btn';
    link.textContent = 'View Full Report';
    banner.append(heading, detail, link);

    // Insert banner at the top of the email body
    const bodyContainer = emailContainer.querySelector('.ii.gt');
    if (bodyContainer) {
        bodyContainer.parentNode.insertBefore(banner, bodyContainer);
    }
}

function scanVisibleEmails() {
    // Gmail reading panes
    const emailContainers = document.querySelectorAll('.adO, .gs, .nH.hx');
    
    emailContainers.forEach(container => {
        // Check if we have already injected a banner (loading or final) into this specific email view
        if (!container.querySelector('.etap-banner')) {
            const data = extractEmailData(container);
            
            if (data && data.body.length > 10) {
                console.log(`[E-TAP] Extracted Email:`, data.subject);
                
                // 1. Immediately inject the loading banner so we don't scan it again on the next tick
                const loadingBanner = document.createElement('div');
                loadingBanner.className = 'etap-banner banner-loading';
                loadingBanner.innerText = '🛡️ E-TAP is analyzing this email...';
                
                const bodyContainer = container.querySelector('.ii.gt');
                if (bodyContainer) {
                    bodyContainer.parentNode.insertBefore(loadingBanner, bodyContainer);
                }

                // 2. Send to background script for analysis
                chrome.runtime.sendMessage({ action: 'analyzeEmail', data: data }, response => {
                    // Remove the loading banner
                    if (loadingBanner.parentNode) {
                        loadingBanner.parentNode.removeChild(loadingBanner);
                    }
                    // Inject the final banner or error banner
                    if (response && response.success) {
                        injectBanner(container, response.report);
                    } else {
                        console.error('E-TAP Analysis Failed:', response?.error);
                        
                        // Inject an error banner so we don't infinitely retry
                        const errorBanner = document.createElement('div');
                        errorBanner.className = 'etap-banner banner-red';
                        errorBanner.innerHTML = `<strong>❌ API Error</strong> - Failed to analyze email. Check terminal for backend crashes.`;
                        const bodyContainer = container.querySelector('.ii.gt');
                        if (bodyContainer) bodyContainer.parentNode.insertBefore(errorBanner, bodyContainer);
                    }
                });
            }
        }
    });
}

// Run scanner periodically to catch newly opened emails in Gmail's SPA
setInterval(scanVisibleEmails, 2000);
