import os
import json
import requests
from dotenv import load_dotenv
from functools import wraps

from flask import Flask, request, redirect, url_for, session, flash, render_template_string, jsonify
import mysql.connector
from mysql.connector import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-before-deployment")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT",4000))
}
import time
import requests

def call_gemini(payload, headers):
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=90
            )

            if response.status_code == 503:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

            return response

        except requests.Timeout:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

    return response
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def run_query(query, values=(), fetch=False, one=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, values)
        result = cursor.fetchone() if one else cursor.fetchall() if fetch else None
        conn.commit()
        return result
    finally:
        cursor.close()
        conn.close()

def current_user():
    if "user_id" not in session:
        return None
    return run_query("SELECT * FROM users WHERE id=%s", (session["user_id"],), one=True)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in first.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

BASE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | Skill2Career</title>
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
<nav class="nav">
  <a class="brand" href="{{ url_for('home') }}"><span class="brand-icon">S</span> Skill2Career</a>
  <div class="nav-links">
    {% if user %}
      <a href="{{ url_for('dashboard') }}">Dashboard</a>
      <a href="{{ url_for('assessment') }}">Assessment</a>
      <a href="{{ url_for('roadmap') }}">Roadmap</a>
      <a href="{{ url_for('courses') }}">Courses</a>
      <a href="{{ url_for('jobs') }}">Careers</a>
      <a href="{{ url_for('resume') }}">Resume</a>
      <a class="nav-cta" href="{{ url_for('logout') }}">Logout</a>
    {% else %}
      <a href="{{ url_for('login') }}">Login</a>
      <a class="nav-cta" href="{{ url_for('register') }}">Get started</a>
    {% endif %}
  </div>
</nav>
<main class="container">
  {% with messages = get_flashed_messages() %}
    {% if messages %}<div class="flash">{% for message in messages %}{{ message }}{% endfor %}</div>{% endif %}
  {% endwith %}
  {{ content|safe }}
</main>

{% if user %}
<div id="site-help-widget" class="site-help-widget">
  <button id="site-help-toggle" class="site-help-toggle" type="button" aria-label="Open Skill2Career help assistant">✦ Help</button>
  <section id="site-help-panel" class="site-help-panel" hidden aria-label="Skill2Career website help chat">
    <header class="site-help-header"><div><b>Skill2Career Assistant</b><small>Website help · Gemini</small></div><button id="site-help-close" type="button" aria-label="Close chat">×</button></header>
    <div id="site-help-log" class="site-help-log"><div class="bot-msg">Hi {{ user.name }}! I can guide you around Skill2Career. Ask how to use assessments, roadmaps, courses, progress tracking, careers or the resume builder.</div></div>
    <form id="site-help-form" class="site-help-form"><input id="site-help-input" maxlength="2000" placeholder="How do I use this page?" required><button class="btn primary" type="submit">Send</button></form>
    <p class="site-help-note">Do not share passwords or API keys in chat.</p>
  </section>
</div>
<script>
(function(){
  const toggle=document.getElementById('site-help-toggle');
  const panel=document.getElementById('site-help-panel');
  const close=document.getElementById('site-help-close');
  const form=document.getElementById('site-help-form');
  const input=document.getElementById('site-help-input');
  const log=document.getElementById('site-help-log');
  if(!toggle||!panel||!form)return;
  let history=[];
  function addMessage(text,kind){
    const node=document.createElement('div');
    node.className=kind==='user'?'user-msg':'bot-msg';
    node.textContent=text;
    log.appendChild(node);
    log.scrollTop=log.scrollHeight;
  }
  toggle.addEventListener('click',()=>{panel.hidden=!panel.hidden;if(!panel.hidden)input.focus();});
  close.addEventListener('click',()=>panel.hidden=true);
  form.addEventListener('submit',async function(e){
    e.preventDefault();
    const message=input.value.trim();
    if(!message)return;
    addMessage(message,'user'); input.value='';
    const send=form.querySelector('button'); send.disabled=true; send.textContent='...';
    try{
      const response=await fetch('/api/chat',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:message,history:history})
      });
      const data=await response.json();
      const answer=data.reply||'Sorry, I could not answer that.';
      addMessage(answer,'bot');
      if(response.ok && data.mode==='gemini'){
        history.push({role:'user',content:message},{role:'assistant',content:answer});
        history=history.slice(-8);
      }
    }catch(err){addMessage('The assistant is temporarily unavailable. Please try again.','bot');}
    finally{send.disabled=false;send.textContent='Send';input.focus();}
  });
})();
</script>
{% endif %}

<footer>© 2026 Skill2Career · Build skills. Find your direction.</footer>
</body></html>
"""

def page(title, content, user=None, **context):
    return render_template_string(BASE, title=title, content=render_template_string(content, user=user, **context), user=user)

@app.route("/")
def home():
    user = current_user()
    content = """
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">YOUR CAREER, YOUR JOURNEY</div>
        <h1>Turn your skills into your <span>future.</span></h1>
        <p class="lead">Discover what you're good at, understand what to learn next, and prepare for your first career opportunity.</p>
        <div class="hero-actions">
          {% if user %}<a class="btn primary" href="{{ url_for('dashboard') }}">Open dashboard</a>
          {% else %}<a class="btn primary" href="{{ url_for('register') }}">Create free account</a><a class="btn secondary" href="{{ url_for('login') }}">I already have an account</a>{% endif %}
        </div>
        <div class="trust"><span>✓ Skill assessment</span><span>✓ Personal roadmap</span><span>✓ Resume builder</span></div>
      </div>
      <div class="hero-art"><div class="orb orb-one"></div><div class="orb orb-two"></div><div class="career-card"><div class="mini-label">YOUR NEXT STEP</div><h3>Learn. Build. Grow.</h3><div class="progress"><i></i></div><p>Small steps create big careers.</p><div class="card-bottom"><span>✦ Personalized learning</span><b>→</b></div></div></div>
    </section>
    <section class="section"><div class="section-head"><div class="eyebrow">ALL IN ONE PLACE</div><h2>Everything you need to move forward</h2></div>
    <div class="feature-grid">
      <article class="feature"><div class="feature-icon">◎</div><h3>Skill assessment</h3><p>Rate your current skills and identify areas to improve.</p></article>
      <article class="feature"><div class="feature-icon">↗</div><h3>Learning roadmap</h3><p>Follow a clear learning path based on your career goal.</p></article>
      <article class="feature"><div class="feature-icon">⌕</div><h3>Career suggestions</h3><p>Explore beginner-friendly roles related to your interests.</p></article>
      <article class="feature"><div class="feature-icon">▤</div><h3>Resume builder</h3><p>Create a simple resume and save it as a PDF.</p></article>
    </div></section>
    """
    return page("Home", content, user)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email, and a password with at least 6 characters.")
        else:
            try:
                run_query("INSERT INTO users (name,email,password_hash) VALUES (%s,%s,%s)",
                          (name, email, generate_password_hash(password)))
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
            except IntegrityError:
                flash("That email is already registered.")
            except mysql.connector.Error as exc:
                flash("Database error: " + str(exc))
    content = """
    <section class="auth-wrap"><div class="auth-info"><div class="eyebrow">START HERE</div><h1>Your next chapter starts with one step.</h1><p>Create your student account to save your assessment, roadmap and resume.</p></div>
    <form class="form-card" method="post"><h2>Create account</h2><label>Full name</label><input name="name" required placeholder="Your name"><label>Email address</label><input name="email" type="email" required placeholder="you@example.com"><label>Password</label><input name="password" type="password" minlength="6" required placeholder="At least 6 characters"><button class="btn primary full">Create account</button><p class="form-foot">Already registered? <a href="{{ url_for('login') }}">Login</a></p></form></section>
    """
    return page("Register", content, current_user())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            user = run_query("SELECT * FROM users WHERE email=%s", (email,), one=True)
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
            flash("Incorrect email or password.")
        except mysql.connector.Error as exc:
            flash("Database error: " + str(exc))
    content = """
    <section class="auth-wrap"><div class="auth-info"><div class="eyebrow">WELCOME BACK</div><h1>Keep moving towards your goal.</h1><p>Your career progress is ready when you are.</p></div>
    <form class="form-card" method="post"><h2>Login</h2><label>Email address</label><input name="email" type="email" required placeholder="you@example.com"><label>Password</label><input name="password" type="password" required placeholder="Your password"><button class="btn primary full">Login</button><p class="form-foot">New here? <a href="{{ url_for('register') }}">Create account</a></p></form></section>
    """
    return page("Login", content, current_user())

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    skills = json.loads(user["skills_json"] or "{}")
    average = round(sum(skills.values()) / len(skills), 1) if skills else 0
    content = """
    <div class="page-heading"><div><div class="eyebrow">STUDENT OVERVIEW</div><h1>Welcome, {{ user.name }} 👋</h1><p>Keep building your skills, one step at a time.</p></div><a class="btn primary" href="{{ url_for('assessment') }}">Update assessment</a><a class="btn secondary" href="{{ url_for('courses') }}">Explore courses</a></div>
    <div class="stats-grid"><div class="stat-card"><span>Career goal</span><strong>{{ user.goal }}</strong><small>Your selected direction</small></div><div class="stat-card"><span>Skills assessed</span><strong>{{ skills|length }}</strong><small>Skills in your profile</small></div><div class="stat-card"><span>Average skill level</span><strong>{{ average }}/5</strong><small>Based on your assessment</small></div></div>
    <div class="dashboard-grid"><section class="panel"><div class="panel-head"><h2>Your skill snapshot</h2><a href="{{ url_for('assessment') }}">Edit</a></div>
    {% if skills %}{% for name, score in skills.items() %}<div class="skill-row"><div><b>{{ name }}</b><span>{{ score }}/5</span></div><div class="progress"><i style="width:{{ score*20 }}%"></i></div></div>{% endfor %}{% else %}<p class="muted">Complete your skill assessment to see your progress here.</p><a class="btn secondary" href="{{ url_for('assessment') }}">Start assessment</a>{% endif %}</section>
    <section class="panel"><h2>CareerBot</h2><p class="muted">Ask a simple question about your learning path.</p><div id="chat-log" class="chat-log"><div class="bot-msg">Hi! I can suggest what to learn next. Try asking: “What should I learn for Python developer?”</div></div><form id="chat-form" class="chat-form"><input id="chat-input" placeholder="Ask CareerBot..." required><button class="btn primary">Send</button></form></section></div>
    <script>
    const form=document.getElementById('chat-form'), input=document.getElementById('chat-input'), log=document.getElementById('chat-log');
    form.addEventListener('submit',async e=>{e.preventDefault();const message=input.value.trim();if(!message)return;const mine=document.createElement('div');mine.className='user-msg';mine.textContent=message;log.appendChild(mine);input.value='';try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})});const d=await r.json();const bot=document.createElement('div');bot.className='bot-msg';bot.textContent=d.reply||'Sorry, I could not answer that.';log.appendChild(bot);}catch(err){const bot=document.createElement('div');bot.className='bot-msg';bot.textContent='CareerBot is temporarily unavailable. Please try again.';log.appendChild(bot);}log.scrollTop=log.scrollHeight;});
    </script>
    """
    return page("Dashboard", content, user, skills=skills, average=average)

@app.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    user = current_user()
    skill_names = ["HTML", "CSS", "JavaScript", "Python", "SQL"]
    if request.method == "POST":
        skills = {s: int(request.form.get(s, 1)) for s in skill_names}
        goal = request.form.get("goal", "Python Developer")
        run_query("UPDATE users SET skills_json=%s, goal=%s WHERE id=%s",
                  (json.dumps(skills), goal, user["id"]))
        flash("Your assessment has been saved.")
        return redirect(url_for("roadmap"))
    current = json.loads(user["skills_json"] or "{}")
    content = """
    <div class="page-heading"><div><div class="eyebrow">KNOW YOUR STARTING POINT</div><h1>Skill assessment</h1><p>Choose the level that best describes your current knowledge.</p></div></div>
    <form class="panel assessment-form" method="post"><h2>Rate your skills</h2><p class="muted">1 = Beginner · 2 = Basic · 3 = Intermediate · 4 = Good · 5 = Strong</p>
    {% for skill in skill_names %}<div class="rating-row"><label for="{{ skill }}">{{ skill }}</label><select id="{{ skill }}" name="{{ skill }}">{% for n in range(1,6) %}<option value="{{ n }}" {% if current.get(skill,1)==n %}selected{% endif %}>{{ n }} - {{ ["","Beginner","Basic","Intermediate","Good","Strong"][n] }}</option>{% endfor %}</select></div>{% endfor %}
    <label class="top-label" for="goal">Choose your career goal</label><select id="goal" name="goal">{% for g in goals %}<option {% if user.goal==g %}selected{% endif %}>{{ g }}</option>{% endfor %}</select><button class="btn primary">Save assessment & build roadmap</button></form>
    """
    goals = ["Python Developer", "Frontend Developer", "Full Stack Developer", "Data Analyst", "Software Tester"]
    return page("Assessment", content, user, skill_names=skill_names, current=current, goals=goals)

@app.route("/roadmap")
@login_required
def roadmap():
    user = current_user()
    skills = json.loads(user["skills_json"] or "{}")
    goal = user["goal"]
    tracks = {
        "Python Developer": ["Python fundamentals", "Functions, modules and OOP", "SQL and database connectivity", "Flask web development", "Build and publish a Python project"],
        "Frontend Developer": ["HTML page structure", "CSS layouts and responsive design", "JavaScript fundamentals", "DOM and API practice", "Build a responsive portfolio"],
        "Full Stack Developer": ["HTML, CSS and JavaScript", "Frontend forms and API calls", "Python Flask backend", "MySQL database basics", "Build and deploy a full-stack app"],
        "Data Analyst": ["Excel and data basics", "Python fundamentals", "SQL queries", "Pandas and data cleaning", "Create a small data dashboard"],
        "Software Tester": ["Software testing fundamentals", "Test cases and bug reports", "SQL basics", "API testing concepts", "Practice testing a sample website"]
    }
    content = """
    <div class="page-heading"><div><div class="eyebrow">YOUR PERSONAL LEARNING PATH</div><h1>{{ goal }} roadmap</h1><p>Work through these steps in order. Adjust the pace to your schedule.</p></div><a class="btn secondary" href="{{ url_for('assessment') }}">Change goal</a></div>
    <section class="panel roadmap-panel"><div class="roadmap-line"></div>{% for step in steps %}<div class="roadmap-step"><div class="step-number">{{ loop.index }}</div><div><h3>{{ step }}</h3><p>{{ descriptions[loop.index0] }}</p></div><span class="step-tag">STEP {{ loop.index }}</span></div>{% endfor %}</section>
    <section class="panel"><h2>Skills to strengthen</h2>{% if skills %}<div class="gap-grid">{% for name, score in skills.items() %}<div class="gap-item"><b>{{ name }}</b><span>{{ score }}/5</span><small>{% if score <= 2 %}Focus area{% elif score == 3 %}Keep practising{% else %}Good foundation{% endif %}</small></div>{% endfor %}</div>{% else %}<p class="muted">Complete the assessment to personalize your skill-gap view.</p>{% endif %}</section>
    """
    descriptions = ["Learn the core concepts and take short notes.", "Practise with small examples until the ideas feel familiar.", "Solve beginner exercises and understand common errors.", "Create a mini project that uses this skill.", "Add the project to your portfolio and explain what you learned."]
    return page("Roadmap", content, user, goal=goal, steps=tracks.get(goal, tracks["Python Developer"]), descriptions=descriptions, skills=skills)

@app.route("/jobs")
@login_required
def jobs():
    user = current_user()
    roles = [
        ("Python Developer Intern", "Python, basic SQL, Flask projects", "Build a small CRUD app and upload it to GitHub."),
        ("Frontend Developer Intern", "HTML, CSS, JavaScript, responsive design", "Create a responsive portfolio with 2 projects."),
        ("Web Development Trainee", "HTML, CSS, JavaScript, backend basics", "Build and document a complete website."),
        ("Junior Data Analyst Trainee", "Excel, SQL, Python basics", "Practise data cleaning and simple charts."),
        ("Software Testing Intern", "Testing concepts, test cases, SQL basics", "Write test cases for a sample login page.")
    ]
    content = """
    <div class="page-heading"><div><div class="eyebrow">EXPLORE POSSIBILITIES</div><h1>Career suggestions</h1><p>Starter role ideas related to {{ user.goal }} and common entry-level skills.</p></div></div>
    <div class="jobs-grid">{% for title, skills, action in roles %}<article class="job-card"><div class="job-icon">↗</div><div class="job-type">SAMPLE ROLE · NOT A LIVE VACANCY</div><h2>{{ title }}</h2><p><b>Useful skills</b><br>{{ skills }}</p><p><b>Suggested preparation</b><br>{{ action }}</p></article>{% endfor %}</div>
    <p class="notice">These are career exploration examples, not verified current openings. Check employer websites and eligibility before applying.</p>
    """
    return page("Careers", content, user, roles=roles)

@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():
    user = current_user()
    data = {"name": user["name"], "email": user["email"], "phone": "", "education": "Diploma in CME", "skills": "HTML, CSS, JavaScript, Python, SQL", "projects": "", "objective": "Motivated diploma student eager to learn and contribute to software development projects."}
    if request.method == "POST":
        data.update({k: request.form.get(k, "").strip() for k in data})
    content = """
    <div class="page-heading"><div><div class="eyebrow">PRESENT YOUR WORK</div><h1>Resume builder</h1><p>Fill in your details, then use Print / Save as PDF.</p></div><button class="btn primary" onclick="window.print()">Print / Save PDF</button></div>
    <div class="resume-layout"><form class="panel resume-form" method="post"><h2>Your details</h2>
    {% for key,label in fields %}<label>{{ label }}</label>{% if key in ["objective","projects"] %}<textarea name="{{ key }}" rows="3">{{ data[key] }}</textarea>{% else %}<input name="{{ key }}" value="{{ data[key] }}" {% if key in ["name","email"] %}required{% endif %}>{% endif %}{% endfor %}<button class="btn secondary">Update preview</button></form>
    <section class="resume-paper"><div class="resume-name">{{ data.name }}</div><div class="resume-contact">{{ data.email }} {% if data.phone %} · {{ data.phone }}{% endif %}</div><hr><h3>Career objective</h3><p>{{ data.objective }}</p><h3>Education</h3><p>{{ data.education }}</p><h3>Skills</h3><p>{{ data.skills }}</p><h3>Projects</h3><p>{{ data.projects or "Add your academic or personal projects here." }}</p></section></div>
    """
    fields = [("name","Full name"),("email","Email"),("phone","Phone"),("education","Education"),("skills","Skills (comma separated)"),("objective","Career objective"),("projects","Projects")]
    return page("Resume", content, user, data=data, fields=fields)

# Curated beginner learning videos. These are individual YouTube lessons/courses;
# YouTube search links are also provided so students can find updated alternatives.
COURSES = {
    "html": {"title":"HTML Full Course", "skill":"HTML", "video_id":"UB1O30fR-EE", "channel":"Traversy Media", "duration_hint":"Beginner course", "quiz":[
        ("What does HTML mainly define?", ["Page structure", "Database storage", "Server hosting"], 0),
        ("Which tag creates a hyperlink?", ["<p>", "<a>", "<img>"], 1),
        ("Which tag is the main page heading?", ["<h1>", "<head>", "<title>"], 0)]},
    "css": {"title":"CSS Crash Course", "skill":"CSS", "video_id":"yfoY53QXEnI", "channel":"Traversy Media", "duration_hint":"Beginner course", "quiz":[
        ("What does CSS control?", ["Page styling", "Database queries", "Python packages"], 0),
        ("Which selector targets a class?", ["#name", ".name", "name()"], 1),
        ("Which layout system is one-dimensional?", ["Flexbox", "SQL", "HTML"], 0)]},
    "javascript": {"title":"JavaScript Crash Course", "skill":"JavaScript", "video_id":"hdI2bqOjy3c", "channel":"Traversy Media", "duration_hint":"Beginner course", "quiz":[
        ("Which keyword declares a block-scoped variable?", ["let", "select", "style"], 0),
        ("Which method selects an element by ID?", ["getElementById", "queryDatabase", "makeElement"], 0),
        ("Which type represents true or false?", ["String", "Boolean", "Array"], 1)]},
    "python": {"title":"Python Full Course for Beginners", "skill":"Python", "video_id":"rfscVS0vtbw", "channel":"freeCodeCamp.org", "duration_hint":"Beginner course", "quiz":[
        ("Which symbol starts a Python comment?", ["//", "#", "<!--"], 1),
        ("Which data type stores True or False?", ["bool", "list", "dict"], 0),
        ("Which keyword defines a function?", ["func", "def", "function"], 1)]},
    "sql": {"title":"SQL Full Course", "skill":"SQL", "video_id":"HXV3zeQKqGY", "channel":"freeCodeCamp.org", "duration_hint":"Beginner course", "quiz":[
        ("Which SQL command reads data?", ["SELECT", "PAINT", "OPEN"], 0),
        ("Which clause filters rows?", ["WHERE", "ORDER", "TABLE"], 0),
        ("Which command adds a new row?", ["INSERT", "JOIN", "GROUP"], 0)]}
}

@app.route("/courses")
@login_required
def courses():
    user = current_user()
    rows = run_query("SELECT video_slug, watched_seconds, duration_seconds, completed, quiz_score FROM course_progress WHERE user_id=%s", (user["id"],), fetch=True)
    progress = {r["video_slug"]: r for r in rows}
    content = """
    <div class="page-heading"><div><div class="eyebrow">LEARN BY DOING</div><h1>Your video courses</h1><p>Recommended starting courses for your {{ user.goal }} path. Watch, track progress and pass the short quiz.</p></div></div>
    <div class="course-grid">{% for slug, course in catalog.items() %}<article class="course-card"><div class="course-thumb"><span>▶</span><small>{{ course.skill }}</small></div><div class="course-body"><div class="course-meta">YOUTUBE · {{ course.channel }}</div><h2>{{ course.title }}</h2><p>Beginner-friendly learning video with progress tracking and a knowledge check.</p>{% set item = progress.get(slug) %}{% if item %}<div class="course-progress"><div><span>Progress</span><b>{{ item.percent }}%</b></div><div class="progress"><i style="width:{{ item.percent }}%"></i></div></div>{% if item.completed %}<span class="complete-label">✓ Completed · Quiz {{ item.quiz_score }}/3</span>{% endif %}{% else %}<div class="course-progress"><div><span>Progress</span><b>0%</b></div><div class="progress"><i style="width:0%"></i></div></div>{% endif %}<a class="btn primary full" href="{{ url_for('course_detail', slug=slug) }}">{% if item and item.completed %}Review course{% elif item %}Continue learning{% else %}Start course{% endif %}</a></div></article>{% endfor %}</div>
    <p class="notice">Progress is estimated from YouTube playback events in this browser. It cannot prove attention or prevent every form of tampering. Course completion also requires passing the quiz.</p>
    """
    for r in rows:
        duration = r["duration_seconds"] or 0
        r["percent"] = min(100, round((r["watched_seconds"] or 0) / duration * 100)) if duration else 0
    return page("Courses", content, user, catalog=COURSES, progress=progress)

@app.route("/courses/<slug>")
@login_required
def course_detail(slug):
    user = current_user()
    course = COURSES.get(slug)
    if not course:
        return redirect(url_for("courses"))
    row = run_query("SELECT * FROM course_progress WHERE user_id=%s AND video_slug=%s", (user["id"], slug), one=True)
    watched = int(row["watched_seconds"] or 0) if row else 0
    duration = int(row["duration_seconds"] or 0) if row else 0
    percent = min(100, round(watched / duration * 100)) if duration else 0
    content = r"""
    <div class="page-heading"><div><div class="eyebrow">YOUTUBE LEARNING</div><h1>{{ course.title }}</h1><p>{{ course.channel }} · {{ course.duration_hint }}</p></div><a class="btn secondary" href="{{ url_for('courses') }}">All courses</a></div>
    <section class="panel video-panel"><div id="yt-player"></div><div class="video-status"><div><b id="progress-label">{{ percent }}% watched</b><p class="muted">Keep the video playing normally. Your progress saves automatically while it is playing.</p></div><div class="video-progress"><div class="progress"><i id="progress-bar" style="width:{{ percent }}%"></i></div></div></div><div id="course-message" class="muted">Playback progress: {{ percent }}%</div></section>
    <section class="panel quiz-panel"><h2>Course completion quiz</h2><p class="muted">Watch at least 90% of the video, then answer the 3 questions. You need at least 2 correct answers.</p><form id="course-quiz">{% for q in course.quiz %}{% set q_index = loop.index0 %}<div class="quiz-question"><b>{{ loop.index }}. {{ q[0] }}</b>{% for option in q[1] %}<label class="quiz-option"><input type="radio" name="q{{ q_index }}" value="{{ loop.index0 }}" required> {{ option }}</label>{% endfor %}</div>{% endfor %}<button class="btn primary">Submit completion quiz</button></form><div id="quiz-result"></div>{% if completed %}<p class="complete-label">✓ This course is marked complete. Quiz score: {{ quiz_score }}/3</p>{% endif %}</section>
    <script>
    const slug={{ slug|tojson }}; let player, lastTime=null, isPlaying=false, saveTimer=null, totalDuration=0, savedPercent={{ percent }};
    function onYouTubeIframeAPIReady(){player=new YT.Player('yt-player',{height:'450',width:'100%',videoId:{{ course.video_id|tojson }},playerVars:{'playsinline':1,'rel':0},events:{onReady:onReady,onStateChange:onStateChange}})}
    function onReady(e){totalDuration=e.target.getDuration()||0;}
    function onStateChange(e){isPlaying=(e.data===1);if(e.data===0){saveProgress(0);document.getElementById('course-message').textContent='Video ended. If your watched progress is at least 90%, complete the quiz below.';} }
    function saveProgress(delta){fetch('/api/course-progress',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:slug,delta_seconds:delta,duration_seconds:Math.round(totalDuration)})}).then(r=>r.json()).then(d=>{if(d.ok){savedPercent=d.percent;document.getElementById('progress-label').textContent=d.percent+'% watched';document.getElementById('progress-bar').style.width=d.percent+'%';document.getElementById('course-message').textContent=d.percent>=90?'Watch requirement met. Complete the quiz to finish.':'Playback progress saved: '+d.percent+'%';}}).catch(()=>{});}
    function trackPlayback(){if(!player)return;totalDuration=player.getDuration()||totalDuration;if(!isPlaying)return;const now=player.getCurrentTime();if(lastTime!==null){const delta=now-lastTime;if(delta>0 && delta<=8){saveProgress(Math.min(6,Math.round(delta)));}}lastTime=now;}
    setInterval(trackPlayback,5000);
    window.addEventListener('beforeunload',()=>{if(player&&isPlaying){const now=player.getCurrentTime();if(lastTime!==null){const d=now-lastTime;if(d>0&&d<=8)saveProgress(Math.min(6,Math.round(d)));}}});
    document.getElementById('course-quiz').addEventListener('submit',async e=>{e.preventDefault();const answers={};new FormData(e.target).forEach((v,k)=>answers[k]=Number(v));const r=await fetch('/api/course-quiz',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:slug,answers:answers})});const d=await r.json();const box=document.getElementById('quiz-result');box.textContent=d.message;box.className=d.completed?'complete-label':'quiz-feedback';if(d.completed){setTimeout(()=>location.reload(),1200);}});
    const tag=document.createElement('script');tag.src='https://www.youtube.com/iframe_api';document.head.appendChild(tag);
    </script>
    """
    return page("Course", content, user, course=course, slug=slug, percent=percent, completed=bool(row and row["completed"]), quiz_score=(row["quiz_score"] if row else None))

@app.route("/api/course-progress", methods=["POST"])
@login_required
def course_progress():
    user = current_user()
    data = request.get_json(silent=True) or {}
    slug = data.get("slug")
    if slug not in COURSES:
        return jsonify({"ok":False,"message":"Unknown course"}), 400
    try:
        delta = max(0, min(6, int(data.get("delta_seconds", 0))))
        duration = max(0, min(21600, int(data.get("duration_seconds", 0))))
    except (TypeError, ValueError):
        return jsonify({"ok":False,"message":"Invalid progress"}), 400
    run_query("""INSERT INTO course_progress (user_id, video_slug, watched_seconds, duration_seconds)
                 VALUES (%s,%s,%s,%s)
                 ON DUPLICATE KEY UPDATE watched_seconds=LEAST(GREATEST(duration_seconds, VALUES(duration_seconds)), watched_seconds + VALUES(watched_seconds)),
                 duration_seconds=GREATEST(duration_seconds, VALUES(duration_seconds))""",
              (user["id"], slug, delta, duration))
    row = run_query("SELECT watched_seconds,duration_seconds FROM course_progress WHERE user_id=%s AND video_slug=%s", (user["id"],slug), one=True)
    total = int(row["duration_seconds"] or 0)
    watched = int(row["watched_seconds"] or 0)
    percent = min(100, round(watched / total * 100)) if total else 0
    return jsonify({"ok":True,"percent":percent,"watched_seconds":watched,"duration_seconds":total})

@app.route("/api/course-quiz", methods=["POST"])
@login_required
def course_quiz():
    user = current_user()
    data = request.get_json(silent=True) or {}
    slug = data.get("slug")
    course = COURSES.get(slug)
    if not course:
        return jsonify({"completed":False,"message":"Unknown course."}), 400
    row = run_query("SELECT watched_seconds,duration_seconds FROM course_progress WHERE user_id=%s AND video_slug=%s", (user["id"],slug), one=True)
    if not row or not row["duration_seconds"] or row["watched_seconds"] < row["duration_seconds"] * 0.90:
        return jsonify({"completed":False,"message":"Please watch at least 90% of the video before taking the completion quiz."})
    answers = data.get("answers", {})
    score = 0
    for i, question in enumerate(course["quiz"]):
        if answers.get("q"+str(i)) == question[2]:
            score += 1
    passed = score >= 2
    run_query("UPDATE course_progress SET quiz_score=%s, completed=%s WHERE user_id=%s AND video_slug=%s", (score, 1 if passed else 0, user["id"], slug))
    return jsonify({"completed":passed,"score":score,"message":("Course completed! Score: "+str(score)+"/3") if passed else ("You scored "+str(score)+"/3. Review the video and try again; 2/3 is required.")})

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    user = current_user()
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"reply": "Please type a question first."}), 400
    if len(message) > 2000:
        return jsonify({"reply": "Please keep your question under 2,000 characters."}), 400

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({
            "reply": "The AI assistant is not configured. Add GEMINI_API_KEY to your .env file and restart Skill2Career.",
            "mode": "setup"
        }), 503

    instructions_path = os.path.join(app.root_path, "custom_gpt_instructions.txt")
    try:
        with open(instructions_path, "r", encoding="utf-8") as f:
            custom_instructions = f.read().strip()
    except OSError:
        custom_instructions = ""

    system_instruction = (
        "You are the Skill2Career Website Help Assistant. Help students understand "
        "how to use registration/login, dashboard, skill assessment, career goals, "
        "learning roadmaps, skill-gap analysis, YouTube courses, playback progress, "
        "course quizzes, career suggestions, and resume builder. Give clear, beginner-friendly "
        "step-by-step directions. Do not claim to perform actions or change account data. "
        "Never ask for passwords, API keys, payment details, or sensitive personal data. "
        "Do not guarantee jobs, salaries, admissions, or course outcomes. Keep responses "
        "age-appropriate. Student name: " + str(user.get("name") or "Student") + ". "
        "Career goal: " + str(user.get("goal") or "Not selected") + ". "
        "Branch: " + str(user.get("branch") or "Not specified") + ". "
        "Self-rated skills (1-5): " + str(user.get("skills_json") or "Not assessed") + ".\n\n"
        "Additional instructions:\n" + (custom_instructions or
        "Use the Skill2Career website-help role described above.")
    )

    # Build a simple text prompt. The Interactions API accepts input as a string.
    # This avoids malformed stateless Step payloads from browser chat history.
    conversation_lines = []
    if isinstance(history, list):
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            if role == "user":
                conversation_lines.append("Student: " + content[:2000])
            elif role == "assistant":
                conversation_lines.append("CareerBot: " + content[:2000])

    conversation_lines.append("Student: " + message)
    input_text = "\n".join(conversation_lines)

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
    endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"
    payload = {
        "model": model,
        "input": input_text,
        "system_instruction": system_instruction,
        "store": False
    }

    try:
        response = requests.post(
            endpoint,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=90
        )

        if not response.ok:
            app.logger.error(
                "Gemini Interactions API returned %s: %s",
                response.status_code,
                response.text[:1200]
            )
            try:
                error_data = response.json().get("error", {})
                error_message = error_data.get("message", "Unknown Gemini API error")
            except (ValueError, AttributeError):
                error_message = "Unknown Gemini API error"
            return jsonify({
                "reply": "Gemini API error (" + str(response.status_code) + "): " + str(error_message)[:500],
                "mode": "error"
            }), 502

        result = response.json()
        reply_parts = []
        for step in result.get("steps", []):
            if step.get("type") == "model_output":
                blocks = step.get("content", [])
                if isinstance(blocks, list):
                    for block in blocks:
                        if isinstance(block, dict) and isinstance(block.get("text"), str):
                            reply_parts.append(block["text"])

        reply = "\n".join(reply_parts).strip()
        if not reply:
            reply = "I couldn't produce a response this time. Please try asking in a different way."

        return jsonify({"reply": reply, "mode": "gemini"})

    except requests.Timeout:
        app.logger.exception("Gemini Interactions API timed out")
        return jsonify({
            "reply": "Gemini took too long to respond. Please try again.",
            "mode": "error"
        }), 504
    except requests.RequestException:
        app.logger.exception("Gemini Interactions API connection failed")
        return jsonify({
            "reply": "Skill2Career could not reach Gemini. Please try again in a moment.",
            "mode": "error"
        }), 502

@app.errorhandler(404)
def not_found(error):
    return page("Not found", "<section class='panel'><h1>Page not found</h1><a href='/'>Go home</a></section>", current_user()), 404

if __name__ == "__main__":
    app.run(debug=True)
