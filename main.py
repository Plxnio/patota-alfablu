import os
import random
from typing import List
from fastapi import FastAPI, Response, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (se ele existir)
load_dotenv()

# Tenta pegar do .env ou do Render. Se não achar nenhum, só aí usa o local.
DATABASE_URL = os.getenv("DATABASE_URL")

# Se mesmo com o .env ele não achar (ex: erro no arquivo), usa o local
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./local_test.db"
    print("⚠️  AVISO: Usando banco de dados LOCAL (arquivo .db).")
    print("Se queria conectar no Supabase, verifique seu arquivo .env")
else:
    print("✅  Conectado ao Banco de Dados Remoto!")

# Correção para o Render/Supabase (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Correção para o Render (ele fornece 'postgres://' mas o SQLAlchemy exige 'postgresql://')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configura a conexão
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- TABELA DO BANCO DE DADOS (Como os dados são salvos lá no Supabase) ---
class PlayerDB(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Nome único
    position = Column(String)
    alternative_position = Column(JSON) # O Postgres aceita listas como JSON
    skill = Column(Integer)
    age = Column(Integer)
    is_guest = Column(Boolean, default=False)

# --- MODELO PARA A API (Como o Javascript envia/recebe) ---
class PlayerSchema(BaseModel):
    name: str
    position: str
    alternative_position: List[str]
    skill: int
    age: int
    is_guest: bool = False

    class Config:
        orm_mode = True

# --- DADOS INICIAIS (Para popular o banco na primeira vez) ---
initial_data = [
    {"name":"Plinio", "position":"LD", "alternative_position":["MEI","LE"], "skill":3, "age":25},
    {"name":"Valdir", "position":"GOL", "alternative_position":[], "skill":4, "age":40},
    {"name":"Edson", "position":"GOL", "alternative_position":[], "skill":4, "age":62},
    {"name":"Bran", "position":"GOL", "alternative_position":[], "skill":3, "age":25},
    {"name":"Zunino", "position":"ZAG", "alternative_position":["LD","LE"], "skill":4, "age":30},
    {"name":"Josce", "position":"ZAG", "alternative_position":[], "skill":4, "age":27},
    {"name":"Eda", "position":"LE", "alternative_position":["LD","ZAG"], "skill":3, "age":50},
    {"name":"Dick", "position":"LE", "alternative_position":["MEI"], "skill":4, "age":45},
    {"name":"Delio", "position":"MEI", "alternative_position":[], "skill":4, "age":55},
    {"name":"Mauro", "position":"MEI", "alternative_position":["ATA"], "skill":5, "age":50},
    {"name":"Ilson", "position":"ATA", "alternative_position":[], "skill":5, "age":35},
    {"name":"Bia", "position":"ATA", "alternative_position":["MEI"], "skill":5, "age":45},
    {"name":"Magrão", "position":"ATA", "alternative_position":[], "skill":5, "age":55},
    {"name":"Gomes", "position":"PD/PE", "alternative_position":[], "skill":4, "age":50},
    {"name":"Erick", "position":"LE", "alternative_position":["PD/PE","ATA"], "skill":4, "age":22},
    {"name":"Gerson 2", "position":"PD/PE", "alternative_position":["LE","LD"], "skill":3, "age":45},
    {"name":"Gerson", "position":"LD", "alternative_position":["PD/PE"], "skill":3, "age":55},
    {"name":"Diomar", "position":"PD/PE", "alternative_position":[], "skill":2, "age":60},
    {"name":"Matheus", "position":"PD/PE", "alternative_position":["ATA"], "skill":2, "age":25},
    {"name":"Minga", "position":"LE", "alternative_position":[], "skill":3, "age":72},
    {"name":"Xande", "position":"MEI", "alternative_position":["LE"], "skill":4, "age":40},
    {"name":"Amarildo", "position":"ATA", "alternative_position":[], "skill":3, "age":50},
    {"name":"Aures", "position":"PD/PE", "alternative_position":["LE"], "skill":3, "age":50},
    {"name":"Fininho", "position":"MEI", "alternative_position":["ATA"], "skill":4, "age":50},
    {"name":"Deba", "position":"MEI", "alternative_position":[], "skill":4, "age":30},
    {"name":"Gustavo", "position":"MEI", "alternative_position":["ATA"], "skill":4, "age":30},
    {"name":"Vânio", "position":"MEI", "alternative_position":["ATA"], "skill":4, "age":40},
    {"name":"Murilo", "position":"ATA", "alternative_position":[], "skill":2, "age":45},
    {"name":"Ricardo", "position":"MEI", "alternative_position":["LD","LE"], "skill":4, "age":35},
    {"name":"Tarcisio", "position":"ATA", "alternative_position":[], "skill":2, "age":50},
    {"name":"Vilmar", "position":"ZAG", "alternative_position":["LE"], "skill":3, "age":45}
]

# Cria a tabela no banco (se não existir)
Base.metadata.create_all(bind=engine)

# ==============================================================================
# BLOCO NOVO: POPULAR O BANCO AUTOMATICAMENTE AO INICIAR
# ==============================================================================
try:
    db = SessionLocal()
    # Verifica se tem 0 jogadores
    if db.query(PlayerDB).count() == 0:
        print("⚠️ BANCO VAZIO DETECTADO NO SUPABASE!")
        print("⏳ Inserindo jogadores iniciais...")
        
        for p_data in initial_data:
            db_player = PlayerDB(**p_data)
            db.add(db_player)
            
        db.commit()
        print("✅ TODOS OS JOGADORES FORAM INSERIDOS COM SUCESSO!")
    else:
        print("✅ O banco já contém dados. Nenhuma inserção necessária.")
finally:
    db.close()
# ==============================================================================

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Função para pegar uma sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# --- ROTA 1: BUSCAR JOGADORES (DO BANCO) ---
@app.get("/players", response_model=List[PlayerSchema])
def get_players(db: Session = Depends(get_db)):
    players = db.query(PlayerDB).all()
    
    # Se o banco estiver vazio (primeira vez), preenche com os dados iniciais
    if not players:
        for p_data in initial_data:
            # Verifica se já existe para evitar erro
            exists = db.query(PlayerDB).filter(PlayerDB.name == p_data["name"]).first()
            if not exists:
                db_player = PlayerDB(**p_data)
                db.add(db_player)
        db.commit()
        players = db.query(PlayerDB).all()
        
    return players

# --- ROTA 2: ATUALIZAR JOGADOR (NO BANCO) ---
@app.post("/update_player")
def update_player(player_data: PlayerSchema, db: Session = Depends(get_db)):
    # Procura o jogador pelo nome
    db_player = db.query(PlayerDB).filter(PlayerDB.name == player_data.name).first()
    
    if db_player:
        # Atualiza os dados
        db_player.age = player_data.age
        db_player.skill = player_data.skill
        db_player.position = player_data.position
        db_player.alternative_position = player_data.alternative_position
        db.commit()
        db.refresh(db_player)
        return {"message": "Atualizado!"}
    else:
        # Se for um convidado novo que virou fixo, cria ele
        new_player = PlayerDB(**player_data.dict())
        db.add(new_player)
        db.commit()
        return {"message": "Criado!"}

# --- CONFIGURAÇÃO DE VAGAS ---
FORMATION_SLOTS = {
    7:  ["GOL", "ZAG", "LD", "LE", "VOL", "MEI", "ATA", "ATA"],
    8:  ["GOL", "ZAG", "LD", "LE", "VOL", "MEI", "PD/PE", "PD/PE", "ATA"],
    9:  ["GOL", "ZAG", "ZAG", "LD", "LE", "VOL","MEI", "PD/PE", "PD/PE", "ATA"],
    10: ["GOL", "ZAG", "ZAG", "LD", "LE", "VOL", "VOL", "MEI", "PD/PE", "PD/PE", "ATA"]
}

# --- ROTA 3: GERAR TIMES ---
@app.post("/generate")
def generate_teams(players: List[PlayerSchema]):
    total_players = len(players)
    if total_players < 16:
        raise HTTPException(status_code=400, detail="Mínimo de 16 jogadores necessários.")

    if total_players <= 17: formation_size = 7
    elif total_players <= 19: formation_size = 8
    elif total_players <= 21: formation_size = 9
    else: formation_size = 10

    available = list(players)
    random.shuffle(available) 

    team1, team2 = [], []
    slots = FORMATION_SLOTS.get(formation_size, [])

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
            # Conversão para dict para manipulação
            best_match = available.pop(0)
            player_dict = best_match.dict()
            player_dict["assigned_position"] = slot 
            target_team.append(player_dict)

    if available:
        available.sort(key=lambda x: (x.skill, x.age), reverse=True)
        while available:
            p = available.pop(0)
            player_dict = p.dict()
            player_dict["assigned_position"] = p.position 
            if len(team1) <= len(team2): team1.append(player_dict)
            else: team2.append(player_dict)

    order = {"GOL":1, "ZAG":2, "LD":3, "LE":4, "VOL":5, "MEI":6,"PD/PE":7, "ATA":8}
    team1.sort(key=lambda x: order.get(x["assigned_position"], 99))
    team2.sort(key=lambda x: order.get(x["assigned_position"], 99))

    return {"team1": team1, "team2": team2}