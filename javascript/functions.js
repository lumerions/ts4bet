
export async function updateBalance() {
    try {
        const response = await fetch('/getbalance');
        const data = await response.text(); 
        const number = parseFloat(data);
        if (!isNaN(number)) {
            const balanceBtn = document.querySelector('.balance-btn');
            if (balanceBtn) balanceBtn.textContent = `$${number.toLocaleString()}`;
        }
    } catch (error) {
        console.error('Error fetching balance:', error);
    }
}

export function adjustBet(multiplier) {
    const input = document.getElementById('betAmount');
    const value = parseFloat(input.value) || 0;
    input.value = Math.max(1, Math.floor(value * multiplier));
}

export function setMaxBet() {
    const input = document.getElementById('betAmount');
    const balanceBtn = document.querySelector('.balance-btn');

    const balanceText = balanceBtn.textContent.replace(/\$|,/g, '');
    const balanceNumber = parseFloat(balanceText) || 0;

    input.value = balanceNumber;
}