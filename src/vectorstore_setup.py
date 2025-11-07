from pathlib import Path
from typing import Sequence

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv; load_dotenv()

from src.data_loader import load_property_data

DEFAULT_DATA_PATH = "data/listing_sample1.csv"
DEFAULT_PERSIST_DIR = "data/embeddings"


def create_vectorstore(chunks: Sequence, persist_dir: str = DEFAULT_PERSIST_DIR):
    persist_path = Path(persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = FAISS.from_documents(chunks, embedding=embeddings)
    store.save_local(str(persist_path))
    return store


def ensure_vectorstore(data_path: str = DEFAULT_DATA_PATH, persist_dir: str = DEFAULT_PERSIST_DIR):
    persist_path = Path(persist_dir)
    index_file = persist_path / "index.faiss"
    docstore_file = persist_path / "index.pkl"

    if index_file.exists() and docstore_file.exists():
        return

    chunks = load_property_data(data_path)
    create_vectorstore(chunks, persist_dir)


def load_vectorstore(persist_dir: str = DEFAULT_PERSIST_DIR):
    persist_path = Path(persist_dir)
    index_file = persist_path / "index.faiss"
    docstore_file = persist_path / "index.pkl"

    if not index_file.exists() or not docstore_file.exists():
        raise FileNotFoundError(
            f"Vectorstore not found in '{persist_dir}'. Run `python -m src.vectorstore_setup` to build it."
        )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local(str(persist_path), embeddings, allow_dangerous_deserialization=True)


if __name__ == "__main__":
    ensure_vectorstore()
