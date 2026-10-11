import os
from dotenv import load_dotenv
from app import create_app

load_dotenv('backend/.env')
app = create_app()

with app.app_context():
    import google.generativeai as genai
    gemini_key = os.getenv('GEMINI_API_KEY')
    print("Key exists:", bool(gemini_key))
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("hello")
        print("Success:", response.text)
    except Exception as e:
        print("REAL ERROR IS:", str(e))
