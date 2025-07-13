class TennisSimulator {
    constructor() {
        this.socket = io();
        this.players = [];
        this.currentChart = null;
        this.isSimulating = false;
        this.startTime = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadPlayers();
        this.setupUIInteractions();
    }
    
    initializeElements() {
        // Form elements
        this.player1Select = document.getElementById('player1Select');
        this.player2Select = document.getElementById('player2Select');
        this.numTrialsInput = document.getElementById('numTrials');
        this.decreaseTrialsBtn = document.getElementById('decreaseTrials');
        this.increaseTrialsBtn = document.getElementById('increaseTrials');
        this.simulateBtn = document.getElementById('simulateBtn');
        this.runAnotherBtn = document.getElementById('runAnotherBtn');
        this.retryBtn = document.getElementById('retryBtn');
        
        // Section elements
        this.simulationSetup = document.getElementById('simulationSetup');
        this.progressSection = document.getElementById('progressSection');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorSection = document.getElementById('errorSection');
        this.warningsSection = document.getElementById('warningsSection');
        
        // Progress elements
        this.progressRing = document.getElementById('progressRing');
        this.progressPercentage = document.getElementById('progressPercentage');
        this.progressText = document.getElementById('progressText');
        this.simulationSpeed = document.getElementById('simulationSpeed');
        this.simulationETA = document.getElementById('simulationETA');
        
        // Unified dashboard elements
        this.player1Name = document.getElementById('player1Name');
        this.player2Name = document.getElementById('player2Name');
        this.matchFormat = document.getElementById('matchFormat');
        this.simulationSummary = document.getElementById('simulationSummary');
        this.warningsList = document.getElementById('warningsList');
        this.errorMessage = document.getElementById('errorMessage');
        
        // Surface-specific results elements
        this.hardResults = {
            player1Name: document.getElementById('hardPlayer1Name'),
            player2Name: document.getElementById('hardPlayer2Name'),
            player1Pct: document.getElementById('hardPlayer1Pct'),
            player2Pct: document.getElementById('hardPlayer2Pct'),
            player1Record: document.getElementById('hardPlayer1Record'),
            player2Record: document.getElementById('hardPlayer2Record'),
            chart: document.getElementById('hardChart')
        };
        
        this.clayResults = {
            player1Name: document.getElementById('clayPlayer1Name'),
            player2Name: document.getElementById('clayPlayer2Name'),
            player1Pct: document.getElementById('clayPlayer1Pct'),
            player2Pct: document.getElementById('clayPlayer2Pct'),
            player1Record: document.getElementById('clayPlayer1Record'),
            player2Record: document.getElementById('clayPlayer2Record'),
            chart: document.getElementById('clayChart')
        };
        
        this.grassResults = {
            player1Name: document.getElementById('grassPlayer1Name'),
            player2Name: document.getElementById('grassPlayer2Name'),
            player1Pct: document.getElementById('grassPlayer1Pct'),
            player2Pct: document.getElementById('grassPlayer2Pct'),
            player1Record: document.getElementById('grassPlayer1Record'),
            player2Record: document.getElementById('grassPlayer2Record'),
            chart: document.getElementById('grassChart')
        };
        
        // Store surface charts
        this.surfaceCharts = {
            hard: null,
            clay: null,
            grass: null
        };
    }
    
    setupEventListeners() {
        // Button event listeners
        this.simulateBtn.addEventListener('click', () => this.startSimulation());
        this.runAnotherBtn.addEventListener('click', () => this.resetSimulation());
        this.retryBtn.addEventListener('click', () => this.resetSimulation());
        
        // Socket event listeners
        this.socket.on('connected', (data) => {
            console.log('Connected to server:', data.status);
        });
        
        this.socket.on('simulation_started', (data) => {
            console.log('Simulation started:', data.status);
            this.startTime = Date.now();
        });
        
        this.socket.on('simulation_progress', (data) => {
            this.updateProgress(data.completed, data.total, data.progress);
        });
        
        this.socket.on('simulation_complete', (data) => {
            this.displayResults(data);
        });
        
        this.socket.on('simulation_error', (data) => {
            this.displayError(data.error);
        });
        
        // Player selection change listeners
        this.player1Select.addEventListener('change', () => this.validateForm());
        this.player2Select.addEventListener('change', () => this.validateForm());
        
        // Trial count control listeners
        this.decreaseTrialsBtn.addEventListener('click', () => this.adjustTrialCount(-1));
        this.increaseTrialsBtn.addEventListener('click', () => this.adjustTrialCount(1));
        this.numTrialsInput.addEventListener('change', () => this.validateTrialCount());
    }
    
    setupUIInteractions() {
        // Format option interactions
        const formatOptions = document.querySelectorAll('.format-option');
        formatOptions.forEach(option => {
            option.addEventListener('click', () => {
                formatOptions.forEach(opt => opt.classList.remove('active'));
                option.classList.add('active');
                const radio = option.querySelector('input[type="radio"]');
                radio.checked = true;
            });
        });
        
        // Add SVG gradient definition for progress ring
        this.addProgressGradient();
    }
    
    addProgressGradient() {
        const svg = this.progressRing.closest('svg');
        if (svg && !svg.querySelector('defs')) {
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
            gradient.setAttribute('id', 'progressGradient');
            gradient.setAttribute('x1', '0%');
            gradient.setAttribute('y1', '0%');
            gradient.setAttribute('x2', '100%');
            gradient.setAttribute('y2', '0%');
            
            const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop1.setAttribute('offset', '0%');
            stop1.setAttribute('stop-color', '#667eea');
            
            const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop2.setAttribute('offset', '100%');
            stop2.setAttribute('stop-color', '#764ba2');
            
            gradient.appendChild(stop1);
            gradient.appendChild(stop2);
            defs.appendChild(gradient);
            svg.appendChild(defs);
        }
    }
    
    async loadPlayers() {
        try {
            const response = await fetch('/api/players');
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.players = data.players;
            this.populatePlayerSelects();
        } catch (error) {
            console.error('Failed to load players:', error);
            this.displayError('Failed to load player data. Please refresh the page.');
        }
    }
    
    populatePlayerSelects() {
        // Clear existing options
        this.player1Select.innerHTML = '<option value="">Select Player 1</option>';
        this.player2Select.innerHTML = '<option value="">Select Player 2</option>';
        
        // Add player options
        this.players.forEach(player => {
            const option1 = new Option(`${player.ranking}. ${player.name}`, player.name);
            const option2 = new Option(`${player.ranking}. ${player.name}`, player.name);
            
            this.player1Select.appendChild(option1);
            this.player2Select.appendChild(option2);
        });
        
        this.validateForm();
    }
    
    validateForm() {
        const player1 = this.player1Select.value;
        const player2 = this.player2Select.value;
        
        const isValid = player1 && player2 && player1 !== player2 && !this.isSimulating;
        this.simulateBtn.disabled = !isValid;
        
        if (player1 && player2 && player1 === player2) {
            this.simulateBtn.textContent = 'Please select different players';
        } else if (this.isSimulating) {
            this.simulateBtn.textContent = 'Simulating...';
        } else {
            this.simulateBtn.textContent = 'Simulate Match';
        }
    }
    
    getFormData() {
        const format = document.querySelector('input[name="format"]:checked').value;
        
        return {
            player1: this.player1Select.value,
            player2: this.player2Select.value,
            format: format,
            num_simulations: parseInt(this.numTrialsInput.value)
        };
    }
    
    adjustTrialCount(delta) {
        const current = parseInt(this.numTrialsInput.value);
        const newValue = Math.max(1, Math.min(10000, current + delta));
        this.numTrialsInput.value = newValue;
        this.validateTrialCount();
    }
    
    validateTrialCount() {
        const value = parseInt(this.numTrialsInput.value);
        if (isNaN(value) || value < 1) {
            this.numTrialsInput.value = 1;
        } else if (value > 10000) {
            this.numTrialsInput.value = 10000;
        }
    }
    
    startSimulation() {
        if (this.isSimulating) return;
        
        const formData = this.getFormData();
        
        if (!formData.player1 || !formData.player2) {
            this.displayError('Please select both players');
            return;
        }
        
        if (formData.player1 === formData.player2) {
            this.displayError('Please select different players');
            return;
        }
        
        this.isSimulating = true;
        this.hideAllSections();
        this.showProgressSection();
        this.disableForm();
        
        // Start simulation via WebSocket
        this.socket.emit('start_simulation', formData);
    }
    
    updateProgress(completed, total, progress) {
        // Update circular progress ring
        const circumference = 2 * Math.PI * 50; // radius = 50
        const offset = circumference - (progress / 100) * circumference;
        this.progressRing.style.strokeDashoffset = offset;
        
        // Update progress text
        this.progressPercentage.textContent = `${Math.round(progress)}%`;
        this.progressText.textContent = `${completed} of ${total} matches completed`;
        
        // Calculate and display speed and ETA
        if (this.startTime && completed > 0) {
            const elapsed = (Date.now() - this.startTime) / 1000; // seconds
            const speed = completed / elapsed;
            const remaining = total - completed;
            const eta = remaining / speed;
            
            this.simulationSpeed.textContent = `${speed.toFixed(1)} matches/sec`;
            
            if (eta < 60) {
                this.simulationETA.textContent = `${Math.round(eta)}s`;
            } else {
                const minutes = Math.floor(eta / 60);
                const seconds = Math.round(eta % 60);
                this.simulationETA.textContent = `${minutes}m ${seconds}s`;
            }
        }
    }
    
    displayResults(data) {
        this.isSimulating = false;
        this.enableForm();
        this.validateForm();
        
        // Update player names and overview
        this.player1Name.textContent = data.player1_name;
        this.player2Name.textContent = data.player2_name;
        
        // Update match format
        const formatNames = { best3: 'Best of 3', best5: 'Best of 5' };
        this.matchFormat.textContent = formatNames[data.format];
        
        // Update simulation summary
        this.simulationSummary.textContent = `${data.num_simulations} simulations across all court surfaces`;
        
        // Display parameter comparison table
        this.displayParameterTable(data);
        
        // Display surface-specific results
        this.displaySurfaceResults(data);
        
        // Display warnings if any
        if (data.fallback_warnings && data.fallback_warnings.length > 0) {
            this.warningsList.innerHTML = '';
            data.fallback_warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning;
                this.warningsList.appendChild(li);
            });
            this.warningsSection.style.display = 'block';
        } else {
            this.warningsSection.style.display = 'none';
        }
        
        this.hideAllSections();
        this.showResultsSection();
    }
    
    displayParameterTable(data) {
        const parametersContent = document.getElementById('parametersContent');
        parametersContent.innerHTML = '';
        
        const categories = [
            {
                name: 'Serving Performance',
                icon: '🎾',
                parameters: [
                    { key: 'first_serve_in_pct', name: 'First Serve In %', betterDirection: 'higher' },
                    { key: 'first_serve_win_pct', name: 'First Serve Win %', betterDirection: 'higher' },
                    { key: 'second_serve_in_pct', name: 'Second Serve In %', betterDirection: 'higher' },
                    { key: 'second_serve_win_pct', name: 'Second Serve Win %', betterDirection: 'higher' }
                ]
            },
            {
                name: 'Returning Performance',
                icon: '🔄',
                parameters: [
                    { key: 'vs_first_serve_win_pct', name: 'vs First Serve Win %', betterDirection: 'higher' },
                    { key: 'vs_second_serve_win_pct', name: 'vs Second Serve Win %', betterDirection: 'higher' }
                ]
            },
            {
                name: 'Break Points',
                icon: '💥',
                parameters: [
                    { key: 'break_point_save_pct', name: 'Break Point Save %', betterDirection: 'higher' },
                    { key: 'break_point_conversion_pct', name: 'Break Point Conversion %', betterDirection: 'higher' }
                ]
            }
        ];
        
        categories.forEach(category => {
            const categoryDiv = this.createParameterCategory(category, data);
            parametersContent.appendChild(categoryDiv);
        });
    }
    
    createParameterCategory(category, data) {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'parameter-category';
        
        // Category header
        const header = document.createElement('div');
        header.className = 'category-header';
        header.innerHTML = `
            <h4 class="category-title">
                <span>${category.icon}</span>
                ${category.name}
            </h4>
        `;
        categoryDiv.appendChild(header);
        
        // Create surface groups
        const surfaces = ['hard', 'clay', 'grass'];
        const surfaceNames = { hard: 'Hard Court', clay: 'Clay Court', grass: 'Grass Court' };
        const surfaceEmojis = { hard: '🏟️', clay: '🟤', grass: '🌱' };
        
        surfaces.forEach(surface => {
            const surfaceData = data.surfaces[surface];
            const surfaceGroup = document.createElement('div');
            surfaceGroup.className = 'surface-group';
            
            // Surface header
            const surfaceHeader = document.createElement('div');
            surfaceHeader.className = `surface-header ${surface}`;
            surfaceHeader.innerHTML = `
                <span>${surfaceEmojis[surface]}</span>
                ${surfaceNames[surface]}
            `;
            surfaceGroup.appendChild(surfaceHeader);
            
            // Parameters table
            const table = document.createElement('table');
            table.className = 'parameters-table';
            
            // Table header
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th class="parameter-name">Parameter</th>
                    <th colspan="4" style="text-align: center;">${data.player1_name}</th>
                    <th colspan="4" style="text-align: center;">${data.player2_name}</th>
                </tr>
                <tr>
                    <th></th>
                    <th class="value-label">Expected</th>
                    <th class="value-label">Observed</th>
                    <th class="value-label">Diff</th>
                    <th class="value-label">Performance</th>
                    <th class="value-label">Expected</th>
                    <th class="value-label">Observed</th>
                    <th class="value-label">Diff</th>
                    <th class="value-label">Performance</th>
                </tr>
            `;
            table.appendChild(thead);
            
            // Table body
            const tbody = document.createElement('tbody');
            category.parameters.forEach(param => {
                const row = this.createParameterRow(param, surfaceData, data.player1_name, data.player2_name);
                tbody.appendChild(row);
            });
            table.appendChild(tbody);
            
            surfaceGroup.appendChild(table);
            categoryDiv.appendChild(surfaceGroup);
        });
        
        return categoryDiv;
    }
    
    createParameterRow(param, surfaceData, player1Name, player2Name) {
        const row = document.createElement('tr');
        
        // Parameter name
        const nameCell = document.createElement('td');
        nameCell.className = 'parameter-name';
        nameCell.textContent = param.name;
        row.appendChild(nameCell);
        
        // Player 1 data
        const p1Expected = surfaceData.input_parameters.player1[param.key];
        const p1Observed = surfaceData.observed_stats?.player1?.[param.key];
        const p1Cells = this.createPlayerCells(p1Expected, p1Observed, param.betterDirection);
        p1Cells.forEach(cell => row.appendChild(cell));
        
        // Player 2 data
        const p2Expected = surfaceData.input_parameters.player2[param.key];
        const p2Observed = surfaceData.observed_stats?.player2?.[param.key];
        const p2Cells = this.createPlayerCells(p2Expected, p2Observed, param.betterDirection);
        p2Cells.forEach(cell => row.appendChild(cell));
        
        return row;
    }
    
    createPlayerCells(expected, observed, betterDirection) {
        const cells = [];
        
        // Expected value
        const expectedCell = document.createElement('td');
        expectedCell.className = 'expected-value';
        expectedCell.textContent = `${(expected * 100).toFixed(1)}%`;
        cells.push(expectedCell);
        
        // Observed value
        const observedCell = document.createElement('td');
        observedCell.className = 'observed-value';
        observedCell.textContent = observed !== undefined ? `${(observed * 100).toFixed(1)}%` : 'N/A';
        cells.push(observedCell);
        
        // Difference and Performance
        let difference = '';
        let performanceClass = 'performance-neutral';
        let performanceText = 'N/A';
        
        if (observed !== undefined && observed !== null) {
            const diff = observed - expected;
            
            if (betterDirection === 'higher') {
                if (diff > 0.01) {
                    performanceClass = 'performance-better';
                    performanceText = 'Better';
                } else if (diff < -0.01) {
                    performanceClass = 'performance-worse';
                    performanceText = 'Worse';
                } else {
                    performanceClass = 'performance-neutral';
                    performanceText = 'Similar';
                }
            } else { // lower is better
                if (diff < -0.01) {
                    performanceClass = 'performance-better';
                    performanceText = 'Better';
                } else if (diff > 0.01) {
                    performanceClass = 'performance-worse';
                    performanceText = 'Worse';
                } else {
                    performanceClass = 'performance-neutral';
                    performanceText = 'Similar';
                }
            }
            
            difference = `${diff >= 0 ? '+' : ''}${(diff * 100).toFixed(1)}%`;
        }
        
        // Difference cell
        const diffCell = document.createElement('td');
        diffCell.className = 'difference-value';
        diffCell.textContent = difference;
        cells.push(diffCell);
        
        // Performance cell
        const perfCell = document.createElement('td');
        perfCell.innerHTML = `<span class="performance-indicator ${performanceClass}">${performanceText}</span>`;
        cells.push(perfCell);
        
        return cells;
    }
    
    displaySurfaceResults(data) {
        const surfaces = ['hard', 'clay', 'grass'];
        
        surfaces.forEach(surface => {
            const surfaceData = data.surfaces[surface];
            const results = this[`${surface}Results`];
            
            // Update player names
            results.player1Name.textContent = data.player1_name;
            results.player2Name.textContent = data.player2_name;
            
            // Update win percentages
            const p1WinPct = surfaceData.player1_win_pct * 100;
            const p2WinPct = surfaceData.player2_win_pct * 100;
            
            results.player1Pct.textContent = `${p1WinPct.toFixed(1)}%`;
            results.player2Pct.textContent = `${p2WinPct.toFixed(1)}%`;
            
            // Update win records
            results.player1Record.textContent = `${surfaceData.player1_wins} wins`;
            results.player2Record.textContent = `${surfaceData.player2_wins} wins`;
            
            // Create mini chart for this surface
            this.createSurfaceChart(surface, surfaceData.set_distributions);
        });
    }
    
    createSurfaceChart(surface, setDistributions) {
        // Destroy existing chart if it exists
        if (this.surfaceCharts[surface]) {
            this.surfaceCharts[surface].destroy();
        }
        
        // Prepare data for mini chart
        const labels = Object.keys(setDistributions).sort();
        const data = labels.map(label => setDistributions[label]);
        
        const results = this[`${surface}Results`];
        const ctx = results.chart.getContext('2d');
        
        this.surfaceCharts[surface] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Matches',
                    data: data,
                    backgroundColor: `hsla(${surface === 'hard' ? 220 : surface === 'clay' ? 15 : 120}, 70%, 60%, 0.8)`,
                    borderColor: `hsla(${surface === 'hard' ? 220 : surface === 'clay' ? 15 : 120}, 70%, 50%, 1)`,
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: '#667eea',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#6b7280',
                            font: {
                                family: 'Inter',
                                size: 10
                            }
                        },
                        grid: {
                            color: 'rgba(107, 114, 128, 0.1)',
                            drawBorder: false
                        }
                    },
                    x: {
                        ticks: {
                            color: '#6b7280',
                            font: {
                                family: 'Inter',
                                size: 10
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                animation: {
                    duration: 800,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }
    
    createSetChart(setDistributions) {
        // Destroy existing chart if it exists
        if (this.currentChart) {
            this.currentChart.destroy();
        }
        
        // Prepare data for chart
        const labels = Object.keys(setDistributions).sort();
        const data = labels.map(label => setDistributions[label]);
        
        const ctx = this.setChartCanvas.getContext('2d');
        this.currentChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of Matches',
                    data: data,
                    backgroundColor: labels.map((_, index) => 
                        `hsla(${240 + index * 30}, 70%, 60%, 0.8)`
                    ),
                    borderColor: labels.map((_, index) => 
                        `hsla(${240 + index * 30}, 70%, 50%, 1)`
                    ),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: '#667eea',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.raw} matches (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#6b7280',
                            font: {
                                family: 'Inter',
                                size: 12
                            }
                        },
                        grid: {
                            color: 'rgba(107, 114, 128, 0.1)',
                            drawBorder: false
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Final Set Score',
                            color: '#374151',
                            font: {
                                family: 'Inter',
                                size: 14,
                                weight: 600
                            }
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                family: 'Inter',
                                size: 12
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }
    
    displayError(message) {
        this.isSimulating = false;
        this.enableForm();
        this.validateForm();
        
        this.errorMessage.textContent = message;
        this.hideAllSections();
        this.showErrorSection();
    }
    
    resetSimulation() {
        this.hideAllSections();
        this.showSimulationSetup();
        this.enableForm();
        this.validateForm();
        
        // Reset progress
        this.progressRing.style.strokeDashoffset = '314';
        this.progressPercentage.textContent = '0%';
        const numTrials = this.numTrialsInput.value;
        this.progressText.textContent = `0 of ${numTrials} matches completed`;
        this.simulationSpeed.textContent = '-- matches/sec';
        this.simulationETA.textContent = '--';
        this.startTime = null;
    }
    
    hideAllSections() {
        this.simulationSetup.style.display = 'none';
        this.progressSection.style.display = 'none';
        this.resultsSection.style.display = 'none';
        this.errorSection.style.display = 'none';
    }
    
    showSimulationSetup() {
        this.simulationSetup.style.display = 'block';
    }
    
    showProgressSection() {
        this.progressSection.style.display = 'block';
    }
    
    showResultsSection() {
        this.resultsSection.style.display = 'block';
    }
    
    showErrorSection() {
        this.errorSection.style.display = 'block';
    }
    
    disableForm() {
        this.player1Select.disabled = true;
        this.player2Select.disabled = true;
        this.numTrialsInput.disabled = true;
        this.decreaseTrialsBtn.disabled = true;
        this.increaseTrialsBtn.disabled = true;
        this.simulateBtn.disabled = true;
        
        const radioInputs = document.querySelectorAll('input[type="radio"]');
        radioInputs.forEach(input => input.disabled = true);
    }
    
    enableForm() {
        this.player1Select.disabled = false;
        this.player2Select.disabled = false;
        this.numTrialsInput.disabled = false;
        this.decreaseTrialsBtn.disabled = false;
        this.increaseTrialsBtn.disabled = false;
        
        const radioInputs = document.querySelectorAll('input[type="radio"]');
        radioInputs.forEach(input => input.disabled = false);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TennisSimulator();
});