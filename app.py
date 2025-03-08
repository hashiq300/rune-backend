from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from rag_chain import initialize_vectorstore, create_gemini_qa_chain, process_documents, create_ollama_qa_chain
from config import Config
import os
from database import get_db, engine, SessionLocal
import models
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
from flask import Response, stream_with_context, jsonify, request
JWT_SECRET = "your-jwt-secret-key-replace-this"  # Change this in production
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds

load_dotenv()




app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'knowledge_base'
app.config['ALLOWED_EXTENSIONS'] = Config.ALLOWED_EXTENSIONS

# Initialize vectorstore and QA chain
vectorstore = initialize_vectorstore()
qa_chain = create_gemini_qa_chain(vectorstore)

# Create database tables
models.Base.metadata.create_all(bind=engine)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            db = SessionLocal()
            current_user = db.query(User).filter_by(user_id=data['user_id']).first()
            db.close()
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
                
        except Exception as e:
            return jsonify({'message': 'Token is invalid', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")



@app.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    chat_id = data.get('chat_id')
    if not chat_id:
        return jsonify({"error": "No chat_id provided"}), 400

    try:
        # Get database session
        db = next(get_db())

        # Fetch chat with chat id and current_user.user_id
        chat = db.query(models.Chat).filter_by(chat_id=chat_id, user_id=current_user.user_id).first()

        if not chat:
            return jsonify({"error": "invalid chat_id or user_id provided"}), 400

        # Fetch previous messages for the chat
        previous_messages = db.query(models.ChatMessage).filter_by(chat_id=chat_id).order_by(models.ChatMessage.timestamp.asc()).all()
        history = [{"role": "user" if not msg.is_bot else "assistant", "content": msg.content} for msg in previous_messages]

        print(history)

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
@token_required
def get_chats(current_user):
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

@app.route("/chat/new", methods=["POST"])
@token_required
def create_chat(current_user):
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
            "user_id": current_user.user_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat/<chat_id>/messages", methods=["GET"])
@token_required
def get_chat_messages(chat_id, current_user):
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
            "chat_id": message.chat_id
        } for message in messages]
        
        return jsonify({
            "chat_id": chat_id,
            "messages": message_list
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    # Check if required fields are present
    if not all(key in data for key in ['name', 'email', 'password', 'confirmPassword']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if passwords match
    if data['password'] != data['confirmPassword']:
        return jsonify({'message': 'Passwords do not match'}), 400
    
    db = SessionLocal()
    
    # Check if user already exists
    existing_user = db.query(User).filter_by(email=data['email']).first()
    if existing_user:
        db.close()
        return jsonify({'message': 'User already exists'}), 409
    
    # Create new user
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        name=data['name'],
        email=data['email'], 
        password_hash=hashed_password
    )
    
    try:
        db.add(new_user)
        db.commit()
        
        # Generate token
        token = jwt.encode({
            'user_id': new_user.user_id,
            'email': new_user.email,
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
        }, JWT_SECRET, algorithm="HS256")
        
        db.close()
        
        return jsonify({
            'message': 'User created successfully',
            'token': token,
            'user': {
                'user_id': new_user.user_id,
                'name': new_user.name,
                'email': new_user.email
            }
        }), 201
        
    except Exception as e:
        db.rollback()
        db.close()
        print(e)
        return jsonify({'message': 'Error creating user', 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Check if required fields are present
    if not all(key in data for key in ['email', 'password']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    db = SessionLocal()
    
    # Find user by email
    user = db.query(User).filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        db.close()
        return jsonify({'message': 'Invalid email or password'}), 401
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate token
    token = jwt.encode({
        'user_id': user.user_id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }, JWT_SECRET, algorithm="HS256")
    
    db.close()
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'user_id': user.user_id,
            'name': user.name,
            'email': user.email
        }
    }), 200

@app.route('/api/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify({
        'user_id': current_user.user_id,
        'name': current_user.name,
        'email': current_user.email
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    # JWT tokens are stateless, so we don't need to do anything server-side
    # The client will remove the token
    return jsonify({'message': 'Logged out successfully'}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)