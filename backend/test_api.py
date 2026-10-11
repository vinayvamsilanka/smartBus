import os
from dotenv import load_dotenv
from app import create_app

load_dotenv('backend/.env')
app = create_app()

with app.app_context():
    import google.generativeai as genai
    gemini_key = os.getenv('GEMINI_API_KEY')
    with open('output_log.txt', 'w', encoding='utf-8') as f:
        f.write(f"Key exists: {bool(gemini_key)}\n")
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-3.6-flash')
            response = model.generate_content("hello")
            f.write(f"Success: {response.text}\n")
        except Exception as e:
            f.write(f"REAL ERROR IS: {str(e)}\n")
