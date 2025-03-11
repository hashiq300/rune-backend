from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.chains import create_retrieval_chain
from langchain_community.document_loaders import TextLoader
from langchain.chains.combine_documents import create_stuff_documents_chain
from config import Config
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter




system_prompt = (
    "You are an AI assistant called RUNE designed for educational purposes. "
    "Use the retrieved context to generate accurate responses. "
    "If you don't know the answer, say so. and ask the user if you want to generate without the context if user says yes give answer without context"
    "do not mention about names like 'user' and 'context' in the response"
    "You can view previous messages provided"
    "DO NOT GENERATE ANY CODE"
    "Syllabus gives the relevent topics that the user need to study from the given notes"
    "If the syllabus is provided, then generate accurate responses for user queries according to the syllabus"
    "If the syllabus is provided and if the user query is about a topic that is not in the syllabus, say so and  ask the user if you need an answer out of the syllabus. If the user says yes, give the answer without referring to the syllabus"
    "If there is no syllabus given, Use the retrieved context to generate accurate responses.  "
    "\n\n"
    "<syllabus>{syllabus}</syllabus>"
    "<context>{context}</context>"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
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

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
# llm = ChatOllama(model=Config.LLM_MODEL, temperature=0.7)

def create_qa_chain(vectorstore, chat_id):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5, "filter": {
        "chat_id": chat_id
    }})
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


vectorstore = initialize_vectorstore()

def process_documents(file_path: str):
  text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
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

