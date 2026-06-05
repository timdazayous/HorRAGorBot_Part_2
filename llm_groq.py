"""
Module d'intégration avec Groq API
Gère la génération de réponses avec le LLM via tool-use (FAISS + Supabase)
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import psycopg2
from dotenv import load_dotenv
from openai import AsyncOpenAI
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FAISS retriever
# ---------------------------------------------------------------------------

_BASE_DIR         = Path(__file__).parent
_FAISS_INDEX_PATH = _BASE_DIR / "data" / "faiss.index"
_ID_MAP_PATH      = _BASE_DIR / "data" / "id_map.npy"

_model:  Optional[SentenceTransformer] = None
_index:  Optional[faiss.Index]         = None
_id_map: Optional[np.ndarray]          = None


def _get_retriever() -> tuple[SentenceTransformer, faiss.Index, np.ndarray]:
    global _model, _index, _id_map
    if _index is not None:
        return _model, _index, _id_map
    logger.info("Chargement SentenceTransformer + index FAISS...")
    _model  = SentenceTransformer("all-MiniLM-L6-v2")
    _index  = faiss.read_index(str(_FAISS_INDEX_PATH))
    _id_map = np.load(str(_ID_MAP_PATH))
    logger.info(f"Index FAISS chargé : {_index.ntotal} vecteurs")
    return _model, _index, _id_map


def initialize_retriever() -> None:
    """Pré-charge le modèle et l'index FAISS (à appeler au démarrage)."""
    _get_retriever()


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _fetch_films_from_db(film_ids: list[int]) -> list[dict]:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        logger.warning("SUPABASE_DB_URL non configurée")
        return []
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, overview, genres, vote_average, release_date "
                "FROM film WHERE id = ANY(%s)",
                (film_ids,)
            )
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Erreur Supabase : {e}")
        return []


# ---------------------------------------------------------------------------
# Tool : search_horror_movies
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_horror_movies",
            "description": (
                "Recherche les films d'horreur les plus pertinents dans la base de données. "
                "À utiliser quand l'utilisateur demande des recommandations, "
                "des films similaires, ou des informations sur des films précis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La requête de recherche sémantique"
                    },
                    "k": {
                        "type": "integer",
                        "description": "Nombre de films à récupérer (défaut : 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def _search_horror_movies(query: str, k: int = 5) -> str:
    """Exécute la recherche FAISS + Supabase et retourne le contexte textuel."""
    model, index, id_map = _get_retriever()
    vec = model.encode([query], normalize_embeddings=True).astype("float32")
    _, indices = index.search(vec, k)

    film_ids = [int(id_map[i]) for i in indices[0] if i < len(id_map)]
    films    = _fetch_films_from_db(film_ids)

    if not films:
        return "Aucun film trouvé dans la base de données."

    parts = []
    for f in films:
        year   = (str(f.get("release_date") or ""))[:4]
        genres = f.get("genres") or []
        if isinstance(genres, list):
            genres = ", ".join(genres)
        parts.append(
            f"Titre : {f['title']} ({year})\n"
            f"Genres : {genres}\n"
            f"Note TMDB : {f.get('vote_average') or 'N/A'}\n"
            f"Synopsis : {f.get('overview') or ''}"
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class LLMResult:
    answer:     str
    tools_used: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Groq LLM
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Tu es HorRAGor, un agent conversationnel spécialisé dans l'univers de l'horreur "
    "(cinéma, littérature, jeux vidéo). "
    "Utilise l'outil search_horror_movies quand l'utilisateur te demande des recommandations, "
    "des films similaires ou des informations sur des titres précis. "
    "Pour les questions générales (définitions, histoire du genre, etc.), réponds directement."
)


class GroqConfig(BaseModel):
    api_key:     str   = Field(..., description="Clé API Groq")
    model:       str   = Field(default="llama-3.3-70b-versatile")
    temperature: float = Field(default=0.7)
    max_tokens:  int   = Field(default=2048)


class GroqLLM:
    """Client Groq avec support tool-use."""

    def __init__(self, config: Optional[GroqConfig] = None):
        if config is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY non configurée. "
                    "Définis la variable d'environnement ou passe une GroqConfig."
                )
            config = GroqConfig(api_key=api_key)

        self.config = config
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        logger.info(f"Client Groq initialisé avec le modèle: {self.config.model}")

    async def generate_response(
        self,
        user_question: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list] = None
    ) -> LLMResult:
        """
        Génère une réponse. Si le LLM appelle search_horror_movies,
        exécute la recherche FAISS+Supabase et relance avec le contexte.
        """
        system = system_prompt or _SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system},
            *list(conversation_history or []),
            {"role": "user", "content": user_question}
        ]

        logger.info(f"Appel Groq : {user_question[:60]}...")

        # Premier appel — avec l'outil disponible
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        choice     = response.choices[0]
        tools_used = ["groq-llm"]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            args      = json.loads(tool_call.function.arguments)
            query     = args.get("query", user_question)
            k         = args.get("k", 5)

            logger.info(f"Outil appelé : search_horror_movies(query={query!r}, k={k})")
            context = await asyncio.to_thread(_search_horror_movies, query, k)
            tools_used = ["search_horror_movies", "groq-llm"]

            # Reconstruction du message assistant pour l'API
            assistant_msg = {
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id":   tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name":      tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                ]
            }

            tool_result_msg = {
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      context
            }

            # Deuxième appel — avec le résultat de l'outil
            response2 = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[*messages, assistant_msg, tool_result_msg],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            answer = response2.choices[0].message.content
        else:
            answer = choice.message.content

        logger.info(f"Réponse générée ({len(answer)} caractères) — outils : {tools_used}")
        return LLMResult(answer=answer, tools_used=tools_used)


def get_groq_client() -> GroqLLM:
    return GroqLLM()


if __name__ == "__main__":
    async def test():
        client = GroqLLM()
        result = await client.generate_response(
            "Recommande-moi un film d'horreur similaire à The Shining"
        )
        print(f"Outils utilisés : {result.tools_used}")
        print(result.answer)

    asyncio.run(test())
