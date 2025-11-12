Revisando la estructura del proyecto y las rutas disponibles para crear el README.


[6 tools called]


Revisando los endpoints de métricas y alertas para documentar todas las rutas:


[3 tools called]


README del proyecto:

```markdown:README.md
# 🏢 SmartFloors Server

API REST para el monitoreo inteligente de edificios con detección automática de anomalías y recomendaciones generadas por IA (Gemini).

## 📋 Tabla de Contenidos

- [Características](#características)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Inicio del Proyecto](#inicio-del-proyecto)
- [Documentación de API](#documentación-de-api)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Estructura del Proyecto](#estructura-del-proyecto)

## ✨ Características

- 📊 Monitoreo de métricas en tiempo real (temperatura, humedad, energía)
- 🚨 Detección automática de anomalías
- 🤖 Recomendaciones inteligentes generadas por Gemini AI
- 📈 Análisis de tendencias y estadísticas
- 🎯 Sistema de alertas con niveles (informativa, media, crítica)
- 🏗️ Gestión de edificios, pisos y umbrales personalizados

## 🔧 Requisitos Previos

- Python 3.12 o superior
- PostgreSQL 12 o superior
- API Key de Google Gemini (opcional, para recomendaciones con IA)

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd smart_floors_server
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar dependencia adicional para Gemini (opcional)

```bash
pip install google-generativeai
```

## ⚙️ Configuración

### 1. Crear archivo `.env`

Copia el archivo `.env.example` (si existe) o crea un nuevo archivo `.env` en la raíz del proyecto:

```env
# Base de datos - Desarrollo
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smartfloors_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Base de datos - Producción (cuando ENV=prod)
POSTGRES_USER_PROD=postgres
POSTGRES_PASSWORD_PROD=tu_password_produccion
POSTGRES_DB_PROD=smartfloors_prod
POSTGRES_HOST_PROD=tu_host_produccion
POSTGRES_PORT_PROD=5432

# Entorno (dev o prod)
ENV=dev

# URL directa de base de datos (opcional, tiene prioridad)
# DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname

# Gemini AI (opcional)
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-pro
```

### 2. Configurar PostgreSQL

Asegúrate de que PostgreSQL esté corriendo y crea la base de datos:

```sql
CREATE DATABASE smartfloors_dev;
```

### 3. Ejecutar migraciones

```bash
alembic upgrade head
```

## 🚀 Inicio del Proyecto

### Modo desarrollo

```bash
python app/main.py
```

O usando uvicorn directamente:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verificar que funciona

Abre tu navegador en: `http://localhost:8000`

Deberías ver:
```json
{
  "message": "API SmartFloors activa ✅"
}
```

### Documentación interactiva

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📚 Documentación de API

### Base URL

```
http://localhost:8000/api/v1
```

---

## 🏢 Edificios (Buildings)

### `GET /api/v1/buildings/`

Lista todos los edificios.

**Respuesta:**
```json
[
  {
    "id": 1,
    "code": "A",
    "created_at": "2024-01-15T10:00:00"
  }
]
```

### `POST /api/v1/buildings/`

Crea un nuevo edificio.

**Body:**
```json
{
  "code": "B"
}
```

---

## 🏠 Pisos (Floors)

### `GET /api/v1/floors/`

Lista todos los pisos.

**Respuesta:**
```json
[
  {
    "id": 1,
    "building_id": 1,
    "name": "Piso 1",
    "number": 1,
    "created_at": "2024-01-15T10:00:00"
  }
]
```

### `POST /api/v1/floors/`

Crea un nuevo piso.

**Body:**
```json
{
  "building_id": 1,
  "name": "Piso 2",
  "number": 2
}
```

---

## 📊 Métricas (Metrics)

### `POST /api/v1/metrics/ingest`

Ingesta métricas en formato JSON (individual o batch).

**Body individual:**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "edificio": "A",
  "piso": 1,
  "temp_C": 28.5,
  "humedad_pct": 65.0,
  "energia_kW": 5.2
}
```

**Body batch:**
```json
{
  "items": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "edificio": "A",
      "piso": 1,
      "temp_C": 28.5,
      "humedad_pct": 65.0,
      "energia_kW": 5.2
    },
    {
      "timestamp": "2024-01-15T10:31:00",
      "edificio": "A",
      "piso": 1,
      "temp_C": 28.7,
      "humedad_pct": 65.5,
      "energia_kW": 5.3
    }
  ]
}
```

**Respuesta:**
```json
{
  "ingested": 2,
  "first_ts": "2024-01-15T10:30:00",
  "last_ts": "2024-01-15T10:31:00",
  "buildings": ["A"]
}
```

**Nota:** Este endpoint detecta automáticamente anomalías y crea alertas si es necesario.

### `POST /api/v1/metrics/upload-csv`

Sube métricas desde un archivo CSV.

**Formato CSV requerido:**
```csv
timestamp,edificio,piso,temp_C,humedad_pct,energia_kW
2024-01-15T10:30:00,A,1,28.5,65.0,5.2
2024-01-15T10:31:00,A,1,28.7,65.5,5.3
```

### `GET /api/v1/metrics/`

Lista métricas con filtros.

**Query Parameters:**
- `edificio` (requerido): Código del edificio
- `piso` (requerido): Número del piso
- `since` (opcional): Fecha inicio (ISO format)
- `until` (opcional): Fecha fin (ISO format)
- `limit` (opcional, default: 200): Límite de resultados
- `offset` (opcional, default: 0): Offset para paginación

**Ejemplo:**
```
GET /api/v1/metrics/?edificio=A&piso=1&limit=50
```

**Respuesta:**
```json
[
  {
    "total": 1000,
    "count": 50,
    "data": [
      {
        "timestamp": "2024-01-15T10:30:00",
        "temp_C": 28.5,
        "humedad_pct": 65.0,
        "energia_kW": 5.2
      }
    ]
  }
]
```

### `GET /api/v1/metrics/trends`

Obtiene series de tiempo para gráficas.

**Query Parameters:**
- `edificio` (requerido): Código del edificio
- `piso` (requerido): Número del piso
- `hours` (opcional, default: 4): Horas hacia atrás (1-24)

**Ejemplo:**
```
GET /api/v1/metrics/trends?edificio=A&piso=1&hours=8
```

**Respuesta:**
```json
{
  "timestamps": ["2024-01-15T10:30:00", "2024-01-15T10:31:00"],
  "temp_C": [28.5, 28.7],
  "humedad_pct": [65.0, 65.5],
  "energia_kW": [5.2, 5.3]
}
```

### `GET /api/v1/metrics/cards`

Obtiene tarjetas de estado por piso con recomendaciones.

**Query Parameters:**
- `edificio` (requerido): Código del edificio

**Ejemplo:**
```
GET /api/v1/metrics/cards?edificio=A
```

**Respuesta:**
```json
[
  {
    "piso": 1,
    "estado": "Media",
    "resumen": "Temp 28.5°C",
    "timestamp": "2024-01-15T10:30:00",
    "valores": {
      "temp_C": 28.5,
      "humedad_pct": 65.0,
      "energia_kW": 5.2
    },
    "detalle": {
      "temperatura": {
        "valor": 28.5,
        "nivel": "medium",
        "recomendacion": "Temperatura alta (28.5°C). Se recomienda activar sistemas de enfriamiento y revisar el flujo de aire."
      },
      "humedad": {
        "valor": 65.0,
        "nivel": "info",
        "recomendacion": "Humedad relativa normal"
      },
      "energia": {
        "valor": 5.2,
        "nivel": "info",
        "recomendacion": "Consumo de energía normal"
      }
    }
  }
]
```

### `GET /api/v1/metrics/alerts`

Lista alertas relacionadas con métricas (legacy, usar `/api/v1/alerts/by-building`).

**Query Parameters:**
- `edificio` (requerido): Código del edificio
- `piso` (opcional): Número del piso
- `nivel` (opcional): `info`, `medium`, `critical`
- `limit` (opcional, default: 200): Límite de resultados

---

## 🚨 Alertas (Alerts)

### `POST /api/v1/alerts/`

Crea una alerta manualmente.

**Body:**
```json
{
  "floor_id": 1,
  "variable": "temperature",
  "level": "critical",
  "status": "open",
  "message": "Temperatura crítica detectada",
  "recommendation": "Ajustar setpoint del Piso 1 a 24°C en los próximos 15 min."
}
```

### `GET /api/v1/alerts/`

Lista alertas con filtros.

**Query Parameters:**
- `floor_id` (opcional): ID del piso
- `status` (opcional): `open`, `acknowledged`, `closed`
- `level` (opcional): `info`, `medium`, `critical`
- `variable` (opcional): `temperature`, `humidity`, `energy`
- `limit` (opcional, default: 200): Límite de resultados

**Ejemplo:**
```
GET /api/v1/alerts/?status=open&level=critical&limit=50
```

### `GET /api/v1/alerts/by-building`

Lista alertas por edificio.

**Query Parameters:**
- `edificio` (requerido): Código del edificio
- `piso` (opcional): Número del piso
- `nivel` (opcional): `info`, `medium`, `critical`
- `status` (opcional): `open`, `acknowledged`, `closed`
- `limit` (opcional, default: 200): Límite de resultados

**Ejemplo:**
```
GET /api/v1/alerts/by-building?edificio=A&nivel=critical&status=open
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "timestamp": "2024-01-15T10:30:00",
    "piso": 1,
    "variable": "temperature",
    "nivel": "critical",
    "status": "open",
    "mensaje": "Temperatura crítica (30.5°C)...",
    "recomendacion": "Ajustar setpoint del Piso 1 a 24°C en los próximos 15 min."
  }
]
```

### `PATCH /api/v1/alerts/{alert_id}/status`

Actualiza el estado de una alerta.

**Query Parameters:**
- `status` (requerido): `open`, `acknowledged`, `closed`

**Ejemplo:**
```
PATCH /api/v1/alerts/1/status?status=acknowledged
```

### `GET /api/v1/alerts/stats`

Obtiene estadísticas de alertas.

**Query Parameters:**
- `edificio` (requerido): Código del edificio
- `hours` (opcional, default: 24): Horas hacia atrás (1-168)

**Ejemplo:**
```
GET /api/v1/alerts/stats?edificio=A&hours=48
```

**Respuesta:**
```json
{
  "total": 25,
  "por_nivel": {
    "critical": 5,
    "medium": 10,
    "info": 10
  },
  "por_variable": {
    "temperature": 15,
    "humidity": 7,
    "energy": 3
  },
  "por_status": {
    "open": 20,
    "acknowledged": 3,
    "closed": 2
  }
}
```

---

## 🎯 Umbrales (Thresholds)

### `GET /api/v1/thresholds/`

Lista todos los umbrales.

### `POST /api/v1/thresholds/`

Crea un nuevo umbral personalizado.

**Body:**
```json
{
  "floor_id": 1,
  "variable": "temperature",
  "lower": 18.0,
  "upper": 28.0,
  "is_active": true
}
```

---

## 📝 Ejemplos de Uso

### Ejemplo 1: Ingesta de métricas y detección automática

```bash
curl -X POST "http://localhost:8000/api/v1/metrics/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2024-01-15T10:30:00",
    "edificio": "A",
    "piso": 1,
    "temp_C": 30.5,
    "humedad_pct": 85.0,
    "energia_kW": 5.2
  }'
```

Esto automáticamente:
- Guarda la métrica
- Detecta anomalías (temperatura crítica y humedad crítica)
- Crea alertas con recomendaciones generadas por Gemini AI

### Ejemplo 2: Obtener estado de todos los pisos

```bash
curl "http://localhost:8000/api/v1/metrics/cards?edificio=A"
```

### Ejemplo 3: Obtener alertas críticas abiertas

```bash
curl "http://localhost:8000/api/v1/alerts/by-building?edificio=A&nivel=critical&status=open"
```

### Ejemplo 4: Actualizar estado de alerta

```bash
curl -X PATCH "http://localhost:8000/api/v1/alerts/1/status?status=acknowledged"
```

### Ejemplo 5: Obtener tendencias de las últimas 8 horas

```bash
curl "http://localhost:8000/api/v1/metrics/trends?edificio=A&piso=1&hours=8"
```

---

## 🏗️ Estructura del Proyecto

```
smart_floors_server/
├── alembic/                 # Migraciones de base de datos
│   └── versions/
├── app/
│   ├── api/
│   │   ├── deps.py          # Dependencias (get_db)
│   │   └── v1/
│   │       ├── endpoints/   # Endpoints de la API
│   │       │   ├── alerts.py
│   │       │   ├── buildings.py
│   │       │   ├── floors.py
│   │       │   ├── metrics.py
│   │       │   └── thresholds.py
│   │       └── router.py     # Router principal
│   ├── core/
│   │   └── config.py        # Configuración y settings
│   ├── db/
│   │   ├── models/          # Modelos SQLAlchemy
│   │   ├── schemas/         # Schemas Pydantic
│   │   └── session.py       # Sesión de BD
│   ├── services/
│   │   └── gemini_service.py # Servicio de Gemini AI
│   └── main.py              # Aplicación FastAPI
├── .env                     # Variables de entorno (no commitear)
├── .env.example             # Ejemplo de variables de entorno
├── alembic.ini              # Configuración de Alembic
├── requirements.txt         # Dependencias Python
└── README.md                # Este archivo
```

---

## 🔍 Umbrales de Alerta

### Temperatura
- **Informativa**: 26-27.9°C
- **Media**: 28-29.4°C
- **Crítica**: ≥29.5°C

### Humedad Relativa
- **Informativa**: <25% o >70%
- **Media**: <22% o >75%
- **Crítica**: <20% o >80%

---

## 🤖 Integración con Gemini AI

El sistema utiliza Google Gemini AI para generar recomendaciones accionables cuando se detectan anomalías. Las recomendaciones incluyen:

- Acciones específicas a realizar
- Tiempo estimado de ejecución
- Referencias al piso afectado

**Ejemplo de recomendación generada:**
> "Ajustar setpoint del Piso 2 a 24°C en los próximos 15 min."

Para habilitar esta funcionalidad:
1. Obtén una API key de [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Agrega `GEMINI_API_KEY` a tu archivo `.env`
3. Instala la dependencia: `pip install google-generativeai`

Si no se configura Gemini, el sistema usará recomendaciones predefinidas.

---

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL

Verifica que:
- PostgreSQL esté corriendo
- Las credenciales en `.env` sean correctas
- La base de datos exista

### Error con Gemini AI

Si ves errores relacionados con Gemini:
- Verifica que `GEMINI_API_KEY` esté configurada
- El sistema funcionará con recomendaciones predefinidas si Gemini no está disponible

### Puerto en uso

Si el puerto 8000 está ocupado:
```bash
uvicorn app.main:app --reload --port 8001
```

---

## 📄 Licencia

[Especificar licencia]

---

## 👥 Contribuidores

[Tu nombre/información]

---

## 📞 Soporte

Para problemas o preguntas, abre un issue en el repositorio.
```

El README incluye:
- Instrucciones de instalación y configuración
- Documentación de todas las rutas con ejemplos
- Ejemplos de uso con curl
- Estructura del proyecto
- Información sobre umbrales y Gemini AI
- Troubleshooting básico

¿Quieres que agregue o modifique algo?