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

    // Update race-specific targets
    updateRaceTargets(data);
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

    // Check if we have race-gender data
    if (!data.race_gender_counts) {
        // Fall back to the original race pie chart if no detailed data
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
            raceChart.destroy();
        }

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

        return;
    }

    // Extract race and gender data for stacked bar chart
    const raceGenderCounts = data.race_gender_counts;

    // Get unique races and genders
    const races = new Set();
    const genders = new Set();

    Object.keys(raceGenderCounts).forEach(key => {
        const parts = key.split(' ');
        if (parts.length >= 2) {
            const race = parts.slice(0, -1).join(' '); // Everything except the last part
            const gender = parts[parts.length - 1]; // Last part is gender
            races.add(race);
            genders.add(gender);
        }
    });

    // Convert to arrays
    const raceLabels = Array.from(races);
    const genderLabels = Array.from(genders);

    // Create datasets (one for each gender)
    const datasets = genderLabels.map(gender => {
        const color = gender.toLowerCase().includes('female') ? 
            ['rgba(255, 99, 132, 0.7)', 'rgba(255, 99, 132, 1)'] : // Female
            ['rgba(54, 162, 235, 0.7)', 'rgba(54, 162, 235, 1)'];  // Male

        return {
            label: gender,
            data: raceLabels.map(race => {
                const key = `${race} ${gender}`;
                return raceGenderCounts[key] || 0;
            }),
            backgroundColor: color[0],
            borderColor: color[1],
            borderWidth: 1
        };
    });

    const chartData = {
        labels: raceLabels,
        datasets: datasets
    };

    if (raceChart) {
        raceChart.destroy();
    }

    raceChart = new Chart(ctx, {
        type: 'bar',
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
                            return `${context.dataset.label}: ${value}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
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
 * Update race-specific target cards
 */
function updateRaceTargets(data) {
    console.log("Race/Gender Data for Progress Bars:", data); // <-- Add this line
    const container = document.getElementById('race-targets-container');

    // Clear existing content
    container.innerHTML = '';

    // Check if we have race-gender data
    if (!data.race_gender_counts || !data.race_gender_targets) {
        container.innerHTML = '<div class="col-12"><div class="alert alert-info">No race-specific data available.</div></div>';
        return;
    }

    // Create a card for each race target
    Object.entries(data.race_gender_targets).forEach(([key, target]) => {
        const count = data.race_gender_counts[key] || 0;
        const progress = data.race_gender_progress[key] || 0;

        // Determine status color based on progress
        let statusClass = 'bg-danger';
        if (progress >= 100) {
            statusClass = 'bg-success';
        } else if (progress >= 75) {
            statusClass = 'bg-warning';
        }

        // Create card HTML
        const card = document.createElement('div');
        card.className = 'col-md-4 mb-3';
        card.innerHTML = `
            <div class="card h-100 border-light">
                <div class="card-body">
                    <h6 class="card-title">${key}</h6>
                    <div class="progress mb-2" style="height: 8px;">
                        <div class="progress-bar ${statusClass}" role="progressbar" 
                             style="width: ${Math.min(progress, 100)}%" 
                             aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <p class="mb-0 d-flex justify-content-between">
                        <span>${count} / ${target}</span>
                        <span class="text-muted">${progress.toFixed(1)}%</span>
                    </p>
                </div>
            </div>
        `;

        container.appendChild(card);
    });
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
