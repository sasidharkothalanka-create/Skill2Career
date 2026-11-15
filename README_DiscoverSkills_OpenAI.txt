# Skill2Career – Discover Skills + OpenAI Website Help

## Included
- Discover Skills page with search and filters.
- Skill detail pages with topic-by-topic learning paths and YouTube search links.
- Add discovered skills to the signed-in student's existing `skills_json` profile. Existing assessment scores are preserved.
- OpenAI-powered website-help chatbot using the OpenAI Responses API.
- The chatbot reads `custom_gpt_instructions.txt` so you can reuse instructions from your existing Custom GPT.

## Important about an existing Custom GPT
A Custom GPT inside ChatGPT cannot be directly embedded in an external website or automatically accessed by the API. To reuse its behavior:
1. Open your Custom GPT in ChatGPT's GPT editor.
2. Copy its Instructions.
3. Paste them into `custom_gpt_instructions.txt`.
4. Knowledge files from that GPT need to be separately uploaded/indexed for website retrieval; they are not imported automatically by this ZIP.

## Setup
1. Extract this ZIP.
2. Open the `skill2career` folder.
3. Install packages:
   `py -m pip install -r requirements.txt`
4. Copy `.env.example` to `.env`.
5. Fill in your Aiven MySQL details and OpenAI API key in `.env`.
6. Keep `.env` private; never upload it to GitHub.
7. Restart the Flask app:
   `py app.py`

## Environment variables
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: your existing Aiven MySQL connection details.
- `SECRET_KEY`: a long random secret.
- `OPENAI_API_KEY`: API key from the OpenAI platform (API billing is separate from ChatGPT subscriptions).
- `OPENAI_MODEL`: defaults to `gpt-4.1-mini`; set a model enabled for your API account if needed.

## Database
No new database table is required for Discover Skills. It stores selected skills in the existing `users.skills_json` column. The existing `course_progress` table and YouTube course tracking code are preserved.

## Navigation
After login, use **Discover Skills** in the top navigation. Open a skill and select **Add to my roadmap**.

## Notes
- YouTube search links open YouTube results; they do not claim course completion.
- Course completion tracking remains the existing playback-progress plus quiz mechanism.
- OpenAI calls run from Flask; the API key is never sent to browser JavaScript.
