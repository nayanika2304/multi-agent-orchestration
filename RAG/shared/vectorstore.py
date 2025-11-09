# shared/vectorstore.py
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import os, glob
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, path: str = "./.chroma", collection: str = "docs", model: str = "text-embedding-3-small"):
        self.path = path
        self.collection = collection
        self.emb = OpenAIEmbeddings(model=model)
        self.vs = None

    def ingest_folder(self, folder: str):
        docs = []
        for p in glob.glob(os.path.join(folder, "**/*"), recursive=True):
            if p.lower().endswith(".pdf"):
                docs.extend(PyPDFLoader(p).load())
            elif p.lower().endswith((".md", ".txt")):
                docs.extend(TextLoader(p, encoding="utf-8").load())
        self.vs = Chroma.from_documents(docs, self.emb, collection_name=self.collection, persist_directory=self.path)
        self.vs.persist()

    def load(self):
        self.vs = Chroma(embedding_function=self.emb, collection_name=self.collection, persist_directory=self.path)

    def search(self, query: str, k: int = 5, filter_dict: dict = None):
        """
        Search the vector store with optional metadata filtering.
        
        Args:
            query: Search query string
            k: Number of results to return
            filter_dict: Optional dictionary of metadata filters (e.g., {"location": "New York"})
        """
        if self.vs is None:
            self.load()
        
        if filter_dict:
            # Use metadata filtering - ChromaDB uses where clause format
            try:
                # Try ChromaDB's native filtering (where clause)
                where_clause = {}
                for key, value in filter_dict.items():
                    where_clause[key] = {"$eq": value}
                
                return self.vs.similarity_search(query, k=k, where=where_clause)
            except Exception as e:
                # Fallback to regular search with manual filtering
                logger.warning(f"Metadata filtering not supported, using manual filter: {e}")
                results = self.vs.similarity_search(query, k=k*3)  # Get more results for filtering
                # Filter manually
                filtered = []
                for doc in results:
                    match = True
                    for key, value in filter_dict.items():
                        if key in doc.metadata:
                            # Case-insensitive partial matching for location
                            if key == "location":
                                doc_loc = str(doc.metadata[key]).lower()
                                query_loc = str(value).lower()
                                if query_loc not in doc_loc and doc_loc not in query_loc:
                                    match = False
                                    break
                            elif str(doc.metadata[key]) != str(value):
                                match = False
                                break
                    if match:
                        filtered.append(doc)
                        if len(filtered) >= k:
                            break
                return filtered if filtered else results[:k]  # Return filtered or fallback to top k
        else:
            return self.vs.similarity_search(query, k=k)