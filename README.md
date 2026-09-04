# 🔄 Skill Swap Network — Connect, Learn, and Grow Together

Skill Swap Network is a web platform that connects users to **swap and exchange skills** with each other 🤝. Instead of paying for lessons, users can teach what they know and learn what they don't — directly from real people in the community.

## 🚀 Tech Stack

**Backend:** Python + Flask
**Database:** MongoDB (Atlas)
**Frontend:** HTML, CSS (Bootstrap), Jinja2 Templates
**Authentication:** Flask Sessions
**Deployment:** Render + Gunicorn

## ⚙️ Features

- 👤 User registration, login, and profile management
- 🔍 Discover and connect with users based on skills offered/wanted
- 💬 Real-time-style one-to-one chat between connected users
- 🔁 Skill swap requests and management
- ⭐ Post-swap reviews and ratings
- 🔔 Live notification system for messages, swaps, and connections
- 🚩 User reporting system for admin moderation
- 🛡️ Admin dashboard for managing users and reports

## 🗂️ Project Structure

```
/app
  /templates      → Jinja2 HTML templates (chat, dashboard, profile, etc.)
  /static         → CSS, JS, images
  __init__.py     → App factory, MongoDB init, notification context processor
  config.py       → App configuration (reads MONGO_URI, SECRET_KEY from env)
  routes.py       → All application routes/views
  models.py       → Data models/helpers
  forms.py        → WTForms form definitions
run.py            → Application entry point
requirements.txt  → Python dependencies
```

## 💻 Local Setup Instructions

**Clone this repository**
```
git clone https://github.com/bperfect13/skill-swap-network.git
cd skill-swap-network
```

**Create and activate a virtual environment**
```
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
```

**Install dependencies**
```
pip install -r requirements.txt
```

**Set up environment variables**

Create a `.env` file in the project root:
```
SECRET_KEY=your_secret_key_here
MONGO_URI=mongodb://localhost:27017/skill_swap_network
```

**Run the app**
```
python run.py
```

The app will be available at `http://127.0.0.1:5000`.

## ☁️ Deployment

This project is deployed using **MongoDB Atlas** for the database and **Render** for hosting, with **Gunicorn** as the production WSGI server.

## 🛠️ Future Improvements

- 📹 Video call integration for live skill sessions
- 📱 Mobile app version
- 🏆 Gamification with badges and skill levels
- 🔎 Advanced search and filtering for skill discovery

## 👨‍💻 Author

**Ryan D'Souza**
🌐 [GitHub](https://github.com/bperfect13)

---

Made with ❤️ to help people learn from each other, one skill at a time 🔄
