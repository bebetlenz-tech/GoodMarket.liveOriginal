// Minigames JavaScript - Live Crash Game Only

let currentSession = null;
let userWallet = null;
let gameActive = false;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎮 Minigames page loaded');
    await loadUserStats();
    await checkGameLimits();
});

async function loadUserStats() {
    try {
        const response = await fetch('/minigames/api/balance');
        const data = await response.json();

        console.log('📊 Balance loaded:', data);

        if (data.success) {
            const availableBalance = data.available_balance || 0;

            updateBalanceDisplay(availableBalance);
            updateWithdrawButton(availableBalance);
        }
    } catch (error) {
        console.error('❌ Error loading balance:', error);
    }
}

function updateBalanceDisplay(availableBalance) {
    const balanceDisplay = document.getElementById('availableBalanceDisplay');

    if (balanceDisplay) {
        if (availableBalance <= 0) {
            balanceDisplay.innerHTML = `
                <div style="font-size: 2.5rem; font-weight: 800; color: #ef4444;">0.00 G$</div>
                <div style="font-size: 0.9rem; color: #fbbf24; margin-top: 0.5rem;">⬇️ Deposit 100-500 G$ to start playing!</div>
            `;
        } else {
            balanceDisplay.textContent = availableBalance.toFixed(2) + ' G$';
        }
    }
}

function updateWithdrawButton(availableBalance) {
    const withdrawBtn = document.getElementById('mainWithdrawBtn');
    if (withdrawBtn) {
        if (availableBalance >= 100) {
            withdrawBtn.disabled = false;
            withdrawBtn.style.cursor = 'pointer';
            withdrawBtn.style.opacity = '1';
            withdrawBtn.textContent = `💸 Withdraw ${availableBalance.toFixed(2)} G$`;
        } else {
            withdrawBtn.disabled = true;
            withdrawBtn.style.cursor = 'not-allowed';
            withdrawBtn.style.opacity = '0.5';
            withdrawBtn.textContent = availableBalance > 0 ? `💸 Min 100 G$ (${availableBalance.toFixed(2)} G$)` : '💸 No Balance';
        }
    }
}

async function checkGameLimits() {
    try {
        const response = await fetch('/minigames/api/check-limit/crash_game');
        const data = await response.json();

        if (data.success && data.limit_check) {
            const limitInfo = data.limit_check;
            const limitText = document.getElementById('limit-crash_game');
            const playBtn = document.getElementById('play-crash_game');

            if (limitText) {
                limitText.textContent = `${limitInfo.remaining_plays} plays remaining today`;
            }

            if (playBtn) {
                playBtn.disabled = !limitInfo.can_play;
            }
        }
    } catch (error) {
        console.error('❌ Error checking game limits:', error);
    }
}

// Open Crash Game
window.openGame = async function(gameType) {
    if (gameType !== 'crash_game') return;

    // First, force reload user stats to get fresh balance
    await loadUserStats();

    // Then check user balance
    try {
        const balanceResponse = await fetch('/minigames/api/balance');
        const balanceData = await balanceResponse.json();

        console.log('💰 Balance check before opening game:', balanceData);

        if (!balanceData.success) {
            showNotification('Failed to load balance', 'error');
            return;
        }

        const availableBalance = balanceData.available_balance || 0;

        console.log('💵 Available balance:', availableBalance);

        if (availableBalance < 50) {
            showNotification(`Insufficient balance! You have ${availableBalance.toFixed(2)} G$. Minimum bet is 50 G$.`, 'error');
            openDepositModal();
            return;
        }

        // Show bet amount selection modal
        showBetAmountModal(availableBalance);

    } catch (error) {
        console.error('❌ Error checking balance:', error);
        showNotification('Failed to check balance', 'error');
    }
};

window.showBetAmountModal = function(availableBalance) {
    const modal = document.getElementById('gameModal');
    const content = document.getElementById('gameContent');

    const minBet = 50;
    const maxBet = Math.min(250, availableBalance);

    content.innerHTML = `
        <div style="padding: 2rem; max-width: 500px; width: 100%;">
            <h2 style="font-size: 2rem; margin-bottom: 1.5rem; color: #6366f1;">🎯 Place Your Bet</h2>

            <div style="background: rgba(99, 102, 241, 0.1); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">💰 Your Available Balance:</div>
                <div style="font-size: 2rem; font-weight: 800; color: #10b981;">${availableBalance.toFixed(2)} G$</div>
            </div>

            <div style="background: rgba(251, 191, 36, 0.1); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid rgba(251, 191, 36, 0.3);">
                <div style="font-size: 0.85rem; color: #fbbf24; font-weight: 600;">⚠️ Bet Limits:</div>
                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.7);">
                    • Minimum: 50 G$<br>
                    • Maximum: 250 G$ per game<br>
                    • Max Crash: 5.00x
                </div>
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; font-size: 0.9rem; color: rgba(255,255,255,0.7); margin-bottom: 0.5rem;">Bet Amount (G$):</label>
                <input type="number" id="betAmountInput" min="${minBet}" max="${maxBet}" step="10" value="${minBet}"
                    style="width: 100%; padding: 1rem; font-size: 1.2rem; background: rgba(255,255,255,0.1); border: 2px solid #6366f1; border-radius: 12px; color: white; text-align: center;">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">Min: ${minBet} G$ | Max: ${maxBet.toFixed(2)} G$</div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; margin-bottom: 1.5rem;">
                <button onclick="window.setBetAmount(50)" style="padding: 0.75rem; background: rgba(99, 102, 241, 0.2); color: #6366f1; border: 1px solid #6366f1; border-radius: 8px; cursor: pointer; font-weight: 600;">50 G$</button>
                <button onclick="window.setBetAmount(100)" style="padding: 0.75rem; background: rgba(99, 102, 241, 0.2); color: #6366f1; border: 1px solid #6366f1; border-radius: 8px; cursor: pointer; font-weight: 600;">100 G$</button>
                <button onclick="window.setBetAmount(200)" style="padding: 0.75rem; background: rgba(99, 102, 241, 0.2); color: #6366f1; border: 1px solid #6366f1; border-radius: 8px; cursor: pointer; font-weight: 600;">200 G$</button>
                <button onclick="window.setBetAmount(${maxBet})" style="padding: 0.75rem; background: rgba(251, 191, 36, 0.2); color: #fbbf24; border: 1px solid #fbbf24; border-radius: 8px; cursor: pointer; font-weight: 600;">Max</button>
            </div>

            <button onclick="window.confirmBetAndStartGame()" style="width: 100%; padding: 1.2rem; background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; border-radius: 12px; font-size: 1.2rem; font-weight: 700; cursor: pointer; margin-bottom: 1rem;">
                🚀 Start Game
            </button>

            <button onclick="window.closeGameModal()" style="width: 100%; padding: 1rem; background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; border-radius: 12px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                Cancel
            </button>
        </div>
    `;

    modal.style.display = 'flex';
};

window.setBetAmount = function(amount) {
    const input = document.getElementById('betAmountInput');
    if (input) {
        input.value = amount;
    }
};

window.confirmBetAndStartGame = async function() {
    const betAmountInput = document.getElementById('betAmountInput');
    const betAmount = parseFloat(betAmountInput.value);

    console.log('🎯 Confirming bet:', betAmount);

    if (!betAmount || betAmount < 50) {
        showNotification('Minimum bet is 50 G$', 'error');
        return;
    }

    if (betAmount > 250) {
        showNotification('Maximum bet is 250 G$ per game', 'error');
        return;
    }

    // Get current balance to validate
    const balanceResponse = await fetch('/minigames/api/balance');
    const balanceData = await balanceResponse.json();
    const availableBalance = balanceData.available_balance || 0;

    console.log('💰 Current balance:', availableBalance);
    console.log('🎲 Bet amount:', betAmount);

    if (availableBalance < 50) {
        showNotification(`No balance! You have ${availableBalance.toFixed(2)} G$. Please deposit at least 100 G$ first.`, 'error');
        closeGameModal();
        openDepositModal();
        return;
    }

    if (betAmount > availableBalance) {
        showNotification(`Insufficient balance! You have ${availableBalance.toFixed(2)} G$, but trying to bet ${betAmount.toFixed(2)} G$.`, 'error');
        return;
    }

    console.log('✅ Balance check passed, starting game...');

    // Start the game with bet amount
    try {
        const response = await fetch('/minigames/api/start-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_type: 'crash_game',
                bet_amount: betAmount
            })
        });

        const data = await response.json();

        if (data.success) {
            currentSession = data.session_id;
            window.currentBetAmount = betAmount;
            startCrashGame(betAmount);
        } else {
            showNotification(data.error || 'Failed to start game', 'error');
        }
    } catch (error) {
        console.error('❌ Error starting game:', error);
        showNotification('Failed to start game', 'error');
    }
};

window.closeGameModal = function() {
    // Stop deposit monitoring if active
    if (depositMonitoringInterval) {
        clearInterval(depositMonitoringInterval);
        depositMonitoringInterval = null;
    }

    // Stop timer if active
    if (window.depositTimerInterval) {
        clearInterval(window.depositTimerInterval);
        window.depositTimerInterval = null;
    }

    document.getElementById('gameModal').style.display = 'none';
    document.getElementById('gameContent').innerHTML = '';
    gameActive = false;
    currentSession = null;
};

// Deposit Modal with Automatic Verification
let depositMonitoringInterval = null;

window.openDepositModal = function() {
    const modal = document.getElementById('gameModal');
    const content = document.getElementById('gameContent');

    content.innerHTML = `
        <div style="padding: 2rem; max-width: 600px; width: 100%;">
            <h2 style="font-size: 2rem; margin-bottom: 1.5rem; color: #6366f1;">💳 Deposit G$ to Play</h2>

            <div style="background: rgba(251, 191, 36, 0.1); padding: 1.5rem; border-radius: 12px; border: 2px solid rgba(251, 191, 36, 0.3); margin-bottom: 2rem;">
                <div style="font-size: 0.9rem; color: #fbbf24; font-weight: 600; margin-bottom: 1rem;">⚠️ Important Instructions:</div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); line-height: 1.6;">
                    • Minimum deposit: <strong style="color: #fbbf24;">100 G$</strong><br>
                    • Maximum per day: <strong style="color: #fbbf24;">500 G$</strong><br>
                    • Send G$ to the deposit address below<br>
                    • Use GoodWallet or any Celo wallet<br>
                    • <strong style="color: #10b981;">Payment will be detected automatically!</strong>
                </div>
            </div>

            <div style="background: rgba(99, 102, 241, 0.1); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">📍 Deposit Address:</div>
                <div style="font-size: 0.75rem; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem;">Send your G$ to this address</div>
                <div id="merchantAddress" style="font-size: 1rem; font-family: monospace; color: #6366f1; word-break: break-all; margin-bottom: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
                    Loading...
                </div>
                <button onclick="window.copyDepositAddress()" style="padding: 0.5rem 1.5rem; background: rgba(99, 102, 241, 0.2); color: #6366f1; border: 1px solid #6366f1; border-radius: 8px; cursor: pointer; width: 100%;">
                    📋 Copy Deposit Address
                </button>
            </div>

            <div id="monitoringStatus" style="background: rgba(99, 102, 241, 0.1); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid rgba(99, 102, 241, 0.3);">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status" style="color: #6366f1;"></div>
                    <div style="color: rgba(255,255,255,0.9);">
                        <strong>🔄 Monitoring for Deposit...</strong><br>
                        <small style="color: rgba(255,255,255,0.7);">Send G$ to the address above. We'll detect it automatically!</small>
                    </div>
                </div>
            </div>

            <button onclick="window.closeGameModal()" style="width: 100%; padding: 1rem; background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; border-radius: 12px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                Cancel
            </button>
        </div>
    `;

    // Load MERCHANT_ADDRESS for deposits
    fetch('/minigames/api/merchant-address')
        .then(res => res.json())
        .then(data => {
            if (data.success && data.merchant_address) {
                document.getElementById('merchantAddress').textContent = data.merchant_address;

                // Auto-start monitoring immediately after loading address
                setTimeout(() => {
                    window.startMonitoringDeposit();
                }, 500);
            } else {
                document.getElementById('merchantAddress').textContent = 'Error loading address';
                showNotification('Failed to load deposit address', 'error');
            }
        })
        .catch(error => {
            console.error('❌ Error loading deposit address:', error);
            document.getElementById('merchantAddress').textContent = 'Error loading address';
            showNotification('Failed to load deposit address', 'error');
        });

    modal.style.display = 'flex';
};

window.copyDepositAddress = function() {
    const address = document.getElementById('merchantAddress').textContent;
    navigator.clipboard.writeText(address).then(() => {
        showNotification('Deposit address copied to clipboard!', 'success');
    });
};

window.startMonitoringDeposit = function() {
    // Show monitoring status with timer
    const statusDiv = document.getElementById('monitoringStatus');
    if (statusDiv) {
        statusDiv.style.display = 'block';
    }

    // Start automatic monitoring (check every 10 seconds for 5 minutes)
    let checkCount = 0;
    const maxChecks = 30; // 5 minutes / 10 seconds
    let remainingSeconds = 300; // 5 minutes in seconds

    // Clear any existing intervals
    if (depositMonitoringInterval) {
        clearInterval(depositMonitoringInterval);
    }
    if (window.depositTimerInterval) {
        clearInterval(window.depositTimerInterval);
    }

    // Update timer display every second
    window.depositTimerInterval = setInterval(() => {
        remainingSeconds--;

        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = remainingSeconds % 60;
        const timeDisplay = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        if (statusDiv && remainingSeconds > 0) {
            statusDiv.innerHTML = `
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status" style="color: #6366f1;"></div>
                        <div style="color: rgba(255,255,255,0.9);">
                            <strong>🔄 Monitoring for Deposit...</strong><br>
                            <small style="color: rgba(255,255,255,0.7);">Send G$ to the address above. We'll detect it automatically!</small>
                        </div>
                    </div>
                    <div style="background: rgba(251, 191, 36, 0.2); padding: 0.5rem 1rem; border-radius: 8px; margin-left: 1rem;">
                        <div style="font-size: 0.8rem; color: #fbbf24; font-weight: 600;">⏱️ ${timeDisplay}</div>
                    </div>
                </div>
            `;
        }

        if (remainingSeconds <= 0) {
            clearInterval(window.depositTimerInterval);
        }
    }, 1000);

    // Check for deposits every 10 seconds
    depositMonitoringInterval = setInterval(async () => {
        checkCount++;

        try {
            console.log(`🔍 Checking for deposits... (${checkCount}/${maxChecks})`);

            const response = await fetch('/minigames/api/auto-verify-deposits', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('📊 Auto-verify result:', result);

            if (result.success && result.deposits_verified > 0) {
                // Deposit found!
                clearInterval(depositMonitoringInterval);
                clearInterval(window.depositTimerInterval);

                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="d-flex align-items-center">
                            <i class="fas fa-check-circle me-2" style="color: #10b981; font-size: 1.2rem;"></i>
                            <div style="color: rgba(255,255,255,0.9);">
                                <strong>✅ Deposit Detected!</strong><br>
                                <small style="color: rgba(255,255,255,0.7);">Found ${result.deposits_verified} deposit(s) totaling ${result.total_amount} G$</small>
                            </div>
                        </div>
                    `;
                }

                showNotification(`Deposit verified! ${result.total_amount} G$ added to your balance`, 'success');

                setTimeout(async () => {
                    await loadUserStats();
                    closeGameModal();
                }, 2000);
            } else if (checkCount >= maxChecks) {
                // 5-minute timeout expired
                clearInterval(depositMonitoringInterval);
                clearInterval(window.depositTimerInterval);

                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div style="background: rgba(251, 191, 36, 0.1); padding: 1.5rem; border-radius: 12px; border: 2px solid rgba(251, 191, 36, 0.3);">
                            <div class="d-flex align-items-center mb-3">
                                <i class="fas fa-hourglass-end me-2" style="color: #fbbf24; font-size: 1.5rem;"></i>
                                <div style="color: rgba(255,255,255,0.9);">
                                    <strong style="font-size: 1.1rem;">⏰ Monitoring Session Expired</strong>
                                </div>
                            </div>
                            <div style="color: rgba(255,255,255,0.8); margin-bottom: 1rem; line-height: 1.6;">
                                The 5-minute deposit monitoring window has ended. Don't worry - your deposit will still be credited automatically once confirmed on the blockchain!
                            </div>
                            <div style="background: rgba(99, 102, 241, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                                <div style="font-size: 0.9rem; color: #6366f1; font-weight: 600; margin-bottom: 0.5rem;">📝 What to do next:</div>
                                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); line-height: 1.6;">
                                    1. If you already sent G$, wait for blockchain confirmation (usually 1-2 minutes)<br>
                                    2. Your balance will update automatically when confirmed<br>
                                    3. Click "Deposit" button again to start a new monitoring session<br>
                                    4. Or refresh the page to check your updated balance
                                </div>
                            </div>
                            <button onclick="window.closeGameModal()" style="width: 100%; padding: 1rem; background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; border-radius: 12px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-bottom: 0.5rem;">
                                💳 Start New Deposit Session
                            </button>
                            <button onclick="window.location.reload()" style="width: 100%; padding: 1rem; background: rgba(99, 102, 241, 0.2); color: #6366f1; border: 1px solid #6366f1; border-radius: 12px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                                🔄 Refresh Page to Check Balance
                            </button>
                        </div>
                    `;
                }

                showNotification('Monitoring expired. Click "Deposit" to start a new session or refresh to check balance.', 'info');
            }
        } catch (error) {
            console.error('❌ Error checking deposits:', error);
        }
    }, 10000); // Check every 10 seconds

    // Trigger immediate first check
    setTimeout(async () => {
        try {
            console.log('🔄 Immediate deposit check...');
            const response = await fetch('/minigames/api/auto-verify-deposits', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const result = await response.json();

            if (result.success && result.deposits_verified > 0) {
                clearInterval(depositMonitoringInterval);
                clearInterval(window.depositTimerInterval);

                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="d-flex align-items-center">
                            <i class="fas fa-check-circle me-2" style="color: #10b981; font-size: 1.2rem;"></i>
                            <div style="color: rgba(255,255,255,0.9);">
                                <strong>✅ Deposit Detected!</strong><br>
                                <small style="color: rgba(255,255,255,0.7);">Found ${result.deposits_verified} deposit(s) totaling ${result.total_amount} G$</small>
                            </div>
                        </div>
                    `;
                }

                showNotification(`Deposit verified! ${result.total_amount} G$ added`, 'success');

                setTimeout(async () => {
                    await loadUserStats();
                    closeGameModal();
                }, 2000);
            }
        } catch (error) {
            console.error('❌ Immediate check error:', error);
        }
    }, 1000);

    showNotification('Monitoring started! You have 5 minutes. Send G$ to the address above.', 'info');
};

// Crash Game Implementation
function startCrashGame(betAmount) {
    const gameContent = document.getElementById('gameContent');

    gameContent.innerHTML = `
        <div style="text-align: center; padding: 2rem;">
            <h2 style="font-size: 2rem; margin-bottom: 1rem; color: #fbbf24;">🚀 Crash Game</h2>
            <p style="color: rgba(255,255,255,0.8); margin-bottom: 0.5rem;">
                Watch the multiplier rise! Cash out before it crashes to win!
            </p>
            <div style="background: rgba(251, 191, 36, 0.2); padding: 0.75rem; border-radius: 12px; margin-bottom: 1.5rem; display: inline-block;">
                <span style="color: #fbbf24; font-weight: 700;">💰 Bet: ${betAmount.toFixed(2)} G$</span>
            </div>

            <div id="crashGameContainer" style="position: relative; width: 100%; max-width: 600px; height: 400px; margin: 0 auto; background: linear-gradient(135deg, #1e293b, #0f172a); border-radius: 20px; overflow: hidden; border: 2px solid #6366f1;">
                <canvas id="crashCanvas" width="600" height="400"></canvas>

                <div id="crashMultiplier" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 5rem; font-weight: 900; color: #10b981; text-shadow: 0 0 30px rgba(16, 185, 129, 0.8), 0 0 60px rgba(16, 185, 129, 0.4);">
                    1.00x
                </div>

                <div id="crashStatus" style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); padding: 0.5rem 1.5rem; border-radius: 12px; font-weight: 600; color: #fbbf24;">
                    Get Ready...
                </div>
            </div>

            <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: center; align-items: center;">
                <button id="cashOutBtn" onclick="window.cashOut()" disabled style="padding: 1rem 3rem; background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; border-radius: 12px; font-size: 1.2rem; font-weight: 700; cursor: not-allowed; opacity: 0.5;">
                    💰 Cash Out
                </button>
                <div id="potentialWin" style="background: rgba(251, 191, 36, 0.2); padding: 1rem 2rem; border-radius: 12px; border: 2px solid #fbbf24;">
                    <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Potential Win:</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #fbbf24;">0 G$</div>
                </div>
            </div>

            <div style="margin-top: 1rem; padding: 1rem; background: rgba(99, 102, 241, 0.1); border-radius: 12px; font-size: 0.9rem; text-align: left;">
                <strong style="color: #fbbf24;">📖 How to Play:</strong><br>
                1. Click "Play Crash Game" to start<br>
                2. Place your bet (50-250 G$ per game)<br>
                3. Watch the multiplier rise from 1.00x<br>
                4. Click "Cash Out" BEFORE it crashes to win!<br>
                5. Your winnings = Bet × Multiplier<br>
                6. If you don't cash out in time, you lose your bet<br>
                <br>
                <strong style="color: #fbbf24;">⚖️ Game Rules:</strong><br>
                • Bet: 50-250 G$ per game<br>
                • Maximum crash: 5.00x<br>
                • Daily limit: 20 games<br>
                • Minimum withdrawal: 100 G$<br>
                • Maximum withdrawal: 10,000 G$<br>
                <br>
                <strong style="color: #10b981;">ℹ️ Important Notice:</strong><br>
                <span style="color: rgba(255,255,255,0.8); font-size: 0.85rem;">
                This minigame is <strong>just for fun</strong> and was built by the <strong>GIMT (GoodDollar Independent Moderator Team)</strong>. 
                This is <strong>not an official GoodDollar product</strong> - it's a community initiative created by the moderator team to enhance the GoodDollar ecosystem experience.
                </span>
            </div>
        </div>
    `;

    setTimeout(() => initCrashGame(), 1000);
}

let crashMultiplier = 1.00;
let crashTarget = 1.00;
let crashed = false;
let cashedOut = false;
let baseReward = 10;
let animationId = null;
let canvas, ctx;
let particles = [];

function initCrashGame() {
    canvas = document.getElementById('crashCanvas');
    ctx = canvas.getContext('2d');

    crashMultiplier = 1.00;
    crashed = false;
    cashedOut = false;
    particles = [];

    // Random crash point between 1.20x and 5.00x (maximum 5x)
    crashTarget = 1.20 + Math.random() * 3.80;

    console.log('🎯 Crash target:', crashTarget.toFixed(2) + 'x');

    document.getElementById('crashStatus').textContent = '🚀 Rising!';
    document.getElementById('cashOutBtn').disabled = false;
    document.getElementById('cashOutBtn').style.cursor = 'pointer';
    document.getElementById('cashOutBtn').style.opacity = '1';

    gameActive = true;
    animateCrash();
}

function animateCrash() {
    if (!gameActive || crashed || cashedOut) return;

    // Increase multiplier with variable speed - MUCH SLOWER
    const increment = 0.003 + Math.random() * 0.005; // Very slow increment for better gameplay
    crashMultiplier += increment;

    // Update display
    const multiplierEl = document.getElementById('crashMultiplier');
    if (multiplierEl) {
        multiplierEl.textContent = crashMultiplier.toFixed(2) + 'x';

        // Color changes based on multiplier
        if (crashMultiplier < 2) {
            multiplierEl.style.color = '#10b981';
        } else if (crashMultiplier < 5) {
            multiplierEl.style.color = '#fbbf24';
        } else {
            multiplierEl.style.color = '#ef4444';
        }
    }

    // Update potential win
    const betAmount = window.currentBetAmount || 10;
    const potentialWin = (betAmount * crashMultiplier).toFixed(2);
    document.getElementById('potentialWin').innerHTML = `
        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Potential Win:</div>
        <div style="font-size: 1.5rem; font-weight: 800; color: #fbbf24;">${potentialWin} G$</div>
    `;

    // Draw animated background
    drawCrashAnimation();

    // Check if crashed
    if (crashMultiplier >= crashTarget) {
        crash();
        return;
    }

    animationId = requestAnimationFrame(animateCrash);
}

function drawCrashAnimation() {
    // Clear canvas
    ctx.fillStyle = 'rgba(15, 23, 42, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Add particles
    if (Math.random() < 0.3) {
        particles.push({
            x: Math.random() * canvas.width,
            y: canvas.height,
            vx: (Math.random() - 0.5) * 2,
            vy: -2 - Math.random() * 3,
            size: 2 + Math.random() * 4,
            life: 1,
            color: crashMultiplier < 2 ? '#10b981' : crashMultiplier < 5 ? '#fbbf24' : '#ef4444'
        });
    }

    // Update and draw particles
    particles = particles.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.01;

        if (p.life <= 0) return false;

        ctx.globalAlpha = p.life;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();

        return true;
    });

    ctx.globalAlpha = 1;

    // Draw rising line graph
    ctx.strokeStyle = crashMultiplier < 2 ? '#10b981' : crashMultiplier < 5 ? '#fbbf24' : '#ef4444';
    ctx.lineWidth = 3;
    ctx.beginPath();
    const progress = (crashMultiplier - 1) / (crashTarget - 1);
    const graphHeight = canvas.height * 0.7 * progress;
    ctx.moveTo(50, canvas.height - 50);
    ctx.lineTo(canvas.width - 50, canvas.height - 50 - graphHeight);
    ctx.stroke();
}

function crash() {
    crashed = true;
    gameActive = false;

    if (animationId) {
        cancelAnimationFrame(animationId);
    }

    // Crash explosion effect
    for (let i = 0; i < 100; i++) {
        particles.push({
            x: canvas.width / 2,
            y: canvas.height / 2,
            vx: (Math.random() - 0.5) * 10,
            vy: (Math.random() - 0.5) * 10,
            size: 3 + Math.random() * 5,
            life: 1,
            color: '#ef4444'
        });
    }

    document.getElementById('crashMultiplier').textContent = '💥 CRASHED!';
    document.getElementById('crashMultiplier').style.color = '#ef4444';
    document.getElementById('crashStatus').textContent = '💥 Crashed at ' + crashMultiplier.toFixed(2) + 'x';
    document.getElementById('cashOutBtn').disabled = true;

    // Finish game with 0 score
    setTimeout(() => finishGame(0), 2000);
}

window.cashOut = async function() {
    if (crashed || cashedOut || !gameActive) return;

    cashedOut = true;
    gameActive = false;

    if (animationId) {
        cancelAnimationFrame(animationId);
    }

    const finalMultiplier = crashMultiplier;
    const betAmount = window.currentBetAmount || 10;
    const totalWinnings = parseFloat((betAmount * finalMultiplier).toFixed(2));

    console.log(`💰 GAME WIN CALCULATION:`);
    console.log(`   Bet amount: ${betAmount} G$`);
    console.log(`   Multiplier: ${finalMultiplier.toFixed(2)}x`);
    console.log(`   Total winnings: ${totalWinnings.toFixed(2)} G$`);
    console.log(`   Net profit: ${(totalWinnings - betAmount).toFixed(2)} G$`);

    document.getElementById('crashStatus').textContent = '✅ Cashed Out at ' + finalMultiplier.toFixed(2) + 'x!';
    document.getElementById('cashOutBtn').disabled = true;
    document.getElementById('crashMultiplier').style.color = '#10b981';

    showNotification(`Successfully cashed out! Won ${totalWinnings} G$!`, 'success');

    setTimeout(() => finishGame(totalWinnings), 2000);
};

async function finishGame(score) {
    try {
        const response = await fetch('/minigames/api/complete-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession,
                score: score,
                game_data: {
                    multiplier: crashMultiplier.toFixed(2),
                    crashed: crashed,
                    cashed_out: cashedOut,
                    bet_amount: window.currentBetAmount,
                    total_winnings: score,
                    net_profit: score - (window.currentBetAmount || 0)
                }
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message || `Game complete! Earned ${score} tokens`, 'success');
            await loadUserStats();
            await checkGameLimits();

            setTimeout(() => {
                closeGameModal();
            }, 2000);
        } else {
            showNotification(data.error || 'Game completion failed', 'error');
        }
    } catch (error) {
        console.error('❌ Error completing game:', error);
        showNotification('Failed to complete game', 'error');
    }
}

// Withdraw winnings
window.withdrawFromMain = async function() {
    try {
        const response = await fetch('/minigames/api/withdraw-winnings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            showNotification(`Successfully withdrawn ${data.amount_withdrawn} G$!`, 'success');
            await loadUserStats();
        } else {
            showNotification(data.error || 'Withdrawal failed', 'error');
        }
    } catch (error) {
        console.error('❌ Error withdrawing:', error);
        showNotification('Withdrawal failed', 'error');
    }
};

// Transaction history modal
window.openTransactionHistoryModal = async function() {
    try {
        const response = await fetch('/minigames/api/transaction-history');
        const data = await response.json();

        if (data.success) {
            showTransactionHistory(data.transactions || []);
        }
    } catch (error) {
        console.error('❌ Error loading transactions:', error);
    }
};

function showTransactionHistory(transactions) {
    const modal = document.getElementById('gameModal');
    const content = document.getElementById('gameContent');

    content.innerHTML = `
        <div style="padding: 2rem; max-width: 800px; width: 100%;">
            <h2 style="font-size: 2rem; margin-bottom: 1.5rem;">📜 Transaction History</h2>
            <div style="max-height: 400px; overflow-y: auto;">
                ${transactions.length === 0 ? '<p style="color: rgba(255,255,255,0.6);">No transactions yet</p>' :
                transactions.map(tx => `
                    <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="color: #10b981; font-weight: 600;">+${tx.reward_amount} G$</span>
                            <span style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">${new Date(tx.created_at).toLocaleString()}</span>
                        </div>
                        ${tx.transaction_hash ? `
                            <a href="https://explorer.celo.org/mainnet/tx/${tx.transaction_hash}" target="_blank" style="color: #6366f1; font-size: 0.85rem; text-decoration: none;">
                                View on Explorer →
                            </a>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    modal.style.display = 'flex';
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.style.display = 'block';
    notification.style.background = type === 'success' ? 'rgba(16, 185, 129, 0.95)' :
                                   type === 'error' ? 'rgba(239, 68, 68, 0.95)' :
                                   'rgba(99, 102, 241, 0.95)';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}



// Game Logs Modal
window.openGameLogsModal = async function() {
    try {
        const response = await fetch('/minigames/api/game-logs');
        const data = await response.json();

        if (!data.success) {
            showNotification('Failed to load game logs', 'error');
            return;
        }

        const logs = data.game_logs || [];
        const deposits = data.deposit_logs || [];
        const withdrawals = data.withdrawal_logs || [];

        const modal = document.getElementById('gameModal');
        const content = document.getElementById('gameContent');

        let totalWins = 0;
        let totalLosses = 0;
        let totalProfit = 0;

        logs.forEach(log => {
            if (log.result === 'WIN') totalWins++;
            else totalLosses++;
            totalProfit += log.profit_loss;
        });

        const totalDeposited = deposits.reduce((sum, d) => sum + d.amount, 0);
        const totalWithdrawn = withdrawals.reduce((sum, w) => sum + w.amount, 0);

        content.innerHTML = `
            <div style="padding: 2rem; max-width: 1000px; width: 100%;">
                <h2 style="font-size: 2rem; margin-bottom: 1.5rem; color: #6366f1;">📊 Complete History</h2>

                <!-- Tab Navigation -->
                <div style="display: flex; gap: 1rem; margin-bottom: 2rem; border-bottom: 2px solid rgba(99, 102, 241, 0.2);">
                    <button onclick="showHistoryTab('games')" id="tab-games" style="padding: 1rem 1.5rem; background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; border-radius: 8px 8px 0 0; cursor: pointer; font-weight: 600;">
                        🎮 Games (${logs.length})
                    </button>
                    <button onclick="showHistoryTab('deposits')" id="tab-deposits" style="padding: 1rem 1.5rem; background: rgba(99, 102, 241, 0.2); color: white; border: none; border-radius: 8px 8px 0 0; cursor: pointer; font-weight: 600;">
                        💳 Deposits (${deposits.length})
                    </button>
                    <button onclick="showHistoryTab('withdrawals')" id="tab-withdrawals" style="padding: 1rem 1.5rem; background: rgba(99, 102, 241, 0.2); color: white; border: none; border-radius: 8px 8px 0 0; cursor: pointer; font-weight: 600;">
                        💸 Withdrawals (${withdrawals.length})
                    </button>
                </div>

                <!-- Games Tab -->
                <div id="history-tab-games" style="display: block;">
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem;">
                        <div style="background: rgba(16, 185, 129, 0.1); padding: 1rem; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">
                            <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Wins</div>
                            <div style="font-size: 1.8rem; font-weight: 800; color: #10b981;">${totalWins}</div>
                        </div>
                        <div style="background: rgba(239, 68, 68, 0.1); padding: 1rem; border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.3);">
                            <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Losses</div>
                            <div style="font-size: 1.8rem; font-weight: 800; color: #ef4444;">${totalLosses}</div>
                        </div>
                        <div style="background: rgba(251, 191, 36, 0.1); padding: 1rem; border-radius: 12px; border: 1px solid rgba(251, 191, 36, 0.3);">
                            <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Net Profit/Loss</div>
                            <div style="font-size: 1.8rem; font-weight: 800; color: ${totalProfit >= 0 ? '#10b981' : '#ef4444'};">${totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)} G$</div>
                        </div>
                    </div>

                    <div style="max-height: 400px; overflow-y: auto;">
                        ${logs.length === 0 ? '<p style="text-align: center; color: rgba(255,255,255,0.5); padding: 2rem;">No games played yet</p>' : `
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="background: rgba(99, 102, 241, 0.1); border-bottom: 2px solid rgba(99, 102, 241, 0.3);">
                                        <th style="padding: 1rem; text-align: left;">Date</th>
                                        <th style="padding: 1rem; text-align: right;">Bet</th>
                                        <th style="padding: 1rem; text-align: center;">Multiplier</th>
                                        <th style="padding: 1rem; text-align: center;">Result</th>
                                        <th style="padding: 1rem; text-align: right;">Profit/Loss</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${logs.map(log => `
                                        <tr style="border-bottom: 1px solid rgba(99, 102, 241, 0.1);">
                                            <td style="padding: 1rem;">${new Date(log.date).toLocaleString()}</td>
                                            <td style="padding: 1rem; text-align: right; font-weight: 600;">${log.bet_amount.toFixed(2)} G$</td>
                                            <td style="padding: 1rem; text-align: center; font-weight: 700; color: #a855f7;">${log.multiplier}x</td>
                                            <td style="padding: 1rem; text-align: center;">
                                                <span style="padding: 0.25rem 0.75rem; border-radius: 6px; font-weight: 600; background: ${log.result === 'WIN' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; color: ${log.result === 'WIN' ? '#10b981' : '#ef4444'};">
                                                    ${log.result}
                                                </span>
                                            </td>
                                            <td style="padding: 1rem; text-align: right; font-weight: 700; color: ${log.profit_loss >= 0 ? '#10b981' : '#ef4444'};">
                                                ${log.profit_loss >= 0 ? '+' : ''}${log.profit_loss.toFixed(2)} G$
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `}
                    </div>
                </div>

                <!-- Deposits Tab -->
                <div id="history-tab-deposits" style="display: none;">
                    <div style="background: rgba(99, 102, 241, 0.1); padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem;">
                        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Deposited</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #6366f1;">${totalDeposited.toFixed(2)} G$</div>
                    </div>

                    <div style="max-height: 400px; overflow-y: auto;">
                        ${deposits.length === 0 ? '<p style="text-align: center; color: rgba(255,255,255,0.5); padding: 2rem;">No deposits yet</p>' : `
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="background: rgba(99, 102, 241, 0.1); border-bottom: 2px solid rgba(99, 102, 241, 0.3);">
                                        <th style="padding: 1rem; text-align: left;">Date</th>
                                        <th style="padding: 1rem; text-align: right;">Amount</th>
                                        <th style="padding: 1rem; text-align: center;">Transaction</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${deposits.map(d => `
                                        <tr style="border-bottom: 1px solid rgba(99, 102, 241, 0.1);">
                                            <td style="padding: 1rem;">${new Date(d.date).toLocaleString()}</td>
                                            <td style="padding: 1rem; text-align: right; font-weight: 700; color: #10b981;">+${d.amount.toFixed(2)} G$</td>
                                            <td style="padding: 1rem; text-align: center;">
                                                <a href="https://explorer.celo.org/mainnet/tx/${d.tx_hash}" target="_blank" style="color: #6366f1; text-decoration: none;">
                                                    ${d.tx_hash.substring(0, 10)}...
                                                </a>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `}
                    </div>
                </div>

                <!-- Withdrawals Tab -->
                <div id="history-tab-withdrawals" style="display: none;">
                    <div style="background: rgba(16, 185, 129, 0.1); padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem;">
                        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Withdrawn</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #10b981;">${totalWithdrawn.toFixed(2)} G$</div>
                    </div>

                    <div style="max-height: 400px; overflow-y: auto;">
                        ${withdrawals.length === 0 ? '<p style="text-align: center; color: rgba(255,255,255,0.5); padding: 2rem;">No withdrawals yet</p>' : `
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="background: rgba(99, 102, 241, 0.1); border-bottom: 2px solid rgba(99, 102, 241, 0.3);">
                                        <th style="padding: 1rem; text-align: left;">Date</th>
                                        <th style="padding: 1rem; text-align: right;">Amount</th>
                                        <th style="padding: 1rem; text-align: center;">Transaction</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${withdrawals.map(w => `
                                        <tr style="border-bottom: 1px solid rgba(99, 102, 241, 0.1);">
                                            <td style="padding: 1rem;">${new Date(w.date).toLocaleString()}</td>
                                            <td style="padding: 1rem; text-align: right; font-weight: 700; color: #ef4444;">-${w.amount.toFixed(2)} G$</td>
                                            <td style="padding: 1rem; text-align: center;">
                                                <a href="https://explorer.celo.org/mainnet/tx/${w.tx_hash}" target="_blank" style="color: #6366f1; text-decoration: none;">
                                                    ${w.tx_hash.substring(0, 10)}...
                                                </a>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `}
                    </div>
                </div>
            </div>
        `;

        // Show modal
        modal.style.display = 'flex';

    } catch (error) {
        console.error('❌ Error loading game logs:', error);
        showNotification('Failed to load game logs', 'error');
    }
};

// Tab switching function
window.showHistoryTab = function(tab) {
    // Hide all tabs
    document.getElementById('history-tab-games').style.display = 'none';
    document.getElementById('history-tab-deposits').style.display = 'none';
    document.getElementById('history-tab-withdrawals').style.display = 'none';

    // Reset all tab buttons
    document.getElementById('tab-games').style.background = 'rgba(99, 102, 241, 0.2)';
    document.getElementById('tab-deposits').style.background = 'rgba(99, 102, 241, 0.2)';
    document.getElementById('tab-withdrawals').style.background = 'rgba(99, 102, 241, 0.2)';

    // Show selected tab
    document.getElementById('history-tab-' + tab).style.display = 'block';
    document.getElementById('tab-' + tab).style.background = 'linear-gradient(135deg, #6366f1, #a855f7)';
};

// Game Logs Modal (keeping for backward compatibility)
window.openGameLogsModal_OLD = async function() {
    try {
        const response = await fetch('/minigames/api/game-logs');
        const data = await response.json();

        if (!data.success) {
            showNotification('Failed to load game logs', 'error');
            return;
        }

        const logs = data.game_logs || [];

        const modal = document.getElementById('gameModal');
        const content = document.getElementById('gameContent');

        let totalWins = 0;
        let totalLosses = 0;
        let totalProfit = 0;

        logs.forEach(log => {
            if (log.result === 'WIN') totalWins++;
            else totalLosses++;
            totalProfit += log.profit_loss;
        });

        content.innerHTML = `
            <div style="padding: 2rem; max-width: 900px; width: 100%;">
                <h2 style="font-size: 2rem; margin-bottom: 1.5rem; color: #6366f1;">📊 Game Logs & History</h2>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div style="background: rgba(16, 185, 129, 0.1); padding: 1rem; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">
                        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Wins</div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #10b981;">${totalWins}</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.1); padding: 1rem; border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.3);">
                        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Losses</div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: #ef4444;">${totalLosses}</div>
                    </div>
                    <div style="background: rgba(251, 191, 36, 0.1); padding: 1rem; border-radius: 12px; border: 1px solid rgba(251, 191, 36, 0.3);">
                        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7);">Total Profit/Loss</div>
                        <div style="font-size: 1.8rem; font-weight: 800; color: ${totalProfit >= 0 ? '#10b981' : '#ef4444'};">
                            ${totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)} G$
                        </div>
                    </div>
                </div>

                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 1rem; max-height: 500px; overflow-y: auto;">
                    ${logs.length === 0 ? '<p style="text-align: center; color: rgba(255,255,255,0.6); padding: 2rem;">No games played yet</p>' : `
                        <table style="width: 100%; color: white;">
                            <thead>
                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                                    <th style="padding: 0.75rem; text-align: left; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Date</th>
                                    <th style="padding: 0.75rem; text-align: right; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Bet</th>
                                    <th style="padding: 0.75rem; text-align: right; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Multiplier</th>
                                    <th style="padding: 0.75rem; text-align: center; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Result</th>
                                    <th style="padding: 0.75rem; text-align: right; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Profit/Loss</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${logs.map(log => {
                                    const date = new Date(log.date);
                                    const isWin = log.result === 'WIN';
                                    return `
                                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                            <td style="padding: 0.75rem; font-size: 0.85rem;">${date.toLocaleString()}</td>
                                            <td style="padding: 0.75rem; text-align: right; font-size: 0.9rem;">${log.bet_amount} G$</td>
                                            <td style="padding: 0.75rem; text-align: right; font-size: 0.9rem; font-weight: 600; color: ${isWin ? '#10b981' : '#ef4444'};">${log.multiplier}x</td>
                                            <td style="padding: 0.75rem; text-align: center;">
                                                <span style="padding: 0.25rem 0.75rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; background: ${isWin ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; color: ${isWin ? '#10b981' : '#ef4444'};">
                                                    ${log.result}
                                                </span>
                                            </td>
                                            <td style="padding: 0.75rem; text-align: right; font-size: 0.9rem; font-weight: 600; color: ${log.profit_loss >= 0 ? '#10b981' : '#ef4444'};">
                                                ${log.profit_loss >= 0 ? '+' : ''}${log.profit_loss.toFixed(2)} G$
                                            </td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    `}
                </div>

                <button onclick="window.closeGameModal()" style="width: 100%; margin-top: 1.5rem; padding: 1rem; background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; border-radius: 12px; font-size: 1rem; font-weight: 600; cursor: pointer;">
                    Close
                </button>
            </div>
        `;

        modal.style.display = 'flex';

    } catch (error) {
        console.error('❌ Error loading game logs:', error);
        showNotification('Failed to load game logs', 'error');
    }
};
