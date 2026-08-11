/**
 * Tennis Simulator - Vercel Compatible Version
 * Uses simple fetch API instead of WebSockets
 */

class TennisSimulator {
    constructor() {
        this.players = [];
        this.currentChart = null;
        this.isSimulating = false;
        this.dashboardGeneration = 0;

        this.initializeElements();
        this.setupEventListeners();
        this.loadPlayers();
        this.loadUpcomingMatches();
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
        this.refreshUpcomingBtn = document.getElementById('refreshUpcomingBtn');

        // Section elements
        this.simulationSetup = document.getElementById('simulationSetup');
        this.loadingSection = document.getElementById('loadingSection');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorSection = document.getElementById('errorSection');
        this.warningsSection = document.getElementById('warningsSection');

        // Unified dashboard elements
        this.player1Name = document.getElementById('player1Name');
        this.player2Name = document.getElementById('player2Name');
        this.matchFormat = document.getElementById('matchFormat');
        this.simulationSummary = document.getElementById('simulationSummary');
        this.warningsList = document.getElementById('warningsList');
        this.errorMessage = document.getElementById('errorMessage');
        this.marketComparisonContent = document.getElementById('marketComparisonContent');
        this.upcomingMatches = document.getElementById('upcomingMatches');
        this.upcomingSummary = document.getElementById('upcomingSummary');
        this.upcomingErrors = document.getElementById('upcomingErrors');

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
        this.refreshUpcomingBtn.addEventListener('click', () => this.loadUpcomingMatches());

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
        const step = 100;
        const newValue = Math.max(100, Math.min(10000, current + (delta * step)));
        this.numTrialsInput.value = newValue;
        this.validateTrialCount();
    }

    validateTrialCount() {
        const value = parseInt(this.numTrialsInput.value);
        if (isNaN(value) || value < 100) {
            this.numTrialsInput.value = 100;
        } else if (value > 10000) {
            this.numTrialsInput.value = 10000;
        }
    }

    async startSimulation() {
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
        this.showLoadingSection();
        this.disableForm();

        try {
            // Make API call
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'Simulation failed');
            }

            this.displayResults(data);
        } catch (error) {
            console.error('Simulation error:', error);
            this.displayError(error.message || 'Simulation failed. Please try again.');
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
        this.simulationSummary.textContent =
            `${data.total_simulations.toLocaleString()} simulated matches ` +
            `(${data.num_simulations.toLocaleString()} per surface), seed ${data.seed}`;

        // Display parameter comparison table
        this.displayParameterTable(data);

        // Display surface-specific results
        this.displaySurfaceResults(data);

        // Display live market prices and model differences
        this.displayMarketComparison(data);

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

    async loadUpcomingMatches() {
        const generation = ++this.dashboardGeneration;
        this.refreshUpcomingBtn.disabled = true;
        this.upcomingSummary.textContent = 'Loading the next seven days of market-listed matches…';
        try {
            const response = await fetch('/api/upcoming?days=7');
            const data = await response.json();
            if (!response.ok || data.error) throw new Error(data.error || 'Unable to load matches');
            if (generation !== this.dashboardGeneration) return;
            this.renderUpcomingMatches(data, generation);
        } catch (error) {
            if (generation !== this.dashboardGeneration) return;
            this.upcomingMatches.replaceChildren();
            const message = document.createElement('p');
            message.className = 'market-unavailable';
            message.textContent = 'Upcoming matches are temporarily unavailable. You can still run a manual simulation below.';
            this.upcomingMatches.appendChild(message);
            this.upcomingSummary.textContent = 'Live schedule unavailable';
        } finally {
            if (generation === this.dashboardGeneration) this.refreshUpcomingBtn.disabled = false;
        }
    }

    renderUpcomingMatches(data, generation) {
        this.upcomingMatches.replaceChildren();
        const errors = data.errors || [];
        this.upcomingErrors.replaceChildren();
        if (errors.length > 0) {
            this.upcomingErrors.style.display = 'block';
            errors.forEach(error => {
                const item = document.createElement('div');
                item.textContent = error;
                this.upcomingErrors.appendChild(item);
            });
        } else {
            this.upcomingErrors.style.display = 'none';
        }

        const matches = data.matches || [];
        this.upcomingSummary.textContent = `${matches.length} market-listed matches · odds refresh about every ${Math.round(data.cache_seconds / 60)} minutes · model data ${data.data_version}`;
        if (matches.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'market-unavailable';
            empty.textContent = 'No upcoming ATP match-winner markets were found.';
            this.upcomingMatches.appendChild(empty);
            return;
        }

        const groups = new Map();
        matches.forEach(match => {
            const date = new Date(match.start_time);
            const key = Number.isNaN(date.getTime()) ? 'Unknown date' : date.toLocaleDateString([], {
                weekday: 'long', month: 'short', day: 'numeric'
            });
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(match);
        });

        const simulationTasks = [];
        groups.forEach((groupMatches, label) => {
            const section = document.createElement('section');
            section.className = 'match-day';
            const heading = document.createElement('h3');
            heading.className = 'match-day-title';
            heading.textContent = this.relativeDateLabel(groupMatches[0].start_time, label);
            section.appendChild(heading);
            const grid = document.createElement('div');
            grid.className = 'match-grid';
            groupMatches.forEach(match => {
                const rendered = this.createUpcomingMatchCard(match);
                grid.appendChild(rendered.card);
                if (rendered.simulationTarget) {
                    simulationTasks.push({match, target: rendered.simulationTarget});
                }
            });
            section.appendChild(grid);
            this.upcomingMatches.appendChild(section);
        });
        this.loadDashboardSimulations(simulationTasks, generation);
    }

    relativeDateLabel(startTime, fallback) {
        const date = new Date(startTime);
        if (Number.isNaN(date.getTime())) return fallback;
        const today = new Date();
        const tomorrow = new Date();
        tomorrow.setDate(today.getDate() + 1);
        const key = value => `${value.getFullYear()}-${value.getMonth()}-${value.getDate()}`;
        if (key(date) === key(today)) return `Today · ${fallback}`;
        if (key(date) === key(tomorrow)) return `Tomorrow · ${fallback}`;
        return fallback;
    }

    createUpcomingMatchCard(match) {
        const card = document.createElement('article');
        card.className = 'upcoming-match-card';

        const meta = document.createElement('div');
        meta.className = 'upcoming-match-meta';
        const tournament = document.createElement('span');
        tournament.textContent = match.tournament || 'ATP match';
        const time = document.createElement('span');
        const start = new Date(match.start_time);
        time.textContent = Number.isNaN(start.getTime()) ? 'Time TBD' : start.toLocaleTimeString([], {
            hour: 'numeric', minute: '2-digit'
        });
        meta.append(tournament, time);
        card.appendChild(meta);

        if (match.surface) {
            const surface = document.createElement('div');
            surface.className = `match-surface match-surface-${match.surface}`;
            surface.textContent = `${match.surface} · ${match.format === 'best5' ? 'best of 5' : 'best of 3'}`;
            card.appendChild(surface);
        }

        const consensus = match.market_comparison?.consensus;
        const players = document.createElement('div');
        players.className = 'upcoming-player-list';
        [match.player1, match.player2].forEach((name, index) => {
            const row = document.createElement('div');
            row.className = 'upcoming-player-row';
            const playerName = document.createElement('strong');
            playerName.textContent = name;
            const price = document.createElement('span');
            const playerMarket = consensus?.[`player${index + 1}`];
            price.textContent = playerMarket ? this.formatProbability(playerMarket.probability) : '—';
            row.append(playerName, price);
            players.appendChild(row);
        });
        card.appendChild(players);

        const marketMeta = document.createElement('div');
        marketMeta.className = 'upcoming-market-meta';
        const providerNames = (match.market_comparison?.providers || []).map(provider =>
            provider.provider === 'kalshi' ? 'Kalshi' : 'Polymarket'
        );
        marketMeta.textContent = `Market consensus · ${providerNames.join(' + ')}`;
        card.appendChild(marketMeta);

        const simulationTarget = document.createElement('div');
        simulationTarget.className = 'dashboard-simulation';
        if (match.simulation_available) {
            simulationTarget.textContent = 'Model simulation queued…';
        } else {
            simulationTarget.classList.add('dashboard-simulation-unavailable');
            simulationTarget.textContent = match.simulation_unavailable_reason;
        }
        card.appendChild(simulationTarget);
        return {card, simulationTarget: match.simulation_available ? simulationTarget : null};
    }

    async loadDashboardSimulations(tasks, generation) {
        let nextIndex = 0;
        const worker = async () => {
            while (nextIndex < tasks.length && generation === this.dashboardGeneration) {
                const task = tasks[nextIndex++];
                try {
                    const response = await fetch(`/api/upcoming/${encodeURIComponent(task.match.id)}/simulation`);
                    const data = await response.json();
                    if (!response.ok || data.error) throw new Error(data.error || 'Simulation unavailable');
                    if (generation === this.dashboardGeneration) this.renderDashboardSimulation(task.target, data);
                } catch (error) {
                    if (generation === this.dashboardGeneration) {
                        task.target.classList.add('dashboard-simulation-unavailable');
                        task.target.textContent = 'Model simulation unavailable.';
                    }
                }
            }
        };
        await Promise.all([worker(), worker()]);
    }

    renderDashboardSimulation(target, data) {
        target.replaceChildren();
        const heading = document.createElement('div');
        heading.className = 'dashboard-model-heading';
        heading.textContent = `Model · ${data.surface} · ${data.num_simulations.toLocaleString()} runs`;
        target.appendChild(heading);

        const probabilities = document.createElement('div');
        probabilities.className = 'dashboard-model-probabilities';
        [[data.player1, data.player1_probability], [data.player2, data.player2_probability]].forEach(([name, value]) => {
            const item = document.createElement('div');
            const label = document.createElement('span');
            label.textContent = name;
            const probability = document.createElement('strong');
            probability.textContent = this.formatProbability(value);
            item.append(label, probability);
            probabilities.appendChild(item);
        });
        target.appendChild(probabilities);

        const comparison = data.market_comparison?.model_comparison?.[data.surface];
        if (comparison) {
            const difference = document.createElement('div');
            difference.className = 'dashboard-model-difference';
            const value = comparison.player1_model_minus_market_pp;
            difference.textContent = `${data.player1}: model ${value >= 0 ? '+' : ''}${value.toFixed(1)} percentage points vs market`;
            target.appendChild(difference);
        }

        const warnings = [...(data.quality?.warnings || []), ...(data.fallback_warnings || [])];
        if (warnings.length > 0) {
            const warning = document.createElement('div');
            warning.className = 'dashboard-quality-warning';
            warning.textContent = warnings.join(' ');
            target.appendChild(warning);
        }
    }

    displayMarketComparison(data) {
        const comparison = data.market_comparison;
        const container = this.marketComparisonContent;
        container.replaceChildren();

        if (!comparison || !comparison.consensus) {
            const message = document.createElement('p');
            message.className = 'market-unavailable';
            message.textContent = comparison?.notice ||
                'No exact live match-winner market was found for this matchup.';
            container.appendChild(message);
            this.appendProviderStatuses(container, comparison?.providers || []);
            return;
        }

        const consensus = comparison.consensus;
        const consensusPanel = document.createElement('div');
        consensusPanel.className = 'market-consensus';

        const label = document.createElement('div');
        label.className = 'market-consensus-label';
        label.textContent = `Market consensus · ${consensus.provider_count} provider${consensus.provider_count === 1 ? '' : 's'}`;
        consensusPanel.appendChild(label);

        const probabilities = document.createElement('div');
        probabilities.className = 'market-consensus-probabilities';
        [consensus.player1, consensus.player2].forEach(player => {
            const playerBox = document.createElement('div');
            const name = document.createElement('span');
            name.className = 'market-player-name';
            name.textContent = player.name;
            const probability = document.createElement('strong');
            probability.textContent = this.formatProbability(player.probability);
            playerBox.append(name, probability);
            probabilities.appendChild(playerBox);
        });
        consensusPanel.appendChild(probabilities);
        container.appendChild(consensusPanel);

        this.appendProviderStatuses(container, comparison.providers || []);

        const modelComparison = comparison.model_comparison || {};
        if (Object.keys(modelComparison).length > 0) {
            const table = document.createElement('table');
            table.className = 'market-model-table';
            const head = document.createElement('thead');
            const headRow = document.createElement('tr');
            ['Surface', `${data.player1_name} model`, 'Market', 'Model − market'].forEach(text => {
                const th = document.createElement('th');
                th.textContent = text;
                headRow.appendChild(th);
            });
            head.appendChild(headRow);
            table.appendChild(head);

            const body = document.createElement('tbody');
            Object.entries(modelComparison).forEach(([surface, values]) => {
                const row = document.createElement('tr');
                const cells = [
                    surface.charAt(0).toUpperCase() + surface.slice(1),
                    this.formatProbability(values.player1_model_probability),
                    this.formatProbability(consensus.player1.probability),
                    `${values.player1_model_minus_market_pp >= 0 ? '+' : ''}${values.player1_model_minus_market_pp.toFixed(1)} pp`
                ];
                cells.forEach(text => {
                    const td = document.createElement('td');
                    td.textContent = text;
                    row.appendChild(td);
                });
                body.appendChild(row);
            });
            table.appendChild(body);
            const tableWrapper = document.createElement('div');
            tableWrapper.className = 'market-table-wrapper';
            tableWrapper.appendChild(table);
            container.appendChild(tableWrapper);
        }

        const notice = document.createElement('p');
        notice.className = 'market-notice';
        notice.textContent = comparison.notice;
        container.appendChild(notice);
    }

    appendProviderStatuses(container, providers) {
        if (providers.length === 0) return;
        const grid = document.createElement('div');
        grid.className = 'market-provider-grid';
        providers.forEach(provider => {
            const card = document.createElement('div');
            card.className = `market-provider market-provider-${provider.status}`;
            const heading = document.createElement('div');
            heading.className = 'market-provider-heading';
            const providerName = document.createElement('strong');
            providerName.textContent = provider.provider === 'kalshi' ? 'Kalshi' : 'Polymarket';
            const status = document.createElement('span');
            status.className = 'market-status';
            status.textContent = provider.status;
            heading.append(providerName, status);
            card.appendChild(heading);

            if (provider.status === 'available') {
                const prices = document.createElement('div');
                prices.className = 'market-provider-prices';
                prices.textContent = `${provider.player1.name} ${this.formatProbability(provider.player1.probability)} · ` +
                    `${provider.player2.name} ${this.formatProbability(provider.player2.probability)}`;
                card.appendChild(prices);

                const detail = document.createElement('div');
                detail.className = 'market-provider-detail';
                const details = [];
                if (provider.volume != null) details.push(`Volume ${provider.volume.toLocaleString()}`);
                if (provider.provider_updated_at) {
                    const updated = new Date(provider.provider_updated_at);
                    if (!Number.isNaN(updated.getTime())) details.push(`Updated ${updated.toLocaleString()}`);
                }
                detail.textContent = details.join(' · ');
                card.appendChild(detail);

                if (provider.source_url) {
                    const link = document.createElement('a');
                    link.href = provider.source_url;
                    link.target = '_blank';
                    link.rel = 'noopener';
                    link.textContent = 'View source market';
                    card.appendChild(link);
                }
            } else {
                const reason = document.createElement('p');
                reason.textContent = provider.reason;
                card.appendChild(reason);
            }
            grid.appendChild(card);
        });
        container.appendChild(grid);
    }

    formatProbability(value) {
        return `${(value * 100).toFixed(1)}%`;
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
                    <th class="player-parameter-heading" colspan="4"></th>
                    <th class="player-parameter-heading" colspan="4"></th>
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
            const playerHeadings = thead.querySelectorAll('.player-parameter-heading');
            playerHeadings[0].textContent = data.player1_name;
            playerHeadings[1].textContent = data.player2_name;
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
        expectedCell.textContent = expected == null ? 'N/A' : `${(expected * 100).toFixed(1)}%`;
        cells.push(expectedCell);

        // Observed value
        const observedCell = document.createElement('td');
        observedCell.className = 'observed-value';
        observedCell.textContent = observed == null ? 'N/A' : `${(observed * 100).toFixed(1)}%`;
        cells.push(observedCell);

        // Difference and Performance
        let difference = '';
        let performanceClass = 'performance-neutral';
        let performanceText = 'N/A';

        if (observed != null && expected != null) {
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
            } else {
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
            const [p1Low, p1High] = surfaceData.player1_win_ci95;
            results.player1Record.textContent =
                `${surfaceData.player1_wins} wins · 95% MC CI ${(p1Low * 100).toFixed(1)}–${(p1High * 100).toFixed(1)}%`;
            results.player2Record.textContent =
                `${surfaceData.player2_wins} wins · 95% MC CI ${((1 - p1High) * 100).toFixed(1)}–${((1 - p1Low) * 100).toFixed(1)}%`;

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
    }

    hideAllSections() {
        this.simulationSetup.style.display = 'none';
        this.loadingSection.style.display = 'none';
        this.resultsSection.style.display = 'none';
        this.errorSection.style.display = 'none';
    }

    showSimulationSetup() {
        this.simulationSetup.style.display = 'block';
    }

    showLoadingSection() {
        this.loadingSection.style.display = 'block';
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
