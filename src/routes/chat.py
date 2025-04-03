from flask import Blueprint, request, jsonify, Response, stream_with_context
import src.models as models
from src.rag_chain import create_qa_chain, vectorstore
from src.routes.auth import token_required
from src.database import get_db
from langchain_core.messages import HumanMessage, AIMessage



chat_router = Blueprint("chat", __name__)



@chat_router.route('/', methods=['POST'])
@token_required
def chat(current_user):
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    chat_id = data.get('chat_id')
    if not chat_id:
        return jsonify({"error": "No chat_id provided"}), 400
    print("Hello")
    try:
        # Get database session
        db = next(get_db())

        # Fetch chat with chat id and current_user.user_id
        chat = db.query(models.Chat).filter_by(chat_id=chat_id, user_id=current_user.user_id).first()

        if not chat:
            return jsonify({"error": "invalid chat_id or user_id provided"}), 400

        # Fetch previous messages for the chat
        previous_messages = db.query(models.ChatMessage).filter_by(chat_id=chat_id).order_by(models.ChatMessage.timestamp.asc()).all()


        history = [HumanMessage(content=msg.content) if not msg.is_bot else AIMessage(content=msg.content) for msg in previous_messages]

        print(history)

        # Save user message
        user_message = models.ChatMessage(
            chat_id=chat_id,
            content=data['message'],
            is_bot=False
        )
          # Commit user message before streaming

        file = db.query(models.File).filter_by(chat_id=chat_id,file_type=models.FileTypeEnum.syllabus).first()

        syllabus = ""

        if file:
            syllabus += file.content

        # Generator to stream the QA chain response
        qa_chain = create_qa_chain(vectorstore, chat_id)
        def generate():
            full_bot_response = ""
            # Assuming qa_chain.stream yields chunks of the response
            for chunk in qa_chain.stream({
                "input": data['message'],
                "chat_history": history,
                "syllabus": syllabus
            }):
                if "answer" in chunk:
                    full_bot_response += chunk["answer"] + " "
                    yield chunk["answer"] + " "
                else:
                    yield ""
            # After streaming completes, save the full bot response to the database

            db.add(user_message)
            db.commit()
            bot_message = models.ChatMessage(
                chat_id=chat_id,
                content=full_bot_response.strip(),
                is_bot=True
            )
            db.add(bot_message)
            db.commit()

        # Return a streaming response
        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@chat_router.route("/", methods=["GET"])
@token_required
def get_chats(current_user):
    try:
        db = next(get_db())
        chats = db.query(models.Chat).filter(models.Chat.user_id == current_user.user_id).all()
        
        # Convert to response format
        chat_list = [{
            "chat_id": chat.chat_id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "user_id": chat.user_id
        } for chat in chats]
        
        return jsonify(chat_list)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@chat_router.route("/bookmark/", methods=["GET"])
@token_required
def get_bookmarked_chats(current_user):
    try:
        db = next(get_db())
        chats = db.query(models.Chat).filter_by(user_id=current_user.user_id, bookmarked=True).all()
        
        # Convert to response format
        chat_list = [{
            "chat_id": chat.chat_id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "user_id": chat.user_id,
            "bookmarked": chat.bookmarked
        } for chat in chats]
        
        return jsonify(chat_list)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@chat_router.route("/bookmark/<chat_id>/", methods=["POST"])
@token_required
def bookmark_chat(current_user, chat_id):
    try:
        db = next(get_db())
        chat = db.query(models.Chat).filter_by(user_id=current_user.user_id, chat_id=chat_id).first()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        
        bookmark = chat.bookmarked


        chat.bookmarked = not bookmark
        db.commit()
        db.refresh(chat)
        
        
        
        return jsonify({"message": f"successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




@chat_router.route("/new", methods=["POST"])
@token_required
def create_chat(current_user):
    try:
        data = request.get_json()
        if "title" not in data:
            return jsonify({"error": "No title provided"}), 400
        

        title = data["title"]

        db = next(get_db())
        
        # Create new chat
        new_chat = models.Chat(
            title=title,
            user_id=current_user.user_id
        )
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)


        new_message = models.ChatMessage(
            chat_id=new_chat.chat_id,
            content="Hello! How can I help you today?",
            is_bot=True
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        return jsonify({
            "chat_id": new_chat.chat_id,
            "title": new_chat.title,
            "created_at": new_chat.created_at.isoformat(),
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_router.route("/<chat_id>/messages", methods=["GET"])
@token_required
def get_chat_messages(current_user, chat_id):
    try:
        db = next(get_db())
        
        # Check if chat exists
        chat = db.query(models.Chat).filter(models.Chat.chat_id == chat_id, models.Chat.user_id == current_user.user_id).first()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        # Get messages for the chat
        messages = db.query(models.ChatMessage)\
            .filter(models.ChatMessage.chat_id == chat_id)\
            .order_by(models.ChatMessage.timestamp.asc())\
            .all()
        
        # Convert to response format
       
        message_list = [{
            "message_id": message.message_id,
            "content": message.content,
            "is_bot": message.is_bot,
            "timestamp": message.timestamp.isoformat(),
            "chat_id": message.chat_id,
        } for message in messages]
        
        return jsonify({
            "chat_id": chat_id,
            "messages": message_list,
            "bookmarked": chat.bookmarked
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@chat_router.route("/<chat_id>/", methods=["DELETE"])
@token_required
def delete_chat(current_user, chat_id):
    try:
        db = next(get_db())
        
        # Check if chat exists
        chat = db.query(models.Chat).filter(models.Chat.chat_id == chat_id, models.Chat.user_id == current_user.user_id).first()
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        # Delete chat
        db.delete(chat)
        db.commit()
        
        return jsonify({"message": "Chat deleted successfully"})
    
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500