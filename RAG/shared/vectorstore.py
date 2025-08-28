# shared/vectorstore.py
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import os, glob

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

    def search(self, query: str, k: int = 5):
        if self.vs is None:
            self.load()
        return self.vs.similarity_search(query, k=k)