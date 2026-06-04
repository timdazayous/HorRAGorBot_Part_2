"""
Interface Streamlit pour HorRAGor BOT
Frontend découplé qui communique avec l'API FastAPI
"""

import streamlit as st
import httpx
import json
from datetime import datetime
import uuid

# Configuration de la page
st.set_page_config(
    page_title="HorRAGor BOT",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration du thème (noir/horreur)
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #111111;
    }
    [data-testid="stSidebar"] {
        background-color: #1b1f24;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

API_URL = "http://localhost:8000"  # À adapter selon votre déploiement
REQUEST_TIMEOUT = 30


# ============================================================================
# GESTION DE SESSION
# ============================================================================

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "is_loading" not in st.session_state:
    st.session_state.is_loading = False


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def send_message_to_api(question: str) -> dict | None:
    """
    Envoie la question à l'API FastAPI et reçoit la réponse
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{API_URL}/chat",
                json={
                    "question": question,
                    "conversation_id": st.session_state.conversation_id,
                    "user_id": "streamlit_user"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Erreur API: {response.status_code}")
                st.error(f"Détail: {response.text}")
                return None
                
    except httpx.ConnectError:
        st.error("❌ Impossible de se connecter à l'API. Vérifiez que le serveur FastAPI est en cours d'exécution.")
        return None
    except httpx.TimeoutException:
        st.error("⏱️ Timeout: la réponse a pris trop de temps.")
        return None
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")
        return None


# ============================================================================
# INTERFACE UTILISATEUR
# ============================================================================

st.markdown("# 👻 HorRAGor BOT")
st.markdown("*Agent conversationnel spécialisé dans l'univers de l'horreur*")

# Sidebar
with st.sidebar:
    st.header("ℹ️ Informations")
    st.write(f"**ID Conversation:** `{st.session_state.conversation_id[:8]}...`")
    
    if st.button("🔄 Nouvelle conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    st.subheader("💡 Exemples de questions:")
    examples = [
        "Recommande-moi un film d'horreur similaire à The Shining",
        "Quel est le film d'horreur le plus ancien de ta base de données?",
        "Dis-moi tout sur Poltergeist",
        "Quelle sont mes chances de survie dans Saw?"
    ]
    for example in examples:
        st.caption(f"• {example}")


# Historique du chat
st.subheader("💬 Conversation")

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=message.get("avatar")):
        st.write(message["content"])
        
        if message["role"] == "assistant" and message.get("tools_used"):
            with st.expander("🔧 Outils utilisés"):
                st.write(", ".join(message["tools_used"]))
        
        if message["role"] == "assistant" and message.get("judge_verdict"):
            verdict = message["judge_verdict"]
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Confiance", f"{verdict['confidence']:.0%}")
            with col2:
                st.caption(f"*Verdict: {verdict['reasoning'][:100]}...*")


# Zone de saisie
col1, col2 = st.columns([1, 10])
with col2:
    user_input = st.chat_input(
        placeholder="Pose ta question sur l'univers de l'horreur...",
        disabled=st.session_state.is_loading
    )

with col1:
    if st.session_state.is_loading:
        st.spinner("⏳")


# Traitement du message utilisateur
if user_input:
    # Ajouter le message utilisateur au chat
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "avatar": "👤"
    })
    
    st.session_state.is_loading = True
    st.rerun()


# Appel API après l'affichage des messages
if st.session_state.is_loading and user_input:
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    api_response = loop.run_until_complete(
        send_message_to_api(user_input)
    )
    
    if api_response:
        # Ajouter la réponse de l'agent
        st.session_state.messages.append({
            "role": "assistant",
            "content": api_response.get("answer", "Erreur de traitement"),
            "tools_used": api_response.get("tools_used", []),
            "judge_verdict": api_response.get("judge_verdict"),
            "avatar": "👻"
        })
    
    st.session_state.is_loading = False
    st.rerun()


# Footer
st.divider()
st.caption(
    f"HorRAGor BOT v1.0 | Session: {st.session_state.conversation_id[:8]} | "
    f"{len(st.session_state.messages)} messages"
)
