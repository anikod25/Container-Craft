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
    }
}