# Importações necessárias para criar a API, gerenciar arquivos estáticos e tipagem de dados
from fastapi import FastAPI, Response, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import random
import json
import os

# Inicializa a aplicação FastAPI
app = FastAPI()

# Monta a pasta "/static" para que o navegador consiga acessar o CSS e o JS.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Nome do arquivo onde os dados serão salvos
DATA_FILE = "players.json"

# Modelo de Dados do Jogador
class Player(BaseModel):
    name: str
    position: str
    alternative_position: List[str]
    skill: int
    age: int
    is_guest: bool = False

# --- DADOS PADRÃO (Caso o arquivo não exista) ---
default_players_data = [
    {"name":"Plinio", "position":"LD", "alternative_position":["MC","LE"], "skill":3, "age":25},
    {"name":"Valdir", "position":"GOL", "alternative_position":[], "skill":4, "age":40},
    {"name":"Edson", "position":"GOL", "alternative_position":[], "skill":4, "age":62},
    {"name":"Bran", "position":"GOL", "alternative_position":[], "skill":3, "age":25},
    {"name":"Zunino", "position":"ZAG", "alternative_position":["LD","LE"], "skill":4, "age":30},
    {"name":"Josce", "position":"ZAG", "alternative_position":[], "skill":4, "age":27},
    {"name":"Eda", "position":"LE", "alternative_position":["LD","ZAG"], "skill":3, "age":50},
    {"name":"Dick", "position":"LE", "alternative_position":["MC"], "skill":4, "age":45},
    {"name":"Delio", "position":"MC", "alternative_position":[], "skill":4, "age":55},
    {"name":"Mauro", "position":"MC", "alternative_position":["ATA"], "skill":5, "age":50},
    {"name":"Ilson", "position":"ATA", "alternative_position":[], "skill":5, "age":35},
    {"name":"Bia", "position":"ATA", "alternative_position":["MC"], "skill":5, "age":45},
    {"name":"Magrão", "position":"ATA", "alternative_position":[], "skill":5, "age":55},
    {"name":"Gomes", "position":"PD/PE", "alternative_position":[], "skill":4, "age":50},
    {"name":"Erick", "position":"LE", "alternative_position":["PD/PE","ATA"], "skill":4, "age":22},
    {"name":"Gerson 2", "position":"PD/PE", "alternative_position":["LE","LD"], "skill":3, "age":45},
    {"name":"Gerson", "position":"LD", "alternative_position":["PD/PE"], "skill":3, "age":55},
    {"name":"Diomar", "position":"PD/PE", "alternative_position":[], "skill":2, "age":60},
    {"name":"Matheus", "position":"PD/PE", "alternative_position":["ATA"], "skill":2, "age":25},
    {"name":"Minga", "position":"LE", "alternative_position":[], "skill":3, "age":72},
    {"name":"Xande", "position":"MC", "alternative_position":["LE"], "skill":4, "age":40},
    {"name":"Amarildo", "position":"ATA", "alternative_position":[], "skill":3, "age":50},
    {"name":"Aures", "position":"PD/PE", "alternative_position":["LE"], "skill":3, "age":50},
    {"name":"Fininho", "position":"MC", "alternative_position":["ATA"], "skill":4, "age":50},
    {"name":"Deba", "position":"MC", "alternative_position":[], "skill":4, "age":30},
    {"name":"Gustavo", "position":"MC", "alternative_position":["ATA"], "skill":4, "age":30},
    {"name":"Vânio", "position":"MC", "alternative_position":["ATA"], "skill":4, "age":40},
    {"name":"Murilo", "position":"ATA", "alternative_position":[], "skill":2, "age":45},
    {"name":"Ricardo", "position":"MC", "alternative_position":["LD","LE"], "skill":4, "age":35},
    {"name":"Tarcisio", "position":"ATA", "alternative_position":[], "skill":2, "age":50},
    {"name":"Vilmar", "position":"ZAG", "alternative_position":["LE"], "skill":3, "age":45}
]

# --- FUNÇÕES DE PERSISTÊNCIA ---
def load_players():
    """Carrega os jogadores do arquivo JSON. Se não existir, cria com o padrão."""
    if not os.path.exists(DATA_FILE):
        save_players(default_players_data) # Cria o arquivo
        return [Player(**p) for p in default_players_data]
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Player(**p) for p in data]
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return [Player(**p) for p in default_players_data]

def save_players(players_list):
    """Salva a lista atual de jogadores no arquivo JSON."""
    # Se receber objetos Player, converte para dict. Se já for dict, usa direto.
    data_to_save = []
    for p in players_list:
        if isinstance(p, Player):
            data_to_save.append(p.dict())
        else:
            data_to_save.append(p)
            
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)

# Carrega dados na memória ao iniciar
db_players = load_players()

# Rota raiz: Entrega o arquivo HTML principal
@app.get("/")
def read_index():
    return FileResponse("static/index.html")

# Rota para o frontend pegar a lista atualizada de jogadores
@app.get("/players")
def get_players():
    return db_players

# Rota auxiliar para evitar erro 404 no favicon
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# CONFIGURAÇÃO DE VAGAS (Slots táticos)
FORMATION_SLOTS = {
    7:  ["GOL", "ZAG", "LD", "LE", "MC", "MC", "ATA", "ATA"],
    8:  ["GOL", "ZAG", "LD", "LE", "MC", "MC", "PD/PE", "PD/PE", "ATA"],
    9:  ["GOL", "ZAG", "ZAG", "LD", "LE", "MC", "MC", "MC", "ATA", "ATA", "ATA"],
    10: ["GOL", "ZAG", "ZAG", "LD", "LE", "MC", "MC", "MC", "ATA", "ATA", "ATA"]
}

# NOVA ROTA: Atualizar Jogador e Salvar no Arquivo
@app.post("/update_player")
def update_player(updated_data: Player):
    global db_players
    found = False
    
    # Procura o jogador na lista pelo nome e atualiza
    for i, p in enumerate(db_players):
        if p.name == updated_data.name:
            db_players[i] = updated_data
            found = True
            break
    
    # Se encontrou e atualizou, salva no arquivo físico
    if found:
        save_players(db_players)

    return {"message": "Jogador atualizado com sucesso", "player": updated_data}

@app.post("/generate")
def generate_teams(players: List[Player]):
    total_players = len(players)
    if total_players < 16:
        raise HTTPException(status_code=400, detail="Mínimo de 16 jogadores necessários.")

    # Lógica Automática da Formação
    if total_players <= 17: formation_size = 7
    elif total_players <= 19: formation_size = 8
    elif total_players <= 21: formation_size = 9
    else: formation_size = 10

    available = list(players)
    random.shuffle(available) 

    team1, team2 = [], []
    slots = FORMATION_SLOTS.get(formation_size, [])

    # Preenchimento das Vagas Titulares
    for slot in slots:
        teams_turn = [team1, team2]
        random.shuffle(teams_turn)

        for target_team in teams_turn:
            if not available: break
            
            def get_priority_score(p):
                score_principal = 1 if p.position == slot else 0
                score_secundario = 1 if slot in p.alternative_position else 0
                return (score_principal, score_secundario, p.skill, p.age)

            available.sort(key=get_priority_score, reverse=True)
            best_match = available.pop(0)
            player_dict = best_match.dict()
            player_dict["assigned_position"] = slot 
            target_team.append(player_dict)

    # Regra dos Jogadores Sobrantes
    if available:
        available.sort(key=lambda x: (x.skill, x.age), reverse=True)
        while available:
            p = available.pop(0)
            player_dict = p.dict()
            player_dict["assigned_position"] = p.position 
            if len(team1) <= len(team2): team1.append(player_dict)
            else: team2.append(player_dict)

    # Ordenação Visual Final
    order = {"GOL":1, "ZAG":2, "LD":3, "LE":4, "MC":5, "PD/PE":6, "ATA":7}
    team1.sort(key=lambda x: order.get(x["assigned_position"], 99))
    team2.sort(key=lambda x: order.get(x["assigned_position"], 99))

    return {"team1": team1, "team2": team2}