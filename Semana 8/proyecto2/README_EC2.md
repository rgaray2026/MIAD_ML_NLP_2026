# Disponibilización del modelo en AWS EC2 con API Flask e interfaz web

## 1. Archivo principal que se debe generar desde el notebook

Antes de desplegar en EC2, ejecute en el notebook la celda incluida en `export_artifacts_cell.py`.
Esa celda genera:

```bash
movie_genre_model_artifacts.pkl
```

Ese archivo contiene:

- `vectorizador_word_final`
- `vectorizador_char_final`
- `modelo_lr_final`
- `modelo_nb_final`
- `mejor_peso_lr`
- `mejor_peso_nb`
- nombres de géneros desde `le.classes_`

## 2. Estructura esperada del proyecto

```bash
movie_genre_api/
├── app.py
├── movie_genre_model_artifacts.pkl
├── requirements.txt
└── templates/
    └── index.html
```

## 3. Probar localmente antes de subir a EC2

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abrir en el navegador:

```text
http://127.0.0.1:5000
```

Probar API:

```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"title":"Toy Story","plot":"A cowboy doll is threatened when a new spaceman toy arrives.","year":1995}'
```

## 4. Crear instancia EC2

Recomendación para el trabajo académico:

- Ubuntu Server 22.04 LTS o 24.04 LTS.
- Tipo mínimo: `t2.micro` para prueba; mejor `t3.small` o superior si el modelo pesa mucho.
- Reglas de entrada del Security Group:
  - SSH: puerto 22 solo desde su IP.
  - HTTP: puerto 80 desde `0.0.0.0/0`.
  - Opcional temporal: puerto 5000 desde su IP para pruebas.

## 5. Instalar dependencias en EC2

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx unzip
```

Subir el proyecto:

```bash
scp -i llave.pem -r movie_genre_api ubuntu@IP_PUBLICA_EC2:/home/ubuntu/
```

Entrar a EC2:

```bash
ssh -i llave.pem ubuntu@IP_PUBLICA_EC2
```

Instalar dependencias:

```bash
cd /home/ubuntu/movie_genre_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 6. Ejecutar con Gunicorn

Prueba manual:

```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

Abrir:

```text
http://IP_PUBLICA_EC2:5000
```

## 7. Crear servicio systemd

```bash
sudo nano /etc/systemd/system/moviegenre.service
```

Contenido:

```ini
[Unit]
Description=API Flask para prediccion de generos de peliculas
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/movie_genre_api
Environment="PATH=/home/ubuntu/movie_genre_api/venv/bin"
ExecStart=/home/ubuntu/movie_genre_api/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl start moviegenre
sudo systemctl enable moviegenre
sudo systemctl status moviegenre
```

## 8. Configurar Nginx para usar puerto 80

```bash
sudo nano /etc/nginx/sites-available/moviegenre
```

Contenido:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Activar configuración:

```bash
sudo ln -s /etc/nginx/sites-available/moviegenre /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Abrir:

```text
http://IP_PUBLICA_EC2
```

## 9. Evidencia para el informe

Para documentar la disponibilización, incluya capturas de:

1. Instancia EC2 en ejecución.
2. Security Group con puertos 22 y 80.
3. Servicio `moviegenre` activo.
4. Interfaz web funcionando en `http://IP_PUBLICA_EC2`.
5. Prueba de la ruta `/predict` devolviendo JSON.
6. Explicación de que el modelo y los vectorizadores se cargan una sola vez en memoria al iniciar Flask/Gunicorn.