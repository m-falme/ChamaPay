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
    @click.argument("name_arg", metavar="[NAME]", required=False)
    @click.argument("phone_arg", metavar="[PHONE]", required=False)
    @click.option("--name", "name_opt", help="Member name")
    @click.option("--phone", "phone_opt", help="Phone, e.g. 07XXXXXXXX or +2547XXXXXXXX")
    @click.option("--treasurer", is_flag=True, help="Make this member a treasurer")
    def add_member_cmd(name_arg, phone_arg, name_opt, phone_opt, treasurer):
        """Add a member to the first chama (positional NAME PHONE or --name/--phone)."""
        from .services import add_member
        name, phone = name_opt or name_arg, phone_opt or phone_arg
        if not name or not phone:
            raise click.UsageError("Provide NAME and PHONE (positionally or via --name/--phone).")
        chama = Chama.query.first()
        if not chama:
            raise click.ClickException("Run seed first")
        m, err = add_member(chama, name, phone, treasurer)
        if err:
            raise click.ClickException(err)
        click.echo(f"Added {m.name} {m.phone}{' (treasurer)' if m.is_treasurer else ''} to {chama.name}")
