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
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "skill2career"),
}
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
    <header class="site-help-header"><div><b>Skill2Career Assistant</b><small>Website help · Groq</small></div><button id="site-help-close" type="button" aria-label="Close chat">×</button></header>
    <div id="site-help-log" class="site-help-log"><div class="bot-msg">Hi {{ user.name }}! I can guide you around Skill2Career. Ask how to use assessments, roadmaps, courses, progress tracking, careers or the resume builder.</div></div>
    <form id="site-help-form" class="site-help-form"><input id="site-help-input" maxlength="2000" placeholder="How do I use this page?" required><button class="btn primary" type="submit">Send</button></form>
    <p class="site-help-note">Do not share passwords or API keys in chat.</p>
  </section>
</div>
return jsonify({"reply": "Please keep your question under 2,000 characters.", "mode": "error"}), 400

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return jsonify({
            "reply": "CareerBot is not configured yet. Add GROQ_API_KEY in your Render Environment settings, then redeploy.",
            "mode": "setup"
        }), 503

    instructions_path = os.path.join(app.root_path, "custom_gpt_instructions.txt")
    try:
        with open(instructions_path, "r", encoding="utf-8") as f:
            custom_instructions = f.read().strip()
    except OSError:
        custom_instructions = ""

    skills_text = user.get("skills_json") or "Not assessed"
    system_instruction = (
        "You are Skill2Career CareerBot, a friendly, accurate and age-appropriate career "
        "guidance assistant for students. Help with career exploration, diploma and degree "
        "pathways, technical skills, learning plans, projects, resumes, interview practice, "
        "government-job exam preparation and how to use the Skill2Career website. "
        "Give practical, beginner-friendly steps. Personalize advice using the student's "
        "profile below, but do not assume information that is not provided. Explain that "
        "eligibility, vacancies, exam dates and salaries must be checked from official sources. "
        "Never guarantee a job, salary, admission or exam result. Do not ask for passwords, "
        "API keys, payment details or sensitive personal information. Do not claim to change "
        "account data or perform actions on the website. Keep answers concise and supportive.\n\n"
        "Student profile:\n"
        "Name: " + str(user.get("name") or "Student") + "\n" +
        "Career goal: " + str(user.get("goal") or "Not selected") + "\n" +
        "Branch: " + str(user.get("branch") or "Not specified") + "\n" +
        "Self-assessed skills (1-5): " + str(skills_text) + "\n\n" +
        "Additional website-specific instructions:\n" + (custom_instructions or "No additional instructions.")
    )

    messages = [{"role": "system", "content": system_instruction}]
    # Accept only the two expected roles and trim history to keep requests small.
    if isinstance(history, list):
        for item in history[-8:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": message})

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "max_completion_tokens": 1200
    }

    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        if not response.ok:
            app.logger.error("Groq API returned %s: %s", response.status_code, response.text[:1200])
            try:
                error_data = response.json().get("error", {})
                error_message = error_data.get("message", "Unknown Groq API error")
            except (ValueError, AttributeError):
                error_message = "Unknown Groq API error"

            if response.status_code == 401:
                friendly = "Groq rejected the API key. Check GROQ_API_KEY in Render Environment settings."
            elif response.status_code == 429:
                friendly = "Groq's rate or usage limit has been reached. Please wait and try again, or check your Groq account limits."
            elif response.status_code == 400:
                friendly = "Groq could not process this request. Check the GROQ_MODEL setting and try again."
            else:
                friendly = "Groq API error (" + str(response.status_code) + "): " + str(error_message)[:350]
            return jsonify({"reply": friendly, "mode": "error"}), 502

        result = response.json()
        choices = result.get("choices", [])
        reply = ""
        if choices and isinstance(choices[0], dict):
            reply = (choices[0].get("message", {}).get("content") or "").strip()
        if not reply:
            reply = "I couldn't produce a response this time. Please try asking in a different way."

        return jsonify({"reply": reply, "mode": "groq"})

    except requests.Timeout:
        app.logger.exception("Groq API request timed out")
        return jsonify({"reply": "CareerBot took too long to respond. Please try again.", "mode": "error"}), 504
    except requests.RequestException:
        app.logger.exception("Groq API connection failed")
        return jsonify({"reply": "Skill2Career could not connect to Groq. Please try again in a moment.", "mode": "error"}), 502
    except (ValueError, KeyError, TypeError):
        app.logger.exception("Unexpected Groq API response")
        return jsonify({"reply": "CareerBot received an unexpected response. Please try again.", "mode": "error"}), 502

@app.errorhandler(404)
def not_found(error):
    return page("Not found", "<section class='panel'><h1>Page not found</h1><a href='/'>Go home</a></section>", current_user()), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
