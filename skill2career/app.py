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
    app.run(debug=True)
