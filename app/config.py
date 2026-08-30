import os


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "skillswap123"
    )

    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb://localhost:27017/skill_swap_network"
    )