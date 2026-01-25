from flask import Flask, request, redirect, session, render_template, jsonify
import json, os ,time ,requests,uuid,base64, random
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from PIL import Image
import io
import google.generativeai as genai
from PIL import Image
import io
from dotenv import load_dotenv
import threading
from io import BytesIO

load_dotenv()

SMTP_SERVER = os.environ.get("SMTP_SERVER_ENV", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT_ENV", 587))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL_ENV", "teamhornbills@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD_ENV", "fmop uljk nswz osvd")

# Useful Functions

def now():
    return datetime.now()

def today():
    return datetime.today()

def load():
    path = "Users.Json" 
    if not os.path.exists(path): return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if data else {}
    except: return {}

def load_posts():
    path = "static/posts.json"
    if not os.path.exists(path): return [] # Return empty list if missing
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if data else []
    except: return []

def load_requests():
    path = "static/requests.json"
    if not os.path.exists(path): return [] # Return empty list if missing
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if data else []
    except: return []

def create_id():
    A1 = str(uuid.uuid4()) 
    uids = load()
    posts = load_posts()
    requests = load_requests()
    all = uids.keys()
    
    all2 = []
    for i in range(len(posts)):
        all2.append(posts[i])
        print(posts[i])
    
    all3 = []
    for i in range(len(requests)):
        all2.append(requests[i])
        print(requests[i])


    if A1 in all or A1 in all2 or A1 in all3:
        return create_id()
    else:
        return A1

def load_claims():
    path = "static/claims.json"
    if not os.path.exists(path):
        return {} # Returns Dictionary { "post_id": ["user_id_1", "user_id_2"] }
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except:
        return {}

def load_contacts():
    path = "static/contacts.json"
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except:
        return {}



keys_string = os.getenv("STABILITY_KEYS")
if keys_string:
    API_KEYS = [k.strip() for k in keys_string.split(",") if k.strip()]
else:
    API_KEYS = []

if not API_KEYS:
    print("⚠️ WARNING: No API keys found in .env file!")


current_key_index = 0

def get_next_key():
    global current_key_index
    if current_key_index < len(API_KEYS) - 1:
        current_key_index += 1
        print(f"🔄 Switching to Key #{current_key_index + 1}...")
        return API_KEYS[current_key_index]
    else:
        print("💀 ALL KEYS EXHAUSTED! Cannot generate images.")
        return None
    
def compress_and_save(image_data, output_path, quality=60):
    try:
        img = Image.open(BytesIO(image_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(output_path, "JPEG", quality=quality, optimize=True)
        print(f"📦 Saved: {os.path.basename(output_path)}")
    except Exception as e:
        print(f"❌ Compression Error: {e}")

def generate_all_variations_stability(post_id, description, source_image_path):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image"
    output_dir = os.path.dirname(source_image_path)
    
    # --- STEP 0: PREPARE IMAGE ---
    resized_path = os.path.join(output_dir, "temp_resized.jpg")
    try:
        with Image.open(source_image_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
            img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            img.save(resized_path, "JPEG")
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        return

    # --- TASKS SETUP (Optimized for REALISM) ---
    # We use specific physical traits that owners notice, not "styles"
    tasks = [
        # 1. The Clone (High Fidelity)
        {"file": "1.jpg", "strength": 0.85, "prompt_suffix": "exact replica, hyper-realistic texture, perfect condition"},
        
        # 2. Material Change (Subtle)
        {"file": "2.jpg", "strength": 0.52, "prompt_suffix": "slightly different material finish, matte texture instead of glossy"},
        
        # 3. Wear & Tear (The Trap) -> Owners know if their item is new or scratched
        {"file": "3.jpg", "strength": 0.55, "prompt_suffix": "visible surface scratches, worn edges, used condition, dust particles"},
        
        # 4. Color Nuance
        {"file": "4.jpg", "strength": 0.53, "prompt_suffix": "slightly darker color shade, different lighting reflection"},
        
        # 5. Manufacturing Variation
        {"file": "5.jpg", "strength": 0.54, "prompt_suffix": "minor manufacturing defect, slightly warped shape, different button placement"},
        
        # 6. The "Clean" Decoy
        {"file": "6.jpg", "strength": 0.55, "prompt_suffix": "brand new condition, polished surface, no scratches, studio lighting"},
    ]

    global current_key_index
    
    if not API_KEYS:
        print("❌ No Keys available. Skipping generation.")
        return

    active_key = API_KEYS[current_key_index]

    for task in tasks:
        target_file = task["file"]
        print(f"🎨 Generating {target_file}...")
        
        success = False
        while not success:
            try:
                headers = {
                    "Authorization": f"Bearer {active_key}",
                    "Accept": "application/json"
                }

                with open(resized_path, "rb") as f:
                    files = {"init_image": f}
                    random_seed = random.randint(0, 4294967295)
                    
                    # ENHANCED PROMPT LOGIC
                    data = {
                        "init_image_mode": "IMAGE_STRENGTH",
                        "image_strength": task["strength"],
                        
                        # POSITIVE PROMPT: Focuses on "In-Painting" the item only
                        "text_prompts[0][text]": (
                            f"A photorealistic macro shot of {description}, {task['prompt_suffix']}, "
                            "preserving the exact original background, identical lighting, 8k resolution, highly detailed"
                        ),
                        "text_prompts[0][weight]": 1,
                        
                        # NEGATIVE PROMPT: Prevents "Cartoonification" and Background shifting
                        "text_prompts[1][text]": (
                            "changing background, shifting shadows, floating objects, "
                            "blurry, low quality, cartoon, 3d render, illustration, "
                            "bad anatomy, distorted text, watermark, signature, "
                            "extra fingers, deformed shape"
                        ),
                        "text_prompts[1][weight]": -1,
                        
                        "cfg_scale": 8, # Sharp adherence to prompt
                        "samples": 1,
                        "steps": 40,    # More steps = More realism
                        "seed": random_seed
                    }
                    
                    response = requests.post(url, headers=headers, files=files, data=data)

                if response.status_code == 200:
                    image_data = base64.b64decode(response.json()["artifacts"][0]["base64"])
                    save_path = os.path.join(output_dir, target_file)
                    compress_and_save(image_data, save_path, quality=50)
                    success = True 
                
                elif response.status_code in [400, 401, 402, 403, 429]: 
                    print(f"⚠️ Key Error ({response.status_code}). Switching keys...")
                    new_key = get_next_key()
                    if new_key:
                        active_key = new_key 
                    else:
                        print("❌ No more keys left!")
                        break 
                else:
                    print(f"❌ Server Error: {response.status_code}")
                    break

            except Exception as e:
                print(f"❌ Connection Error: {e}")
                break
        
        if not success and not os.path.exists(os.path.join(output_dir, target_file)):
            import shutil
            shutil.copy(resized_path, os.path.join(output_dir, target_file))
            print(f"⚠️ Used fallback image for {target_file}")
        
        time.sleep(2) 

    if os.path.exists(resized_path):
        try:
            os.remove(resized_path)
        except:
            pass


# App starts

app = Flask(__name__)
app.secret_key = os.environ['SESSION_KEY']

# Ensure storage folders exist on startup
os.makedirs("static/posts", exist_ok=True)
os.makedirs("static/requests", exist_ok=True)
os.makedirs("static/proofs", exist_ok=True)

# Ensure JSON files exist with empty data if missing
if not os.path.exists("static/posts.json"):
    with open("static/posts.json", "w") as f: json.dump([], f)

if not os.path.exists("static/requests.json"):
    with open("static/requests.json", "w") as f: json.dump([], f)


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route('/get_user_name')
def get_user_name():
    target_uid = request.args.get('uid')
    users = load()
    
    # Check if UID exists in the dictionary
    if target_uid in users:
        # Return only the name, keeping email/password safe
        return jsonify({"name": users[target_uid]['name']})
    
    return jsonify({"name": "Community Member"})


# When Session not Active that is used is not logged In

@app.route("/", methods =["POST", "GET"])
def firstview():
        if "uid" in session:
            data = load()
            name = None
            email = None
            for uid, others in data.items():
                if uid == session["uid"]:
                    name = others["name"]
                    email = others["email"]
                else:
                    pass    
                
            return render_template("Base/main_page.html", 
                            user_name=name, 
                            user_email=email)
        else:
            return redirect("/login")
      

@app.route("/login",methods =["POST","GET"])
def login():
    if "uid" in session:         
        return redirect("/main_page")
    else:
        return render_template("loginXsignup/Login.html")


@app.route("/Entry", methods =["POST", "GET"])     ## Execute Login ##
def Checking():

    if "uid" in session:
        return redirect("/main_page")
    else:
        input_data = request.form                         
        ldata = load()
        for uid,others in ldata.items():
            if input_data["username"]==others["username"]:
                if input_data["password"] == others["password"]: 

                    ## Starting the Login session with User ID

                    session.permanent = True
                    session["uid"] = uid
                    return render_template("loginXsignup/CrtLogin.html")
                
                else:
                    ## Wrong Password
                    return render_template("loginXsignup/Wrong_credentials.html")
            else:
                pass        
        return render_template("loginXsignup/Wrong_credentials.html")
            

@app.route("/SignUp", methods =["POST", "GET"])
def signup():
    
    if "uid" not in session:
        return render_template("loginXsignup/SignUp.html")       ####
    else:
        return redirect("/main_page")


@app.route("/ProcessSignUp", methods = ["POST","GET"])
def process():

    if "uid" in session:
        return redirect("/main_page")
    else:
        info = request.form
        data = load()
        ## Checking if username already exists
        for uid,others in data.items():
            if info["username"]==others["username"]:
                return render_template("loginXsignup/UAExist.html")
            else:
                pass  

        new_user = {"username":f"{info['username']}",
                    "name":f"{info['full_name']}",
                    "email":f"{info['email']}",
                    "password":f"{info['password']}"}          
        new_uid = str(create_id())
        
        data[new_uid] = new_user
        with open("Users.Json","w") as f:
            json.dump(data,f, indent = 4)
        return render_template("loginXsignup/UserCreated.html")    
    


@app.route("/logout")
def logout():
    if "uid" in session:  
        session.clear()   
        return render_template("loginXsignup/LoggedOut.html")
    else:    
        return redirect("/")


## Code for the Main Site where user can go only after Login

@app.route("/main_page", methods =["POST", "GET"])
def dashboard():
    data = load()
    name = None
    email = None
    for uid, others in data.items():
        if uid == session["uid"]:
            name = others["name"]
            email = others["email"]
        else:
            pass    
        
    return render_template("Base/main_page.html", 
                    user_name=name, 
                    user_email=email,
                    user_id = session["uid"])


@app.route("/about",methods = ["POST","GET"])
def about():
    if "uid" not in session:
        return redirect("/")
    else:
        return render_template("Base/about.html")


@app.route("/create-found", methods = ["POST", "GET"])
def found_item():
    if "uid" not in session:
        return redirect("/")
    else:
        return render_template("Base/found_item.html")


@app.route("/create-lost", methods = ["POST", "GET"])
def lost_item():
    if "uid" not in session:
        return redirect("/")
    else:
        return render_template("Base/lost_item.html")


#######################################################

# CONFIG
UPLOAD_FOLDER = 'static/posts'

@app.route('/submit_found', methods=['POST'])
def submit_found():
    if "uid" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    # 1. Extract Text Data
    title = request.form.get('title')
    category = request.form.get('category')
    location = request.form.get('location')
    description = request.form.get('description')
    
    questions_json = request.form.get('questions_json')
    try:
        questions_list = json.loads(questions_json) if questions_json else []
    except:
        questions_list = []

    # 2. Create ID & Folder
    new_id = str(uuid.uuid4())
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    post_folder = os.path.join(UPLOAD_FOLDER, str(new_id))
    os.makedirs(post_folder, exist_ok=True)

    # 3. Handle File Upload (The "Source")
    file = request.files.get('file')
    
    if file and file.filename != '':
        # We save the user's real photo as 'source.jpg'
        # This file is NEVER shown to the public.
        source_path = os.path.join(post_folder, "source.jpg")
        file.save(source_path)
        
        # 4. Start AI Generation in Background
        # This will create 1.jpg (Clone) and 2-6.jpg (Distractors)
        thread = threading.Thread(
            target=generate_all_variations_stability, 
            args=(new_id, description, source_path)
        )
        thread.start()

    # 5. Save Post Data
    new_post = {
        "id": new_id,
        "user_id": session["uid"],
        "title": title,
        "category": category,
        "location": location,
        "time": time_now,
        "description": description,
        "questions": questions_list,
        "type": "Found",
        # CRITICAL: We hardcode 'jpg' because the AI output is always jpg
        "ext": "jpg" 
    }
    
    posts = load_posts()
    posts.append({new_id: new_post})
    
    with open("static/posts.json", "w") as f:
        json.dump(posts, f, indent=4)
    
    return jsonify({"status": "success", "message": "Post saved successfully"}), 200


@app.route('/api/generate_questions', methods=['POST'])
def generate_questions_api():
    if "uid" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Get Data
        image_file = request.files.get('image')
        title = request.form.get('title', 'Found Item')
        desc = request.form.get('description', '')

        if not image_file:
            return jsonify({"error": "No image uploaded"}), 400

        
        # Read file into RAM
        img_bytes = image_file.read()
        
        # Convert to Pillow Image
        image = Image.open(io.BytesIO(img_bytes))

        load_dotenv()
        api_key = os.getenv('GENAI_API_KEY')
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
            ROLE: You are an expert Lost & Found verification agent. Your goal is to generate security questions to verify ownership of a found item.
            
            INPUT DATA:
            - Item Title: "{title}"
            - User Description: "{desc}"
            - Image: [Attached]

            TASK:
            Analyze the image and text to generate 5-7 specific "Ownership Challenge" questions.
            
            CRITICAL RULES FOR QUESTIONS:
            1. VISIBLE BUT IGNORED: Focus on details a casual observer might miss but an owner knows (e.g., "Where is the dent located?" instead of "Is there a dent?").
            2. CONTENT vs. APPEARANCE: If it's a bag/wallet, ask about contents visible in the image (if open) or specific external pockets.
            3. NO IMPOSSIBLE DETAILS: Do NOT ask for serial numbers or tiny text unless they are huge and obvious. The owner doesn't memorize serial numbers.
            4. MULTIPLE CHOICE STYLE: Frame questions that require specific knowledge, not just "Yes/No".
            
            BAD QUESTION EXAMPLES (AVOID):
            - "Is it blue?" (Too obvious, anyone can see the photo)
            - "What is the serial number?" (Owner won't know)
            - "Is it old?" (Subjective)

            GOOD QUESTION EXAMPLES (USE THESE TYPES):
            - "There is a sticker on the back. What character or text is on it?"
            - "One of the zippers has a unique keychain attached. What shape is it?"
            - "There is a specific wear pattern on the corner. Which corner is most damaged?"
            - "What is the specific brand logo color on the front tag?"

            OUTPUT FORMAT:
            Return ONLY a raw JSON list of strings. No markdown, no "json" tags.
            Example: ["Question 1?", "Question 2?", "Question 3?"]"""

        response = model.generate_content([prompt, image])
        
        # Parse Response
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response.replace("```json", "").replace("```", "")
        
        questions = json.loads(text_response)
        
        return jsonify({"questions": questions})

    except Exception as e:
        print(f"Gemini Error: {e}")
        return jsonify({"questions": ["What is the specific color?", "Are there any distinct marks?"]})

#######################################################

@app.route('/submit_lost', methods=['POST'])
def submit_lost():
    if "uid" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    # 1. Gather Data
    title = request.form['title']
    category = request.form['category']
    description = request.form['description']
    location = request.form.get('location', 'Unknown')
    
    # Time Logic
    time_last_seen = request.form['time_last_seen']
    formatted_time = time_last_seen.replace("T", " ")
    
    # 2. Check for Duplicate Description
    requests_data = load_requests() # Ensure this function reads static/requests.json
    input_desc_clean = description.strip().lower()
    
    for group in requests_data:
        for item in group.values():
            existing_desc = item.get('description', '').strip().lower()
            if existing_desc == input_desc_clean:
                return jsonify({"status": "error", "message": "Description already exists."}), 400

    # 3. Create ID
    req_id = str(uuid.uuid4())

    # 4. Image Logic & Folder Creation
    file = request.files.get('image')
    file_ext = None # Default to None if no image

    if file and file.filename != '':
        # A. Detect Extension
        if '.' in file.filename:
            file_ext = file.filename.rsplit('.', 1)[1].lower()
        else:
            file_ext = 'jpg' # Fallback
        
        # B. Create Folder: static/requests/{req_id}
        # We ensure we are stepping into the 'requests' subfolder, not 'posts'
        save_folder = os.path.join('static', 'requests', req_id)
        os.makedirs(save_folder, exist_ok=True)
        
        # C. Save Image as 1.ext
        file.save(os.path.join(save_folder, f'1.{file_ext}'))

    # 5. Create Object (INCLUDE EXTENSION)
    new_request = {
        "UID": session.get("uid", "guest"),
        "title": title,
        "category": category,
        "description": description,
        "location": location,
        "time": formatted_time,
        "type": "Request",
        "ext": file_ext  # <--- CRITICAL: Main page needs this to know image exists
    }

    # 6. Save to JSON
    requests_data.append({req_id: new_request})
    
    with open("static/requests.json", "w") as f:
        json.dump(requests_data, f, indent=4)

    return jsonify({"status": "success", "message": "Request saved"}), 200

#######################################################

@app.route('/found-details')
def found_details():

    if "uid" not in session:
        return redirect('/login')
    else:
        return render_template('Base/found_details.html')



### Here is the mailing system

# Helper to load claims safely
def load_claims():
    try:
        if not os.path.exists("static/claims.json"):
            return {}
        with open("static/claims.json", "r") as f:
            return json.load(f)
    except:
        return {}

# THE MISSING LINK: This tells the HTML button to disable itself
@app.route('/check_claim_status')
def check_claim_status():
    if "uid" not in session: 
        return jsonify({"claimed": False})
    
    post_id = request.args.get('post_id')
    user_id = session["uid"]
    
    claims = load_claims()
    
    # Check if YOUR user ID is inside the list for THIS post ID
    if post_id in claims and user_id in claims[post_id]:
        return jsonify({"claimed": True})
    
    return jsonify({"claimed": False})


@app.route('/process_claim', methods=['POST'])
def process_claim():
    if "uid" not in session: return redirect('/login')

    # --- 1. DATA EXTRACTION ---
    user_id = session['uid']
    post_id = request.form.get('post_id')
    founder_uid = request.form.get('founder_uid')
    post_title = request.form.get('post_title')
    extra_details = request.form.get('extra_details')
    selected_image = request.form.get('selected_image', '')

    # --- 2. DUPLICATE CHECK (Stop Double Claims) ---
    claims = load_claims()
    # If the item exists in claims AND your user ID is in the list
    if post_id in claims and user_id in claims[post_id]:
        print(f"🚫 BLOCKED: User {user_id} tried to claim {post_id} twice.")
        # Stop here and tell them
        return "<h3>You have already submitted a claim for this item.</h3><a href='/main_page'>Go Back</a>", 400

    # --- 3. FORMAT SECURITY ANSWERS ---
    answers = []
    for key in request.form:
        if key.startswith("answer_"):
            idx = key.split("_")[1]
            question = request.form.get(f"question_{idx}")
            ans = request.form.get(key)
            answers.append(f"<b>Q: {question}</b><br>A: {ans}")
    answer_html = "<br><br>".join(answers)

    # --- 4. IMAGE MATCHING LOGIC ---
    is_image_correct = False
    if selected_image.strip().startswith("1.") or "/1." in selected_image:
        is_image_correct = True
    
    if is_image_correct:
        image_status_msg = "<span style='color:green; font-weight:bold;'>✅ MATCHED</span> (They identified the original photo)"
    else:
        image_status_msg = "<span style='color:red; font-weight:bold;'>❌ MIS-MATCHED</span> (They picked a fake image)"

    # --- 5. SAVE TO DATABASE ---
    if post_id not in claims: claims[post_id] = []
    claims[post_id].append(user_id)
    
    try:
        with open("static/claims.json", "w") as f:
            json.dump(claims, f, indent=4)
    except Exception as e:
        print(f"Database Save Error: {e}")

    # --- 6. SEND FULL EMAIL (Wrapped in Try/Except) ---
    try:
        users = load()
        founder_data = users.get(founder_uid, {})
        founder_email = founder_data.get('email')
        
        # Get Claimer Info
        claimer_data = users.get(user_id, {})
        claimer_email = claimer_data.get('email', 'Unknown')
        claimer_name = claimer_data.get('name', 'Unknown User')

        if founder_email:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = founder_email
            msg['Subject'] = f"🔔 Claim Request: {post_title}"

            # FULL HTML BODY
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #587363;">New Claim for '{post_title}'</h2>
                
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
                    <h3>👤 Claimer: {claimer_name}</h3>
                    <p>Email: <a href="mailto:{claimer_email}">{claimer_email}</a></p>
                </div>
                
                <div style="margin-top: 20px;">
                    <h3>🖼️ Image Verification Result:</h3>
                    <p style="font-size: 1.1rem;">{image_status_msg}</p>
                </div>
                
                <div style="margin-top: 20px;">
                    <h3>❓ Security Answers</h3>
                    {answer_html}
                </div>
                
                <div style="margin-top: 20px; background: #fffbe6; padding: 15px; border-left: 4px solid #ffe58f;">
                    <h3>📝 Message from Claimer</h3>
                    <p>"{extra_details}"</p>
                </div>
                <hr>
                <p>Reply directly to this email to contact the claimer.</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))

            # SEND
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) # 20 second timeout
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"✅ Full Email successfully sent to {founder_email}")
        else:
            print(f"⚠️ User {founder_uid} has no email address.")

    except Exception as e:
        print(f"❌ Email Failed (But App Continued): {e}")
        pass

    return redirect('/main_page')

##########################


@app.route('/lost-details')
def lost_details():
    if "uid" not in session: 
        return redirect('/login')
    
    # Assuming this file is also in Base folder for consistency
    return render_template('Base/lost_details.html')


@app.route('/check_contact_status')
def check_contact_status():
    if "uid" not in session: return jsonify({"contacted": False})
    
    post_id = request.args.get('post_id')
    user_id = session["uid"]
    contacts = load_contacts()
    
    # Check if this user has ALREADY contacted the owner for this post
    if post_id in contacts and user_id in contacts[post_id]:
        return jsonify({"contacted": True})
    
    return jsonify({"contacted": False})


@app.route('/process_found_report', methods=['POST'])
def process_found_report():
    if "uid" not in session: return redirect('/login')

    try:
        finder_uid = session['uid']
        post_id = request.form.get('post_id')
        requester_uid = request.form.get('requester_uid')
        post_title = request.form.get('post_title')
        message = request.form.get('message')

        # --- DATABASE LOGIC (Save the contact) ---
        contacts = load_contacts()
        if post_id not in contacts: contacts[post_id] = []
        if finder_uid not in contacts[post_id]:
            contacts[post_id].append(finder_uid)
            with open("static/contacts.json", "w") as f:
                json.dump(contacts, f, indent=4)

        # --- EMAIL LOGIC (Wrapped to never crash) ---
        users = load()
        owner_data = users.get(requester_uid, {})
        owner_email = owner_data.get('email')

        if owner_email:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = owner_email
            msg['Subject'] = f"🙌 Found: {post_title}"
            msg.attach(MIMEText(f"Someone found your item!\n\nMessage: {message}", 'plain'))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"✅ Email sent to {owner_email}")
        else:
            print(f"⚠️ Owner {requester_uid} has no email. Skipping.")

    except Exception as e:
        print(f"❌ Email Error (App continued safely): {e}")
        pass

    return redirect('/main_page')


app.run(host = "0.0.0.0", port = 81)

