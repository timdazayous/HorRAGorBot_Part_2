"""
Module d'intégration avec Groq API
Gère la génération de réponses avec le LLM via tool-use (FAISS + Supabase)
"""

import asyncio
import json
import logging
import os
import re
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
from tools import (
    query_movie_metadata,       QUERY_METADATA_TOOL,
    find_similar_horror_movies, FIND_SIMILAR_TOOL,
    calculate_movie_age,        MOVIE_AGE_TOOL,
    scrape_detailed_synopsis,   SCRAPE_SYNOPSIS_TOOL,
)

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
    QUERY_METADATA_TOOL,
    FIND_SIMILAR_TOOL,
    MOVIE_AGE_TOOL,
    SCRAPE_SYNOPSIS_TOOL,
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

_MAX_RETRIES = 2

_JUDGE_SYSTEM_PROMPT = (
    "Tu es Le Juge, un évaluateur strict de HorRAGor BOT. "
    "Ta mission : détecter les hallucinations et vérifier la cohérence des réponses. "
    "Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après. "
    'Format obligatoire : {"is_valid": true, "confidence": 0.95, "reasoning": "..."} '
    "is_valid = false si : hallucinations détectées, réponse hors sujet, données contredites, "
    "réponse vide ou incompréhensible. confidence entre 0.0 et 1.0."
)


@dataclass
class LLMResult:
    answer:        str
    tools_used:    list[str] = field(default_factory=list)
    judge_verdict: Optional[dict] = None


# ---------------------------------------------------------------------------
# Groq LLM
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Tu es HorRAGor, un agent conversationnel spécialisé dans l'univers de l'horreur "
    "(cinéma, littérature, jeux vidéo). "
    "Tu disposes de deux outils pour interroger ta base de données :\n"
    "- query_movie_metadata : utilise-le OBLIGATOIREMENT quand l'utilisateur mentionne "
    "un film précis par son titre (ex: 'parle-moi de X', 'infos sur X', 'c'est quoi X'). "
    "Cet outil retourne les métadonnées réelles : année, genres, notes TMDB/IMDB/RT, synopsis.\n"
    "- similar_movies : utilise-le quand l'utilisateur demande des films similaires à un titre précis "
    "(ex: 'films similaires à X', 'recommande des films comme X').\n"
    "- search_horror_movies : utilise-le pour les recherches sémantiques libres "
    "(ex: 'recommande-moi un film d'horreur psychologique', 'films avec des fantômes').\n"
    "- detailed_synopsis : utilise-le UNIQUEMENT si l'utilisateur demande des détails approfondis "
    "non présents en base : anecdotes, tournage, contexte de production, ou dit 'dis-m'en plus', "
    "'plus de détails', 'anecdotes sur le film'.\n"
    "- movie_age : utilise-le quand l'utilisateur demande l'âge d'un film, "
    "depuis combien de temps il est sorti, ou s'il est récent/ancien.\n"
    "Pour les questions générales sans titre précis (histoire du genre, définitions), "
    "réponds directement sans outil.\n\n"
    "IMPORTANT — Format de réponse quand tu utilises query_movie_metadata :\n"
    "Commence TOUJOURS par afficher les données brutes de la base sans gras ni titre markdown, "
    "sur des lignes séparées avec ce modèle :\n"
    "🎬 [Titre] — [Année]\n"
    "Genres  : [genres]\n"
    "Notes   : [notes]\n"
    "Synopsis: [synopsis]\n"
    "--------\n"
    "Puis écris ton commentaire en dessous de la ligne de tirets, en texte normal."
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

    async def _judge_response(
        self,
        question: str,
        answer: str,
        tools_used: Optional[list] = None
    ) -> dict:
        """Appel LLM secondaire — Le Juge évalue la réponse de l'agent."""
        context_info = (
            f"Outils utilisés : {', '.join(tools_used)}"
            if tools_used else "Réponse directe sans outil"
        )
        user_msg = (
            f"Question posée : {question}\n\n"
            f"Contexte : {context_info}\n\n"
            f"Réponse de l'agent :\n{answer}\n\n"
            "La réponse est-elle fidèle, complète et sans hallucination ?\n"
            'Réponds en JSON : {"is_valid": true/false, "confidence": 0.0-1.0, "reasoning": "..."}'
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg}
                ],
                temperature=0.1,
                max_tokens=256
            )
            content = resp.choices[0].message.content or ""
            match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"[Juge] Évaluation indisponible : {e}")
        return {"is_valid": True, "confidence": 0.75, "reasoning": "Évaluation automatique non disponible."}

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
            tool_call  = choice.message.tool_calls[0]
            tool_name  = tool_call.function.name
            args       = json.loads(tool_call.function.arguments)

            logger.info(f"Outil appelé : {tool_name}({args})")

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

            if tool_name == "query_movie_metadata":
                movie_name  = args.get("movie_name", "")
                metadata    = await asyncio.to_thread(query_movie_metadata, movie_name)
                tools_used  = ["query_movie_metadata", "groq-llm"]

                # Le LLM génère uniquement le commentaire — les métadonnées
                # sont préfixées directement, sans passer par le LLM
                tool_result_msg = {
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content": (
                        metadata +
                        "\n\n[INSTRUCTION : génère UNIQUEMENT un commentaire/analyse "
                        "en texte normal. Ne recopie PAS les données ci-dessus.]"
                    )
                }
                response2 = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[*messages, assistant_msg, tool_result_msg],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                commentary = response2.choices[0].message.content
                answer = f"{metadata}\n\n--------\n\n{commentary}"

            elif tool_name == "movie_age":
                movie_name = args.get("movie_name", "")
                age_result = await asyncio.to_thread(calculate_movie_age, movie_name)
                tools_used = ["movie_age", "groq-llm"]

                tool_result_msg = {
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content": (
                        age_result +
                        "\n\n[INSTRUCTION : intègre cette information dans une réponse naturelle.]"
                    )
                }
                response2 = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[*messages, assistant_msg, tool_result_msg],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                answer = response2.choices[0].message.content

            elif tool_name == "detailed_synopsis":
                movie_name = args.get("movie_name", "")
                wiki_text  = await asyncio.to_thread(scrape_detailed_synopsis, movie_name)
                tools_used = ["detailed_synopsis", "groq-llm"]

                tool_result_msg = {
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content": (
                        wiki_text +
                        "\n\n[INSTRUCTION : résume et commente ces informations Wikipedia "
                        "de façon engageante pour un fan d'horreur, en texte naturel.]"
                    )
                }
                response2 = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[*messages, assistant_msg, tool_result_msg],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                answer = response2.choices[0].message.content

            elif tool_name == "similar_movies":
                movie_name = args.get("movie_name", "")
                k          = args.get("k", 5)
                model, index, id_map = _get_retriever()
                similar    = await asyncio.to_thread(
                    find_similar_horror_movies, movie_name, k, model, index, id_map
                )
                tools_used = ["find_similar_horror_movies", "groq-llm"]

                tool_result_msg = {
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content": (
                        similar +
                        "\n\n[INSTRUCTION : génère un court commentaire sur ces recommandations "
                        "en texte normal, sans réécrire la liste.]"
                    )
                }
                response2  = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[*messages, assistant_msg, tool_result_msg],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                answer = f"{similar}\n\n--------\n\n{response2.choices[0].message.content}"

            else:
                query   = args.get("query", user_question)
                k       = args.get("k", 5)
                context = await asyncio.to_thread(_search_horror_movies, query, k)
                tools_used = ["search_horror_movies", "groq-llm"]

                tool_result_msg = {
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      context
                }
                response2 = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[*messages, assistant_msg, tool_result_msg],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                answer = response2.choices[0].message.content
        else:
            answer = choice.message.content

        # ── Le Juge : évaluation + retry (max _MAX_RETRIES) ──────────────────
        verdict = await self._judge_response(user_question, answer, tools_used)
        logger.info(
            f"[Juge] valid={verdict.get('is_valid')} "
            f"conf={verdict.get('confidence'):.2f} — {verdict.get('reasoning','')[:80]}"
        )

        retry_messages = [*messages, {"role": "assistant", "content": answer}]

        for attempt in range(_MAX_RETRIES):
            if verdict.get("is_valid", True) or verdict.get("confidence", 1.0) >= 0.65:
                break
            logger.info(f"[Juge] Retry {attempt + 1}/{_MAX_RETRIES}")
            retry_messages.append({
                "role": "user",
                "content": (
                    f"[Critique du Juge] Ta réponse n'est pas satisfaisante : "
                    f"{verdict.get('reasoning', '')}. "
                    "Corrige-la en restant fidèle aux données et sans hallucination."
                )
            })
            retry_resp = await self.client.chat.completions.create(
                model=self.config.model,
                messages=retry_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            answer = retry_resp.choices[0].message.content
            retry_messages.append({"role": "assistant", "content": answer})
            verdict = await self._judge_response(user_question, answer, tools_used)
            logger.info(
                f"[Juge] Après retry {attempt + 1} : valid={verdict.get('is_valid')} "
                f"conf={verdict.get('confidence'):.2f}"
            )

        logger.info(f"Réponse finale ({len(answer)} caractères) — outils : {tools_used}")
        return LLMResult(answer=answer, tools_used=tools_used, judge_verdict=verdict)


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
