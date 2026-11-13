# Location Project

[![CI](https://github.com/Logesh2097/Location_project/actions/workflows/ci.yml/badge.svg)](https://github.com/Logesh2097/Location_project/actions/workflows/ci.yml)

A small Django web app that shows the approximate location of the visitor's IP
address, using the [ip-api.com](https://ip-api.com/docs/api:json) geolocation API.

## Overview

Open the page and it shows the country, city, coordinates, time zone and postal
code that ip-api.com reports for your public IP address. It is a single-page,
server-rendered app with no database models, written as a Django learning project.

## Features

- Looks up the visitor's own address (`REMOTE_ADDR`), not a fixed one.
- When the visitor's address is private or loopback, as it is in local development, it falls back to the server's public address, so the page still shows something useful on your own machine.
- Optional `X-Forwarded-For` support for deployments behind a reverse proxy, off by default because the header can be forged.
- A message on the page, not a server error, when the lookup fails or is rate-limited.
- Tests that run without network access.

## Architecture

```
Browser ── GET / ──▶ location_app.views.index ──▶ geolocation.client_ip(request)
                                               ──▶ geolocation.locate(ip) ──▶ ip-api.com
        ◀── HTML ───  (renders index.html)     ◀── location record / GeolocationError
```

| Piece | Responsibility |
|---|---|
| `location_app/views.py` | Calls the lookup and renders the template |
| `location_app/geolocation.py` | Works out the visitor's public IP and queries ip-api.com; turns failures into a `GeolocationError` with a user-safe message |
| `location_app/templates/index.html` | The result page |
| `location_pro/settings.py` | Django settings, driven by environment variables |

## Technology stack

| | |
|---|---|
| Language | Python 3.10+ |
| Framework | Django 5.2 |
| HTTP client | requests |
| External API | ip-api.com (free tier, no key) |
| UI | Django templates, Bootstrap 3 (CDN) |
| Tooling | ruff, GitHub Actions |

## Project structure

```
.
├── manage.py
├── location_pro/         # Django project: settings, root URLs, WSGI/ASGI
├── location_app/         # The location app
│   ├── views.py
│   ├── geolocation.py    # ip-api.com client
│   ├── tests.py
│   └── templates/index.html
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Installation and setup

```bash
git clone https://github.com/Logesh2097/Location_project.git
cd Location_project
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit .env
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes, unless `DJANGO_DEBUG=true` | Django secret key |
| `DJANGO_DEBUG` | no (default `false`) | `true` for local development only |
| `DJANGO_ALLOWED_HOSTS` | no (default `localhost,127.0.0.1`) | Comma-separated host names |
| `TRUST_X_FORWARDED_FOR` | no (default `false`) | `true` only behind a reverse proxy you control |

No API key is needed.

## Running the application

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

The app defines no models, so no migration is needed to use it. Django will
print a notice about unapplied migrations for its built-in apps; run
`python manage.py migrate` if you want to use the admin site.

## Routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | The location page |
| | `/admin/` | Django admin |

## Testing

```bash
pip install -r requirements-dev.txt
ruff check .
python manage.py test
```

The tests replace the network call with a mock. The same commands run in
GitHub Actions on every push.

## Limitations

- IP geolocation is approximate: it usually identifies the city of the internet provider, not the visitor.
- The free tier of ip-api.com is plain `http`, is limited to 45 requests a minute, and is for non-commercial use.

## Future improvements

- Cache lookups per address to stay inside the rate limit.
- Show the location on a map.
