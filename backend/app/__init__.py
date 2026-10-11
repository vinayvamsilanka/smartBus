from flask import Flask
from app.extensions import db, jwt, bcrypt, migrate
from app.config import Config
from flask_cors import CORS

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='../../frontend/templates', static_folder='../../frontend/static')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.optimizer import optimizer_bp
    from app.routes.tracking import tracking_bp
    from app.routes.booking import booking_bp
    from app.admin import admin_ui_bp
    from app.routes.rewards import rewards_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(optimizer_bp, url_prefix='/api/optimizer')
    app.register_blueprint(tracking_bp, url_prefix='/api/tracking')
    app.register_blueprint(booking_bp, url_prefix='/api/booking')
    app.register_blueprint(admin_ui_bp, url_prefix='/admin')
    app.register_blueprint(rewards_bp, url_prefix='/api/rewards')

    # Register UI routes
    from flask import render_template, jsonify
    from sqlalchemy import text
    from datetime import datetime
    
    @app.route('/health')
    def health_check():
        db_status = "healthy"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"degraded: {str(e)}"
        return jsonify({
            "status": "online",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    @app.route('/google57f4fc5570ae169b.html')
    def google_verification():
        return "google-site-verification: google57f4fc5570ae169b.html", 200, {'Content-Type': 'text/html'}

    @app.route('/robots.txt')
    def robots_txt():
        content = "User-agent: *\nAllow: /\nSitemap: https://smartbus-ai-r4ay.onrender.com/sitemap.xml\n"
        return content, 200, {'Content-Type': 'text/plain'}

    @app.route('/sitemap.xml')
    def sitemap_xml():
        content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://smartbus-ai-r4ay.onrender.com/</loc>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://smartbus-ai-r4ay.onrender.com/safety</loc>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://smartbus-ai-r4ay.onrender.com/eco-rewards</loc>
    <priority>0.7</priority>
  </url>
</urlset>"""
        return content, 200, {'Content-Type': 'application/xml'}

    @app.route('/')
    def index():
        from app.models import City
        from app.models.bus import Route
        cities = City.query.filter_by(is_active=True).order_by(City.name).all()
        popular_routes = Route.query.filter_by(is_active=True).limit(4).all()
        return render_template('index.html', cities=cities, popular_routes=popular_routes)
        
    @app.route('/results')
    def results():
        return render_template('results.html')
        
    @app.route('/details')
    def details():
        return render_template(
            'details.html',
            payment_receiver_upi=app.config.get('PAYMENT_RECEIVER_UPI'),
            payment_receiver_name=app.config.get('PAYMENT_RECEIVER_NAME')
        )
        
    @app.route('/dashboard')
    def dashboard():
        from flask import session, redirect, url_for
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('dashboard.html')

    @app.route('/eco-rewards')
    def eco_rewards():
        from flask import session, redirect, url_for
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return render_template('eco_rewards.html')

    @app.route('/safety')
    def safety():
        from app.models.metrics import SafetyMetrics
        from app.models.bus import Bus
        safest_coaches = SafetyMetrics.query.order_by(SafetyMetrics.overall_score.desc()).limit(5).all()
        safest_data = []
        for s in safest_coaches:
            bus = Bus.query.get(s.bus_id)
            if bus:
                safest_data.append({
                    "bus_number": bus.bus_number,
                    "type": bus.type,
                    "driver_score": s.driver_score,
                    "maintenance_score": s.maintenance_score,
                    "night_safety": s.night_safety,
                    "women_safety": s.women_safety,
                    "overall_score": s.overall_score
                })
        return render_template('safety.html', safest_coaches=safest_data)

    @app.route('/login')
    def login():
        from flask import session, redirect, url_for
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        from flask import session, redirect, url_for
        session.pop('user_id', None)
        session.pop('user_name', None)
        return redirect(url_for('index'))

    return app
