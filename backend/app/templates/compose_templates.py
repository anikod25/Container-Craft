import yaml, json

TEMPLATES = {
    "nginx": {
        "image": "nginx:latest",
        "ports": ["80:80"],
        "volumes": ["./nginx.conf:/etc/nginx/nginx.conf"]
    },
    "postgres": {
        "image": "postgres:latest",
        "environment": {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "password",
            "POSTGRES_DB": "mydb"
        },
        "volumes": ["postgres_data:/var/lib/postgresql/data"]
    },
    "redis": {
        "image": "redis:latest",
        "ports": ["6379:6379"],
        "volumes": ["redis_data:/data"]
    },
    "mongodb": {
        "image": "mongo:latest",
        "ports": ["27017:27017"],
        "environment": {
            "MONGO_INITDB_ROOT_USERNAME": "root",
            "MONGO_INITDB_ROOT_PASSWORD": "password"
        },
        "volumes": ["mongo_data:/data/db"]
    },
    "node": {
        "image": "node:latest",
        "ports": ["3000:3000"],
        "volumes": ["./app:/usr/src/app"],
        "working_dir": "/usr/src/app",
        "command": "npm start"
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
        "volumes": ["mysql_data:/var/lib/mysql"]
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
        "volumes": ["mariadb_data:/var/lib/mysql"]
    },
    "apache": {
        "image": "httpd:latest",
        "ports": ["80:80"],
        "volumes": ["./public-html:/usr/local/apache2/htdocs"]
    },
    "node-custom": {
        "build": ".",
        "ports": ["3000:3000"],
        "volumes": ["./app:/usr/src/app", "/usr/src/app/node_modules"],
        "environment": {
            "NODE_ENV": "development"
        },
        "command": "npm run dev"
    },
    "flask": {
        "build": ".",
        "ports": ["5000:5000"],
        "volumes": ["./app:/app"],
        "environment": {
            "FLASK_APP": "app.py",
            "FLASK_ENV": "development",
            "FLASK_DEBUG": "1"
        },
        "command": "flask run --host=0.0.0.0"
    },
    "django": {
        "build": ".",
        "ports": ["8000:8000"],
        "volumes": ["./app:/app"],
        "environment": {
            "DJANGO_SETTINGS_MODULE": "myproject.settings",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1"
        },
        "command": "python manage.py runserver 0.0.0.0:8000"
    },
}