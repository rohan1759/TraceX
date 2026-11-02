import argparse
import getpass
import os
import sys
import bcrypt
import yaml


def main():
    parser = argparse.ArgumentParser(description="Add a new Reporter to login_config.yml")
    parser.add_argument("--username", required=True, help="Unique username for the reporter")
    parser.add_argument("--name", required=True, help="Full name of the reporter")
    parser.add_argument("--email", required=True, help="Email address of the reporter")
    parser.add_argument("--city", required=True, help="City of the reporter")
    parser.add_argument("--area", required=True, help="Locality/area of the reporter")
    parser.add_argument("--config", default="login_config.yml", help="Path to login_config.yml")

    args = parser.parse_args()

    config_path = args.config
    if not os.path.isabs(config_path):
        if not os.path.exists(config_path):
            alt_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "login_config.yml",
            )
            if os.path.exists(alt_path):
                config_path = alt_path

    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at '{config_path}'.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error reading configuration file: {e}", file=sys.stderr)
        sys.exit(1)

    credentials = config.setdefault("credentials", {})
    usernames = credentials.setdefault("usernames", {})

    username = args.username.strip()
    if not username:
        print("Error: Username cannot be empty.", file=sys.stderr)
        sys.exit(1)

    # Refuse duplicate usernames
    if username in usernames:
        print(
            f"Error: Username '{username}' already exists. Cannot create duplicate.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Prompt for password with getpass (falls back to readline if stdin is piped)
    if sys.stdin.isatty():
        password = getpass.getpass("Enter password: ")
    else:
        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            try:
                password = getpass.getpass("Enter password: ")
            except Exception:
                pass
    if not password:
        print("Error: Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    # Generate bcrypt hash
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Add reporter record
    usernames[username] = {
        "name": args.name.strip(),
        "email": args.email.strip(),
        "city": args.city.strip(),
        "area": args.area.strip(),
        "role": "Reporter",
        "password": pw_hash,
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )
        print(f"Reporter '{username}' ({args.name}) successfully added to {config_path}.")
    except Exception as e:
        print(f"Error writing to configuration file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
