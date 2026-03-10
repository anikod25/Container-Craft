import yaml, json

TEMPLATES = {
    "nginx": {
        "image": "nginx:latest",
        "ports": ["80:80"],
        "volumes": ["./nginx.conf:/etc/nginx/nginx.conf"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "0s"
        }
    },
    "postgres": {
        "image": "postgres:latest",
        "environment": {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "password",
            "POSTGRES_DB": "mydb"
        },
        "volumes": ["postgres_data:/var/lib/postgresql/data"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD-SHELL", "pg_isready -U user -d mydb"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
            "start_period": "30s"
        }
    },
    "redis": {
        "image": "redis:latest",
        "ports": ["6379:6379"],
        "volumes": ["redis_data:/data"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "redis-cli", "ping"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
            "start_period": "0s"
        }
    },
    "mongodb": {
        "image": "mongo:latest",
        "ports": ["27017:27017"],
        "environment": {
            "MONGO_INITDB_ROOT_USERNAME": "root",
            "MONGO_INITDB_ROOT_PASSWORD": "password"
        },
        "volumes": ["mongo_data:/data/db"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "30s"
        }
    },
    "node": {
        "image": "node:latest",
        "ports": ["3000:3000"],
        "volumes": ["./app:/usr/src/app"],
        "working_dir": "/usr/src/app",
        "command": "npm start",
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:3000"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "20s"
        }
    },
    "mysql": {
        "image": "mysql:latest",
        "ports": ["3306:3306"],
        "environment": {
            "MYSQL_ROOT_PASSWORD": "rootpassword",
            "MYSQL_DATABASE": "mydb",
            "MYSQL_USER": "user",
            "MYSQL_PASSWORD": "password"
        },
        "volumes": ["mysql_data:/var/lib/mysql"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "mysqladmin", "ping", "-h", "localhost"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
            "start_period": "30s"
        }
    },
    "mariadb": {
        "image": "mariadb:latest",
        "ports": ["3306:3306"],
        "environment": {
            "MARIADB_ROOT_PASSWORD": "rootpassword",
            "MARIADB_DATABASE": "mydb",
            "MARIADB_USER": "user",
            "MARIADB_PASSWORD": "password"
        },
        "volumes": ["mariadb_data:/var/lib/mysql"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
            "start_period": "30s"
        }
    },
    "apache": {
        "image": "httpd:latest",
        "ports": ["80:80"],
        "volumes": ["./public-html:/usr/local/apache2/htdocs"],
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "0s"
        }
    },

    # --- custom build templates: build is now an object, not a plain string ---
    "node-custom": {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile"
        },
        "ports": ["3000:3000"],
        "volumes": ["./app:/usr/src/app", "/usr/src/app/node_modules"],
        "environment": {
            "NODE_ENV": "development"
        },
        "command": "npm run dev",
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:3000"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "20s"
        }
    },
    "flask": {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile"
        },
        "ports": ["5000:5000"],
        "volumes": ["./app:/app"],
        "environment": {
            "FLASK_APP": "app.py",
            "FLASK_ENV": "development",
            "FLASK_DEBUG": "1"
        },
        "command": "flask run --host=0.0.0.0",
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:5000"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "20s"
        }
    },
    "django": {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile"
        },
        "ports": ["8000:8000"],
        "volumes": ["./app:/app"],
        "environment": {
            "DJANGO_SETTINGS_MODULE": "myproject.settings",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1"
        },
        "command": "python manage.py runserver 0.0.0.0:8000",
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:8000"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "20s"
        }
    },
}