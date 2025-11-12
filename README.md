# 🏠 Mahdi AI Property Assistant

> An intelligent rental property search assistant powered by **Retrieval-Augmented Generation (RAG)** that understands natural language queries and maintains conversation context.

**🔗 [Live Demo](https://mahdi-ai-property-assistant-xsgdp85bc5ex9rdwmtcs8i.streamlit.app)** | **📊 [Technical Deep Dive](AI_ENHANCEMENTS_SUMMARY.md)**

---

## 📸 Demo

**Chat Interface with Conversation Memory:**

```
User: "Find 2-bedroom apartments in Toronto under $2500"
Mahdi: Here are 3 two-bedroom apartments...
      - 3385 Dundas St W (Toronto): 2 bed, 1 bath, $1400/month
      - 123 Main St (Toronto): 2 bed, 2 bath, $2200/month
      ...

User: "What about ones with parking?"
Mahdi: [Remembers context: Toronto, 2-bed, <$2500, adds parking filter]
      - 456 Queen St (Toronto): 2 bed, 1 bath, $1800/month [Parking included]
```

**Market Analysis:**
```
User: "Compare rent in Toronto vs Mississauga"
Mahdi: Toronto (1 bed): Average $1800, Range $1500-$2100 (45 listings)
       Toronto (2 bed): Average $2256, Range $1800-$3200 (78 listings)
       Mississauga (1 bed): Average $1650, Range $1400-$1900 (32 listings)
       Mississauga (2 bed): Average $2037, Range $1600-$2800 (54 listings)
```

---

## 💡 What This Project Does

Mahdi is an **AI-powered rental property assistant** that:

1. **Understands Natural Language**: Ask questions like a human, not like a search engine
   - "Show me pet-friendly 2-bedroom apartments with parking under $2500"
   - "What about cheaper ones?" (remembers previous context)

2. **Hybrid Search**: Combines semantic understanding with precise filtering
   - Semantic search finds properties matching the "vibe" of your query
   - Structured filters ensure exact matches (bedrooms, price, amenities)

3. **Maintains Conversation Context**: No need to repeat yourself
   - Follows up on previous questions
   - Remembers your preferences throughout the conversation

4. **Market Insights**: Compare neighborhoods and analyze pricing trends
   - Segmented by bedroom count for accurate comparisons
   - Statistical analysis (average, median, range)

**Key Innovation**: True agentic RAG system - the AI decides when to search, compare, or analyze based on your intent, not just keyword matching.

### Key Features

- 🤖 **Agentic AI**: LangChain agents with GPT-4o-mini for intelligent conversation handling
- 🔍 **Hybrid Search**: Combines semantic similarity (FAISS) with structured filtering (bedrooms, price, amenities)
- 💬 **Conversation Memory**: Remembers context and handles follow-up questions
- 📊 **Market Analysis**: Segmented price comparisons by bedroom count
- ⚡ **Performance**: 100x faster search through pre-computed embeddings
- 🎯 **Smart Filtering**: Natural language support for amenities (parking, pet-friendly, furnished, etc.)

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| **AI/ML** | LangChain (Agents, Tools), OpenAI GPT-4o-mini, FAISS Vector DB |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **Backend** | Python 3.13, Pandas, NumPy |
| **Frontend** | Streamlit (deployed on Streamlit Cloud) |
| **APIs** | OpenAI API, Rentcast Property Data API |
| **Data** | 12,000+ property listings (CSV → Vector embeddings) |

**Architecture**: Agentic RAG with hybrid retrieval (semantic + structured filtering)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mahekk357/Mahdi-AI-Property-Assistant.git
   cd Mahdi-AI-Property-Assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Build the vector database**
   ```bash
   python -m src.vectorstore_setup
   ```

6. **Run the app**
   ```bash
   streamlit run app.py
   ```

---

## 💡 Usage Examples

### Property Search
```
User: "Find me a 2-bedroom apartment in Toronto under $2500"
User: "What about ones with parking?"
```

### Natural Language Queries
- "2 bedrooms" / "2+ beds" / "at least 2 bedrooms"
- "$2000-$3000" / "between $2k and $3k" / "around $2500"
- "pet-friendly" / "parking" / "furnished" / "gym access"

---

## 📊 Performance Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Search Speed** | 5-10 seconds | <1 second | 100x faster |
| **Query Understanding** | Basic | 20+ patterns | 10x better |
| **Follow-up Questions** | ❌ Broken | ✅ Working | Fixed |

---

## 📧 Contact

**Mahekk Shaikh**
- GitHub: [@Mahekk357](https://github.com/Mahekk357)
- Project: [Mahdi-AI-Property-Assistant](https://github.com/Mahekk357/Mahdi-AI-Property-Assistant)

---

**Built with AI and modern ML techniques**
