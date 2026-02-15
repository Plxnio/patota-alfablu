// Variável players começa vazia, pois vamos carregar do arquivo no servidor
let players = [];
let guests = []; 
let editingPlayerName = null;
const allPosOptions = ["GOL", "ZAG", "LD", "LE", "MC", "PD/PE", "ATA"];

// Ao carregar a página, busca os dados do servidor
async function loadPlayers() {
    try {
        const res = await fetch('/players');
        if (res.ok) {
            players = await res.json();
            init(); // Renderiza o grid após carregar
        }
    } catch (e) {
        console.error("Erro ao carregar jogadores:", e);
    }
}

function init() {
    const g = document.getElementById("grid");
    const dataList = document.getElementById("playersList");
    
    // Salva o estado dos checkboxes antes de limpar o grid para não perder marcação ao recarregar
    const checkedStates = {};
    document.querySelectorAll('.player-card input[type="checkbox"]').forEach(cb => {
        checkedStates[cb.value] = cb.checked;
    });

    g.innerHTML = ""; 
    dataList.innerHTML = ""; 

    const allAvailable = [...players, ...guests];

    allAvailable.sort((a,b) => a.name.localeCompare(b.name)).forEach(p => {
        const guestTag = p.is_guest ? " (Conv)" : "";
        const isChecked = checkedStates[p.name] || p.is_guest;
        
        g.innerHTML += `
            <div class="player-card ${p.is_guest ? 'guest-card' : ''}">
                <label style="display: flex; align-items: center; gap: 12px; cursor: pointer; flex: 1;">
                    <input type="checkbox" value="${p.name}" ${isChecked ? 'checked' : ''} onchange="update()"> 
                    <div style="flex: 1;"><b>${p.name}${guestTag}</b><br>
                    <small>⭐${p.skill} | ${p.position} | ${p.alternative_position} </small></div>
                </label>
                <button type="button" class="btn-edit-small" onclick="openEditModal('${p.name}')">✏️</button>
            </div>`;
        dataList.innerHTML += `<option value="${p.name}">`;
    });
    update();
}

function openEditModal(name) {
    editingPlayerName = name;
    const p = [...players, ...guests].find(x => x.name === name);
    document.getElementById("editPlayerTitle").innerText = `Editar: ${name}`;
    document.getElementById("editAge").value = p.age;
    document.getElementById("editSkill").value = p.skill; // Carrega a skill atual
    
    const primarySelect = document.getElementById("editPrimaryPos");
    primarySelect.innerHTML = allPosOptions.map(pos => 
        `<option value="${pos}" ${p.position === pos ? 'selected' : ''}>${pos}</option>`
    ).join("");
    renderAltPositions(p.alternative_position);
    document.getElementById("editModal").style.display = "flex";
}

function renderAltPositions(currentAlts = []) {
    const primaryPos = document.getElementById("editPrimaryPos").value;
    const grid = document.getElementById("altPositionsGrid");
    grid.innerHTML = allPosOptions
        .filter(pos => pos !== primaryPos)
        .map(pos => `
            <label style="font-size: 11px; display: flex; align-items: center; gap: 4px;">
                <input type="checkbox" name="altPos" value="${pos}" ${currentAlts.includes(pos) ? 'checked' : ''}> ${pos}
            </label>
        `).join("");
}

async function saveEdit() {
    const p = [...players, ...guests].find(x => x.name === editingPlayerName);
    if (!p) return;
    
    // Atualiza objeto local (visualização imediata)
    p.age = parseInt(document.getElementById("editAge").value);
    p.skill = parseInt(document.getElementById("editSkill").value);
    p.position = document.getElementById("editPrimaryPos").value;
    const selectedAlts = Array.from(document.querySelectorAll('input[name="altPos"]:checked')).map(cb => cb.value);
    p.alternative_position = selectedAlts;

    // Se NÃO for convidado, salva no arquivo via servidor
    if (!p.is_guest) {
        try {
            const res = await fetch('/update_player', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(p)
            });
            if (!res.ok) alert("Erro ao salvar. Verifique o console.");
        } catch (e) {
            console.error("Erro de conexão:", e);
        }
    }

    closeEditModal();
    init();
}

function closeEditModal() {
    document.getElementById("editModal").style.display = "none";
    editingPlayerName = null;
}

function addGuest() {
    const name = document.getElementById("guestName").value.trim();
    const skill = parseInt(document.getElementById("guestSkill").value);
    const position = document.getElementById("guestPosition").value;
    if (!name) return alert("Digite o nome do convidado!");
    if ([...players, ...guests].some(p => p.name === name)) return alert("Este nome já está na lista!");
    guests.push({ name: name, position: position, alternative_position: [], skill: skill, age: 30, is_guest: true });
    document.getElementById("guestName").value = "";
    init();
}

function update() { 
    const count = document.querySelectorAll('.player-card input[type="checkbox"]:checked').length;
    document.getElementById("total").innerText = count;
    const fmtDisplay = document.getElementById("formationDisplay");
    const btn = document.getElementById("btnGenerate");
    if (count < 16) {
        fmtDisplay.innerText = `Falta ${16 - count}`;
        fmtDisplay.className = "fmt-warn";
        btn.disabled = true;
    } else {
        btn.disabled = false;
        fmtDisplay.className = "fmt-ok";
        if (count <= 17) fmtDisplay.innerText = "7 na linha (3-2-2)";
        else if (count <= 19) fmtDisplay.innerText = "8 na linha (3-2-3)";
        else if (count <= 21) fmtDisplay.innerText = "9 na linha (3-3-3)";
        else fmtDisplay.innerText = "10 na linha (4-3-3)";
    }
}

async function generate() {
    const selectedNames = Array.from(document.querySelectorAll('.player-card input[type="checkbox"]:checked')).map(i => i.value);
    // Busca tanto em players (do servidor) quanto em guests
    const selected = [...players, ...guests].filter(p => selectedNames.includes(p.name));
    
    if(selected.length < 16) return alert("Mínimo de 16 jogadores necessários!");
    const res = await fetch(`/generate`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(selected) });
    if(!res.ok) { const error = await res.json(); return alert("Erro: " + error.detail); }
    const data = await res.json();
    document.getElementById("resultsArea").style.display = "flex";
    renderTable(data.team1, "t1");
    renderTable(data.team2, "t2");
    updateStats(data.team1, data.team2);
}

function renderTable(team, id) {
    let html = `<table><tr><th>Pos</th><th>Nome</th></tr>`;
    team.forEach(p => {
        const guestTag = p.is_guest ? " (Conv)" : "";
        html += `<tr><td class="pos">${p.assigned_position}</td><td>${p.name}${guestTag}</td></tr>`;
    });
    document.getElementById(id).innerHTML = html + `</table>`;
}

function updateStats(t1, t2) {
    const today = new Date();
    document.getElementById("matchDate").innerText = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()} - 19h30`;
    const birthdayName = document.getElementById("inputBirthday").value;
    const locationName = document.getElementById("inputLocation").value;
    if(birthdayName) {
        document.getElementById("matchTitle").innerText = `Aniversário ${birthdayName}`;
        document.getElementById("matchTitle").style.display = "block";
    } else { document.getElementById("matchTitle").innerText = "Patota"; }
    document.getElementById("matchLocation").innerText = `Local: ${locationName}`;
    const calc = (team) => {
        if (!team.length) return {age: 0, skill: 0};
        const age = team.reduce((acc, p) => acc + p.age, 0) / team.length;
        const skill = team.reduce((acc, p) => acc + p.skill, 0) / team.length;
        return { age: age.toFixed(1), skill: skill.toFixed(2) };
    };
    const s1 = calc(t1); const s2 = calc(t2);
    document.getElementById("avgAge1").innerText = s1.age + " anos";
    document.getElementById("avgAge2").innerText = s2.age + " anos";
    document.getElementById("avgSkill1").innerText = "⭐ " + s1.skill;
    document.getElementById("avgSkill2").innerText = "⭐ " + s2.skill;
}

// Inicia carregando do servidor
loadPlayers();