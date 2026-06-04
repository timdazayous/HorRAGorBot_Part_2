# 🚀 HorRAGor BOT - Quick Start avec Grok

## ⚡ Démarrage rapide en 5 minutes

### Step 1: Obtenir une clé API Grok

1. Allez sur: **https://console.x.ai/**
2. Connexion / Création de compte
3. Allez dans **API Keys** 
4. Cliquez sur **Create New API Key**
5. Copiez la clé (commence par `sk_...`)

### Step 2: Configurer .env

Ouvrez le fichier `.env` et remplacez:

```env
XAI_API_KEY=your_xai_api_key_here
```

Par votre vraie clé:

```env
XAI_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Installer les dépendances

```bash
pip install -r requirements.txt
```

### Step 4: Tester la configuration Grok

```bash
python test_grok_config.py
```

Vous devriez voir:
```
✅ Configuration
✅ Import du module
✅ Client Grok
✅ Génération de réponse
```

### Step 5: Lancer l'API

**Terminal 1 - API FastAPI:**
```bash
python main.py
```

Allez sur: http://localhost:8000/docs pour voir la documentation Swagger

**Terminal 2 - Interface Streamlit:**
```bash
streamlit run streamlit_app.py
```

Allez sur: http://localhost:8501

## 🧪 Tester l'API avec curl

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Recommande-moi un film d'\''horreur comme The Shining"
  }'
```

Réponse attendue:
```json
{
  "answer": "[Réponse générée par Grok...]",
  "tools_used": ["grok-llm"],
  "judge_verdict": {
    "is_valid": true,
    "confidence": 0.95,
    "reasoning": "Réponse générée par Grok et validée..."
  },
  "conversation_id": "conv_default"
}
```

## 📝 Architecture

```
┌─────────────────┐
│   Streamlit     │
│  (Front-End)    │
└────────┬────────┘
         │ HTTP POST
         │ /chat
         ↓
┌─────────────────┐
│   FastAPI       │
│  (Back-End)     │
└────────┬────────┘
         │ async call
         │ generate_response()
         ↓
┌─────────────────┐
│  Grok (xAI)     │
│    LLM          │
└─────────────────┘
```

## 🔑 Fichiers clés

| Fichier | Rôle |
|---------|------|
| `main.py` | API FastAPI avec endpoint `/chat` |
| `llm_grok.py` | Client Grok asynchrone |
| `streamlit_app.py` | Interface utilisateur |
| `.env` | Configuration (clé API) |
| `requirements.txt` | Dépendances |

## 📚 Endpoints disponibles

### 1. `/health` (GET)
Vérifie que l'API fonctionne

```bash
curl http://localhost:8000/health
```

### 2. `/chat` (POST)
Envoie une question et reçoit une réponse de Grok

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "Ta question ici"}'
```

### 3. `/info` (GET)
Infos sur les modèles et outils

```bash
curl http://localhost:8000/info
```

### 4. `/docs` (GET)
Documentation Swagger interactive

```
http://localhost:8000/docs
```

## ⚙️ Configuration avancée

Éditer les variables d'environnement dans `.env`:

```env
# Modèle Grok (grok-2, grok-beta)
LLM_MODEL=grok-2

# Température (0 = déterministe, 1 = créatif)
LLM_TEMPERATURE=0.7

# Nombre max de tokens par réponse
LLM_MAX_TOKENS=2048

# Host/Port de l'API
API_HOST=0.0.0.0
API_PORT=8000
```

## 🐛 Dépannage

### Erreur: "XAI_API_KEY not configured"
→ Assurez-vous que le fichier `.env` existe et que la clé est configurée

### Erreur: "Connection refused"
→ Vérifiez que l'API est lancée: `python main.py`

### Erreur: "Module not found"
→ Installez les dépendances: `pip install -r requirements.txt`

### Streamlit ne trouve pas l'API
→ Vérifiez que `API_URL = "http://localhost:8000"` dans `streamlit_app.py`

## 📖 Documentation

- **API xAI**: https://docs.x.ai/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Streamlit**: https://docs.streamlit.io/

## 💡 Prochaines étapes

1. Ajouter les autres outils (query_movie_metadata, find_similar_horror_movies, etc.)
2. Connecter Supabase
3. Implémenter LangGraph pour les workflows avancés
4. Ajouter FAISS pour l'indexation locale

---

**Enjoy HorRAGor BOT! 👻** 🎬🎮📖
