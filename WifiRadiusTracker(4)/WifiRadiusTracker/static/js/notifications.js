// Notification System for the MikroTik Hotspot Portal
if (typeof NotificationSystem === 'undefined') {
    const NotificationSystem = {
        /**
         * Shows a success notification
         * @param {string} message - The message to display
         * @param {number} duration - How long the notification should stay visible (in ms)
         */
        success: function(message, duration = 5000) {
            this.showNotification(message, 'success', duration);
        },

        /**
         * Shows an info notification
         * @param {string} message - The message to display
         * @param {number} duration - How long the notification should stay visible (in ms)
         */
        info: function(message, duration = 5000) {
            this.showNotification(message, 'info', duration);
        },

        /**
         * Shows a warning notification
         * @param {string} message - The message to display
         * @param {number} duration - How long the notification should stay visible (in ms)
         */
        warning: function(message, duration = 5000) {
            this.showNotification(message, 'warning', duration);
        },

        /**
         * Shows an error notification
         * @param {string} message - The message to display
         * @param {number} duration - How long the notification should stay visible (in ms)
         */
        error: function(message, duration = 5000) {
            this.showNotification(message, 'danger', duration);
        },

        /**
         * Creates and shows a notification
         * @param {string} message - The message to display
         * @param {string} type - Type of notification (success, info, warning, danger)
         * @param {number} duration - How long the notification should stay visible (in ms)
         */
        showNotification: function(message, type, duration) {
            const container = document.getElementById('notification-container');

            if (!container) {
                console.error('Notification container not found');
                return;
            }

            // Create notification element
            const notification = document.createElement('div');
            notification.className = `toast show bg-${type} text-white`;
            notification.setAttribute('role', 'alert');
            notification.setAttribute('aria-live', 'assertive');
            notification.setAttribute('aria-atomic', 'true');

            // Icon based on notification type
            let icon = 'info-circle';
            if (type === 'success') icon = 'check-circle';
            if (type === 'warning') icon = 'exclamation-triangle';
            if (type === 'danger') icon = 'times-circle';

            // Notification content
            notification.innerHTML = `
                <div class="toast-header bg-${type} text-white border-0">
                    <i class="fas fa-${icon} me-2"></i>
                    <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            `;

            // Add to container
            container.appendChild(notification);

            // Set up close button
            const closeButton = notification.querySelector('.btn-close');
            closeButton.addEventListener('click', function() {
                container.removeChild(notification);
            });

            // Auto remove after duration
            setTimeout(() => {
                if (notification.parentNode === container) {
                    container.removeChild(notification);
                }
            }, duration);
        }
    };

    // Make it available globally
    window.NotificationSystem = NotificationSystem;
}

// Check for session expiry and show warnings
function checkSessionExpiry() {
  const sessionElement = document.getElementById('session-time-remaining');
  if (!sessionElement) return;

  const secondsRemaining = parseInt(sessionElement.getAttribute('data-remaining-seconds'));
  const warningThreshold = 5 * 60; // 5 minutes in seconds

  if (secondsRemaining <= warningThreshold && secondsRemaining > 0) {
    const minutesRemaining = Math.ceil(secondsRemaining / 60);
    NotificationSystem.warning(
      `Your session will expire in approximately ${minutesRemaining} minute${minutesRemaining !== 1 ? 's' : ''}. 
       Please purchase more time to continue using the internet.`,
      'Session Expiring Soon',
      { duration: 120000 }
    );
  }
};

// Initialize on document load
document.addEventListener('DOMContentLoaded', function() {
  // Check session expiry on page load
  checkSessionExpiry();

  // Add click event for package selection if needed
  const packageCards = document.querySelectorAll('.package-card');
  if (packageCards.length > 0) {
    packageCards.forEach(card => {
      card.addEventListener('click', function() {
        const packageId = this.getAttribute('data-package-id');
        if (typeof window.selectPackage === 'function') {
          window.selectPackage(packageId);
        }
      });
    });
  }
});

// Define the selectPackage function if it doesn't exist
if (typeof window.selectPackage === 'undefined') {
  window.selectPackage = function(packageId) {
    const packageInput = document.getElementById('package_id');
    if (packageInput) {
      packageInput.value = packageId;

      // Highlight selected package
      document.querySelectorAll('.package-card').forEach(card => {
        if (card.getAttribute('data-package-id') === packageId) {
          card.classList.add('selected');
        } else {
          card.classList.remove('selected');
        }
      });

      // Scroll to payment form
      const paymentForm = document.getElementById('payment-form');
      if (paymentForm) {
        paymentForm.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };
}