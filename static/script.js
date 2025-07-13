class TennisSimulator {
    constructor() {
        this.socket = io();
        this.players = [];
        this.currentChart = null;
        this.isSimulating = false;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadPlayers();
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
        
        // Progress elements
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        
        // Results elements
        this.player1Name = document.getElementById('player1Name');
        this.player2Name = document.getElementById('player2Name');
        this.player1WinPct = document.getElementById('player1WinPct');
        this.player2WinPct = document.getElementById('player2WinPct');
        this.player1Record = document.getElementById('player1Record');
        this.player2Record = document.getElementById('player2Record');
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
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = `${Math.round(progress)}% (${completed}/${total} matches)`;
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
        this.player1WinPct.textContent = `${(data.player1_win_pct * 100).toFixed(1)}%`;
        this.player2WinPct.textContent = `${(data.player2_win_pct * 100).toFixed(1)}%`;
        
        // Update win records
        this.player1Record.textContent = `${data.player1_wins} wins out of ${data.total_simulations}`;
        this.player2Record.textContent = `${data.player2_wins} wins out of ${data.total_simulations}`;
        
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
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
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
                            stepSize: 1
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Final Set Score'
                        }
                    }
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
        this.progressFill.style.width = '0%';
        this.progressText.textContent = '0% (0/1000 matches)';
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