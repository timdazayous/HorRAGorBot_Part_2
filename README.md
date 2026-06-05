# 🩸 HorRAGor BOT — Partie 2

Agent conversationnel spécialisé dans l'univers de l'horreur (cinéma, littérature, jeux vidéo), basé sur une architecture **ReAct** (LangGraph + Groq LLM + FAISS + Supabase).

---

## Architecture

```
┌─────────────────────────────┐
│   Streamlit  (Front-End)    │
│   frontend/app.py           │
└──────────────┬──────────────┘
               │ HTTP POST /chat
               ▼
┌─────────────────────────────┐
│   FastAPI    (Back-End)     │
│   main_api.py               │
└──────────────┬──────────────┘
               │ generate_response()
               ▼
┌─────────────────────────────┐
│   Groq LLM  llama-3.3-70b  │
│   llm_groq.py               │
└──────────────┬──────────────┘
               │ tool calls
       ┌───────┴────────┐
       ▼                ▼
┌────────────┐   ┌──────────────────┐
│ FAISS RAM  │   │ Supabase (PostgreSQL) │
│ 1179 films │   │ film / evaluation │
└────────────┘   └──────────────────┘
```

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| LLM | Groq — `llama-3.3-70b-versatile` |
| Back-End | FastAPI + Uvicorn (async) |
| Front-End | Streamlit + thème Dracula |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Mémoire vectorielle | FAISS (index en RAM) |
| Base de données | Supabase (PostgreSQL) |
| Dépendances | `uv` |

---

## Prérequis

- Python 3.10+
- `uv` installé
- Compte [Groq](https://console.groq.com/) (gratuit)
- Accès Supabase (hérité Partie 1)

---

## Installation

```bash
git clone https://github.com/timdazayous/HorRAGorBot_Part_2.git
cd HorRAGorBot_Part_2
uv sync
```

---

## Configuration

Crée un fichier `.env` à la racine (copie `.env.example`) :

```env
# LLM
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx

# Base de données Supabase
DATABASE_URL=postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres
SUPABASE_DB_URL=postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres

# Optionnel — configuration du serveur
API_HOST=0.0.0.0
API_PORT=8000
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

> La clé Groq est disponible sur [console.groq.com](https://console.groq.com/) → **API Keys** → **Create API Key**

---

## Lancement

**Terminal 1 — API FastAPI**
```bash
py main_api.py
# → http://localhost:8000
# → Swagger : http://localhost:8000/docs
```

**Terminal 2 — Interface Streamlit**
```bash
cd frontend
streamlit run app.py
# → http://localhost:8501
```

---

## Outils de l'agent (Tools)

| Tool | Nom | Déclencheur |
|------|-----|-------------|
| 1 | `query_movie_metadata` | Question sur un film précis |
| 2 | `similar_movies` | Demande de films similaires |
| 3 | `search_horror_movies` | Recherche sémantique libre |
| 4 | `calculate_movie_age` | *(à venir)* |
| 5 | `scrape_detailed_synopsis` | *(à venir)* |

### Exemples de questions

```
"Parle-moi de The Shining"           → query_movie_metadata
"Films similaires à Hereditary"      → similar_movies
"Recommande un film de possession"   → search_horror_movies
```

---

## Endpoints API

### `GET /health`
```bash
curl http://localhost:8000/health
```

### `POST /chat`
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "Parle-moi de The Shining"}'
```

Réponse :
```json
{
  "answer": "Titre : The Shining...\n--------\nUn classique de Kubrick...",
  "tools_used": ["query_movie_metadata", "groq-llm"],
  "judge_verdict": null,
  "conversation_id": "conv_default"
}
```

### `GET /info`
```bash
curl http://localhost:8000/info
```

---

## Structure du projet

```
HorRAGorBot_Part_2/
├── frontend/
│   ├── app.py                    # Interface Streamlit (thème horreur)
│   └── .streamlit/config.toml   # Thème Dracula
├── tools/
│   ├── __init__.py
│   ├── query_movie_metadata.py   # Tool 1 — métadonnées SQL
│   └── find_similar_horror_movies.py  # Tool 2 — similarité FAISS
├── utils/
│   └── build_faiss_index.py      # Construction de l'index FAISS
├── data/
│   ├── faiss.index               # Index vectoriel (1179 films)
│   └── id_map.npy                # Mapping index → ID film
├── main_api.py                   # API FastAPI
├── llm_groq.py                   # Client Groq + dispatch des tools
├── .env.example                  # Template de configuration
└── pyproject.toml                # Dépendances (uv)
```

---

## Dépannage

| Erreur | Solution |
|--------|----------|
| `GROQ_API_KEY non configurée` | Vérifie le fichier `.env` |
| `SUPABASE_DB_URL non configurée` | Ajoute `SUPABASE_DB_URL` dans `.env` |
| `ModuleNotFoundError` | Lance `uv sync` |
| `Connection refused` | Vérifie que `py main_api.py` tourne |
| HuggingFace télécharge le modèle | Normal au 1er lancement (~91 Mo, mis en cache ensuite) |

---

## Branches de développement

| Branche | Développeur |
|---------|-------------|
| `main` | Production |
| `dev-tim` | Tim — Front-End + Tools |
| `dev-nicolas` | Nicolas — FAISS + Tools |
| `dev_julie` | Julie — API + Tools |

---

## Partie 1

Le pipeline de données (ingestion TMDB, Kaggle, IMDB, Rotten Tomatoes, PySpark) est documenté ici [old_README.md](<HorRAGor BOT Partie 1.pdf>)
