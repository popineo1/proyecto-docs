# Proyecto Docs

SaaS para **gestión, procesamiento y análisis de documentos financieros** con una arquitectura moderna basada en **FastAPI, Angular y PostgreSQL**.

El sistema permite:

- gestión **multiempresa (multi-tenant)**
- autenticación segura con **JWT**
- **subida y almacenamiento de documentos**
- **pipeline de procesamiento de documentos**
- **extracción de datos**
- generación automática de **registros financieros**
- **revisión manual de datos extraídos**
- **dashboard de métricas financieras**

---

# Arquitectura

El proyecto sigue una arquitectura **full-stack separada**:

proyecto-docs
│
├── backend → API (FastAPI)
├── frontend → Aplicación web (Angular)
└── database → PostgreSQL


---

# Tecnologías principales

| Capa | Tecnología |
|-----|-------------|
Backend | FastAPI |
Frontend | Angular |
Base de datos | PostgreSQL |
ORM | SQLAlchemy |
Migraciones | Alembic |
Autenticación | JWT |
Procesamiento documentos | Pipeline interno |
Gestión dependencias | pip / npm |

---

# Estructura del proyecto

backend
│
├── alembic → migraciones de base de datos
│
├── app
│ │
│ ├── api
│ │ └── v1
│ │ └── endpoints
│ │ ├── auth.py
│ │ ├── documents.py
│ │ ├── jobs.py
│ │ ├── financial_entries.py
│ │ └── dashboard.py
│ │
│ ├── core
│ │ ├── config.py
│ │ ├── database.py
│ │ ├── security.py
│ │ └── dependencies.py
│ │
│ ├── db
│ │ └── base.py
│ │
│ ├── models
│ │ ├── user.py
│ │ ├── tenant.py
│ │ ├── membership.py
│ │ ├── document.py
│ │ ├── job.py
│ │ ├── extraction_run.py
│ │ ├── financial_entry.py
│ │ └── audit_log.py
│ │
│ ├── schemas
│ │ ├── auth.py
│ │ ├── user.py
│ │ ├── tenant.py
│ │ ├── document.py
│ │ ├── financial_entry.py
│ │ └── dashboard.py
│ │
│ ├── repositories
│ │ └── user_repository.py
│ │
│ ├── services
│ │ ├── auth_service.py
│ │ ├── user_service.py
│ │ ├── document_service.py
│ │ ├── job_service.py
│ │ ├── extraction_service.py
│ │ ├── financial_entry_service.py
│ │ └── dashboard_service.py
│ │
│ └── main.py
│
└── requirements.txt


---

# Instalación

## 1. Clonar repositorio

```bash
git clone https://github.com/roldaan04/proyecto-docs.git
cd proyecto-docs

Backend
Crear entorno virtual
cd backend
python -m venv venv


Activar entorno virtual:

Windows
venv\Scripts\activate

Linux / Mac
source venv/bin/activate

Instalar dependencias
pip install -r requirements.txt

Variables de entorno

Crear archivo .env dentro de backend.

Ejemplo:

DATABASE_URL=postgresql://usuario:password@localhost:5432/saas_web
SECRET_KEY=supersecretkey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

Base de datos

El proyecto utiliza PostgreSQL.

Aplicar migraciones:

alembic upgrade head


Ver versión actual:

alembic current

Ejecutar backend
uvicorn app.main:app --reload


API disponible en:

http://127.0.0.1:8000


Documentación automática:

http://127.0.0.1:8000/docs

Modelo de datos principal

El sistema utiliza una arquitectura orientada a pipeline de procesamiento documental.

User
  │
Membership
  │
Tenant
  │
Document
  │
Job
  │
ExtractionRun
  │
FinancialEntry

Descripción
Modelo	Descripción
User	usuarios del sistema
Tenant	empresa / organización
Membership	relación usuario-empresa
Document	archivo subido
Job	proceso de tratamiento del documento
ExtractionRun	resultado de extracción de datos
FinancialEntry	registro financiero generado
Pipeline de procesamiento

Flujo completo del sistema:

Subir documento
      ↓
Guardar archivo
      ↓
Crear registro Document
      ↓
Crear Job de procesamiento
      ↓
Ejecutar Job
      ↓
Crear ExtractionRun
      ↓
Normalizar datos extraídos
      ↓
Crear FinancialEntry
      ↓
Revisión manual

Endpoints principales
Autenticación
Endpoint	Descripción
POST /api/v1/auth/register	registro empresa + usuario
POST /api/v1/auth/login	login
GET /api/v1/auth/me	usuario autenticado
GET /api/v1/auth/me/tenants	tenants del usuario
Documentos
Endpoint	Descripción
POST /api/v1/documents/upload	subir documento
GET /api/v1/documents	listar documentos
GET /api/v1/documents/{id}	detalle documento
GET /api/v1/documents/{id}/jobs	jobs del documento
Jobs
Endpoint	Descripción
POST /api/v1/jobs/{job_id}/run-mock	ejecutar procesamiento
Financial Entries
Endpoint	Descripción
GET /api/v1/financial-entries	listar registros financieros
GET /api/v1/financial-entries/{id}	detalle registro
PATCH /api/v1/financial-entries/{id}/review	aprobar/rechazar revisión
Dashboard
Endpoint	Descripción
GET /api/v1/dashboard/summary	métricas del tenant

Ejemplo de respuesta:

{
  "total_expenses": 159.95,
  "total_income": 0,
  "total_vat": 27.76,
  "documents_processed": 5,
  "pending_reviews": 1
}

Flujo de autenticación

1️⃣ Registrar empresa y usuario

POST /api/v1/auth/register


2️⃣ Obtener token

POST /api/v1/auth/login


3️⃣ Usar token en la API

Authorization: Bearer TOKEN


4️⃣ Seleccionar tenant

X-Tenant-Id: TENANT_UUID

Estado actual del proyecto

El backend ya implementa el MVP funcional completo del motor de procesamiento documental.

Funcionalidades implementadas:

autenticación JWT

arquitectura multi-tenant

subida y almacenamiento de documentos

pipeline de procesamiento

ejecución de jobs

extracción de datos

generación automática de registros financieros

dashboard de métricas

revisión manual de registros

Próximos pasos

Frontend MVP en Angular:

autenticación

selección de tenant

dashboard

gestión de documentos

revisión de registros financieros

Mejoras futuras backend:

OCR real

worker asíncrono (Celery / Redis)

almacenamiento cloud (S3)

clasificación automática de documentos

IA para extracción avanzada

Licencia

Proyecto privado.