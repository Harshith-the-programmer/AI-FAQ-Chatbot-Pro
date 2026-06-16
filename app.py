import streamlit as st
import pandas as pd
import nltk
import re
import os

from dotenv import load_dotenv

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import google.generativeai as genai

# -----------------------------
# Environment Setup
# -----------------------------
load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "models/gemini-2.5-flash"
)


# -----------------------------
# NLTK
# -----------------------------
try:
    stopwords.words("english")
except LookupError:
    nltk.download("stopwords")



# -----------------------------
# Streamlit Config
# -----------------------------
st.set_page_config(
    page_title="AI FAQ Chatbot Pro",
    page_icon="🤖",
    layout="centered"
)

with open("styles/style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )

# -----------------------------
# Load Dataset
# -----------------------------
df = pd.read_csv("data/faqs.csv")

# -----------------------------
# NLP Setup
# -----------------------------
stemmer = PorterStemmer()

stop_words = set(
    stopwords.words("english")
)

# -----------------------------
# Text Preprocessing
# -----------------------------
def preprocess_text(text):

    abbreviations = {
        "ai": "artificial intelligence",
        "ml": "machine learning",
        "nlp": "natural language processing",
        "llm": "large language model",
        "rag": "retrieval augmented generation",
        "cv": "computer vision"
    }

    text = text.lower()

    for short, full in abbreviations.items():
        text = text.replace(short, full)

    text = re.sub(
        r"[^a-zA-Z0-9\s]",
        "",
        text
    )

    tokens = text.split()

    processed = []

    for word in tokens:

        if word not in stop_words:

            processed.append(
                stemmer.stem(word)
            )

    return " ".join(processed)

# -----------------------------
# Process FAQ Questions
# -----------------------------
df["processed_question"] = (
    df["question"].apply(
        preprocess_text
    )
)

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2)
)

faq_vectors = vectorizer.fit_transform(
    df["processed_question"]
)

# -----------------------------
# FAQ Retrieval
# -----------------------------
def get_best_match(user_question):

    processed_query = preprocess_text(
        user_question
    )

    query_vector = vectorizer.transform(
        [processed_query]
    )

    scores = cosine_similarity(
        query_vector,
        faq_vectors
    )[0]

    top_indices = scores.argsort()[-3:][::-1]

    best_index = top_indices[0]

    best_score = scores[best_index]

    answer = df.iloc[best_index]["answer"]

    question = df.iloc[best_index]["question"]

    top_matches = []

    for idx in top_indices:

        top_matches.append(
            (
                df.iloc[idx]["question"],
                float(scores[idx])
            )
        )

    return (
        question,
        answer,
        best_score,
        top_matches
    )

# -----------------------------
# Gemini Fallback with Memory
# -----------------------------
def ask_gemini(user_question):

    try:

        conversation_history = ""

        recent_messages = st.session_state.messages[-6:]

        for msg in recent_messages:

            conversation_history += (
                f"{msg['role']}: {msg['content']}\n"
            )

        prompt = f"""
You are an AI assistant.

Use the conversation history to understand
follow-up questions and references such as:
it, they, this, that, those, these.

Conversation History:
{conversation_history}

Current User Question:
{user_question}

Provide a concise and educational answer.
"""

        response = model.generate_content(
            prompt
        )

        return response.text

    except Exception:

        return (
            "I'm unable to access Gemini AI at the moment. "
            "Please try again in a few minutes."
        )

# -----------------------------
# Response Logic
# -----------------------------

def generate_response(user_question):

    (
        matched_question,
        faq_answer,
        score,
        top_matches
    ) = get_best_match(
        user_question
    )

    # High confidence FAQ answer
    if score >= 0.50:

        return (
            faq_answer,
            score,
            "FAQ Database",
            top_matches
        )

    # Medium confidence -> Gemini
    if score >= 0.30:

        gemini_answer = ask_gemini(
            user_question
        )

        return (
            gemini_answer,
            score,
            "Gemini AI",
            top_matches
        )

    # Low confidence -> Off-topic
    return (
        "⚠️ This chatbot specializes in AI, ML, NLP, LLMs, RAG, and Data Science.\n\nPlease ask a relevant question from these topics.",
        score,
        "Domain Restriction",
        top_matches
    )


# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:

    st.session_state.messages = []


# -----------------------------
# Header
# -----------------------------
col1, col2 = st.columns([8, 2])

with col1:

    st.markdown(
        """
        <h1>🤖 AI FAQ Chatbot Pro</h1>

        <div class="subtitle">
        • NLP &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        • TF-IDF &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        • Cosine Similarity &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        • Gemini AI
        </div>

        <div style="
            text-align:center;
            color:#9ca3af;
            font-size:15px;
            margin-top:10px;
            margin-bottom:20px;
        ">
        💡 You can ask questions about AI, ML, NLP, LLMs, RAG, and Data Science.
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:

    st.write("")
    st.write("")

    if st.button(
        "🗑️ Clear Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()

# -----------------------------
# Chat History
# -----------------------------
for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.write(
            message["content"]
        )

# -----------------------------
# Chat Input
# -----------------------------
user_input = st.chat_input(
    "Ask an AI-related question..."
)

if user_input:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.spinner(
        "Thinking..."
    ):

        (
            answer,
            score,
            source,
            top_matches
        ) = generate_response(
            user_input
        )

        if source == "FAQ Database":
            source_badge = "📚 FAQ Knowledge Base"
        else:
            source_badge = "🤖 Gemini AI"

        final_response = (
            f"{answer}\n\n"
            f"{source_badge}"
        )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": final_response
            }
        )

    st.rerun()

