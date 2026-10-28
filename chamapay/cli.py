import click

from .models import Chama, Member, db


def register(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Drop all data first")
    def seed_cmd(reset):
        """Load demo data for 'Umoja Women Group'."""
        from .seed import seed
        click.echo(seed(reset=reset))

    @app.cli.command("send-reminders")
    def reminders_cmd():
        """SMS every member who has not paid this month."""
        from .services import send_reminders
        for chama in Chama.query.all():
            sent = send_reminders(chama)
            click.echo(f"{chama.name}: reminded {len(sent)} member(s)")

    @app.cli.command("voice-reminders")
    def voice_cmd():
        """Call late members (requires VOICE_ENABLED=1)."""
        from .services import voice_reminders
        for chama in Chama.query.all():
            for phone, st in voice_reminders(chama).items():
                click.echo(f"{phone}: {st}")

    @app.cli.command("add-member")
    @click.argument("name")
    @click.argument("phone")
    @click.option("--treasurer", is_flag=True)
    def add_member_cmd(name, phone, treasurer):
        """Add a member (e.g. your own sandbox simulator number) to the first chama."""
        from .ussd import normalize_phone
        chama = Chama.query.first()
        if not chama:
            raise click.ClickException("Run seed first")
        db.session.add(Member(chama_id=chama.id, name=name, phone=normalize_phone(phone), is_treasurer=treasurer))
        db.session.commit()
        click.echo(f"Added {name} {normalize_phone(phone)} to {chama.name}")
