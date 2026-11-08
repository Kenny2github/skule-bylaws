# Bylaw Editor
WYSIWYG editor for EngSoc Bylaws.

## Configuration
Configure an Apache site as follows:
```apache
DocumentRoot <build>
ProxyRequests Off
<Location "/api">
    ProxyPass http://127.0.0.1:<port>/
    ProxyPassReverse http://127.0.0.1:<port>/
    RequestHeader set X-Forwarded-Proto https
    RequestHeader set X-Forwarded-Prefix /api
</Location>
```
where `<build>` is the path to the `build` directory in the repository, and `<port>` is the value of `FLASK_PORT`.

Place the following environment variables in a `.env` file at the root of the repository, and run either `flask run` (1) or `python -m scripts.server` (2) from the same place.

| Environment variable | Value | (1) | (2) |
|:--|:--|:--:|:--:|
| `FLASK_APP` | `scripts.server` | Required | Ignored |
| `FLASK_PORT` | Port number to run on | Ignored | Required |
| `FLASK_DEBUG` | [Debug mode](https://flask.palletsprojects.com/en/stable/debugging/) | Ignored | Default `0` |
| `BEHIND_PROXY` | `1` if running behind the Apache config above | Default `0` | Default `0` |
| `SESSION_KEY` | Output of running `python -c "import secrets; print(secrets.token_hex())"` once | Required | Required |
| `GOOGLE_CLIENT_ID` | Google OAuth app client ID | Required | Required |
| `GOOGLE_CLIENT_SECRET` | Google OAuth app client secret | Required | Required |
| `GOOGLE_REDIRECT_URI` | Google OAuth app redirect URI (make sure this matches the external server, not the internal reverse-proxied server) | Required | Required |
| `DB_URI` | [SQLAlchemy database URI](https://docs.sqlalchemy.org/en/20/core/engines.html) | Required | Required |
