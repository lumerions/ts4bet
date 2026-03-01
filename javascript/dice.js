import { updateBalance } from './functions.js';
import { adjustBet } from './functions.js';
import { setMaxBet } from './functions.js';
const slider = document.getElementById('diceSlider');
const winChanceTxt = document.getElementById('winChance');
const multiplierTxt = document.getElementById('diceMultiplier');
const rollTargetTxt = document.getElementById('rollTarget');
const rollBtn = document.getElementById('rollDiceBtn');
const resultDisplay = document.getElementById('diceResult');
const modeLabel = document.getElementById('modeLabel');
const btnOver = document.getElementById('btnOver');
const btnUnder = document.getElementById('btnUnder');
const mineInput = document.getElementById("mineCount");
let isOverMode = true;

mineInput.parentElement.style.display = "none"; 
mineInput.parentElement.previousElementSibling.style.display = "none"; 

function updateDiceUI() {
    const val = parseInt(slider.value);
    let winChance;

    if (isOverMode) {
        winChance = 100 - val; 
        modeLabel.textContent = "over";
        slider.style.background = `linear-gradient(to right, #ef4444 ${val}%, #22c55e ${val}%)`;
    } else {
        winChance = val; 
        modeLabel.textContent = "under";
        slider.style.background = `linear-gradient(to right, #22c55e ${val}%, #ef4444 ${val}%)`;
    }

    const winChanceDecimal = winChance / 100;
    const multiplier = winChanceDecimal > 0 ? (0.98 / winChanceDecimal).toFixed(4) : 0;

    winChanceTxt.textContent = winChance.toFixed(2) + '%';
    multiplierTxt.textContent = multiplier + 'x';
    rollTargetTxt.textContent = val;
}

btnOver.addEventListener('click', () => {
    isOverMode = true;
    btnOver.classList.add('active');
    btnUnder.classList.remove('active');
    updateDiceUI();
});

btnUnder.addEventListener('click', () => {
    isOverMode = false;
    btnUnder.classList.add('active');
    btnOver.classList.remove('active');
    updateDiceUI();
});


slider.addEventListener('input', updateDiceUI);

rollBtn.addEventListener('click', async () => {
    const BetAmount = parseFloat(document.getElementById('betAmount').value) || 0;
    const targetNumber = parseInt(slider.value);
    
    rollBtn.disabled = true;
    resultDisplay.style.opacity = '0.5';

    try {
        const response = await fetch('/games/dice/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ 
                BetAmount, 
                targetNumber,
                prediction: isOverMode ? 'over' : 'under',
            })
        });

        if (!response.ok) throw new Error('Network error');

        const result = await response.json();

            if (result.error) { 
                throw new Error(result.error || "Something went wrong with playing dice.");
            }

            const rollValue = result.roll ?? result.data?.roll;
            if (rollValue === undefined) {
                throw new Error("Dice roll not found in server response.");
            }

        resultDisplay.textContent = result.roll.toFixed(2);
        resultDisplay.style.opacity = '1';
        resultDisplay.style.color = result.win ? '#22c55e' : '#ef4444';

        updateBalance();
        
    } catch (err) {
        console.error('Dice Roll Error:', err);
        alert('Error rolling dice. Check console.');
    } finally {
        rollBtn.disabled = false;
    }
});

updateDiceUI();