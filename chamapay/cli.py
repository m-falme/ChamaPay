import click

from .models import Chama


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
