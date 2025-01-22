from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from rag_chain import initialize_vectorstore, create_qa_chain, process_documents
from config import Config
import os

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'knowledge_base'
app.config['ALLOWED_EXTENSIONS'] = Config.ALLOWED_EXTENSIONS

# Initialize vectorstore and QA chain
vectorstore = initialize_vectorstore()
qa_chain = create_qa_chain(vectorstore) if vectorstore else None

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    global qa_chain
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    if not qa_chain:
        return jsonify({"error": "Upload documents first"}), 400

    try:
        result = qa_chain.invoke({"query": data['message']})
        sources = [{
            "content": doc.page_content,
            "source": doc.metadata['source']
        } for doc in result['source_documents']]
        
        return jsonify({
            "response": result['result'],
            "sources": sources
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    global vectorstore, qa_chain
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

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
            splits = process_documents(file_path)
            embeddings = OllamaEmbeddings(model=Config.EMBEDDING_MODEL)

            if vectorstore:
                vectorstore.add_documents(splits)
            else:
                vectorstore = Chroma.from_documents(
                    documents=splits,
                    embedding=embeddings,
                    persist_directory=Config.CHROMA_DIR
                )
                qa_chain = create_qa_chain(vectorstore)

            return jsonify({"message": "File processed successfully"}), 200
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)}), 500
        finally:
            os.remove(file_path)
            # pass
    else:
        return jsonify({"error": "Invalid file type"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)