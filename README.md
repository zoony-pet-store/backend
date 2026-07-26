# Online Pet Store

Backend for an online pet store where customers can browse products, select
product variants, add items to a cart, and place orders.

## Technology Stack

- **Python:** 3.11+
- **Framework:** Django 5.2.3
- **API:** Django REST Framework
- **Database:** PostgreSQL
- **Authentication:** JWT and Google OAuth2
- **Admin panel:** Django Admin with Unfold
- **Image storage:** Cloudinary
- **Backend deployment:** Render
- **Production database:** Supabase PostgreSQL

## Project Diagram

![Online Pet Store diagram](Images/Diagram_online_pet_store.drawio.svg)

## Local Development Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd <backend-directory>
```

Replace `<repository-url>` with the backend repository URL and
`<backend-directory>` with the cloned folder name.

### 2. Create a virtual environment

#### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the environment file

Copy `.env.example` to `.env`.

#### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

#### macOS / Linux

```bash
cp .env.example .env
```

Update the local PostgreSQL credentials in `.env` when necessary.

Do not commit the `.env` file because it may contain private credentials.

### 5. Create a PostgreSQL database

Create a local PostgreSQL database named:

```text
zoony
```

Using PostgreSQL CLI:

```bash
psql -U postgres -c "CREATE DATABASE zoony;"
```

The database can also be created using pgAdmin.

Make sure the following values in `.env` match your local PostgreSQL
configuration:

```dotenv
DB_NAME=zoony
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

### 6. Apply database migrations

```bash
python manage.py migrate
```

### 7. Create an admin user

```bash
python manage.py createsuperuser
```

### 8. Run the development server

```bash
python manage.py runserver
```

The backend will be available at:

```text
http://localhost:8000
```

## Local URLs

- Django Admin: `http://localhost:8000/admin/`
- Swagger API documentation: `http://localhost:8000/api/docs/`
- Health check: `http://localhost:8000/health/`

## Frontend Integration

The local frontend is expected to run at:

```text
http://localhost:3000
```

Frontend environment variables:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000
```

The backend `.env` file should contain:

```dotenv
CORS_ALLOWED_ORIGINS=http://localhost:3000
CSRF_TRUSTED_ORIGINS=http://localhost:3000
```

Use the exact API routes defined by the backend. The project has
`APPEND_SLASH = False`, so routes with and without a trailing slash may be
treated as different URLs.

## Running Checks

Run Django system checks:

```bash
python manage.py check
```

Run tests:

```bash
python manage.py test
```

## Development Workflow

Create a separate branch for each change:

```bash
git checkout -b feature/short-task-name
```

After making changes:

```bash
git add .
git commit -m "feat: describe the change"
git push -u origin feature/short-task-name
```

Create a merge request and merge the branch after review.
