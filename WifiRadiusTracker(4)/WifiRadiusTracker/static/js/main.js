/**
 * Main JavaScript for MikroTik WiFi Hotspot
 */

// Notification System
const NotificationSystem = {
  // Toast container
  container: null,
  
  // Initialize the notification system
  init: function() {
    // Create toast container if it doesn't exist
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      this.container.style.zIndex = '1090';
      document.body.appendChild(this.container);
    }
  },
  
  // Show a notification
  show: function(options) {
    // Initialize if not already
    this.init();
    
    // Default options
    const defaults = {
      title: 'Notification',
      message: '',
      type: 'info', // info, success, warning, danger
      duration: 5000, // ms
      icon: null,
      autoHide: true
    };
    
    // Merge options
    const settings = {...defaults, ...options};
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast border-${settings.type}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    // Set auto-hide
    if (settings.autoHide) {
      toastEl.setAttribute('data-bs-delay', settings.duration);
      toastEl.setAttribute('data-bs-autohide', 'true');
    } else {
      toastEl.setAttribute('data-bs-autohide', 'false');
    }
    
    // Set icon based on type if not provided
    if (!settings.icon) {
      switch(settings.type) {
        case 'success':
          settings.icon = 'fas fa-check-circle';
          break;
        case 'warning':
          settings.icon = 'fas fa-exclamation-triangle';
          break;
        case 'danger':
          settings.icon = 'fas fa-times-circle';
          break;
        default:
          settings.icon = 'fas fa-info-circle';
      }
    }
    
    // Create toast content
    toastEl.innerHTML = `
      <div class="toast-header bg-${settings.type} text-white">
        <i class="${settings.icon} me-2"></i>
        <strong class="me-auto">${settings.title}</strong>
        <small>${new Date().toLocaleTimeString()}</small>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${settings.message}
      </div>
    `;
    
    // Add to container
    this.container.appendChild(toastEl);
    
    // Create Bootstrap toast and show it
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    
    // Return the toast for further manipulation
    return toast;
  },
  
  // Convenience methods for different notification types
  success: function(message, title = 'Success', options = {}) {
    return this.show({...options, title, message, type: 'success'});
  },
  
  warning: function(message, title = 'Warning', options = {}) {
    return this.show({...options, title, message, type: 'warning'});
  },
  
  error: function(message, title = 'Error', options = {}) {
    return this.show({...options, title, message, type: 'danger'});
  },
  
  info: function(message, title = 'Information', options = {}) {
    return this.show({...options, title, message, type: 'info'});
  },
  
  // Show session expiration warning
  sessionExpiration: function(minutes) {
    return this.warning(
      `Your session will expire in ${minutes} minutes. Would you like to extend it?`,
      'Session Expiring',
      {
        autoHide: false,
        duration: 0,
        actionButton: {
          text: 'Extend Session',
          action: function() {
            // Code to extend session
            console.log('Session extension requested');
            // This would call your backend API to extend the session
          }
        }
      }
    );
  }
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
  // Enable Bootstrap tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function(tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Enable Bootstrap popovers
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map(function(popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // Initialize notification system
  NotificationSystem.init();

  // Auto-hide alerts after 5 seconds
  setTimeout(function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 5000);

  // Toggle password visibility
  const togglePassword = document.querySelectorAll('.toggle-password');
  togglePassword.forEach(function(button) {
    button.addEventListener('click', function() {
      const input = document.querySelector(button.getAttribute('data-target'));
      if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
      } else {
        input.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
      }
    });
  });
});

/**
 * Format bytes to human-readable format
 * @param {number} bytes - The bytes to format
 * @param {number} decimals - The number of decimal places
 * @returns {string} - Formatted string
 */
function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format seconds to hours:minutes:seconds
 * @param {number} seconds - Total seconds
 * @returns {string} - Formatted time string
 */
function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '00:00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  return [hours, minutes, secs]
    .map(v => v < 10 ? '0' + v : v)
    .join(':');
}

/**
 * Format currency
 * @param {number} amount - The amount to format
 * @param {string} currency - Currency code (default: KES)
 * @returns {string} - Formatted currency string
 */
function formatCurrency(amount, currency = 'KES') {
  return currency + ' ' + parseFloat(amount).toFixed(2);
}

/**
 * Check payment status periodically
 * @param {number} paymentId - The payment ID to check
 * @param {number} interval - Check interval in milliseconds
 */
function checkPaymentStatus(paymentId, interval = 5000) {
  const statusElement = document.getElementById('payment-status');
  const statusContainer = document.getElementById('payment-status-container');
  
  if (!statusElement || !statusContainer) return;
  
  const checkStatus = () => {
    fetch(`/payment/check/${paymentId}`)
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          if (data.status === 'completed') {
            statusElement.textContent = 'Payment Completed';
            statusContainer.className = 'alert alert-success';
            
            // Show success message
            document.getElementById('payment-pending').classList.add('d-none');
            document.getElementById('payment-success').classList.remove('d-none');
            
            // Redirect after 3 seconds if redirect URL is provided
            if (data.redirect) {
              setTimeout(() => {
                window.location.href = data.redirect;
              }, 3000);
            }
            
            // Stop checking
            clearInterval(interval);
          } else if (data.status === 'failed') {
            statusElement.textContent = 'Payment Failed';
            statusContainer.className = 'alert alert-danger';
            
            // Show failure message
            document.getElementById('payment-pending').classList.add('d-none');
            document.getElementById('payment-failed').classList.remove('d-none');
            
            // Stop checking
            clearInterval(interval);
          }
        } else {
          console.error('Error checking payment status:', data.message);
        }
      })
      .catch(error => {
        console.error('Error:', error);
      });
  };
  
  // Check immediately
  checkStatus();
  
  // Set up interval
  const intervalId = setInterval(checkStatus, interval);
  
  return intervalId;
}

/**
 * Copy text to clipboard
 * @param {string} text - The text to copy
 * @param {string} elementId - ID of element to update with success message
 */
function copyToClipboard(text, elementId) {
  const element = document.getElementById(elementId);
  
  navigator.clipboard.writeText(text)
    .then(() => {
      if (element) {
        const originalText = element.textContent;
        element.textContent = 'Copied!';
        
        setTimeout(() => {
          element.textContent = originalText;
        }, 2000);
      }
    })
    .catch(err => {
      console.error('Could not copy text: ', err);
    });
}

/**
 * Register service worker for PWA functionality
 */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/service-worker.js')
      .then(registration => {
        console.log('ServiceWorker registration successful with scope: ', registration.scope);
      })
      .catch(err => {
        console.log('ServiceWorker registration failed: ', err);
      });
  });
}
/**
 * Main JavaScript for MikroTik WiFi Hotspot
 */

// Notification System
const NotificationSystem = {
  init: function() {
    this.container = document.getElementById('notification-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'notification-container';
      this.container.className = 'position-fixed top-0 end-0 p-3';
      this.container.style.zIndex = '1050';
      document.body.appendChild(this.container);
    }
  },
  
  show: function(message, type = 'info', duration = 5000) {
    const id = 'notification-' + Date.now();
    const iconMap = {
      'success': 'fas fa-check-circle',
      'warning': 'fas fa-exclamation-triangle',
      'danger': 'fas fa-times-circle',
      'info': 'fas fa-info-circle'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast show bg-${type === 'error' ? 'danger' : type} text-white`;
    toast.id = id;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="toast-header bg-${type === 'error' ? 'danger' : type} text-white">
        <i class="${iconMap[type === 'error' ? 'danger' : type]} me-2"></i>
        <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
        <small>Just now</small>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    `;
    
    this.container.appendChild(toast);
    
    // Remove after duration
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toast.remove();
      }, 500);
    }, duration);
    
    return id;
  },
  
  success: function(message, duration) {
    return this.show(message, 'success', duration);
  },
  
  warning: function(message, duration) {
    return this.show(message, 'warning', duration);
  },
  
  error: function(message, duration) {
    return this.show(message, 'danger', duration);
  },
  
  info: function(message, duration) {
    return this.show(message, 'info', duration);
  }
};

// Session Timer

// Package selection function for the packages page
function selectPackage(packageId) {
    if (typeof packageId !== 'undefined') {
        window.location.href = '/payment/checkout/' + packageId;
    }
}
class SessionTimer {
  constructor(endTime, displaySelector) {
    this.endTime = new Date(endTime).getTime();
    this.display = document.querySelector(displaySelector);
    this.interval = null;
    if (this.display) {
      this.start();
    }
  }
  
  start() {
    this.interval = setInterval(() => {
      this.update();
    }, 1000);
    this.update();
  }
  
  update() {
    const now = new Date().getTime();
    const distance = this.endTime - now;
    
    if (distance <= 0) {
      clearInterval(this.interval);
      this.display.innerHTML = "EXPIRED";
      this.display.parentElement.classList.add('bg-danger');
      NotificationSystem.warning('Your session has expired. Please purchase a new package to continue.');
      return;
    }
    
    // Time calculations
    const hours = Math.floor(distance / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
    
    // Warning when less than 10 minutes left
    if (distance < (10 * 60 * 1000) && distance > (9 * 60 * 1000)) {
      NotificationSystem.warning('Your session will expire in less than 10 minutes. Consider extending your time.');
    }
    
    this.display.innerHTML = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  
  stop() {
    clearInterval(this.interval);
  }
}

// Data Usage Graph
function initDataUsageChart(elementId, downloadData, uploadData, labels) {
  const ctx = document.getElementById(elementId);
  if (!ctx) return;
  
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Download (MB)',
          data: downloadData,
          borderColor: '#3498db',
          backgroundColor: 'rgba(52, 152, 219, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Upload (MB)',
          data: uploadData,
          borderColor: '#2ecc71',
          backgroundColor: 'rgba(46, 204, 113, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: 'rgba(255, 255, 255, 0.7)'
          }
        },
        x: {
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          },
          ticks: {
            color: 'rgba(255, 255, 255, 0.7)'
          }
        }
      },
      plugins: {
        legend: {
          labels: {
            color: 'rgba(255, 255, 255, 0.7)'
          }
        }
      }
    }
  });
}

// Toggle dark/light mode
function toggleDarkMode() {
  const html = document.documentElement;
  if (html.getAttribute('data-bs-theme') === 'dark') {
    html.setAttribute('data-bs-theme', 'light');
    localStorage.setItem('theme', 'light');
  } else {
    html.setAttribute('data-bs-theme', 'dark');
    localStorage.setItem('theme', 'dark');
  }
}

// Copy voucher code to clipboard
function copyVoucherCode(element) {
  const codeElement = element.parentElement.querySelector('.voucher-code');
  const text = codeElement.textContent.trim();
  
  navigator.clipboard.writeText(text).then(() => {
    // Change button text temporarily
    const originalText = element.innerHTML;
    element.innerHTML = '<i class="fas fa-check"></i> Copied!';
    
    // Reset after 2 seconds
    setTimeout(() => {
      element.innerHTML = originalText;
    }, 2000);
    
    // Show notification
    NotificationSystem.success('Voucher code copied to clipboard!');
  }).catch(err => {
    console.error('Failed to copy: ', err);
    NotificationSystem.error('Failed to copy voucher code.');
  });
}

// Package selection enhancement
function selectPackage(packageId) {
  // Remove selection from all packages
  document.querySelectorAll('.package-card').forEach(card => {
    card.classList.remove('border-primary');
    card.querySelector('.btn-select-package').classList.remove('btn-primary');
    card.querySelector('.btn-select-package').classList.add('btn-outline-primary');
  });
  
  // Add selection to selected package
  const selectedCard = document.getElementById(`package-${packageId}`);
  if (selectedCard) {
    selectedCard.classList.add('border-primary');
    selectedCard.querySelector('.btn-select-package').classList.remove('btn-outline-primary');
    selectedCard.querySelector('.btn-select-package').classList.add('btn-primary');
    
    // Update hidden input for the form
    document.getElementById('selected_package_id').value = packageId;
  }
}

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
  // Enable Bootstrap tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function(tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Enable Bootstrap popovers
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map(function(popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // Initialize notification system
  NotificationSystem.init();

  // Auto-hide alerts after 5 seconds
  setTimeout(function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 5000);

  // Toggle password visibility
  const togglePassword = document.querySelectorAll('.toggle-password');
  togglePassword.forEach(function(button) {
    button.addEventListener('click', function() {
      const input = document.querySelector(button.getAttribute('data-target'));
      if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
      } else {
        input.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
      }
    });
  });
  
  // Check for active session timer
  const timerDisplay = document.getElementById('session-timer-display');
  if (timerDisplay) {
    const endTime = timerDisplay.getAttribute('data-end-time');
    if (endTime) {
      new SessionTimer(endTime, '#session-timer-display');
    }
  }
  
  // Set theme preference from localStorage
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
  }
  
  // Add dark mode toggle button to navbar if it doesn't exist
  const userDropdown = document.querySelector('#userDropdown');
  if (userDropdown) {
    const dropdownMenu = userDropdown.nextElementSibling;
    if (dropdownMenu && !document.getElementById('dark-mode-toggle')) {
      const divider = document.createElement('li');
      divider.innerHTML = '<hr class="dropdown-divider">';
      
      const themeToggle = document.createElement('li');
      themeToggle.innerHTML = `
        <a class="dropdown-item" href="#" id="dark-mode-toggle" onclick="toggleDarkMode(); return false;">
          <i class="fas fa-moon me-2"></i> Toggle Dark Mode
        </a>
      `;
      
      const logoutItem = dropdownMenu.querySelector('a[href*="logout"]').parentElement;
      dropdownMenu.insertBefore(divider, logoutItem);
      dropdownMenu.insertBefore(themeToggle, logoutItem);
    }
  }
  
  // Initialize any data usage charts
  if (typeof Chart !== 'undefined' && document.getElementById('dataUsageChart')) {
    // Sample data - would be replaced with actual data from backend
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const downloadData = [65, 59, 80, 81, 56, 55, 40];
    const uploadData = [28, 48, 40, 19, 86, 27, 90];
    
    initDataUsageChart('dataUsageChart', downloadData, uploadData, labels);
  }
  
  // Package selection click event
  document.querySelectorAll('.btn-select-package').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      const packageId = this.getAttribute('data-package-id');
      selectPackage(packageId);
    });
  });
});
