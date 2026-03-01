
document.addEventListener('DOMContentLoaded', () => {
    const currentUsername = "{{ username }}"; 
    let globalInventory = [];
    let createSelection = []; 
    let joinSelection = [];   
    let activeMatchId = null;
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    const getItemFromId = (formattedId) => {
        const [name, serial] = formattedId.split('#');
        return globalInventory.find(i => String(i.itemname) === name && String(i.serial) === serial);
    };

    document.querySelectorAll('.side-option').forEach(opt => {
        opt.addEventListener('click', () => {
            document.querySelectorAll('.side-option').forEach(el => el.classList.remove('selected'));
            opt.classList.add('selected');
        });
    });

    document.getElementById('coinflipCreateBtn')?.addEventListener('click', async function() {
        if (createSelection.length === 0) {
            return alert("Please select at least one item.");
        }

        const sideEl = document.querySelector('.side-option.selected');
        if (!sideEl) return alert("Select a side first!");

        const selectedSide = document.querySelector('.side-option.selected').getAttribute('data-side');
        const btn = this;

        const formattedData = createSelection.map(idString => {
            const item = getItemFromId(idString); 
            return {
                itemid: item.itemid,
                serial: item.serial,
                itemname: item.itemname
            };
        });

        btn.disabled = true;
        btn.innerText = "Creating...";

        try {
            const response = await fetch('/createcoinflip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                body: JSON.stringify({
                    Side: selectedSide,       
                    coinflipData: formattedData 
                })
            });

            const result = await response.json();

            if (result.success) {
                location.reload(); 
            } else {
                alert(result.error || "Failed to create match.");
            }
        } catch (e) {
            console.error(e);
            alert("An error occurred while creating the match.");
        } finally {
            btn.disabled = false;
            btn.innerText = "Create Match";
        }
    });

    const updateStats = (prefix, selection) => {
        const totalItems = selection.length;
        const totalValue = selection.reduce((sum, id) => {
            const item = getItemFromId(id);
            return sum + (item ? parseFloat(item.Value) : 0);
        }, 0);
        
        document.getElementById(`${prefix}TotalItems`).textContent = totalItems;
        document.getElementById(`${prefix}TotalValue`).textContent = `$${totalValue.toFixed(2)}`;
    };

    const renderInventory = (containerId, selectionArr, prefix) => {
        const grid = document.getElementById(containerId);
        if(!grid) return;
        grid.innerHTML = '';
        globalInventory.forEach(item => {
            const itemIdentifier = `${item.itemname}#${item.serial}`;
            const div = document.createElement('div');
            div.className = `inventory-item ${selectionArr.includes(itemIdentifier) ? 'selected' : ''}`;
            div.innerHTML = `
                <div class="select-box"></div>
                <img src="${item.ImageUrl}" alt="${item.itemname}">
                <span class="serial">#${item.serial}</span>
                <span class="name">${item.itemname}</span>
                <span class="value">$${item.Value.toLocaleString()}</span>
            `;

            
            div.onclick = () => {
                const index = selectionArr.indexOf(itemIdentifier);
                if(index > -1) selectionArr.splice(index, 1);
                else selectionArr.push(itemIdentifier);
                
                div.classList.toggle('selected');
                updateStats(prefix, selectionArr);
            };
            grid.appendChild(div);
        });
    };

    const openJoinModal = (id) => {
        activeMatchId = id;
        joinSelection = [];
        updateStats('join', joinSelection);
        renderInventory('joinInventory', joinSelection, 'join');
        document.getElementById('joinCoinflipModal').classList.add('open');
    };

    document.querySelectorAll('.close, [data-close]').forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-close') || btn.closest('.modal').id;
            document.getElementById(target).classList.remove('open');
        });
    });

    document.getElementById("createMatchBtn")?.addEventListener("click", () => {
        createSelection = [];
        updateStats('create', createSelection);
        renderInventory('createInventory', createSelection, 'create');
        document.getElementById("createCoinflipModal").classList.add("open");
    });

    document.getElementById('confirmJoinBtn')?.addEventListener('click', async function() {
        if (joinSelection.length === 0) return alert("Please select items to join.");
        const btn = this;
        btn.disabled = true;
        btn.innerText = "Joining...";

        try {
            const response = await fetch('/JoinMatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    matchId: activeMatchId,
                    items: joinSelection 
                })
            });
            const result = await response.json();
            if (result.success) location.reload();
            else alert(result.error || "Failed to join match.");
        } catch (e) {
            alert("An error occurred.");
        } finally {
            btn.disabled = false;
            btn.innerText = "Confirm Join";
        }
    });

      function flipCoin(winnerSide, callback) {
          const coin = document.getElementById('coin');
          const overlay = document.getElementById('coinflipOverlay');
          
          overlay.style.display = 'flex'; 
          
          const finalResult = (winnerSide.toLowerCase() === 'heads' ? 0 : 1);
          
          coin.style.transition = 'none';
          coin.style.transform = 'rotateY(0deg)';
          
          coin.offsetWidth;
          
          coin.style.transition = 'transform 3s ease-out';
          const spins = 10; 
          const deg = (spins * 360) + (finalResult === 0 ? 0 : 180);
          coin.style.transform = `rotateY(${deg}deg)`;
      
          setTimeout(() => {
              if (callback) callback(winnerSide);
              
              setTimeout(() => {
                  overlay.style.display = 'none';
                  location.reload(); 
              }, 2000);
          }, 3500);
      }
               

    document.querySelector('.coinflip-container')?.addEventListener('click', e => {
        const matchCard = e.target.closest('.match-card');
        if (!matchCard) return;


        const matchId = matchCard.dataset.id;
        const CoinflipCreator = matchCard.dataset.isCreator;
        const Winner = matchCard.dataset.winner || "";

         if (Winner.length > 0) {
            matchCard.querySelectorAll('button:not(.view-btn)').forEach(btn => {
                btn.style.visibility = 'hidden'; 
            });
         }

        if (e.target.classList.contains('join-btn')) {
            if (!e.target.disabled) openJoinModal(matchCard.dataset.id);
        }

        if (e.target.classList.contains('cancel-btn')) {
            const btn = e.target;
            btn.disabled = true;
            btn.innerText = "Cancelling...";

            async function cancelCoinflip() {
                try {
                    const response = await fetch('/cancelcoinflip', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                             matchId: matchId, CoinflipCreator: CoinflipCreator 
                            }
                        )
                    });

                    const result = await response.json();
                    if (result.success) {
                        location.reload(); 
                    } else {
                        alert(result.error || "Failed to cancel match.");
                    }
                } catch (err) {
                    console.error(err);
                    alert("An error occurred while trying to cancel.");
                }
                finally {
                    btn.disabled = false;
                    btn.innerText = "Join";
                    btn.style.backgroundColor = "#16a34a";
                }
            }

            cancelCoinflip()
        }

        if (e.target.classList.contains('view-btn')) {
          const p1Side = matchCard.dataset.side;
          const totalVal = matchCard.dataset.totalValue;
          
          const p1Node = matchCard.querySelector('.player:first-child');
          const p2Node = matchCard.querySelector('.player:last-child');
          
          const p1User = p1Node.getAttribute('data-username');
          const p2User = p2Node.getAttribute('data-username');
          
          const isCreator = (p1User === currentUsername);
          const hasJoiner = (p2User && p2User !== "");
          
          let html = `
              <div style="text-align:center; margin-bottom: 15px; color: #22c55e; font-weight: bold;">
                  Match Value: $${totalVal}
              </div>
              <div style="display:flex;justify-content:center;align-items:center;gap:25px;margin-bottom:20px;">
          `;
      
          [p1Node, p2Node].forEach((p, idx) => {
              const avatar = p.querySelector('.player-avatar')?.src;
              const isEmpty = p.querySelector('.empty-avatar-placeholder');
              const username = p.getAttribute('data-username') || "Waiting...";
              const sideIcon = (idx === 0) ? (p1Side === "Heads" ? "🪙" : "💰") : (p1Side === "Heads" ? "💰" : "🪙");
              
              if (isEmpty) {
                  html += `<div class="player"><div class="empty-avatar-placeholder" style="width:70px;height:70px;"></div><div style="font-size: 0.7rem; margin-top:5px; color:#666;">Waiting...</div></div>`;
              } else {
                  html += `
                      <div class="player">
                          <div class="side-badge" style="width:24px;height:24px;font-size:0.7rem;">${sideIcon}</div>
                          <img src="${avatar}" class="player-avatar" style="width:70px;height:70px;">
                          <div style="font-size: 0.75rem; margin-top: 5px; color: #94a3b8;">${username}</div>
                      </div>`;
              }
              if(idx === 0) html += `<div class="vs-text" style="font-size:1rem;">VS</div>`;
          });
      
          html += `</div>`;
      
          html += `<div style="display:flex;justify-content:center;gap:40px;margin-top:15px;">`;
      
          [p1Node, p2Node].forEach((p, idx) => {
             const items = p.querySelectorAll('.player-items-preview .preview-item img');
              html += `<div style="display:flex;flex-direction:column;align-items:center;">`;
              html += `<div style="margin-bottom:5px;color:#ccc;font-size:0.85rem;">${p.getAttribute('data-username') || "Waiting..."}'s Items</div>`;
              items.forEach(img => {
                  html += `<div class="preview-item" style="width:40px;height:40px;margin:2px;"><img src="${img.src}"></div>`;
              });
              html += `</div>`;
          });
      
          html += `</div>`;
      
          document.getElementById('viewCoinflipContent').innerHTML = html;
      
          const actionArea = document.getElementById('viewModalActions');
          actionArea.innerHTML = `<button class="action-btn withdraw" id="viewModalCloseBtn">Close</button>`;
          
          if (isCreator && hasJoiner && Winner.length === 0) {
              const acceptBtn = document.createElement('button');
              acceptBtn.className = "action-btn deposit";
              acceptBtn.innerText = "Accept Match";
              acceptBtn.onclick = () => handleAccept(matchCard.dataset.id);
              actionArea.prepend(acceptBtn);
          } else if (!hasJoiner && !isCreator) {
              const jBtn = document.createElement('button');
              jBtn.className = "action-btn deposit";
              jBtn.innerText = "Join Match";
              jBtn.onclick = () => {
                  document.getElementById('viewCoinflipModal').classList.remove('open');
                  openJoinModal(matchCard.dataset.id);
              };
              actionArea.prepend(jBtn);
          }
      
          document.getElementById('viewModalCloseBtn').onclick = () => {
              document.getElementById('viewCoinflipModal').classList.remove('open');
          };

          document.getElementById('viewCoinflipModal').classList.add('open');

         if (Winner.length > 0) {
            setTimeout(() => {
               flipCoin(Winner);
            }, 500);
         }
      }
    });

    async function handleAccept(matchId) {
        try {
            const response = await fetch('/AcceptMatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ matchId: matchId })
            });
            const result = await response.json();
            if (result.success) {

            flipCoin(result.winnerside, () => {
                setTimeout(() => {
                    location.reload();
                }, 2000);
            });
            }
        } catch (e) {
            alert("An error occurred.");
        }
    }

    async function fetchInventory() {
        try {
            const res = await fetch('/GetInventory');
            globalInventory = await res.json();
            if (document.getElementById("createCoinflipModal").classList.contains("open")) {
               renderInventory('createInventory', createSelection, 'create');
            }
        } catch (e) {
            globalInventory = [];
        }
    }
    fetchInventory();
});
