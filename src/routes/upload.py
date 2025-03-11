from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from config import Config
from src.rag_chain import process_documents, vectorstore
import os
from src.routes.auth import token_required
from src.models import Chat, File, FileTypeEnum
from src.database import get_db
from src.file import FileMemory
import threading
from langchain_community.document_loaders import PyPDFLoader


files = FileMemory()


upload_router = Blueprint("upload", __name__)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS





@upload_router.route('/<chat_id>/', methods=['GET'])
@token_required
def get_all_files(current_user, chat_id):


    try:
        db = next(get_db())

        chat = db.query(Chat).filter_by(chat_id=chat_id, user_id=current_user.user_id).first()
        if not chat:
            return jsonify({"error": "Invalid chat_id"}), 404
    

        files = db.query(File).filter_by(chat_id=chat_id).all()

        processed_files = [
            {
                "file_id": file.file_id,
                "file_name": file.file_name,
                "status": file.status.value,
                "file_type": file.file_type.value
            } for file in files
        ]

        return jsonify(processed_files), 200
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500 

@upload_router.route('/progress/<file_id>', methods=['GET'])
@token_required
def get_file_progress(current_user, file_id):
    try:
        file = files.get_file(file_id)
        print(file)
        if not file:
            return jsonify({"error": "Invalid file_id"}), 404
        
        
        if file["user_id"] != current_user.user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        if file["status"] == "completed":
            return jsonify({"progress": 100, "completed": True}), 200
        

        
        return jsonify({"progress": file.get("progress"), "completed": False}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

    


@upload_router.route('/delete/<file_id>', methods=['POST'])
@token_required
def delete_file(current_user, file_id):

    data = request.get_json()

    if "chat_id" not in data:
        return jsonify({"error": "chat_id is required"}), 400
    
    chat_id = data.get('chat_id')

    try:
        db = next(get_db())

        chat = db.query(Chat).filter_by(chat_id=chat_id, user_id=current_user.user_id).first()
        if not chat:
            return jsonify({"error": "Invalid chat_id"}), 404
    

        file = db.query(File).filter_by(chat_id=chat_id, file_id=file_id).first()

        if not file:
            return jsonify({"error": "Invalid file_id"}), 404
        
        db.delete(file)
        db.commit()

        deleted_file = {
            "file_id": file.file_id,
            "file_name": file.file_name,
            "status": file.status.value,
            "file_type": file.file_type.value
        }

        return jsonify(deleted_file), 200
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
def process_file(file_path, chat_id, file_id):
    


    file = files.get_file(file_id)

    whole_text = ""

    if file["file_type"] == "syllabus":

        loader = PyPDFLoader(file_path)

        pages = loader.load()

        whole_text = "\n".join([page.page_content for page in pages])


    else:
        splits = process_documents(file_path)

        for split in splits:
            # Add chat_id to metadata
            if not split.metadata:
                split.metadata = {}
            split.metadata['chat_id'] = chat_id

        if vectorstore:

            batch_size = 10
            total_size = len(splits)
            for i in range(0, len(splits), batch_size):
                vectorstore.add_documents(splits[i:min(i+batch_size, total_size)])
                progress = ((i + batch_size) / total_size) * 100
                files.update_progress(file_id, progress)

    

    files.set_file_completed(file_id)
    os.remove(file_path)



    try:
        db = next(get_db())
        file = db.query(File).filter_by(chat_id=chat_id, file_id=file_id).first()
        file.status = "processed"
        if file.file_type.value == "syllabus":
            file.content = whole_text
        db.commit()
        db.refresh(file)
    except Exception as e:
        print(e)
        return False
    
    return True


@upload_router.route('/new', methods=['POST'])
@token_required
def upload_file(current_user):

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    if "chat_id" not in request.form:
        return jsonify({"error": "chat_id is required"}), 400
    
    if "file_type" not in request.form:
        return jsonify({"error": "file_type is required"}), 400
    
    chat_id = request.form.get('chat_id')
    file_type = request.form.get('file_type')
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    

    if file and allowed_file(file.filename):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)

        try:
            db = next(get_db())

            chat = db.query(Chat).filter_by(chat_id=chat_id, user_id=current_user.user_id).first()

            if not chat:
                return jsonify({"error": "Invalid chat_id"}), 404
            
            new_file = File(
                file_name=filename,
                chat_id=chat_id,
                file_type=file_type,
                status="pending",
            )

            db.add(new_file)
            db.commit()
            db.refresh(new_file)

            files.add_file(new_file.file_id, {
                "file_id": new_file.file_id,
                "file_name": filename,
                "user_id": current_user.user_id,
                "file_type": new_file.file_type.value,
                "progress": 0,
                "status": "pending"
            })
            

            threading.Thread(target=process_file, args=(file_path, chat_id, new_file.file_id)).start()


            return jsonify({"message": "File processed successfully"}), 200
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
            
            # pass
    else:
        return jsonify({"error": "Invalid file type"}), 400