from dotenv import load_dotenv
load_dotenv()

from flask import Flask, session
from flask_pymongo import PyMongo
from app.config import Config

mongo = PyMongo()


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    mongo.init_app(app)

    from app.routes import main

    app.register_blueprint(main)

    # --------------------------------
    # Global Notification Count
    # --------------------------------

    @app.context_processor
    def inject_notifications():

        unread_count = 0

        if session.get("user_id"):

            unread_count = mongo.db.notifications.count_documents({
                "user_id": session["user_id"],
                "read": False
            })

        return {
            "unread_count": unread_count
        }

    return app