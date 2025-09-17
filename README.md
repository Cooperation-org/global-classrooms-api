# global-classrooms-api
Backend service for Global Classrooms - managing environmental education projects, GoodDollar rewards, and cross-community collaboration.



### Prerequisites
- Python 3.11+
- PostgreSQL
- Git

### 1. Clone & Setup Environment
```bash
git clone <your-repo-url>
cd global-classrooms-api
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```


### 3. Environment Configuration
Create `.env` file:
```bash
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME=global_classrooms
DB_USER=username
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
```


## Quick Start Commands

```bash
# 1. Activate environment
cd global-classrooms-api
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create database
sudo -u postgres createdb global_classrooms

# 4. Run migrations
python manage.py makemigrations core
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser

# 6. Load sample data
python manage.py load_sample_data

# 7. Start server
python3 manage.py runserver
```

## Access Points

- **API Health Check:** http://127.0.0.1:8000/api/health/
- **Admin Panel:** http://127.0.0.1:8000/admin/
- **API Root:** http://127.0.0.1:8000/api/


## Development Commands

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Django shell
python manage.py shell

# Collect static files (production)
python manage.py collectstatic
```

