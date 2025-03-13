/**
 * Charts and visualization for MikroTik WiFi Hotspot
 */

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
  // Daily Revenue Chart
  initDailyRevenueChart();
  
  // Package Popularity Chart
  initPackagePopularityChart();
  
  // Active Sessions Chart
  initActiveSessionsChart();
  
  // Data Usage Chart
  initDataUsageChart();
});

/**
 * Initialize daily revenue chart
 */
function initDailyRevenueChart() {
  const ctx = document.getElementById('dailyRevenueChart');
  if (!ctx) return;
  
  // Get chart data from data attribute
  const chartDataElement = document.getElementById('daily-revenue-data');
  if (!chartDataElement) return;
  
  let chartData;
  try {
    chartData = JSON.parse(chartDataElement.textContent);
  } catch (e) {
    console.error('Error parsing chart data:', e);
    return;
  }
  
  // Prepare data for chart
  const labels = chartData.map(item => item.date);
  const values = chartData.map(item => item.revenue);
  
  // Create chart
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Daily Revenue (KES)',
        data: values,
        backgroundColor: 'rgba(52, 152, 219, 0.5)',
        borderColor: 'rgba(52, 152, 219, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return 'KES ' + value;
            }
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              return 'Revenue: KES ' + context.raw.toFixed(2);
            }
          }
        }
      }
    }
  });
}

/**
 * Initialize package popularity chart
 */
function initPackagePopularityChart() {
  const ctx = document.getElementById('packagePopularityChart');
  if (!ctx) return;
  
  // Get chart data from data attribute
  const chartDataElement = document.getElementById('package-popularity-data');
  if (!chartDataElement) return;
  
  let chartData;
  try {
    chartData = JSON.parse(chartDataElement.textContent);
  } catch (e) {
    console.error('Error parsing chart data:', e);
    return;
  }
  
  // Prepare data for chart
  const labels = chartData.map(item => item.name);
  const counts = chartData.map(item => item.count);
  const revenue = chartData.map(item => item.revenue);
  
  // Create chart
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: [
          'rgba(52, 152, 219, 0.7)',
          'rgba(46, 204, 113, 0.7)',
          'rgba(155, 89, 182, 0.7)',
          'rgba(241, 196, 15, 0.7)',
          'rgba(231, 76, 60, 0.7)'
        ],
        borderColor: [
          'rgba(52, 152, 219, 1)',
          'rgba(46, 204, 113, 1)',
          'rgba(155, 89, 182, 1)',
          'rgba(241, 196, 15, 1)',
          'rgba(231, 76, 60, 1)'
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = Math.round((value / total) * 100);
              const packageRevenue = revenue[context.dataIndex];
              
              return [
                label + ': ' + value + ' purchases (' + percentage + '%)',
                'Revenue: KES ' + packageRevenue.toFixed(2)
              ];
            }
          }
        }
      }
    }
  });
}

/**
 * Initialize active sessions chart
 */
function initActiveSessionsChart() {
  const ctx = document.getElementById('activeSessionsChart');
  if (!ctx) return;
  
  // This would typically be populated with real data from an API
  // For now, we'll use sample data
  const chartDataElement = document.getElementById('active-sessions-data');
  if (!chartDataElement) return;
  
  let chartData;
  try {
    chartData = JSON.parse(chartDataElement.textContent);
  } catch (e) {
    console.error('Error parsing chart data:', e);
    return;
  }
  
  // Create chart
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: [{
        label: 'Active Sessions',
        data: chartData.values,
        backgroundColor: 'rgba(46, 204, 113, 0.2)',
        borderColor: 'rgba(46, 204, 113, 1)',
        borderWidth: 2,
        tension: 0.3,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            precision: 0
          }
        }
      }
    }
  });
}

/**
 * Initialize data usage chart
 */
function initDataUsageChart() {
  const ctx = document.getElementById('dataUsageChart');
  if (!ctx) return;
  
  // This would typically be populated with real data from an API
  // For now, we'll use sample data
  const chartDataElement = document.getElementById('data-usage-data');
  if (!chartDataElement) return;
  
  let chartData;
  try {
    chartData = JSON.parse(chartDataElement.textContent);
  } catch (e) {
    console.error('Error parsing chart data:', e);
    return;
  }
  
  // Create chart
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: chartData.labels,
      datasets: [
        {
          label: 'Upload (MB)',
          data: chartData.upload,
          backgroundColor: 'rgba(52, 152, 219, 0.7)',
          borderColor: 'rgba(52, 152, 219, 1)',
          borderWidth: 1
        },
        {
          label: 'Download (MB)',
          data: chartData.download,
          backgroundColor: 'rgba(231, 76, 60, 0.7)',
          borderColor: 'rgba(231, 76, 60, 1)',
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return value + ' MB';
            }
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ': ' + context.raw + ' MB';
            }
          }
        }
      }
    }
  });
}

/**
 * Update chart with new data (for real-time updates)
 * @param {string} chartId - The chart ID
 * @param {Array} labels - New labels
 * @param {Array} data - New data
 */
function updateChart(chartId, labels, data) {
  const chartInstance = Chart.getChart(chartId);
  if (!chartInstance) return;
  
  chartInstance.data.labels = labels;
  chartInstance.data.datasets[0].data = data;
  chartInstance.update();
}
