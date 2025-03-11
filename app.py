from flask import Flask
from flask_cors import CORS
from src.database import engine
import src.models as models
from dotenv import load_dotenv
from src.routes.auth import auth_router
from src.routes.upload import upload_router
from src.routes.chat import chat_router
from src.routes.mcq import mcq_router
from src.routes.flash import flashcard_router

load_dotenv()

app = Flask(__name__)
CORS(app)

models.Base.metadata.create_all(bind=engine)


@app.route("/", methods=["GET"])
def index():
    return "Hello server is working"


app.register_blueprint(chat_router, url_prefix="/api/chat")

app.register_blueprint(upload_router, url_prefix="/api/upload")

app.register_blueprint(auth_router, url_prefix="/api/auth")

app.register_blueprint(mcq_router, url_prefix="/api/mcq")

app.register_blueprint(flashcard_router, url_prefix="/api/flashcard")



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)