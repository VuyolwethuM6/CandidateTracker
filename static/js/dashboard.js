document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    loadDashboardData();
    
    // Set up refresh interval (every 30 seconds)
    setInterval(loadDashboardData, 30000);
});

// Chart instances
let genderChart, pwdChart, raceChart, programChart, institutionChart;

/**
 * Load dashboard data from API
 */
function loadDashboardData() {
    fetch('/api/dashboard/metrics')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading, show content
            document.getElementById('dashboard-loading').style.display = 'none';
            document.getElementById('dashboard-content').style.display = 'block';
            
            // Check if data is empty
            if (data.total_candidates === 0) {
                document.getElementById('no-data-message').style.display = 'block';
                return;
            } else {
                document.getElementById('no-data-message').style.display = 'none';
            }
            
            // Update metrics
            updateMetricsCards(data);
            
            // Update charts
            updateCharts(data);
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            document.getElementById('dashboard-loading').style.display = 'none';
            document.getElementById('dashboard-content').style.display = 'block';
            document.getElementById('no-data-message').style.display = 'block';
        });
}

/**
 * Update metrics cards with data
 */
function updateMetricsCards(data) {
    const totalTarget = 600;
    
    // Total candidates card
    document.getElementById('total-count').textContent = data.total_candidates;
    document.getElementById('total-target').textContent = totalTarget;
    document.getElementById('total-percent').textContent = `${data.total_percent.toFixed(1)}%`;
    
    const totalProgress = document.getElementById('total-progress');
    totalProgress.style.width = `${data.total_percent}%`;
    totalProgress.classList.add(data.total_percent >= 100 ? 'bg-success' : 'bg-primary');
    
    // Female candidates card
    document.getElementById('female-count').textContent = data.female_count;
    document.getElementById('total-for-female').textContent = data.total_candidates;
    document.getElementById('female-percent').textContent = `${data.female_percent.toFixed(1)}%`;
    
    const femaleProgress = document.getElementById('female-progress');
    femaleProgress.style.width = `${data.female_percent}%`;
    
    const femaleCard = document.getElementById('female-card');
    if (data.female_percent >= 65) {
        femaleCard.className = 'card h-100 card-status-good';
        femaleProgress.className = 'progress-bar progress-bar-striped bg-success';
    } else if (data.female_percent >= 60) {
        femaleCard.className = 'card h-100 card-status-warning';
        femaleProgress.className = 'progress-bar progress-bar-striped bg-warning';
    } else {
        femaleCard.className = 'card h-100 card-status-danger';
        femaleProgress.className = 'progress-bar progress-bar-striped bg-danger';
    }
    
    // PWD candidates card
    document.getElementById('pwd-count').textContent = data.pwd_count;
    document.getElementById('total-for-pwd').textContent = data.total_candidates;
    document.getElementById('pwd-percent').textContent = `${data.pwd_percent.toFixed(1)}%`;
    
    const pwdProgress = document.getElementById('pwd-progress');
    pwdProgress.style.width = `${data.pwd_percent}%`;
    
    const pwdCard = document.getElementById('pwd-card');
    if (data.pwd_percent >= 5) {
        pwdCard.className = 'card h-100 card-status-good';
        pwdProgress.className = 'progress-bar progress-bar-striped bg-success';
    } else if (data.pwd_percent >= 3.5) {
        pwdCard.className = 'card h-100 card-status-warning';
        pwdProgress.className = 'progress-bar progress-bar-striped bg-warning';
    } else {
        pwdCard.className = 'card h-100 card-status-danger';
        pwdProgress.className = 'progress-bar progress-bar-striped bg-danger';
    }
}

/**
 * Update all charts with data
 */
function updateCharts(data) {
    updateGenderChart(data);
    updatePwdChart(data);
    updateRaceChart(data);
    updateProgramChart(data);
    updateInstitutionChart(data);
}

/**
 * Update race distribution chart
 */
function updateRaceChart(data) {
    const ctx = document.getElementById('raceChart').getContext('2d');
    
    // Get race data
    const races = data.race_counts || {};
    const raceLabels = Object.keys(races);
    const raceCounts = Object.values(races);
    
    // Define a color palette for race pie chart
    const backgroundColors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(199, 199, 199, 0.7)'
    ];
    
    const borderColors = [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(199, 199, 199, 1)'
    ];
    
    // Create background and border color arrays matching the number of race categories
    const bgColors = raceLabels.map((_, i) => backgroundColors[i % backgroundColors.length]);
    const bdColors = raceLabels.map((_, i) => borderColors[i % borderColors.length]);
    
    const chartData = {
        labels: raceLabels,
        datasets: [{
            data: raceCounts,
            backgroundColor: bgColors,
            borderColor: bdColors,
            borderWidth: 1
        }]
    };
    
    if (raceChart) {
        raceChart.data = chartData;
        raceChart.update();
    } else {
        raceChart = new Chart(ctx, {
            type: 'pie',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update gender distribution chart
 */
function updateGenderChart(data) {
    const ctx = document.getElementById('genderChart').getContext('2d');
    console.log(data.male_count - data.female_count);
    
    const chartData = {
        labels: ['Female', 'Male'],
        datasets: [{
            data: [data.female_count, data.male_count - data.female_count],
            backgroundColor: ['rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)'],
            borderColor: ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)'],
            borderWidth: 1
        }]
    };
    
    if (genderChart) {
        genderChart.data = chartData;
        genderChart.update();
    } else {
        genderChart = new Chart(ctx, {
            type: 'pie',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update PWD status chart
 */
function updatePwdChart(data) {
    const ctx = document.getElementById('pwdChart').getContext('2d');
    
    const chartData = {
        labels: ['PWD', 'Non-PWD'],
        datasets: [{
            data: [data.pwd_count, data.total_candidates - data.pwd_count],
            backgroundColor: ['rgba(255, 159, 64, 0.7)', 'rgba(153, 102, 255, 0.7)'],
            borderColor: ['rgba(255, 159, 64, 1)', 'rgba(153, 102, 255, 1)'],
            borderWidth: 1
        }]
    };
    
    if (pwdChart) {
        pwdChart.data = chartData;
        pwdChart.update();
    } else {
        pwdChart = new Chart(ctx, {
            type: 'pie',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update program distribution chart
 */
function updateProgramChart(data) {
    const ctx = document.getElementById('programChart').getContext('2d');
    
    // Get program data
    const programs = data.program_counts || {};
    const programLabels = Object.keys(programs);
    const programCounts = Object.values(programs);
    
    const chartData = {
        labels: programLabels,
        datasets: [{
            label: 'Candidates',
            data: programCounts,
            backgroundColor: 'rgba(75, 192, 192, 0.7)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }]
    };
    
    if (programChart) {
        programChart.data = chartData;
        programChart.update();
    } else {
        programChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Candidates'
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update institution distribution chart
 */
function updateInstitutionChart(data) {
    const ctx = document.getElementById('institutionChart').getContext('2d');
    
    // Get institution data
    const institutions = data.institution_counts || {};
    const institutionLabels = Object.keys(institutions);
    const institutionCounts = Object.values(institutions);
    
    const chartData = {
        labels: institutionLabels,
        datasets: [{
            label: 'Candidates',
            data: institutionCounts,
            backgroundColor: 'rgba(153, 102, 255, 0.7)',
            borderColor: 'rgba(153, 102, 255, 1)',
            borderWidth: 1
        }]
    };
    
    if (institutionChart) {
        institutionChart.data = chartData;
        institutionChart.update();
    } else {
        institutionChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Candidates'
                        }
                    },
                    x: {
                        ticks: {
                            callback: function(val, index) {
                                // Truncate institution names if they're too long
                                const label = this.getLabelForValue(val);
                                if (label.length > 15) {
                                    return label.substr(0, 15) + '...';
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
}
