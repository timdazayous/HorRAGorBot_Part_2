"""
Module d'intégration avec Groq API
Gère la génération de réponses avec le LLM
"""

import logging
import os
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GroqConfig(BaseModel):
    """Configuration pour Groq"""
    api_key: str = Field(..., description="Clé API Groq")
    model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Modèle Groq à utiliser"
    )
    temperature: float = Field(default=0.7, description="Température (0-1)")
    max_tokens: int = Field(default=2048, description="Nombre max de tokens")


class GroqLLM:
    """Client pour interagir avec Groq"""

    def __init__(self, config: Optional[GroqConfig] = None):
        """Initialise le client Groq"""

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

        logger.info(
            f"Client Groq initialisé avec le modèle: {self.config.model}"
        )

    async def generate_response(
        self,
        user_question: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Génère une réponse avec Groq
        """

        if system_prompt is None:
            system_prompt = """Tu es HorRAGor, un agent conversationnel spécialisé
dans l'univers de l'horreur (cinéma, littérature, jeux vidéo).
Tu es compétent, enthousiaste et tu fournis des réponses détaillées et pertinentes.
Tu aimes l'horreur sous toutes ses formes."""

        messages = []

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({
            "role": "user",
            "content": user_question
        })

        try:
            logger.info(
                f"Appel à Groq avec la question: {user_question[:50]}..."
            )

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            answer = response.choices[0].message.content

            logger.info(
                f"Réponse générée avec succès ({len(answer)} caractères)"
            )

            return answer

        except Exception as e:
            logger.error(f"Erreur lors de l'appel à Groq: {str(e)}")
            raise

    async def generate_response_with_context(
        self,
        user_question: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Génère une réponse en utilisant un contexte spécifique
        """

        if system_prompt is None:
            system_prompt = """Tu es HorRAGor, un agent conversationnel spécialisé
dans l'univers de l'horreur. Utilise le contexte fourni pour répondre à la question."""

        prompt_with_context = f"""Contexte pertinent:
{context}

Question de l'utilisateur:
{user_question}

Réponds de manière concise et pertinente en utilisant le contexte fourni."""

        return await self.generate_response(
            prompt_with_context,
            system_prompt=system_prompt
        )


def get_groq_client() -> GroqLLM:
    """Factory function pour obtenir le client Groq"""
    return GroqLLM()


if __name__ == "__main__":
    import asyncio

    async def test():
        client = GroqLLM()

        response = await client.generate_response(
            "Recommande-moi un film d'horreur classique"
        )

        print("Réponse Groq:")
        print(response)

    asyncio.run(test())