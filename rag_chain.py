from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
from config import Config
import os
from langchain_community.document_loaders import PyPDFLoader


def initialize_vectorstore():
    embeddings = OllamaEmbeddings(model=Config.EMBEDDING_MODEL)
    if os.path.exists(Config.CHROMA_DIR):
        return Chroma(
            persist_directory=Config.CHROMA_DIR,
            embedding_function=embeddings
        )
    # Create a new empty vectorstore if none exists
    return Chroma(
        persist_directory=Config.CHROMA_DIR,
        embedding_function=embeddings
    )

def create_qa_chain(vectorstore):
    llm = ChatOllama(model=Config.LLM_MODEL, temperature=0.7)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True
    )

def process_documents(file_path: str):
  text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=200
  )
  if file_path.endswith(".txt"):
      loader = TextLoader(file_path)
      documents = loader.load()
      return text_splitter.split_documents(documents)
  elif file_path.endswith(".pdf"):
      pdf = PyPDFLoader(file_path)
      pages = pdf.load()

      return text_splitter.split_documents(pages)
  

  return []