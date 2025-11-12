"""
Mahdi AI Property Assistant - Main Entry Point

Streamlit app for intelligent rental property search using:
- LangChain agents with GPT-4o-mini
- FAISS semantic search
- Hybrid filtering (semantic + structured)
- Conversation memory
"""

from src.ui_app import main

if __name__ == "__main__":
    main()