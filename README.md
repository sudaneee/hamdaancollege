# Hamdaan International College — Django Website

The public marketing website, rebuilt on Django + SQLite. Every piece of
content shown on the site — hero text, statistics, programmes, departments,
facilities, news, events, gallery photos, admission requirements, contact
details, social links — is stored in the database and editable from the
Django admin at **/django-admin/**, with no code changes required.

This phase covers the **public website only**. The student/staff/admin/
applicant portals from the earlier static MVP are intentionally not part of
this build yet — they'll be tackled as a separate phase, as agreed.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_data     # loads starter content + creates the admin user
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** for the site and
**http://127.0.0.1:8000/django-admin/** for the admin panel.

## Default admin login

```
Username: admin
Password: admin12345
```

**Change this password immediately** (Admin → Users → admin → change
password) — `seed_data` only creates it if no superuser exists yet, so
running the command again afterward won't reset it.

## What `seed_data` does

Populates the database with the same content the client already approved in
the static MVP: site settings, homepage stats, "why choose us" cards, core
values, departments, all 17 programmes, student life activities, sample
events and news articles. It's safe to re-run — it skips anything that
already exists.

**Facilities and gallery photos are intentionally left empty** — those
models require a real uploaded image, so add them yourself via
Admin → Facilities / Gallery Images once you have real campus photos.

## Editing content

Everything below is managed from `/django-admin/`, under the **Website**
section:

- **Site Settings** — hero text, admission status/session, phone numbers,
  email, address, social links, footer text. Singleton — there's only one
  record, and admin takes you straight to it.
- **About Page Content** — Who We Are, Mission, Vision, Principal's message
  (rich text editor). Also singleton.
- **Statistics** — the four animated homepage counters.
- **Why choose items** / **Core Values** — the icon-based feature cards.
- **Departments** / **Programmes** — full academic catalogue. Programme
  detail pages are generated automatically from the programme name.
- **Facilities** / **Student Life Activities**
- **News articles** — rich text editor (CKEditor 5) with image upload.
  Draft/Published status controls visibility on the site.
- **Events**
- **Gallery Categories** / **Gallery Images**
- **Contact messages** — submissions from the public contact form land here.
- **Applications** — submissions from the public Apply Now form, including
  uploaded documents. Status and payment status are editable per row.

Icon fields (e.g. on Statistics, Why Choose, Core Values, Departments,
Student Life) take a Font Awesome class name, e.g. `fa-heart-pulse` —
see https://fontawesome.com/search?o=r&m=free for the full free icon set.

## Project layout

```
hamdaan_django/
├── hamdaan_cms/        # project settings, root urls
├── website/            # the one app: models, views, forms, admin, templates
│   ├── templates/website/
│   └── management/commands/seed_data.py
├── templates/          # base.html + navbar/footer/topbar partials
├── static/website/     # css, js, logo (same design as the approved MVP)
├── media/              # uploaded images (created at runtime)
└── db.sqlite3
```
