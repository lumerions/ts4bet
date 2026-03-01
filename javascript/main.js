import { updateBalance } from './functions.js';

document.addEventListener('DOMContentLoaded', () => {
    const wrapper = document.querySelector('.balance-wrapper');
    const modal = document.getElementById('walletModal');
    const inventoryModal = document.getElementById('inventoryModal');
    const inventoryActionModal = document.getElementById('inventoryActionModal');
    const closeBtn = modal?.querySelector('.close');
    const closeInventoryBtn = inventoryModal?.querySelector('.close');
    const closeInventoryActionBtn = document.getElementById('closeInventoryAction');
    const tabs = document.querySelectorAll('.tab');
    const depositBtn = document.getElementById('depositBtn');
    const withdrawBtn = document.getElementById('withdrawBtn');
    const instructions = document.getElementById('instructions');
    const inputField = document.getElementById('amount');
    const openDepositBtn = document.getElementById('openDeposit');
    const openWithdrawBtn = document.getElementById('openWithdraw');
    const openInventoryBtn = document.getElementById('Inventory');
    const sortBtn = document.getElementById('sortBtn');
    const sortDropdown = document.getElementById('sortDropdown');
    const InventoryDepositBtn = document.getElementById('InventoryDepositBtn');
    const InventoryWithdrawBtn = document.getElementById('InventoryWithdrawBtn');
    const inventoryActionTitle = document.getElementById('inventoryActionTitle');
    const inventoryInstructions = document.getElementById('inventoryInstructions');
    const inventoryActionBtn = document.getElementById('inventoryActionBtn');
    const totalValueLabel = document.querySelector('#totalValue strong');
    const searchInput = document.getElementById('inventorySearch');
    let TotalValue = 0;
    let ToWithdraw = {};

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.toLowerCase();

        const inventoryItems = document.querySelectorAll('.inventory-item');

        inventoryItems.forEach(item => {
            const name = item.querySelector('.name')?.textContent.toLowerCase() || '';
            const serial = item.querySelector('.serial')?.textContent.toLowerCase() || '';

            if (name.includes(query) || serial.includes(query)) {
                item.style.display = 'inline-block'; 
            } else {
                item.style.display = 'none'; 
            }
        });
    });

    updateBalance();

    wrapper?.querySelector('.balance-btn')?.addEventListener('click', e => {
        e.stopPropagation();
        wrapper.classList.toggle('open');
    });

    window.addEventListener('click', () => {
        wrapper?.classList.remove('open');
        if (sortDropdown) sortDropdown.style.display = 'none';
    });

    function openWallet(type) {
        inventoryModal?.classList.remove('open');
        modal?.classList.add('open');
        switchTab(type);
    }

    function switchTab(type) {
        tabs.forEach(tab => tab.classList.remove('active'));
        const activeTab = document.querySelector('.tab.' + type);
        if (activeTab) activeTab.classList.add('active');

        if (type === 'deposit') {
            depositBtn.style.display = 'block';
            withdrawBtn.style.display = 'none';
            if (instructions) instructions.innerHTML = `1. Enter amount<br>2. Click Initiate<br>3. Complete in-game`;
        } else {
            depositBtn.style.display = 'none';
            withdrawBtn.style.display = 'block';
            if (instructions) instructions.innerHTML = `1. Enter amount<br>2. Click Initiate<br>3. Complete in-game`;
        }
    }

    openDepositBtn?.addEventListener('click', () => openWallet('deposit'));
    openWithdrawBtn?.addEventListener('click', () => openWallet('withdraw'));
    
    closeBtn?.addEventListener('click', () => {
        modal?.classList.remove('open');
    });
    closeInventoryBtn?.addEventListener('click', () => {
        inventoryActionModal?.classList.remove('open'); 
        inventoryModal?.classList.remove('open');
    });

    modal?.addEventListener('click', e => { if (e.target === modal) modal.classList.remove('open'); });

    tabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.classList.contains('deposit') ? 'deposit' : 'withdraw'));
    });

    depositBtn?.addEventListener('click', () => {
        const val = parseFloat(inputField?.value);
        if (val > 0) window.location.href = `/deposit?amount=${val}`;
    });

    withdrawBtn?.addEventListener('click', () => {
        const val = parseFloat(inputField?.value);
        if (val > 0) window.location.href = `/withdraw?amount=${val}&page=home`;
    });

    function UpdateTotalValueLabel() {
        const formatted = TotalValue.toLocaleString();
        if (totalValueLabel) totalValueLabel.textContent = `$${formatted}`;
    }

openInventoryBtn?.addEventListener('click', async (e) => {
    e.stopPropagation();
    
    const targetModal = document.getElementById('inventoryModal');
    targetModal.classList.add('open');
    
    const grid = targetModal.querySelector('.inventory-grid');
    grid.innerHTML = ''; 

    TotalValue = 0;
    ToWithdraw = {};
    UpdateTotalValueLabel();

    try {
        const response = await fetch('/GetInventory');
        const data = await response.json();

        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'inventory-item'; 
            
            div.innerHTML = `
                <div class="select-box"></div>
                <img src="${item.ImageUrl}" alt="${item.itemname}">
                <span class="serial">#${item.serial}</span>
                <span class="name">${item.itemname}</span>
                <span class="value">$${item.Value.toLocaleString()}</span>
            `;

            div.addEventListener('click', () => {
                const val = parseFloat(item.Value) || 0;
                
                const isNowSelected = div.classList.toggle('selected');

                if (isNowSelected) {
                    TotalValue += val;
                    if (!ToWithdraw[item.itemname]) ToWithdraw[item.itemname] = {};
                    ToWithdraw[item.itemname][item.serial] = true;
                } else {
                    TotalValue -= val;
                    if (ToWithdraw[item.itemname]) {
                        delete ToWithdraw[item.itemname][item.serial];
                        if (Object.keys(ToWithdraw[item.itemname]).length === 0) {
                            delete ToWithdraw[item.itemname];
                        }
                    }
                }
                UpdateTotalValueLabel();
            });

            grid.appendChild(div);
        });

    } catch (error) {
        console.error('Fetch Error:', error);
    }
});

    inventoryActionBtn?.addEventListener('click', async e => {
        if (inventoryActionBtn.textContent === 'Initiate Deposit') {
            window.location.href = '/deposititems';
        } else {
            const itemdata = ToWithdraw; 

            try {
                const response = await fetch('/withdrawitems', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ itemdata })
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.error || 'Request failed');
                }

                const data = await response.json();

                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    console.error('No redirect URL returned');
                }
            } catch (err) {
                console.error('Error withdrawing items:', err.message);
            }

        }
    });

    inventoryModal?.addEventListener('click', e => { if (e.target === inventoryModal) inventoryModal.classList.remove('open'); });

    sortBtn?.addEventListener('click', e => {
        e.stopPropagation();
        if (sortDropdown) sortDropdown.style.display = sortDropdown.style.display === 'block' ? 'none' : 'block';
    });

    InventoryDepositBtn?.addEventListener('click', () => openInventoryAction('deposit'));
    InventoryWithdrawBtn?.addEventListener('click', () => openInventoryAction('withdraw'));

    function openInventoryAction(type) {
        if (TotalValue == 0 && type !== 'deposit' ) {
            return
        }

        inventoryModal?.classList.remove('open');

        if (inventoryActionTitle) inventoryActionTitle.textContent =
            type === 'deposit' ? 'Inventory Deposit' : 'Inventory Withdraw';

        if (inventoryActionBtn) {
            inventoryActionBtn.className = `action-btn ${type}`;
            inventoryActionBtn.textContent = type === 'deposit' ? 'Initiate Deposit' : 'Initiate Withdraw';
        }

        if (inventoryInstructions) inventoryInstructions.innerHTML = `
            1. Click the button below to open Roblox<br>
            2. Join the game to complete the transaction<br>
            3. Complete deposit in-game
        `;

        inventoryActionModal?.classList.add('open');
    }

    closeInventoryActionBtn?.addEventListener('click', () => {
        console.log(inventoryActionModal?.classList.contains('open'))
        if (inventoryActionModal?.classList.contains('open')) {
            inventoryActionModal?.classList.remove('open');
            inventoryModal?.classList.add('open');
        } else {
            if (inventoryModal?.classList.contains('open')) {
                inventoryModal?.classList.remove('open');
            } else {
                inventoryActionModal?.classList.add('open');
            }
        }
    });

    inventoryActionModal?.addEventListener('click', e => { if (e.target === inventoryActionModal) inventoryActionModal.classList.remove('open'); });

    const currentPath = window.location.pathname;
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) link.classList.add('active');
    });

    UpdateTotalValueLabel();
});