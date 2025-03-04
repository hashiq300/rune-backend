from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from config import Config
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


system_prompt = (
    "You are an AI assistant called RUNE designed for educational purposes. "
    "Use the retrieved context to generate accurate responses. "
    "If you don't know the answer, say so. and ask the user if you want to generate without the context if user says yes give answer without context"
    "do not mention about names like 'user' and 'context' in the response"
    "\n\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)


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

def create_ollama_qa_chain(vectorstore):
    llm = ChatOllama(model=Config.LLM_MODEL, temperature=0.7)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain

def create_gemini_qa_chain(vectorstore):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


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