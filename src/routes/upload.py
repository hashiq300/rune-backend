from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from config import Config
from src.rag_chain import process_documents, vectorstore
import os


upload_router = Blueprint("upload", __name__)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS






@upload_router.route('/new', methods=['POST'])
def upload_file():

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
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