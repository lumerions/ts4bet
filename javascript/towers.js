import { updateBalance } from './functions.js';
import { adjustBet } from './functions.js';
import { setMaxBet } from './functions.js';
let currentbetamount = 0;

document.getElementById('playTowersBtn').addEventListener('click', async () => {
    const betAmount = parseFloat(document.getElementById('betAmount').value) || 0;
    const mineCount = parseInt(document.getElementById('mineCount').value) || 0;
    const playBtn = document.getElementById('playTowersBtn');

    if (playBtn.textContent.includes('Cashout')) {
        try {
            const response = await fetch('/games/cashout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ Game: "Towers" })
            });

            if (!response.ok) throw new Error('Request failed');

            if (response.redirected) window.location.href = response.url;

            const result =  await response.json();
            const mines = result.mines;

            if (Array.isArray(mines)) {
                document.querySelectorAll('.payout').forEach(cellEl => {
                    const index = Number(cellEl.dataset.index);
                    const r = Number(cellEl.dataset.row);
                    const payoutEl = cellEl.querySelector('.payout-value');
                    const dollarEl = cellEl.querySelector('span'); 

                    cellEl.classList.remove('mine', 'reveal');

                    if (mines.includes(index)) {
                        cellEl.classList.add('mine');
                        if (dollarEl) dollarEl.style.display = 'none'; 
                        if (payoutEl) payoutEl.textContent = '💣';
                    } else if (cellEl.classList.contains('clicked')) {
                        cellEl.classList.add('reveal');
                        if (payoutEl) {
                            const betA = Number(result.betamount) || 0;
                            let mine_multiplier = (result.mines.length / 23) ** 1.5 + 0.1;  
                            let cashAmount = Math.floor(betA * (r + 1) * mine_multiplier * 0.4);
                            payoutEl.textContent = cashAmount;
                        }
                    }
                });
            }

                    
            updateBalance();
            playBtn.style.backgroundColor = '';
            playBtn.textContent = 'Play Towers';

        } catch (err) {
            console.error('Error starting Towers:', err);
            alert('Failed to start Towers. Please try again.');
        }
    } else {
        try {
            currentbetamount = betAmount
            const Game = "Towers";
            const response =  await fetch('/games/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ betAmount, mineCount, Game })
            });

            if (!response.ok) throw new Error('Request failed');

            if (response.redirected) {
                window.location.href = response.url;
            } else {
                updateBalance();
            }

        } catch (err) {
            console.error('Error starting Towers:', err);
            alert('Failed to start Towers. Please try again.');
        }
    }
});

document.querySelectorAll('.payout').forEach(cell => {
    cell.addEventListener('click', async () => {
        if (cell.classList.contains('revealed')) return;

        const grid = document.querySelector('.payout-grid');
        if (grid.classList.contains('gamedone')) return;

        const tileIndex = cell.dataset.index;
        const Row = cell.dataset.row;
        const playBtn = document.getElementById('playTowersBtn');
        const Game = "Towers";

        try {
            const response =  await fetch('/games/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ tileIndex, Game })
            });
        
            if (!response.ok) throw new Error('Request failed');
        
            const result = await response.json();
            const mines = result.mines;
        
            if (result.ismine && Array.isArray(mines)) {
                document.querySelectorAll('.payout').forEach(cellEl => {
                    const index = Number(cellEl.dataset.index);
                    const payoutEl = cellEl.querySelector('.payout-value');
                    const dollarEl = cellEl.querySelector('span'); 
        
                    cellEl.classList.remove('mine', 'reveal');
        
                    if (mines.includes(index)) {
                        cellEl.classList.add('mine');
                        if (dollarEl) dollarEl.style.display = 'none'; 
                        if (payoutEl) payoutEl.textContent = '💣';
                    } else if (cellEl.classList.contains('clicked') && index == tileIndex) {
                        cellEl.classList.add('reveal');
                        if (payoutEl) {
                            const row = Number(cellEl.dataset.row);
                            const bet = Number(result.betamount) || 0;
                            const mineCount = Number(result.minescount) || 0;
                            let mine_multiplier = (mineCount / 23) ** 1.5 + 0.1;  
                            let cashAmount = Math.floor(bet * (row + 1) * mine_multiplier * 0.4);
                            payoutEl.textContent = cashAmount;
                        }
                    }
                });
        
                const playBtn = document.getElementById('playTowersBtn');
                playBtn.style.backgroundColor = '';
                playBtn.textContent = 'Play Towers';
                document.getElementById('currentAmount').textContent = '0';
                document.querySelector('.payout-grid').classList.add('gamedone');
        
            } else { 
                cell.classList.add('clicked', 'revealed');
                const rowValue = cell.dataset.row;
                const playBtn = document.getElementById('playTowersBtn');
        
                const cashoutResponse = await fetch(`/games/cashoutamount?Game=Towers&Row=${rowValue}`, { method: 'GET', credentials: 'include' });
                if (!cashoutResponse.ok) return;
        
                const data =  await cashoutResponse.json();
                const currentAmount = data.amount -Number(currentbetamount);
                cell.classList.add('reveal'); 
                document.getElementById('currentAmount').textContent = currentAmount;
                playBtn.style.backgroundColor = '#16a34a';
                playBtn.textContent = 'Cashout';
            }
        
        } catch (err) {
            console.error('Error handling tile click:', err);
        }

    });
});

let row = -1;

async function restoreRevealedTiles() {
    const response = await fetch(`/games/getCurrentData?Game=Towers`, { method: 'GET', credentials: 'include' });

    if (!response.ok) return;

    const revealedIndices = await response.json();

    document.querySelectorAll('.payout').forEach(cell => {
        const index = Number(cell.dataset.index);
        const maxRow = 8;
        const currentrow = maxRow - 1 - Math.floor(index / 3);

        if (currentrow > row) row = currentrow;

        if (revealedIndices.includes(index)) {
            cell.classList.add('reveal');
        }
    });

    const playBtn = document.getElementById('playTowersBtn');
    playBtn.textContent = revealedIndices.length ? 'Cashout' : 'Play Towers';
    playBtn.style.backgroundColor = revealedIndices.length ? '#16a34a' : '';
}

async function initGame() {
    await restoreRevealedTiles();

    try {
        const response = await fetch(`/games/cashoutamount?Game=Towers&Row=${row}`, { 
            credentials: 'include' 
        });

        if (response.ok) {
            const data = await response.json(); 
            
            const currentamount = Number(data.amount) || 0 - Number(currentbetamount) ;
            document.getElementById('currentAmount').textContent = currentamount;

            document.querySelectorAll('.payout').forEach(cell => {
                const payoutEl = cell.querySelector('.payout-value');
                if (payoutEl) {
                    const row = Number(cell.dataset.row);
                    const betamount = Number(data.betamount) || 0;
                    const mineCount = Number(data.minescount) || 0;
                    let mine_multiplier = mineCount / 23 ** 1.5 + 0.1
                    let cashAmount = Math.floor(betamount * (row + 1) * mine_multiplier * 0.4)
                    payoutEl.textContent = cashAmount;
                } else {
                    console.warn('Invalid payout element', cell);
                }
            });
        }
    } catch (err) {
        console.error("Initialization error:", err);
    }
}

initGame();
