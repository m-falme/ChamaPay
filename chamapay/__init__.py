import os
from flask import Flask
from .models import db


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///" + os.path.abspath("chamapay.db")),
        DASHBOARD_PASSWORD=os.environ.get("DASHBOARD_PASSWORD", "changeme"),
    )
    if config:
        app.config.update(config)
    db.init_app(app)

    from .ussd import bp as ussd_bp
    from .webhooks import bp as hooks_bp
    from .dashboard import bp as dash_bp
    app.register_blueprint(ussd_bp)
    app.register_blueprint(hooks_bp)
    app.register_blueprint(dash_bp)

    from . import cli
    from .services import fmt, month_label

    app.jinja_env.filters["kes"] = fmt
    app.jinja_env.filters["month"] = month_label

    @app.template_filter("smsbadge")
    def smsbadge(status):
        st = (status or "").lower()
        if st.startswith(("success", "sent", "submitted", "queued", "received", "delivered")):
            return "ok"
        if st.startswith("not sent"):
            return "wait"
        return "bad"
    cli.register(app)

    with app.app_context():
        db.create_all()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
