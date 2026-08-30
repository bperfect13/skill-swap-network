from fileinput import filename
import os

import json
from datetime import datetime, timezone, timedelta


from flask import current_app
from PIL import Image
from flask import jsonify


from werkzeug.utils import secure_filename

from bson import ObjectId

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app
)

from app import mongo
# --------------------------------
# Notification Helper
# --------------------------------

def create_notification(
    user_id,
    notification_type,
    message,
    related_user_id=None
):

    notification = {

        "user_id": str(user_id),

        "type": notification_type,

        "message": message,

        "related_user_id": (
            str(related_user_id)
            if related_user_id
            else None
        ),

        "read": False,

        "created_at": datetime.now(timezone.utc)

    }

    mongo.db.notifications.insert_one(
        notification
    )

main = Blueprint("main", __name__) 

ALLOWED_EXTENSIONS = {

    "png",
    "jpg",
    "jpeg"

}


def allowed_file(filename):

    return (

        "." in filename

        and

        filename.rsplit(".", 1)[1].lower()

        in ALLOWED_EXTENSIONS

    )


@main.route("/")
def home():

    users = mongo.db.users.count_documents({})

    return render_template(
        "index.html",
        total_users=users
    )


@main.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if email already exists
        existing_user = mongo.db.users.find_one({
            "email": email
        })

        if existing_user:

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return render_template("register.html")

        user = {

    "name": name,

    "email": email,

    "password": password,

    "phone": "",

    "location": "",

    "profession": "",

    "bio": "",

    "linkedin": "",

    "github": "",

    "portfolio": "",

    "profile_picture": "default.png",

    "skills_offer": [],

    "skills_need": [],

    "matches": [],

    "requests": [],

    "connections": []

}

        mongo.db.users.insert_one(user)

        flash(
            "Registration Successful! Please login.",
            "success"
        )

        return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        # --------------------------------
        # Find user
        # --------------------------------

        user = mongo.db.users.find_one({

            "email": email,

            "password": password

        })

        # --------------------------------
        # Check login
        # --------------------------------

        if user:

            # --------------------------------
            # Store user information in session
            # --------------------------------

            session["user_id"] = str(
                user["_id"]
            )

            session["user_name"] = user["name"]

            session["profile_picture"] = user.get(
                "profile_picture",
                "default.png"
            )

            # --------------------------------
            # Store admin status
            # --------------------------------

            session["is_admin"] = user.get(
                "is_admin",
                False
            )

            # --------------------------------
            # Go to Dashboard
            # --------------------------------

            return redirect(
                url_for("main.dashboard")
            )

        # --------------------------------
        # Invalid login
        # --------------------------------

        flash(
            "Invalid Email or Password",
            "danger"
        )

    return render_template(
        "login.html"
    )

# ==========================================
# FORGOT PASSWORD
# ==========================================

@main.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # --------------------------------
        # Check email
        # --------------------------------

        user = mongo.db.users.find_one({
            "email": email
        })

        if not user:

            flash(
                "No account was found with that email address.",
                "danger"
            )

            return render_template(
                "forgot_password.html"
            )

        # --------------------------------
        # Check passwords
        # --------------------------------

        if not new_password:

            flash(
                "Please enter a new password.",
                "warning"
            )

            return render_template(
                "forgot_password.html"
            )

        if new_password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "forgot_password.html"
            )

        # --------------------------------
        # Update password
        # --------------------------------

        mongo.db.users.update_one(

            {
                "_id": user["_id"]
            },

            {
                "$set": {
                    "password": new_password
                }
            }

        )

        flash(
            "Password updated successfully! Please login.",
            "success"
        )

        return redirect(
            url_for("main.login")
        )

    return render_template(
        "forgot_password.html"
    )


@main.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    # Current logged in user
    user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

        # --------------------------------
    # Admin Dashboard
    # --------------------------------

    if user and user.get("is_admin", False):

        total_users = mongo.db.users.count_documents({
            "is_admin": {
                "$ne": True
            }
        })

        total_swaps = mongo.db.swaps.count_documents({})

        total_connection_entries = 0

        for db_user in mongo.db.users.find(
            {
                "is_admin": {
                    "$ne": True
                }
            },
            {
                "connections": 1
            }
        ):

            total_connection_entries += len(
                db_user.get("connections", [])
            )

        total_connections = (
            total_connection_entries // 2
        )

        normal_users = list(
            mongo.db.users.find(
                {
                    "is_admin": {
                        "$ne": True
                    }
                },
                {
                    "password": 0
                }
            )
        )

                # --------------------------------
        # Get Reports
        # --------------------------------

        reports = list(
            mongo.db.reports.find({})
            .sort(
                "created_at",
                -1
            )
        )
        return render_template(

            "admin.html",

            total_users=total_users,

            total_connections=total_connections,

            total_swaps=total_swaps,

            normal_users=normal_users,

            reports=reports

        )

    # Get all users
    all_users = list(
        mongo.db.users.find()
    )

    recommended_matches = []

    # ------------------------------------
    # Find Recommended Matches
    # ------------------------------------

    for other_user in all_users:

        # Skip yourself
        if other_user["_id"] == user["_id"]:
            continue

        # Skip users already connected
        if str(other_user["_id"]) in user.get("connections", []):
            continue

        # Skip users to whom you've already sent a request
        already_sent = False

        for req in other_user.get("requests", []):

            if req["sender_id"] == session["user_id"]:
                already_sent = True
                break

        if already_sent:
            continue

        # Skip users who have already sent YOU a request
        incoming_request = False

        for req in user.get("requests", []):

            if req["sender_id"] == str(other_user["_id"]):
                incoming_request = True
                break

        if incoming_request:
            continue

        # ----------------------------
        # Matching Algorithm
        # ----------------------------

        user_need = {
            skill.strip().lower()
            for skill in user.get("skills_need", [])
        }

        user_offer = {
            skill.strip().lower()
            for skill in user.get("skills_offer", [])
        }

        other_need = {
            skill.strip().lower()
            for skill in other_user.get("skills_need", [])
        }

        other_offer = {
            skill.strip().lower()
            for skill in other_user.get("skills_offer", [])
        }

        offer_match = user_need.intersection(other_offer)

        need_match = user_offer.intersection(other_need)

        total_match = len(offer_match) + len(need_match)

        total_possible = len(user_offer) + len(user_need)

        if total_possible == 0:
            match_percentage = 0
        else:
            match_percentage = round(
                (total_match / total_possible) * 100
            )

        if total_match > 0:

            recommended_matches.append({

                "user": other_user,

                "score": total_match,

                "percentage": match_percentage,

                "offer_match": sorted(list(offer_match)),

                "need_match": sorted(list(need_match))

            })

    # Sort by best match first
    recommended_matches.sort(

        key=lambda x: x["percentage"],

        reverse=True

    )

    # ------------------------------------
    # Build Connections List
    # ------------------------------------

    connections = []

    for connection_id in user.get("connections", []):

        connection = mongo.db.users.find_one({

            "_id": ObjectId(connection_id)

        })

        if connection:

            connections.append(connection)

    # ------------------------------------
    # Render Dashboard
    # ------------------------------------

    return render_template(

        "dashboard.html",

        user=user,

        matches=recommended_matches,

        connections=connections

    )

@main.route("/browse")
def browse():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    # --------------------------------
    # Search & Filter Values
    # --------------------------------

    search = request.args.get(
        "search",
        ""
    ).strip()

    offer_skill = request.args.get(
        "offer_skill",
        ""
    ).strip()

    need_skill = request.args.get(
        "need_skill",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    profession = request.args.get(
        "profession",
        ""
    ).strip()

    sort = request.args.get(
        "sort",
        ""
    ).strip()

    user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    # --------------------------------
    # Build MongoDB Query
    # --------------------------------

    query = {}

    if search:

        query["$or"] = [

            {
                "name": {
                    "$regex": search,
                    "$options": "i"
                }
            },

            {
                "skills_offer": {
                    "$regex": search,
                    "$options": "i"
                }
            },

            {
                "skills_need": {
                    "$regex": search,
                    "$options": "i"
                }
            }

        ]

    all_users = list(
        mongo.db.users.find(query)
    )

    browse_users = []

    for other_user in all_users:

        # Skip yourself
        if other_user["_id"] == user["_id"]:
            continue

        # Skip admin users
        if other_user.get("is_admin", False):
            continue

        # Skip connected users
        if str(other_user["_id"]) in user.get("connections", []):
            continue

        # Skip already sent requests
        already_sent = False

        for req in other_user.get("requests", []):

            if req["sender_id"] == session["user_id"]:
                already_sent = True
                break

        if already_sent:
            continue

        # Skip incoming requests
        already_received = False

        for req in user.get("requests", []):

            if req["sender_id"] == str(other_user["_id"]):
                already_received = True
                break

        if already_received:
            continue

        # --------------------------
        # MATCHING ALGORITHM
        # --------------------------

        user_need = {
            skill.strip().lower()
            for skill in user.get("skills_need", [])
        }

        user_offer = {
            skill.strip().lower()
            for skill in user.get("skills_offer", [])
        }

        other_need = {
            skill.strip().lower()
            for skill in other_user.get("skills_need", [])
        }

        other_offer = {
            skill.strip().lower()
            for skill in other_user.get("skills_offer", [])
        }

        offer_match = user_need.intersection(other_offer)

        need_match = user_offer.intersection(other_need)

        total_match = len(offer_match) + len(need_match)

        total_possible = len(user_offer) + len(user_need)

        if total_possible == 0:
            percentage = 0
        else:
            percentage = round(
                (total_match / total_possible) * 100
            )

        browse_users.append({

            "user": other_user,

            "percentage": percentage,

            "offer_match": sorted(list(offer_match)),

            "need_match": sorted(list(need_match))

        })

    # --------------------------------
    # Sorting
    # --------------------------------

    if sort == "match_asc":

        browse_users.sort(
            key=lambda x: x["percentage"]
        )

    elif sort == "name_asc":

        browse_users.sort(
            key=lambda x: x["user"].get("name", "").lower()
        )

    elif sort == "name_desc":

        browse_users.sort(
            key=lambda x: x["user"].get("name", "").lower(),
            reverse=True
        )

    else:
        # Default = Highest Match
        browse_users.sort(
            key=lambda x: x["percentage"],
            reverse=True
        )

    # --------------------------------
    # Dropdown Values
    # --------------------------------

    offer_skills = sorted(

        {

            skill

            for u in mongo.db.users.find()

            for skill in u.get("skills_offer", [])

            if skill.strip()

        }

    )

    need_skills = sorted(

        {

            skill

            for u in mongo.db.users.find()

            for skill in u.get("skills_need", [])

            if skill.strip()

        }

    )

    locations = sorted(

        {

            u.get("location")

            for u in mongo.db.users.find()

            if u.get("location")

        }

    )

    professions = sorted(

        {

            u.get("profession")

            for u in mongo.db.users.find()

            if u.get("profession")

        }

    )

    return render_template(

        "browse.html",

        users=browse_users,

        search=search,
        offer_skill=offer_skill,
        need_skill=need_skill,
        location=location,
        profession=profession,
        sort=sort,

        offer_skills=offer_skills,
        need_skills=need_skills,
        locations=locations,
        professions=professions

    )

@main.route("/profile/<user_id>")
def profile(user_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    # --------------------------------
    # Get current user
    # --------------------------------

    current_user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    # --------------------------------
    # Get profile user
    # --------------------------------

    profile_user = mongo.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not profile_user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.browse")
        )

        # --------------------------------
    # Hide admin profile from normal users
    # --------------------------------

    if (
        profile_user.get("is_admin", False)
        and not current_user.get("is_admin", False)
    ):

        flash(
            "This profile is not available.",
            "warning"
        )

        return redirect(
            url_for("main.browse")
        )

    # --------------------------------
    # Connection status
    # --------------------------------

    connected = (
        str(profile_user["_id"])
        in current_user.get("connections", [])
    )

    # --------------------------------
    # Check if request already sent
    # --------------------------------

    already_sent = False

    for req in profile_user.get("requests", []):

        if req["sender_id"] == session["user_id"]:

            already_sent = True

            break

    # --------------------------------
    # Check incoming request
    # --------------------------------

    incoming_request = False

    for req in current_user.get("requests", []):

        if req["sender_id"] == user_id:

            incoming_request = True

            break

    # --------------------------------
    # Own profile
    # --------------------------------

    is_own_profile = (
        user_id == session["user_id"]
    )

    # =================================
    # RATINGS & REVIEWS
    # =================================

    reviews = list(

        mongo.db.reviews.find({

            "reviewed_user_id": user_id

        }).sort(

            "created_at",
            -1

        )

    )

    # --------------------------------
    # Calculate average rating
    # --------------------------------

    if reviews:

        average_rating = round(

            sum(
                review["rating"]
                for review in reviews
            ) / len(reviews),

            1

        )

    else:

        average_rating = 0

    # --------------------------------
    # Render profile
    # --------------------------------

    return render_template(

        "profile.html",

        profile=profile_user,

        connected=connected,

        already_sent=already_sent,

        incoming_request=incoming_request,

        is_own_profile=is_own_profile,

        reviews=reviews,

        average_rating=average_rating

    )
   
@main.route("/add_offer_skill", methods=["POST"])
def add_offer_skill():

    if "user_id" not in session:

        return redirect(url_for("main.login"))

    skill = request.form["skill"]

    mongo.db.users.update_one(

        {
            "_id": ObjectId(session["user_id"])
        },

        {
            "$push": {

                "skills_offer": skill

            }

        }

    )

    return redirect(url_for("main.dashboard"))

@main.route("/add_need_skill", methods=["POST"])
def add_need_skill():

    if "user_id" not in session:

        return redirect(url_for("main.login"))

    skill = request.form["skill"]

    mongo.db.users.update_one(

        {
            "_id": ObjectId(session["user_id"])
        },

        {
            "$push": {

                "skills_need": skill

            }

        }

    )

    return redirect(url_for("main.dashboard"))

@main.route("/delete_offer_skill", methods=["POST"])
def delete_offer_skill():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    skill = request.form["skill"]

    mongo.db.users.update_one(

        {
            "_id": ObjectId(session["user_id"])
        },

        {
            "$pull": {
                "skills_offer": skill
            }
        }

    )

    return redirect(url_for("main.dashboard")) 

@main.route("/delete_need_skill", methods=["POST"])
def delete_need_skill():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    skill = request.form["skill"]

    mongo.db.users.update_one(

        {
            "_id": ObjectId(session["user_id"])
        },

        {
            "$pull": {
                "skills_need": skill
            }
        }

    )

    return redirect(url_for("main.dashboard"))

@main.route("/send_request", methods=["POST"])
def send_request():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    receiver_id = request.form["receiver_id"]

    sender = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    receiver = mongo.db.users.find_one({
        "_id": ObjectId(receiver_id)
    })

        # --------------------------------
    # Admin cannot participate in
    # normal connection requests
    # --------------------------------

    if sender.get("is_admin", False):

        flash(
            "Admins cannot send connection requests.",
            "warning"
        )

        return redirect(
            url_for("main.dashboard")
        )

    if receiver.get("is_admin", False):

        flash(
            "You cannot connect with the admin.",
            "warning"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # Check if request already exists
    for req in receiver.get("requests", []):

        if req["sender_id"] == str(sender["_id"]):

            flash(
                "You have already sent a request to this user.",
                "warning"
            )

            return redirect(url_for("main.dashboard"))

    request_data = {

        "sender_id": str(sender["_id"]),
        "sender_name": sender["name"],
        "sender_email": sender["email"]

    }

    # --------------------------------
    # Add Request to Receiver
    # --------------------------------

    mongo.db.users.update_one(

        {
            "_id": ObjectId(receiver_id)
        },

        {
            "$push": {
                "requests": request_data
            }
        }

    )

    # --------------------------------
    # Create Notification
    # --------------------------------

    notification = {

        "user_id": receiver_id,

        "type": "request",

        "message": f"{sender['name']} sent you a skill swap request.",

        "related_user_id": str(sender["_id"]),

        "read": False,

        "created_at": datetime.now(timezone.utc)

    }

    # --------------------------------
    # Save Notification to MongoDB
    # --------------------------------

    mongo.db.notifications.insert_one(notification)

    # --------------------------------
    # Success Message
    # --------------------------------

    flash(
        "Skill Swap Request Sent Successfully!",
        "success"
    )

    return redirect(url_for("main.dashboard"))

@main.route("/accept_request", methods=["POST"])
def accept_request():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    sender_id = request.form["sender_id"]

    receiver_id = session["user_id"]

    sender = mongo.db.users.find_one({

        "_id": ObjectId(sender_id)

    })

    receiver = mongo.db.users.find_one({

        "_id": ObjectId(receiver_id)

    })

    # --------------------------------
    # Create Connection for Receiver
    # --------------------------------

    mongo.db.users.update_one(

        {
            "_id": ObjectId(receiver_id)
        },

        {
            "$addToSet": {
                "connections": sender_id
            }
        }

    )

    # --------------------------------
    # Create Connection for Sender
    # --------------------------------

    mongo.db.users.update_one(

        {
            "_id": ObjectId(sender_id)
        },

        {
            "$addToSet": {
                "connections": receiver_id
            }
        }

    )

    # --------------------------------
    # Remove Request
    # --------------------------------

    mongo.db.users.update_one(

        {
            "_id": ObjectId(receiver_id)
        },

        {
            "$pull": {

                "requests": {
                    "sender_id": sender_id
                }

            }
        }

    )
        # --------------------------------
    # Create Skill Swap
    # --------------------------------

    swap = {

        "user1_id": sender_id,

        "user2_id": receiver_id,

        "user1_name": sender["name"],

        "user2_name": receiver["name"],

        "status": "active",

        "created_at": datetime.now(timezone.utc),

        "completed_at": None

    }

    mongo.db.swaps.insert_one(swap)

    # --------------------------------
    # Create Notification for Sender
    # --------------------------------

    mongo.db.notifications.insert_one({

        "user_id": sender_id,

        "type": "accepted",

        "message": f"{receiver['name']} accepted your skill swap request.",

        "related_user_id": receiver_id,

        "read": False,

        "created_at": datetime.now(timezone.utc)

    })

    flash(

        "Request Accepted!",

        "success"

    )

    return redirect(url_for("main.dashboard"))

# ==========================================
# SKILL SWAPS
# ==========================================

@main.route("/swaps")
def swaps():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user_id"]

    # --------------------------------
    # Get all swaps involving current user
    # --------------------------------

    swaps = list(
        mongo.db.swaps.find({
            "$or": [
                {
                    "user1_id": current_user_id
                },
                {
                    "user2_id": current_user_id
                }
            ]
        }).sort(
            "created_at",
            -1
        )
    )

    # --------------------------------
    # Prepare swap information
    # --------------------------------

    for swap in swaps:

        if swap["user1_id"] == current_user_id:

            swap["other_user_id"] = swap["user2_id"]
            swap["other_user_name"] = swap["user2_name"]

        else:

            swap["other_user_id"] = swap["user1_id"]
            swap["other_user_name"] = swap["user1_name"]

    return render_template(
        "swaps.html",
        swaps=swaps
    )

# ==========================================
# MARK SKILL SWAP AS COMPLETED
# ==========================================

@main.route("/complete_swap/<swap_id>", methods=["POST"])
def complete_swap(swap_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user_id"]

    swap = mongo.db.swaps.find_one({
        "_id": ObjectId(swap_id)
    })

    if not swap:

        flash(
            "Skill swap not found.",
            "danger"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Check user belongs to swap
    # --------------------------------

    if current_user_id not in [
        swap["user1_id"],
        swap["user2_id"]
    ]:

        flash(
            "You are not part of this skill swap.",
            "danger"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Check if already completed
    # --------------------------------

    if swap.get("status") == "completed":

        flash(
            "This skill swap is already completed.",
            "warning"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Mark as completed
    # --------------------------------

    mongo.db.swaps.update_one(

        {
            "_id": ObjectId(swap_id)
        },

        {
            "$set": {

                "status": "completed",

                "completed_at":
                    datetime.now(timezone.utc)

            }
        }

    )

    flash(
        "Skill swap marked as completed!",
        "success"
    )

    return redirect(
        url_for("main.swaps")
    )

# ==========================================
# RATE & REVIEW
# ==========================================

@main.route("/rate_swap/<swap_id>", methods=["GET", "POST"])
def rate_swap(swap_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user_id"]

    # --------------------------------
    # Get Skill Swap
    # --------------------------------

    swap = mongo.db.swaps.find_one({
        "_id": ObjectId(swap_id)
    })

    if not swap:

        flash(
            "Skill swap not found.",
            "danger"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Check user belongs to this swap
    # --------------------------------

    if current_user_id not in [
        swap["user1_id"],
        swap["user2_id"]
    ]:

        flash(
            "You are not part of this skill swap.",
            "danger"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Swap must be completed
    # --------------------------------

    if swap.get("status") != "completed":

        flash(
            "You can rate a user only after completing the skill swap.",
            "warning"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Determine reviewed user
    # --------------------------------

    if current_user_id == swap["user1_id"]:

        reviewed_user_id = swap["user2_id"]

        reviewed_user_name = swap["user2_name"]

    else:

        reviewed_user_id = swap["user1_id"]

        reviewed_user_name = swap["user1_name"]

    # --------------------------------
    # Check for existing review
    # --------------------------------

    existing_review = mongo.db.reviews.find_one({

        "swap_id": str(swap["_id"]),

        "reviewer_id": current_user_id

    })

    if existing_review:

        flash(
            "You have already reviewed this skill swap.",
            "warning"
        )

        return redirect(
            url_for("main.swaps")
        )

    # --------------------------------
    # Submit Review
    # --------------------------------

    if request.method == "POST":

        rating = request.form.get(
            "rating",
            type=int
        )

        review_text = request.form.get(
            "review",
            ""
        ).strip()

        # Validate rating

        if rating not in [1, 2, 3, 4, 5]:

            flash(
                "Please select a rating between 1 and 5 stars.",
                "danger"
            )

            return redirect(
                url_for(
                    "main.rate_swap",
                    swap_id=swap_id
                )
            )

        # --------------------------------
        # Create Review
        # --------------------------------

        review = {

            "swap_id": str(swap["_id"]),

            "reviewer_id": current_user_id,

            "reviewed_user_id": reviewed_user_id,

            "rating": rating,

            "review": review_text,

            "created_at": datetime.now(timezone.utc)

        }

        # --------------------------------
        # Save Review
        # --------------------------------

        mongo.db.reviews.insert_one(
            review
        )

        # --------------------------------
        # Notification
        # --------------------------------

        create_notification(

            reviewed_user_id,

            "review",

            f"{session['user_name']} rated you {rating} out of 5 stars.",

            current_user_id

        )

        flash(
            "Your rating and review were submitted successfully!",
            "success"
        )

        return redirect(
            url_for(
                "main.profile",
                user_id=reviewed_user_id
            )
        )

    # --------------------------------
    # Open Rating Page
    # --------------------------------

    return render_template(

        "rate_swap.html",

        swap=swap,

        reviewed_user_name=reviewed_user_name

    )

@main.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user_id = session["user_id"]

    # --------------------------------
    # Get all notifications
    # --------------------------------

    notifications = list(
        mongo.db.notifications.find({
            "user_id": user_id
        }).sort(
            "created_at",
            -1
        )
    )

    # --------------------------------
    # Make notification timestamps
    # explicitly UTC-aware
    # --------------------------------

    for notification in notifications:

        created_at = notification.get("created_at")

        if created_at:

            if created_at.tzinfo is None:

                notification["created_at"] = created_at.replace(
                    tzinfo=timezone.utc
                )

    # --------------------------------
    # Mark all unread notifications
    # as read
    # --------------------------------

    mongo.db.notifications.update_many(

        {
            "user_id": user_id,
            "read": False
        },

        {
            "$set": {
                "read": True
            }
        }

    )

    return render_template(

        "notifications.html",

        notifications=notifications

    )

@main.route("/reject_request", methods=["POST"])
def reject_request():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    sender_id = request.form["sender_id"]

    mongo.db.users.update_one(

        {

            "_id": ObjectId(session["user_id"])

        },

        {

            "$pull": {

                "requests": {

                    "sender_id": sender_id

                }

            }

        }

    )

    flash(

        "Request Rejected.",

        "warning"

    )

    return redirect(url_for("main.dashboard"))


@main.route("/cancel_connection", methods=["POST"])
def cancel_connection():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user_id"]

    connection_id = request.form["connection_id"]

    # Remove connection from current user
    mongo.db.users.update_one(

        {
            "_id": ObjectId(current_user_id)
        },

        {
            "$pull": {
                "connections": connection_id
            }
        }

    )

    # Remove current user from the other user's connections
    mongo.db.users.update_one(

        {
            "_id": ObjectId(connection_id)
        },

        {
            "$pull": {
                "connections": current_user_id
            }
        }

    )

    flash(
        "Connection Removed Successfully!",
        "success"
    )

    return redirect(url_for("main.dashboard")) 

@main.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        location = request.form["location"]
        profession = request.form["profession"]
        linkedin = request.form["linkedin"]
        github = request.form["github"]
        portfolio = request.form["portfolio"]
        bio = request.form["bio"]

        # ----------------------------
        # Skills
        # ----------------------------

        skills_offer = json.loads(
            request.form.get("skills_offer", "[]")
        )

        skills_need = json.loads(
            request.form.get("skills_need", "[]")
        )

        picture = request.files.get("profile_picture")

        # ----------------------------
        # Profile Picture Upload
        # ----------------------------

        if picture and picture.filename != "":

            if allowed_file(picture.filename):

                filename = secure_filename(picture.filename)

                extension = filename.rsplit(".", 1)[1].lower()

                filename = f'{session["user_id"]}.{extension}'

                upload_folder = os.path.join(
                    current_app.static_folder,
                    "uploads",
                    "profile_pictures"
                )

                os.makedirs(upload_folder, exist_ok=True)

                filepath = os.path.join(
                    upload_folder,
                    filename
                )

                image = Image.open(picture)

                image = image.convert("RGB")

                image.thumbnail((500, 500))

                image.save(
                    filepath,
                    quality=90
                )

                mongo.db.users.update_one(
                    {
                        "_id": ObjectId(session["user_id"])
                    },
                    {
                        "$set": {
                            "profile_picture": filename
                        }
                    }
                )

                session["profile_picture"] = filename

            else:

                flash(
                    "Only JPG, JPEG and PNG images are allowed.",
                    "danger"
                )

                return redirect(
                    url_for("main.edit_profile")
                )

        # ----------------------------
        # Update Other Profile Details
        # ----------------------------

        mongo.db.users.update_one(

            {
                "_id": ObjectId(session["user_id"])
            },

            {
                "$set": {

                    "name": name,
                    "email": email,
                    "phone": phone,
                    "location": location,
                    "profession": profession,
                    "linkedin": linkedin,
                    "github": github,
                    "portfolio": portfolio,
                    "bio": bio,

                    "skills_offer": skills_offer,
                    "skills_need": skills_need

                }
            }

        )

        session["user_name"] = name

        flash(
            "Profile Updated Successfully!",
            "success"
        )

        return redirect(
            url_for("main.my_profile")
        )

    return render_template(
        "edit_profile.html",
        user=user
    )

@main.route("/my_profile")
def my_profile():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user = mongo.db.users.find_one({

        "_id": ObjectId(session["user_id"])

    })
    print(user)

    return render_template(

        "my_profile.html",

        user=user

    )

@main.route("/notification_count")
def notification_count():

    if "user_id" not in session:
        return {
            "count": 0
        }

    count = mongo.db.notifications.count_documents({
        "user_id": session["user_id"],
        "read": False
    })

    return {
        "count": count
    }

# ==========================================
# CHAT PAGE
# ==========================================

@main.route("/chat/<user_id>")
def chat(user_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user_id"]

    # --------------------------------
    # Prevent chatting with yourself
    # --------------------------------

    if current_user_id == user_id:

        flash(
            "You cannot chat with yourself.",
            "warning"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Get current user
    # --------------------------------

    current_user = mongo.db.users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not current_user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Get other user
    # --------------------------------

    other_user = mongo.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not other_user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Admin information
    # --------------------------------

    current_user_is_admin = current_user.get(
        "is_admin",
        False
    )

    other_user_is_admin = other_user.get(
        "is_admin",
        False
    )

    # --------------------------------
    # Check chat permission
    # --------------------------------

    allowed_chat = False

    # Admin → Normal user
    if current_user_is_admin and not other_user_is_admin:

        allowed_chat = True

    # Normal user → Admin (view only)
    elif not current_user_is_admin and other_user_is_admin:

        allowed_chat = True

    # Normal user ↔ Normal user
    elif (
        not current_user_is_admin
        and not other_user_is_admin
        and user_id in current_user.get(
            "connections",
            []
        )
    ):

        allowed_chat = True

    if not allowed_chat:

        flash(
            "You cannot access this conversation.",
            "warning"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Get messages
    # --------------------------------

    messages = list(
        mongo.db.messages.find({

            "$or": [

                {
                    "sender_id": current_user_id,
                    "receiver_id": user_id
                },

                {
                    "sender_id": user_id,
                    "receiver_id": current_user_id
                }

            ]

        }).sort(
            "created_at",
            1
        )
    )

    # --------------------------------
    # Convert UTC → IST
    # --------------------------------

    ist = timezone(
        timedelta(
            hours=5,
            minutes=30
        )
    )

    for message in messages:

        created_at = message.get(
            "created_at"
        )

        if created_at:

            if created_at.tzinfo is None:

                created_at = created_at.replace(
                    tzinfo=timezone.utc
                )

            message["created_at"] = (
                created_at.astimezone(ist)
            )

        # --------------------------------
        # Existing messages without "read"
        # are treated as already read
        # --------------------------------

        message["is_unread"] = (
            message.get("read", True) is False
            and message.get("receiver_id") == current_user_id
        )

            # --------------------------------
        # Determine message ownership
        # --------------------------------

        message["is_sent"] = (
            message.get("sender_id") == current_user_id
        )

    # --------------------------------
    # Count unread incoming messages
    # --------------------------------

    unread_count = sum(
        1
        for message in messages
        if message["is_unread"]
    )

    # --------------------------------
    # Mark incoming unread messages
    # as read AFTER identifying them
    # --------------------------------

    mongo.db.messages.update_many(

        {
            "sender_id": user_id,
            "receiver_id": current_user_id,
            "read": False
        },

        {
            "$set": {
                "read": True
            }
        }

    )

    # --------------------------------
    # Prepare date separators
    # --------------------------------

    now_ist = datetime.now(ist)

    today_date = now_ist.date()

    yesterday_date = (
        today_date -
        timedelta(days=1)
    )

    previous_date = None

    for message in messages:

        message_date = message[
            "created_at"
        ].date()

        message["show_date_separator"] = (
            message_date != previous_date
        )

        if message["show_date_separator"]:

            if message_date == today_date:

                message["date_label"] = "Today"

            elif message_date == yesterday_date:

                message["date_label"] = "Yesterday"

            else:

                message["date_label"] = (
                    message["created_at"].strftime(
                        "%d %B %Y"
                    )
                )

        else:

            message["date_label"] = ""

        previous_date = message_date

    # --------------------------------
    # Find first unread message
    # --------------------------------

    unread_marker_added = False

    for message in messages:

        if message["is_unread"] and not unread_marker_added:

            message["show_unread_separator"] = True

            unread_marker_added = True

        else:

            message["show_unread_separator"] = False

    # --------------------------------
    # Normal user viewing admin =
    # read-only
    # --------------------------------

    read_only = (
        not current_user_is_admin
        and other_user_is_admin
    )

    # --------------------------------
    # Open chat page
    # --------------------------------

    return render_template(

        "chat.html",

        other_user=other_user,

        messages=messages,

        today_date=today_date,

        yesterday_date=yesterday_date,

        unread_count=unread_count,

        read_only=read_only

    )
# ==========================================
# SEND MESSAGE
# ==========================================

@main.route("/send_message/<receiver_id>", methods=["POST"])
def send_message(receiver_id):

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    sender_id = session["user_id"]

    # --------------------------------
    # Prevent messaging yourself
    # --------------------------------

    if sender_id == receiver_id:

        flash(
            "You cannot message yourself.",
            "warning"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Get users
    # --------------------------------

    sender = mongo.db.users.find_one({
        "_id": ObjectId(sender_id)
    })

    receiver = mongo.db.users.find_one({
        "_id": ObjectId(receiver_id)
    })

    if not sender or not receiver:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    sender_is_admin = sender.get(
        "is_admin",
        False
    )

    receiver_is_admin = receiver.get(
        "is_admin",
        False
    )

    # --------------------------------
    # Messaging permissions
    # --------------------------------

    allowed_to_send = False

    # Admin can message normal user
    if sender_is_admin and not receiver_is_admin:

        allowed_to_send = True

    # Normal user can message another
    # normal user only when connected
    elif (
        not sender_is_admin
        and not receiver_is_admin
        and receiver_id in sender.get(
            "connections",
            []
        )
    ):

        allowed_to_send = True

    # Normal user → Admin is NOT allowed
    elif not sender_is_admin and receiver_is_admin:

        flash(
            "You cannot reply to an admin.",
            "warning"
        )

        return redirect(
            url_for(
                "main.chat",
                user_id=receiver_id
            )
        )

    if not allowed_to_send:

        flash(
            "You are not allowed to send messages to this user.",
            "warning"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Get message
    # --------------------------------

    message_text = request.form.get(
        "message",
        ""
    ).strip()

    if not message_text:

        flash(
            "Message cannot be empty.",
            "warning"
        )

        return redirect(
            url_for(
                "main.chat",
                user_id=receiver_id
            )
        )

    # --------------------------------
    # Create message
    # --------------------------------

    message_data = {

    "sender_id": sender_id,

    "receiver_id": receiver_id,

    "message": message_text,

    "read": False,

    "created_at": datetime.now(
        timezone.utc
    )

}
    # --------------------------------
    # Save message
    # --------------------------------

    mongo.db.messages.insert_one(
        message_data
    )

    # --------------------------------
    # Create notification
    # --------------------------------

    notification = {

        "user_id": receiver_id,

        "type": "message",

        "message":
            f"{sender['name']} sent you a new message.",

        "related_user_id": sender_id,

        "read": False,

        "created_at":
            datetime.now(timezone.utc)

    }

    mongo.db.notifications.insert_one(
        notification
    )

    # --------------------------------
    # Return to chat
    # --------------------------------

    return redirect(
        url_for(
            "main.chat",
            user_id=receiver_id
        )
    )
# ==========================================
# MESSAGES / CONVERSATION LIST
# ==========================================

# ==========================================
# MESSAGES / CONVERSATION LIST
# ==========================================

@main.route("/messages")
def messages():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user_id"]

    # --------------------------------
    # Get current user
    # --------------------------------

    current_user = mongo.db.users.find_one({
        "_id": ObjectId(current_user_id)
    })

    if not current_user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    current_user_is_admin = current_user.get(
        "is_admin",
        False
    )

    # --------------------------------
    # Build conversation user IDs
    # --------------------------------

    conversation_ids = set(
        current_user.get(
            "connections",
            []
        )
    )

    # --------------------------------
    # Admin:
    # Can see all normal users
    # --------------------------------

    if current_user_is_admin:

        normal_users = mongo.db.users.find({

            "is_admin": {
                "$ne": True
            }

        })

        for normal_user in normal_users:

            conversation_ids.add(
                str(normal_user["_id"])
            )

    # --------------------------------
    # Normal user:
    # Add admin(s) only when a
    # conversation exists
    # --------------------------------

    else:

        admin_users = mongo.db.users.find({

            "is_admin": True

        })

        for admin_user in admin_users:

            admin_id = str(
                admin_user["_id"]
            )

            existing_message = mongo.db.messages.find_one({

                "$or": [

                    {
                        "sender_id": current_user_id,
                        "receiver_id": admin_id
                    },

                    {
                        "sender_id": admin_id,
                        "receiver_id": current_user_id
                    }

                ]

            })

            if existing_message:

                conversation_ids.add(
                    admin_id
                )

    conversations = []

    # --------------------------------
    # Build conversations
    # --------------------------------

    for connection_id in conversation_ids:

        connection_user = mongo.db.users.find_one({

            "_id": ObjectId(connection_id)

        })

        if not connection_user:

            continue

        # --------------------------------
        # Latest message
        # --------------------------------

        latest_message = mongo.db.messages.find_one(

            {

                "$or": [

                    {
                        "sender_id":
                            current_user_id,

                        "receiver_id":
                            connection_id
                    },

                    {
                        "sender_id":
                            connection_id,

                        "receiver_id":
                            current_user_id
                    }

                ]

            },

            sort=[
                (
                    "created_at",
                    -1
                )
            ]

        )

        conversations.append({

            "user":
                connection_user,

            "latest_message":
                latest_message

        })

    # --------------------------------
    # Sort by latest message
    # --------------------------------

    conversations.sort(

        key=lambda conversation:

        conversation["latest_message"]["created_at"]

        if conversation["latest_message"]

        else datetime.min.replace(
            tzinfo=timezone.utc
        ),

        reverse=True

    )

    return render_template(

        "messages.html",

        conversations=conversations

    )

# ==========================================
# ADMIN DASHBOARD
# ==========================================

@main.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect(url_for("main.login"))

    current_user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    if not current_user or not current_user.get(
        "is_admin",
        False
    ):

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # Dashboard is now the admin page
    return redirect(
        url_for("main.dashboard")
    )

# ==========================================
# ADMIN - DELETE USER
# ==========================================

@main.route("/admin/delete_user/<user_id>", methods=["POST"])
def admin_delete_user(user_id):

    # --------------------------------
    # Check login
    # --------------------------------

    if "user_id" not in session:
        return redirect(
            url_for("main.login")
        )

    # --------------------------------
    # Get current user
    # --------------------------------

    current_user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    # --------------------------------
    # Check admin permission
    # --------------------------------

    if not current_user or not current_user.get(
        "is_admin",
        False
    ):

        flash(
            "Access denied. Admins only.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Get user to delete
    # --------------------------------

    user_to_delete = mongo.db.users.find_one({
        "_id": ObjectId(user_id)
    })

    if not user_to_delete:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Prevent deleting an admin
    # --------------------------------

    if user_to_delete.get("is_admin", False):

        flash(
            "Admin accounts cannot be deleted.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Prevent accidental self-delete
    # --------------------------------

    if user_id == session["user_id"]:

        flash(
            "You cannot delete your own account from the admin panel.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )

    # --------------------------------
    # Delete user's profile picture
    # --------------------------------

    profile_picture = user_to_delete.get(
        "profile_picture",
        "default.png"
    )

    if profile_picture != "default.png":

        upload_folder = os.path.join(
            current_app.static_folder,
            "uploads",
            "profile_pictures"
        )

        profile_picture_path = os.path.join(
            upload_folder,
            profile_picture
        )

        if os.path.exists(
            profile_picture_path
        ):

            os.remove(
                profile_picture_path
            )

    # --------------------------------
    # Remove user from connections
    # --------------------------------

    mongo.db.users.update_many(

        {},

        {
            "$pull": {
                "connections": user_id
            }
        }

    )

    # --------------------------------
    # Remove requests sent by user
    # --------------------------------

    mongo.db.users.update_many(

        {},

        {
            "$pull": {
                "requests": {
                    "sender_id": user_id
                }
            }
        }

    )

    # --------------------------------
    # Delete messages involving user
    # --------------------------------

    mongo.db.messages.delete_many({

        "$or": [

            {
                "sender_id": user_id
            },

            {
                "receiver_id": user_id
            }

        ]

    })

    # --------------------------------
    # Delete notifications involving user
    # --------------------------------

    mongo.db.notifications.delete_many({

        "$or": [

            {
                "user_id": user_id
            },

            {
                "related_user_id": user_id
            }

        ]

    })

    # --------------------------------
    # Delete skill swaps involving user
    # --------------------------------

    mongo.db.swaps.delete_many({

        "$or": [

            {
                "user1_id": user_id
            },

            {
                "user2_id": user_id
            }

        ]

    })

    # --------------------------------
    # Delete reviews involving user
    # --------------------------------

    mongo.db.reviews.delete_many({

        "$or": [

            {
                "reviewer_id": user_id
            },

            {
                "reviewed_user_id": user_id
            }

        ]

    })

        # --------------------------------
    # Mark related reports as completed
    # --------------------------------

    mongo.db.reports.update_many(

        {
            "reported_user_id": user_id,
            "status": "pending"
        },

        {
            "$set": {

                "status": "completed",

                "resolution": "User deleted by admin",

                "resolved_at": datetime.now(timezone.utc)

            }
        }

    )

    # --------------------------------
    # Delete user document
    # --------------------------------

    mongo.db.users.delete_one({

        "_id": ObjectId(user_id)

    })

    # --------------------------------
    # Success message
    # --------------------------------

    flash(
        f"{user_to_delete['name']} was deleted successfully.",
        "success"
    )

    return redirect(
        url_for("main.dashboard")
    )

# ==========================================
# REPORT USER
# ==========================================

@main.route("/report_user/<user_id>", methods=["GET", "POST"])
def report_user(user_id):

    # --------------------------------
    # Check login
    # --------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("main.login")
        )

    current_user_id = session["user_id"]

    # --------------------------------
    # Prevent reporting yourself
    # --------------------------------

    if current_user_id == user_id:

        flash(
            "You cannot report yourself.",
            "warning"
        )

        return redirect(
            url_for(
                "main.profile",
                user_id=user_id
            )
        )

    # --------------------------------
    # Get current user
    # --------------------------------

    current_user = mongo.db.users.find_one({

        "_id": ObjectId(current_user_id)

    })

    # --------------------------------
    # Get reported user
    # --------------------------------

    reported_user = mongo.db.users.find_one({

        "_id": ObjectId(user_id)

    })

    if not reported_user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("main.browse")
        )

    # --------------------------------
    # Admin cannot be reported
    # --------------------------------

    if reported_user.get("is_admin", False):

        flash(
            "The admin cannot be reported.",
            "warning"
        )

        return redirect(
            url_for(
                "main.profile",
                user_id=user_id
            )
        )

    # --------------------------------
    # Prevent duplicate pending report
    # --------------------------------

    existing_report = mongo.db.reports.find_one({

        "reporter_id": current_user_id,

        "reported_user_id": user_id,

        "status": "pending"

    })

    if existing_report:

        flash(
            "You have already reported this user.",
            "warning"
        )

        return redirect(
            url_for(
                "main.profile",
                user_id=user_id
            )
        )

    # --------------------------------
    # Submit report
    # --------------------------------

    if request.method == "POST":

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        details = request.form.get(
            "details",
            ""
        ).strip()

        allowed_reasons = [

            "Spam",
            "Harassment",
            "Fake Profile",
            "Inappropriate Content",
            "Scam",
            "Other"

        ]

        # --------------------------------
        # Validate reason
        # --------------------------------

        if reason not in allowed_reasons:

            flash(
                "Please select a valid report reason.",
                "danger"
            )

            return redirect(
                url_for(
                    "main.report_user",
                    user_id=user_id
                )
            )

        # --------------------------------
        # Validate details
        # --------------------------------

        if not details:

            flash(
                "Please provide some details about the report.",
                "warning"
            )

            return redirect(
                url_for(
                    "main.report_user",
                    user_id=user_id
                )
            )

        # --------------------------------
        # Create report
        # --------------------------------

        report = {

            "reporter_id": current_user_id,

            "reporter_name": current_user["name"],

            "reported_user_id": user_id,

            "reported_user_name": reported_user["name"],

            "reason": reason,

            "details": details,

            "status": "pending",

            "created_at": datetime.now(timezone.utc)

        }

        # --------------------------------
        # Save report
        # --------------------------------

        mongo.db.reports.insert_one(
            report
        )

        flash(
            "Report submitted successfully.",
            "success"
        )

        return redirect(
            url_for(
                "main.profile",
                user_id=user_id
            )
        )

    # --------------------------------
    # Display report page
    # --------------------------------

    return render_template(

        "report_user.html",

        reported_user=reported_user

    )

@main.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("main.home"))