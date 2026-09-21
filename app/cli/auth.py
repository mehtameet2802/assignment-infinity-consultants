import getpass
import sys

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app.config import settings
from app.services.auth import (
    create_api_key_record,
    generate_raw_api_key,
    has_usable_api_key,
)


@click.group("auth")
def auth_cli():
    """API key administration commands."""


@auth_cli.command("hash-password")
def hash_password():
    """Generate ADMIN_PASSWORD_HASH from a prompted password."""
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        click.echo("Passwords do not match.", err=True)
        sys.exit(1)
    if not first:
        click.echo("Password cannot be empty.", err=True)
        sys.exit(1)
    click.echo(generate_password_hash(first))


@auth_cli.command("create-initial-key")
def create_initial_key():
    """Create the first API key (prints the raw key once)."""
    pepper = settings.api_key_pepper
    if not pepper:
        click.echo("API_KEY_PEPPER must be set in the environment.", err=True)
        sys.exit(1)
    from flask import current_app
    from app.database import SessionLocal

    with current_app.app_context():
        db = SessionLocal()
        try:
            if has_usable_api_key(db):
                click.echo(
                    "A usable API key already exists. Refusing to create another.",
                    err=True,
                )
                sys.exit(1)
            raw_key = generate_raw_api_key()
            create_api_key_record(db, raw_key, pepper)
        finally:
            db.close()
    click.echo("Initial API key created. Store it securely; it cannot be recovered.")
    click.echo(raw_key)


def register_auth_cli(app: Flask) -> None:
    app.cli.add_command(auth_cli)
