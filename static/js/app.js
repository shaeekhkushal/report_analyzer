/* ===========================
   Universal Report Analyzer
   Main Application Script
   =========================== */

// --- DOM References ---
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadedReports = document.getElementById('uploadedReports');
const sampleReports = document.getElementById('sampleReports');
const uploadMessage = document.getElementById('uploadMessage');
const uploadLoading = document.getElementById('uploadLoading');

// --- Drag & Drop ---
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragging');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragging');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragging');
    fileInput.files = e.dataTransfer.files;
    showSelectedFiles();
});

uploadArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
    showSelectedFiles();
});

// --- File Selection Preview ---
function showSelectedFiles() {
    const container = document.getElementById('selectedFiles');
    if (fileInput.files.length === 0) {
        container.style.display = 'none';
        return;
    }
    container.style.display = 'block';
    const fileListHtml = Array.from(fileInput.files).map((file, i) => {
        const size = file.size < 1024 ? file.size + ' B'
            : file.size < 1048576 ? (file.size / 1024).toFixed(1) + ' KB'
            : (file.size / 1048576).toFixed(1) + ' MB';
        const ext = file.name.split('.').pop().toLowerCase();
        const icons = { html: '\u{1F310}', json: '\u{1F4CB}', csv: '\u{1F4CA}', xlsx: '\u{1F4D7}', xls: '\u{1F4D7}' };
        const icon = icons[ext] || '\u{1F4C4}';
        return `<div class="selected-file-item">
            <span class="selected-file-icon">${icon}</span>
            <span class="selected-file-name">${file.name}</span>
            <span class="selected-file-size">${size}</span>
        </div>`;
    }).join('');
    container.innerHTML = `
        <div class="selected-files">
            <div class="selected-files-title">\u{1F4CE} ${fileInput.files.length} file(s) selected</div>
            ${fileListHtml}
        </div>
    `;
}

// --- Upload ---
function uploadFiles() {
    if (fileInput.files.length === 0) {
        showMessage('Please select files first', 'error');
        return;
    }

    uploadLoading.style.display = 'block';
    uploadMessage.innerHTML = '';

    const formData = new FormData();
    for (let file of fileInput.files) {
        formData.append('files', file);
    }

    const detailedCheckbox = document.getElementById('detailedAnalysis');
    formData.append('detailed', detailedCheckbox.checked ? 'true' : 'false');

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(results => {
        uploadLoading.style.display = 'none';
        let successCount = 0;
        let successFiles = [];
        results.forEach(result => {
            if (result.success) {
                successCount++;
                successFiles.push(result.filename);
            } else {
                showMessage(`Error: ${result.filename} - ${result.error}`, 'error');
            }
        });
        if (successCount > 0) {
            fileInput.value = '';
            document.getElementById('selectedFiles').style.display = 'none';
            loadUploadedReports();
            const fileListHtml = successFiles.map(f => `<div style="color: #a9b1d6; font-size: 0.9em;">\u2705 ${f}</div>`).join('');
            uploadMessage.innerHTML = `
                <div class="upload-success-summary">
                    <div class="success-icon">\u{1F389}</div>
                    <div class="success-text">${successCount} file(s) analyzed successfully!</div>
                    ${fileListHtml}
                    <button class="view-results-btn" onclick="showResultsView()" style="margin-top: 12px;">View Results \u2192</button>
                </div>
            `;
        }
    })
    .catch(err => {
        uploadLoading.style.display = 'none';
        showMessage(`Upload failed: ${err}`, 'error');
    });
}

// --- Sample Reports ---
function loadSampleReports() {
    uploadLoading.style.display = 'block';
    const detailedCheckbox = document.getElementById('detailedAnalysis');
    const detailed = detailedCheckbox.checked;

    fetch(`/sample-reports?detailed=${detailed}`)
    .then(res => res.json())
    .then(results => {
        uploadLoading.style.display = 'none';
        displayReports(results, sampleReports);
        switchTab('sample');
        showResultsView();
    })
    .catch(err => {
        uploadLoading.style.display = 'none';
        showMessage(`Failed to load sample reports: ${err}`, 'error');
    });
}

// --- Load Uploaded Reports ---
function loadUploadedReports() {
    const detailedCheckbox = document.getElementById('detailedAnalysis');
    const detailed = detailedCheckbox ? detailedCheckbox.checked : true;

    fetch(`/uploaded-reports?detailed=${detailed}`)
    .then(res => res.json())
    .then(results => {
        displayReports(results, uploadedReports);
        updateReportCount(results.length);
        const viewBtn = document.getElementById('viewReportsBtn');
        if (viewBtn) {
            viewBtn.style.display = results.length > 0 ? 'block' : 'none';
        }
    })
    .catch(err => console.error(err));
}

// --- Metric Formatting ---
function formatMetricName(name) {
    const labels = {
        'failed_requests': 'Failed Requests',
        'failure_rate': 'Failure Rate',
        'http_duration_avg': 'Average Response Time',
        'http_duration_max': 'Maximum Response Time',
        'http_duration_min': 'Minimum Response Time',
        'http_duration_median': 'Median Response Time',
        'http_duration_p90': 'P90 Response Time',
        'http_duration_p95': 'P95 Response Time',
        'http_duration_p99': 'P99 Response Time',
        'total_requests': 'Total Requests',
        'success_rate': 'Success Rate',
        'throughput': 'Throughput',
        'concurrent_users': 'Concurrent Users',
        'test_duration': 'Test Duration'
    };
    return labels[name] || name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function groupMetrics(metrics) {
    const groups = {
        'Response Time': [],
        'Success & Errors': [],
        'Throughput': [],
        'Other': []
    };

    metrics.forEach(m => {
        if (m.name.includes('duration') || m.name.includes('latency')) {
            groups['Response Time'].push(m);
        } else if (m.name.includes('failure') || m.name.includes('error') || m.name.includes('success')) {
            groups['Success & Errors'].push(m);
        } else if (m.name.includes('throughput') || m.name.includes('requests')) {
            groups['Throughput'].push(m);
        } else {
            groups['Other'].push(m);
        }
    });

    return groups;
}

// --- Display Reports ---
function displayReports(results, container) {
    if (results.length === 0) {
        container.innerHTML = '<p style="color: #565f89; text-align: center; padding: 20px;">No reports yet</p>';
        return;
    }

    container.innerHTML = results.map((result, index) => {
        if (result.error) {
            return `
                <div class="report-item">
                    <div class="report-header" style="background: linear-gradient(135deg, #f7768e 0%, #ff9e64 100%);">
                        <div class="report-title">
                            <div class="report-filename">${result.filename}</div>
                        </div>
                    </div>
                    <div class="report-content">
                        <div class="error-message">
                            Error: ${result.error}
                        </div>
                    </div>
                </div>
            `;
        }

        const hasDetailed = result.detailed_analysis && result.detailed_analysis.html;

        const metricGroups = groupMetrics(result.metrics);
        const metricsHtml = Object.entries(metricGroups)
            .filter(([_, metrics]) => metrics.length > 0)
            .map(([group, metrics]) => `
                <div class="report-section">
                    <div class="section-title" data-icon="">${group}</div>
                    <div class="metrics-grid">
                        ${metrics.map(m => `
                            <div class="metric-card">
                                <div class="metric-label">${formatMetricName(m.name)}</div>
                                <div class="metric-value">
                                    ${m.value.toFixed(2)}
                                    <span class="metric-unit">${m.unit}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');

        const insightsHtml = result.insights.length > 0
            ? `
                <div class="report-section">
                    <div class="section-title" data-icon="\u{1F4A1}">Key Insights & Analysis</div>
                    <div class="insights-container success-message">
                        ${result.insights.map(insight => {
                            let iconClass = '';
                            let containerClass = '';
                            if (insight.includes('CRITICAL') || insight.includes('critical') || insight.includes('severe')) {
                                iconClass = '\u{1F534}';
                                containerClass = 'critical';
                            } else if (insight.includes('HIGH') || insight.includes('moderate') || insight.includes('elevated')) {
                                iconClass = '\u26A0\uFE0F';
                                containerClass = 'warning';
                            } else {
                                iconClass = '\u2705';
                            }
                            return `
                                <div class="insight-item ${containerClass}">
                                    <span class="insight-icon">${iconClass}</span>
                                    <span class="insight-text">${insight}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `
            : '';

        const executiveSummary = `
            <div class="report-section">
                <div class="section-title" data-icon="\u{1F4C4}">Analysis Summary</div>
                <table class="metrics-table">
                    <tr>
                        <td style="padding: 10px;"><strong>Report Format:</strong></td>
                        <td style="padding: 10px;">${result.file_type.toUpperCase()}</td>
                    </tr>

                    <tr>
                        <td style="padding: 10px;"><strong>Total Metrics:</strong></td>
                        <td style="padding: 10px;">${result.metrics.length}</td>
                    </tr>
                    ${hasDetailed ? `
                    <tr>
                        <td style="padding: 10px;"><strong>Issues Found:</strong></td>
                        <td style="padding: 10px;">
                            <span style="color: ${result.detailed_analysis.has_critical ? '#f7768e' : '#9ece6a'}; font-weight: bold;">
                                ${result.detailed_analysis.total_issues} issues
                                ${result.detailed_analysis.has_critical ? '(Critical)' : ''}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px;"><strong>Analysis Type:</strong></td>
                        <td style="padding: 10px;"><span style="color: #7aa2f7; font-weight: bold;">Detailed</span></td>
                    </tr>
                    ` : `
                    <tr>
                        <td style="padding: 10px;"><strong>Analysis Type:</strong></td>
                        <td style="padding: 10px;"><span style="color: #9ece6a; font-weight: bold;">Basic</span></td>
                    </tr>
                    `}
                </table>
            </div>
        `;

        let detailedSection = '';
        if (hasDetailed) {
            detailedSection = `
                <div id="detailed-toggle-${index}" class="detailed-analysis-toggle" onclick="toggleDetailed(${index})">
                    <strong>\u{1F4CA} View Detailed Analysis Report</strong>
                    <span class="icon">\u25BC</span>
                </div>
                <div id="detailed-content-${index}" style="display: none;">
                    ${result.detailed_analysis.html}
                </div>
            `;
        }

        return `
            <div class="report-item">
                <div class="report-header">
                    <div class="report-title">
                        <div class="report-filename">${result.filename}</div>
                        <div class="report-meta">Performance Report Analysis</div>
                    </div>
                </div>
                <div class="report-content">
                    <div style="text-align: right; margin-bottom: 10px;">
                        <a href="/export-detailed-csv/${encodeURIComponent(result.filename)}" class="download-btn" target="_blank" download>
                            Download Report (CSV)
                        </a>
                    </div>
                    ${executiveSummary}
                    ${metricsHtml}
                    ${insightsHtml}
                    ${detailedSection}
                </div>
            </div>
        `;
    }).join('');
}

// --- Toggle Detailed Analysis ---
function toggleDetailed(index) {
    const toggle = document.getElementById(`detailed-toggle-${index}`);
    const content = document.getElementById(`detailed-content-${index}`);

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.classList.add('expanded');
    } else {
        content.style.display = 'none';
        toggle.classList.remove('expanded');
    }
}

// --- Clear Uploads ---
function clearUploads() {
    showConfirmModal(
        '\u{1F5D1}\uFE0F',
        'Clear All Uploads',
        'Are you sure you want to delete all uploaded files? This action cannot be undone and will permanently remove all reports from the server.',
        () => {
            fetch('/clear-uploads', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    uploadedReports.innerHTML = '';
                    updateReportCount(0);
                    const viewBtn = document.getElementById('viewReportsBtn');
                    if (viewBtn) viewBtn.style.display = 'none';
                    showUploadView();
                }
            })
            .catch(err => showMessage(`Failed: ${err}`, 'error'));
        }
    );
}

// --- Confirmation Modal ---
function showConfirmModal(icon, title, message, onConfirm) {
    const modal = document.getElementById('confirmModal');
    const modalIcon = modal.querySelector('.modal-icon');
    const modalTitle = modal.querySelector('.modal-title');
    const modalMessage = document.getElementById('modalMessage');
    const confirmBtn = document.getElementById('modalConfirmBtn');

    modalIcon.textContent = icon;
    modalTitle.textContent = title;
    modalMessage.textContent = message;

    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.addEventListener('click', () => {
        closeModal();
        onConfirm();
    });

    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('confirmModal');
    modal.classList.remove('active');
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('confirmModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
});

// --- Tab Switching ---
function switchTab(tab) {
    const uploadedBtn = document.querySelectorAll('.tab-btn')[0];
    const sampleBtn = document.querySelectorAll('.tab-btn')[1];

    if (tab === 'uploaded') {
        uploadedReports.style.display = 'block';
        sampleReports.style.display = 'none';
        uploadedBtn.classList.add('active');
        sampleBtn.classList.remove('active');
    } else {
        uploadedReports.style.display = 'none';
        sampleReports.style.display = 'block';
        uploadedBtn.classList.remove('active');
        sampleBtn.classList.add('active');
    }
}

// --- Messages ---
function showMessage(text, type) {
    const className = type === 'error' ? 'error-message' : 'success-message';
    uploadMessage.innerHTML = `<div class="${className}">${text}</div>`;
    setTimeout(() => {
        uploadMessage.innerHTML = '';
    }, 5000);
}

function updateReportCount(count) {
    document.getElementById('reportCount').textContent = count;
}

// --- View Switching ---
function showUploadView() {
    document.getElementById('uploadView').classList.remove('hidden');
    document.getElementById('resultsView').classList.add('hidden');
}

function showResultsView() {
    document.getElementById('uploadView').classList.add('hidden');
    document.getElementById('resultsView').classList.remove('hidden');
}

// --- Initialize ---
loadUploadedReports();
