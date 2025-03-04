from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from rag_chain import initialize_vectorstore, create_gemini_qa_chain, process_documents, create_ollama_qa_chain
from config import Config
import os
from sqlalchemy.orm import Session
from database import get_db, engine
import models
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine


load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'knowledge_base'
app.config['ALLOWED_EXTENSIONS'] = Config.ALLOWED_EXTENSIONS

# Initialize vectorstore and QA chain
vectorstore = initialize_vectorstore()
qa_chain = create_gemini_qa_chain(vectorstore)
# qa_chain = create_ollama_qa_chain(vectorstore)

# Create database tables
models.Base.metadata.create_all(bind=engine)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")
from flask import Response, stream_with_context, jsonify, request

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Get database session
        db = next(get_db())

        # Create chat if chat_id is not provided
        chat_id = data.get('chat_id')
        if not chat_id:
            new_chat = models.Chat(title="New Chat")
            db.add(new_chat)
            db.commit()
            chat_id = new_chat.chat_id

        # Fetch previous messages for the chat
        previous_messages = db.query(models.ChatMessage).filter_by(chat_id=chat_id).order_by(models.ChatMessage.timestamp.asc()).all()
        history = [{"role": "user" if not msg.is_bot else "assistant", "content": msg.content} for msg in previous_messages]

        # Save user message
        user_message = models.ChatMessage(
            chat_id=chat_id,
            content=data['message'],
            is_bot=False
        )
        db.add(user_message)
        db.commit()  # Commit user message before streaming

        # Generator to stream the QA chain response
        def generate():
            full_bot_response = ""
            # Assuming qa_chain.stream yields chunks of the response
            for chunk in qa_chain.stream({
                "input": data['message'],
                "chat_history": history  # Pass previous messages here
            }):
                if "answer" in chunk:
                    full_bot_response += chunk["answer"] + " "
                    yield chunk["answer"] + " "
                else:
                    yield ""
            # After streaming completes, save the full bot response to the database
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


@app.route("/chat", methods=["GET"])
def get_chats():
    try:
        db = next(get_db())
        chats = db.query(models.Chat).all()
        
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
    


@app.route('/upload', methods=['POST'])
def upload_file():

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            chat_id = request.form.get('chat_id')
            if not chat_id:
                return jsonify({"error": "chat_id is required"}), 400
            

            splits = process_documents(file_path)

            for split in splits:
                # Add chat_id to metadata
                if not split.metadata:
                    split.metadata = {}
                split.metadata['chat_id'] = chat_id

            if vectorstore:
                vectorstore.add_documents(splits)

            return jsonify({"message": "File processed successfully"}), 200
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
        finally:
            os.remove(file_path)
            # pass
    else:
        return jsonify({"error": "Invalid file type"}), 400

@app.route("/chat/create", methods=["POST"])
def create_chat():
    try:
        data = request.get_json()
        title = data.get('title', 'New Chat')
        
        db = next(get_db())
        
        # Create new chat
        new_chat = models.Chat(
            title=title
        )
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        
        return jsonify({
            "chat_id": new_chat.chat_id,
            "title": new_chat.title,
            "created_at": new_chat.created_at.isoformat(),
            "user_id": new_chat.user_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat/<chat_id>/messages", methods=["GET"])
def get_chat_messages(chat_id):
    try:
        db = next(get_db())
        
        # Check if chat exists
        chat = db.query(models.Chat).filter(models.Chat.chat_id == chat_id).first()
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
            "chat_id": message.chat_id
        } for message in messages]
        
        return jsonify({
            "chat_id": chat_id,
            "messages": message_list
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)