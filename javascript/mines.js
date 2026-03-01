import { updateBalance } from './functions.js';

function adjustBet(multiplier) {
    const input = document.getElementById('betAmount');
    const value = parseFloat(input.value) || 0;
    input.value = Math.max(1, Math.floor(value * multiplier));
}

function setMaxBet() {
    const input = document.getElementById('betAmount');
    const balanceBtn = document.querySelector('.balance-btn');

    const balanceText = balanceBtn.textContent.replace(/\$|,/g, '');
    const balanceNumber = parseFloat(balanceText) || 0;

    input.value = balanceNumber;
}

document.getElementById('playMinesBtn').addEventListener('click', async () => {
    const betAmount = parseFloat(document.getElementById('betAmount').value) || 0;
    const mineCount = parseInt(document.getElementById('mineCount').value) || 0;
    const playBtn = document.getElementById('playMinesBtn');

    if (playBtn.textContent.includes('Cashout')) {
            try {
            const response = await fetch('/games/cashout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
            });
    
            if (!response.ok) throw new Error('Request failed');
    
            if (response.redirected) {
                window.location.href = response.url;
            }

            const result = await response.json();
            const mines = result.mines;

            if (Array.isArray(mines)) {
                document.querySelectorAll('.cell').forEach(cellEl => {
                    const index = Number(cellEl.dataset.index);
            
                    if (mines.includes(index)) {
                        cellEl.textContent = '💣';
                        cellEl.classList.add('mine');
                    } else if (!cellEl.classList.contains('clicked')) {
                        cellEl.classList.add('reveal');
                    } else {
                        cellEl.textContent = '$';
                    }
                });
            }

        updateBalance();
        playBtn.style.backgroundColor = '';
        playBtn.textContent = 'Play Mines';

        } catch (err) {
            console.error('Error starting Mines:', err);
            alert('Failed to start Mines. Please try again.');
        }
    } else {
        try {
            const Game = "Mines"
            const response = await fetch('/games/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ betAmount, mineCount, Game})
            });
    
            if (!response.ok) throw new Error('Request failed');

            if (response.redirected) {
                window.location.href = response.url;
            } else {
                updateBalance();
            }
    

        } catch (err) {
            console.error('Error starting Mines:', err);
            alert('Failed to start Mines. Please try again.');
        }

    }
    
});

document.querySelectorAll('.cell').forEach(cell => {
cell.addEventListener('click', async () => {
    if (cell.classList.contains('revealed')) return;

    const grid = document.querySelector('.grid');
    if (grid.classList.contains('gamedone')) return;

    const tileIndex = cell.dataset.index;
    const playBtn = document.getElementById('playMinesBtn');
    const Game = "Mines";

    try {
        const response = await fetch('/games/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ tileIndex,Game })
        });

        if (!response.ok) throw new Error('Request failed');

        const result = await response.json();
        const mines = result.mines;

        if (result.ismine && Array.isArray(mines)) {
            document.querySelectorAll('.cell').forEach(cellEl => {
                const index = Number(cellEl.dataset.index);
                if (mines.includes(index)) {
                    cellEl.textContent = '💣';
                    cellEl.classList.add('mine');
                } else if (!cellEl.classList.contains('clicked')) {
                    cellEl.classList.add('reveal');
                }
            });

            playBtn.style.backgroundColor = '';
            playBtn.textContent = 'Play Mines';
            document.getElementById('multiplier').textContent = '1x';
            document.getElementById('currentAmount').textContent = '0';
            document.getElementById('amountAfter').textContent = '0';

            grid.classList.add('gamedone');

        } else { 
            cell.textContent = '$';
            cell.classList.add('clicked');
            cell.classList.add('revealed');

            const game = "Mines"; 
            
            const cashoutResponse = await fetch(`/games/cashoutamount?Game=${encodeURIComponent(game)}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
            });

            if (!cashoutResponse.ok) throw new Error('Failed to fetch cashout info');

            const data = await cashoutResponse.json();

            const currentAmount = data.amount;
            const amountAfterNextTile = data.amountafter;
            const multiplier = data.multiplier;

            document.getElementById('multiplier').textContent = multiplier.toFixed(2) + 'x';
            document.getElementById('currentAmount').textContent = currentAmount;
            document.getElementById('amountAfter').textContent = amountAfterNextTile;

            playBtn.style.backgroundColor = '#16a34a';
            playBtn.textContent = 'Cashout';
        }

    } catch (err) {
        console.error('Error handling tile click:', err);
    }
});
});

async function Initiate() {
    const errorMessage = document.querySelector('.error-message');
    if (errorMessage) {
        openWallet('withdraw');
    }

    const cashoutResponse = await fetch('/games/cashoutamount?Game=Mines', {
        method: 'GET',
        credentials: 'include', 
    });

    if (!cashoutResponse.ok) throw new Error('Failed to fetch cashout info');

    const data = await cashoutResponse.json();

    const currentAmount = data.amount;
    const amountAfterNextTile = data.amountafter;
    const multiplier = data.multiplier;

    document.getElementById('multiplier').textContent = multiplier.toFixed(2) + 'x';
    document.getElementById('currentAmount').textContent = currentAmount;
    document.getElementById('amountAfter').textContent = amountAfterNextTile;

    async function restoreRevealedTiles() {
        try {
            const response = await fetch(`/games/getCurrentData?Game=Mines`, { method: 'GET', credentials: 'include' });
    
            if (!response.ok) throw new Error('Failed to fetch current mines data');
    
            const revealedIndices = await response.json(); 
    
            document.querySelectorAll('.cell').forEach(cell => {
                const index = Number(cell.dataset.index);
    
                if (revealedIndices.includes(index)) {
                    cell.textContent = '$';
                    cell.classList.add('clicked', 'revealed'); 
                }
            });

            const playBtn = document.getElementById('playMinesBtn');

            if (revealedIndices.length > 0) {
                playBtn.style.backgroundColor = '#16a34a';
                playBtn.textContent = 'Cashout';
            } else {
                playBtn.style.backgroundColor = ''; 
                playBtn.textContent = 'Play Mines';
            }
    
        } catch (err) {
            console.error('Error restoring revealed tiles:', err);
        }
    }

restoreRevealedTiles()
}     

Initiate();  