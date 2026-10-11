import os
from dotenv import load_dotenv
from app import create_app

load_dotenv('backend/.env')
app = create_app()

with app.app_context():
    from flask import session, request
    with app.test_request_context(json={'message': 'heyyy'}):
        from app.routes.optimizer import chat
        
        # Override print in optimizer.py locally to capture it
        import app.routes.optimizer
        _orig_print = builtins.print if 'builtins' in globals() else print
        def mock_print(*args, **kwargs):
            if "Gemini API Initialization Failed" in str(args):
                with open('error_log.txt', 'w', encoding='utf-8') as f:
                    f.write(str(args))
            _orig_print(*args, **kwargs)
        
        # actually, just let's see what happens...
        res = chat()
        print("Status:", res[1] if isinstance(res, tuple) else res.status_code)
        
