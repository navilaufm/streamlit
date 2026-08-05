# 🚀 Aplicaciones Streamlit & Guía Completa de Despliegue (Nginx + Systemd + PWA Móvil + GEE)

Este repositorio contiene aplicaciones web e indicadores climáticos/geoespaciales desarrollados con **Streamlit**, **Google Earth Engine (GEE)**, **Folium**, **Rasterio** y **Plotly**.

---

## 📌 Resumen de Aplicaciones Publicadas

| Aplicación | Archivo Python | Puerto | Servicio Systemd | Modo PWA | URL Pública |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mis Estaciones** | `estacion_meteo.py` | `8501` | `streamlit-estaciones.service` | ✅ Instalable (PWA) | 👉 [https://gc.meteo.tech/mis-estaciones](https://gc.meteo.tech/mis-estaciones) |
| **GEE Cuencas** | `app_gee.py` | `8502` | `streamlit-gee-cuencas.service` | 🌐 Web App | 👉 [https://gc.meteo.tech/gee-cuencas](https://gc.meteo.tech/gee-cuencas) |

---

## 📲 Configuración PWA (Progressive Web App para Móviles)

La aplicación **Mis Estaciones** está configurada como una **PWA completa**:

### ✨ Características habilitadas:
* 📲 **Instalable en pantalla de inicio:** En Android (Chrome) e iPhone/iPad (Safari).
* 🖼️ **Icono oficial personalizado:** Generado desde `https://gc.meteo.tech/images/meteo_tech.png` (iconos en 192x192, 512x512 y Apple Touch Icon 180x180).
* 🎨 **Pantalla de carga (Splash Screen):** Color de tema `#0e1117` sin mostrar la barra de navegación web.
* 🏷️ **Nombre PWA:** `"Mis Estaciones"`.

### 📂 Archivos PWA generados:
* `/home/ubuntu/projects/streamlit/pwa/manifest.json`
* `/home/ubuntu/projects/streamlit/pwa/icon-192.png`
* `/home/ubuntu/projects/streamlit/pwa/icon-512.png`
* `/home/ubuntu/projects/streamlit/pwa/apple-touch-icon.png`

---

## 🏗️ Arquitectura del Sistema

```text
[ Usuario / Celular (Android & iOS) ]
                 │ (HTTPS)
                 ▼
 [ Cloudflare ] (Terminación SSL / HTTPS)
                 │ (HTTP puerto 80)
                 ▼
  [ Nginx ] (Proxy Inverso + Inyección de Cabeceras PWA)
       ├── /pwa/             ──►  [ Archivos Estáticos PWA (Icons & Manifest) ]
       ├── /mis-estaciones  ──►  [ Streamlit App 1 ] (http://127.0.0.1:8501) (Managed by Systemd)
       └── /gee-cuencas     ──►  [ Streamlit App 2 ] (http://127.0.0.1:8502) (Managed by Systemd)
```

---

## ⚙️ Servicios de Sistema Persistentes (`systemd`)

Para que las aplicaciones se ejecuten en segundo plano y **se reconecten/levanten automáticamente si el servidor se reinicia o falla**, están configuradas como servicios de `systemd`.

### 📋 Comandos de Administración Systemd:

```bash
# Ver estado activo
sudo systemctl status streamlit-estaciones
sudo systemctl status streamlit-gee-cuencas

# Reiniciar una aplicación (ej. tras realizar cambios en el código Python)
sudo systemctl restart streamlit-estaciones
sudo systemctl restart streamlit-gee-cuencas

# Ver logs/registros en tiempo real
journalctl -u streamlit-estaciones -f
journalctl -u streamlit-gee-cuencas -f

# Ver el comando exacto que ejecuta un servicio
systemctl cat streamlit-estaciones
```

---

## 🌐 Configuración de Nginx (`/etc/nginx/sites-available/gc.meteo.tech`)

```nginx
server {
    listen 80;
    server_name gc.meteo.tech;

    location / {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Estáticos de PWA (Iconos y Manifest)
    location /pwa/ {
        alias /home/ubuntu/projects/streamlit/pwa/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # App 1: Mis Estaciones (PWA Habilitada)
    location /mis-estaciones {
        proxy_pass http://127.0.0.1:8501/mis-estaciones;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 86400;

        # Inyección PWA
        sub_filter "<head>" "<head><link rel=\"manifest\" href=\"/pwa/manifest.json\"><link rel=\"apple-touch-icon\" href=\"/pwa/apple-touch-icon.png\"><meta name=\"apple-mobile-web-app-capable\" content=\"yes\"><meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\"><meta name=\"theme-color\" content=\"#0e1117\"><meta name=\"apple-mobile-web-app-title\" content=\"Mis Estaciones\">";
        sub_filter_once on;
    }

    # App 2: GEE Cuencas
    location /gee-cuencas {
        proxy_pass http://127.0.0.1:8502/gee-cuencas;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 86400;
    }
}
```

---

## 🔑 Autenticación con Google Earth Engine (GEE)

* **Archivo de clave activa:** `ee-cydata-a4f71d1cb9dd.json`
* **Cuenta de Servicio:** `service-ee-cydata@ee-cydata.iam.gserviceaccount.com`
* **Proyecto Google Cloud:** `ee-cydata`
