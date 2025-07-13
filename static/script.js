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
        this.simulateBtn = document.getElementById('simulateBtn');
        this.runAnotherBtn = document.getElementById('runAnotherBtn');
        this.retryBtn = document.getElementById('retryBtn');
        
        // Section elements
        this.simulationSetup = document.getElementById('simulationSetup');
        this.progressSection = document.getElementById('progressSection');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorSection = document.getElementById('errorSection');
        this.warningsSection = document.getElementById('warningsSection');
        
        // Progress elements (updated for new design)
        this.progressRing = document.getElementById('progressRing');
        this.progressPercentage = document.getElementById('progressPercentage');
        this.progressText = document.getElementById('progressText');
        this.simulationSpeed = document.getElementById('simulationSpeed');
        this.simulationETA = document.getElementById('simulationETA');
        
        // Results elements
        this.player1Name = document.getElementById('player1Name');
        this.player2Name = document.getElementById('player2Name');
        this.player1WinPct = document.getElementById('player1WinPct');
        this.player2WinPct = document.getElementById('player2WinPct');
        this.player1Record = document.getElementById('player1Record');
        this.player2Record = document.getElementById('player2Record');
        this.player1Confidence = document.getElementById('player1Confidence');
        this.player2Confidence = document.getElementById('player2Confidence');
        this.matchSurface = document.getElementById('matchSurface');
        this.matchFormat = document.getElementById('matchFormat');
        this.warningsList = document.getElementById('warningsList');
        this.errorMessage = document.getElementById('errorMessage');
        
        // Chart canvas
        this.setChartCanvas = document.getElementById('setChart');
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
    }
    
    setupUIInteractions() {
        // Surface option interactions
        const surfaceOptions = document.querySelectorAll('.surface-option');
        surfaceOptions.forEach(option => {
            option.addEventListener('click', () => {
                surfaceOptions.forEach(opt => opt.classList.remove('active'));
                option.classList.add('active');
                const radio = option.querySelector('input[type="radio"]');
                radio.checked = true;
            });
        });
        
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
        const surface = document.querySelector('input[name="surface"]:checked').value;
        const format = document.querySelector('input[name="format"]:checked').value;
        
        return {
            player1: this.player1Select.value,
            player2: this.player2Select.value,
            surface: surface,
            format: format
        };
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
        
        const formData = this.getFormData();
        
        // Update player names
        this.player1Name.textContent = formData.player1;
        this.player2Name.textContent = formData.player2;
        
        // Update win percentages
        const p1WinPct = data.player1_win_pct * 100;
        const p2WinPct = data.player2_win_pct * 100;
        this.player1WinPct.textContent = `${p1WinPct.toFixed(1)}%`;
        this.player2WinPct.textContent = `${p2WinPct.toFixed(1)}%`;
        
        // Update win records
        this.player1Record.textContent = `${data.player1_wins} wins out of ${data.total_simulations}`;
        this.player2Record.textContent = `${data.player2_wins} wins out of ${data.total_simulations}`;
        
        // Update confidence bars
        this.player1Confidence.style.width = `${p1WinPct}%`;
        this.player2Confidence.style.width = `${p2WinPct}%`;
        
        // Update match details
        const surfaceNames = { hard: 'Hard Court', clay: 'Clay', grass: 'Grass' };
        const formatNames = { best3: 'Best of 3', best5: 'Best of 5' };
        this.matchSurface.textContent = surfaceNames[formData.surface];
        this.matchFormat.textContent = formatNames[formData.format];
        
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
        
        // Create set distribution chart
        this.createSetChart(data.set_distributions);
        
        this.hideAllSections();
        this.showResultsSection();
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
        this.progressText.textContent = '0 of 1000 matches completed';
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
        this.simulateBtn.disabled = true;
        
        const radioInputs = document.querySelectorAll('input[type="radio"]');
        radioInputs.forEach(input => input.disabled = true);
    }
    
    enableForm() {
        this.player1Select.disabled = false;
        this.player2Select.disabled = false;
        
        const radioInputs = document.querySelectorAll('input[type="radio"]');
        radioInputs.forEach(input => input.disabled = false);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TennisSimulator();
});