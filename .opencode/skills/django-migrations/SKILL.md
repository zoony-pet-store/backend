---
name: django-migrations
description: Use when changing Django models or database schema.
---

# Django Migrations

## Required

After model changes

1. `python manage.py makemigrations`
2. `python manage.py makemigrations --check --dry-run`
3. `python manage.py migrate`

Never manually edit generated migrations unless requested.
