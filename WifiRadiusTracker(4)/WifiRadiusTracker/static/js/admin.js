/**
 * Admin panel JavaScript for MikroTik WiFi Hotspot
 */

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
  // Initialize datepickers if available
  const datepickers = document.querySelectorAll('.datepicker');
  if (datepickers.length > 0) {
    datepickers.forEach(element => {
      element.addEventListener('input', function(e) {
        validateDateFormat(e.target);
      });
    });
  }

  // Initialize search functionality
  const searchForm = document.getElementById('searchForm');
  if (searchForm) {
    searchForm.addEventListener('submit', function(e) {
      const searchInput = document.getElementById('search');
      if (searchInput && searchInput.value.trim() === '') {
        e.preventDefault();
      }
    });
  }

  // Initialize voucher bulk actions
  const bulkActionForm = document.getElementById('bulkActionForm');
  if (bulkActionForm) {
    const selectAllCheckbox = document.getElementById('selectAll');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    
    // Select all checkbox
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', function() {
        itemCheckboxes.forEach(checkbox => {
          checkbox.checked = selectAllCheckbox.checked;
        });
        updateBulkActionButtons();
      });
    }
    
    // Individual checkboxes
    itemCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', function() {
        updateBulkActionButtons();
        
        // Update "select all" checkbox state
        if (selectAllCheckbox) {
          selectAllCheckbox.checked = [...itemCheckboxes].every(cb => cb.checked);
          selectAllCheckbox.indeterminate = !selectAllCheckbox.checked && 
                                           [...itemCheckboxes].some(cb => cb.checked);
        }
      });
    });
    
    // Bulk action buttons
    const bulkActionButtons = document.querySelectorAll('.bulk-action-btn');
    bulkActionButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        e.preventDefault();
        
        const action = this.dataset.action;
        document.getElementById('bulkAction').value = action;
        
        // Confirm deletion
        if (action === 'delete' && !confirm('Are you sure you want to delete the selected items?')) {
          return;
        }
        
        bulkActionForm.submit();
      });
    });
    
    // Initial update of bulk action buttons
    updateBulkActionButtons();
  }

  // Quick user status toggle
  const statusToggles = document.querySelectorAll('.status-toggle');
  statusToggles.forEach(toggle => {
    toggle.addEventListener('change', function() {
      const userId = this.dataset.userId;
      const isActive = this.checked;
      
      fetch(`/admin/users/${userId}/toggle-status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ is_active: isActive })
      })
      .then(response => response.json())
      .then(data => {
        if (!data.success) {
          // Revert the toggle if the update failed
          this.checked = !isActive;
          alert(data.message || 'Failed to update user status');
        }
      })
      .catch(error => {
        console.error('Error:', error);
        this.checked = !isActive;
        alert('An error occurred while updating the user status');
      });
    });
  });

  // Real-time session monitoring (if on admin session page)
  if (document.getElementById('active-sessions-table')) {
    // Refresh active sessions every 30 seconds
    setInterval(refreshActiveSessions, 30000);
  }

  // Initialize any date range pickers for reports
  initDateRangePicker();
});

/**
 * Update bulk action buttons based on checkbox state
 */
function updateBulkActionButtons() {
  const checkedCount = document.querySelectorAll('.item-checkbox:checked').length;
  const bulkActionButtons = document.querySelectorAll('.bulk-action-btn');
  const selectedCountSpan = document.getElementById('selectedCount');
  
  bulkActionButtons.forEach(button => {
    button.disabled = checkedCount === 0;
  });
  
  if (selectedCountSpan) {
    selectedCountSpan.textContent = checkedCount;
    selectedCountSpan.parentElement.style.display = checkedCount > 0 ? 'inline-block' : 'none';
  }
}

/**
 * Validate date format for inputs
 * @param {HTMLElement} input - The date input element
 */
function validateDateFormat(input) {
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  
  if (!dateRegex.test(input.value)) {
    input.setCustomValidity('Please use YYYY-MM-DD format');
  } else {
    input.setCustomValidity('');
  }
}

/**
 * Get CSRF token from cookies
 * @returns {string} - CSRF token
 */
function getCsrfToken() {
  const name = 'csrftoken';
  const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
  return match ? decodeURIComponent(match[3]) : '';
}

/**
 * Refresh active sessions table
 */
function refreshActiveSessions() {
  const table = document.getElementById('active-sessions-table');
  if (!table) return;
  
  const tableBody = table.querySelector('tbody');
  if (!tableBody) return;
  
  fetch('/admin/sessions/active/data')
    .then(response => response.json())
    .then(data => {
      if (data.success && data.sessions) {
        // Update session rows
        updateSessionTable(tableBody, data.sessions);
      }
    })
    .catch(error => {
      console.error('Error refreshing sessions:', error);
    });
}

/**
 * Update session table with new data
 * @param {HTMLElement} tableBody - The table body element
 * @param {Array} sessions - Array of session data
 */
function updateSessionTable(tableBody, sessions) {
  // Map sessions by ID for easier comparison
  const sessionMap = new Map();
  sessions.forEach(session => {
    sessionMap.set(session.id, session);
  });
  
  // Update existing rows and track which ones are updated
  const updatedIds = new Set();
  const rows = tableBody.querySelectorAll('tr');
  
  rows.forEach(row => {
    const sessionId = parseInt(row.dataset.sessionId);
    if (sessionMap.has(sessionId)) {
      updatedIds.add(sessionId);
      updateSessionRow(row, sessionMap.get(sessionId));
    } else {
      // Fade out removed sessions
      row.style.opacity = '0.5';
      row.classList.add('text-muted');
      
      // Find the status cell and update it
      const statusCell = row.querySelector('.session-status');
      if (statusCell) {
        statusCell.innerHTML = '<span class="status-badge status-inactive">Inactive</span>';
      }
    }
  });
  
  // Add new rows for new sessions
  sessionMap.forEach((session, id) => {
    if (!updatedIds.has(id)) {
      const newRow = createSessionRow(session);
      tableBody.insertBefore(newRow, tableBody.firstChild);
      
      // Highlight new row
      newRow.classList.add('highlight-animation');
      setTimeout(() => {
        newRow.classList.remove('highlight-animation');
      }, 3000);
    }
  });
}

/**
 * Update a session table row with new data
 * @param {HTMLElement} row - The table row element
 * @param {Object} session - Session data
 */
function updateSessionRow(row, session) {
  // Update remaining time
  const remainingTimeCell = row.querySelector('.remaining-time');
  if (remainingTimeCell) {
    remainingTimeCell.textContent = formatTime(session.remaining_time.total_seconds);
  }
  
  // Update data usage
  const downloadCell = row.querySelector('.download-usage');
  if (downloadCell) {
    downloadCell.textContent = formatBytes(session.usage.download);
  }
  
  const uploadCell = row.querySelector('.upload-usage');
  if (uploadCell) {
    uploadCell.textContent = formatBytes(session.usage.upload);
  }
}

/**
 * Create a new session table row
 * @param {Object} session - Session data
 * @returns {HTMLElement} - The created row element
 */
function createSessionRow(session) {
  const row = document.createElement('tr');
  row.dataset.sessionId = session.id;
  
  row.innerHTML = `
    <td>${session.user.username}</td>
    <td>${session.package.name}</td>
    <td>${session.ip_address || 'N/A'}</td>
    <td>${session.mac_address || 'N/A'}</td>
    <td>${new Date(session.start_time).toLocaleString()}</td>
    <td class="remaining-time">${formatTime(session.remaining_time.total_seconds)}</td>
    <td class="download-usage">${formatBytes(session.usage.download)}</td>
    <td class="upload-usage">${formatBytes(session.usage.upload)}</td>
    <td class="session-status"><span class="status-badge status-active">Active</span></td>
    <td>
      <form method="POST" action="/admin/sessions/${session.id}/disconnect">
        <input type="hidden" name="csrf_token" value="${getCsrfToken()}">
        <button type="submit" class="btn btn-sm btn-danger">
          <i class="fas fa-times-circle"></i> Disconnect
        </button>
      </form>
    </td>
  `;
  
  return row;
}

/**
 * Initialize date range picker for reports
 */
function initDateRangePicker() {
  const startDateInput = document.getElementById('start_date');
  const endDateInput = document.getElementById('end_date');
  
  if (!startDateInput || !endDateInput) return;
  
  // Set default dates if not set
  if (!startDateInput.value) {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    startDateInput.value = date.toISOString().split('T')[0];
  }
  
  if (!endDateInput.value) {
    const date = new Date();
    endDateInput.value = date.toISOString().split('T')[0];
  }
  
  // Ensure end date is not before start date
  startDateInput.addEventListener('change', function() {
    if (endDateInput.value < startDateInput.value) {
      endDateInput.value = startDateInput.value;
    }
    endDateInput.min = startDateInput.value;
  });
  
  // Set initial min value for end date
  endDateInput.min = startDateInput.value;
}
