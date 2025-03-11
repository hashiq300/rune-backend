from flask import Blueprint, jsonify, request
from langchain_core.prompts import ChatPromptTemplate
from src.rag_chain import vectorstore, llm
from src.routes.auth import token_required
from src.database import get_db
from langchain_google_genai import ChatGoogleGenerativeAI

mcq_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Generate a list of multiple-choice questions based on the context. "
                  "Each question should have a unique id, a question string, a list of options, "
                  "and the index of the correct answer in the options list. "
                  "Generate 10 questions"
                  "YOU ONLY NEED TO RESPOND WITH JSON FORMAT, NO ADDITIONAL EXPLANATION NEEDED"
                  "Return the questions in JSON format. \n\n {context}"),
    ]
)



mcq_router = Blueprint("mcq", __name__)



@mcq_router.route("/<chat_id>/", methods=["POST"])
@token_required
def generate_mcq(current_user, chat_id):
    try:
        db = next(get_db())
        keywords = request.json.get("keywords")


        if not keywords:
            return jsonify({"error": "No keywords provided"}), 400
        

        context = retrieve_context_based_on_keyword(keywords, chat_id)

        
        
        print(keywords)

        mcq_prompt_with_context = mcq_prompt.format(context=context)
        response = llm.invoke(mcq_prompt_with_context)

        text = response.text()

        return jsonify({ "data": text}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Internal server error"}), 500


def retrieve_context_based_on_keyword(keywords, chat_id):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5, "filter": {
        "chat_id": chat_id
    }})

    final_str = ""

    for keyword in keywords:

        relevant_docs = retriever.invoke(keyword)

        context = " ".join([doc.page_content for doc in relevant_docs])

        final_str += context

    return final_str