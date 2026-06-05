# Recipe Backend API

## Estructura del proyecto

```
recipeBackend/
├── app/
│   ├── main.py                  # FastAPI app + middleware
│   ├── core/
│   │   ├── config.py            # Settings desde .env (pydantic-settings)
│   │   ├── supabase.py          # Clientes Supabase (anon + service_role)
│   │   └── dependencies.py     # Dependencias FastAPI (auth JWT, etc.)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # Router principal v1
│   │       └── endpoints/       # Un archivo por recurso/módulo
│   │           └── recipes.py
│   ├── models/                  # Representación de tablas Supabase
│   │   └── recipe.py
│   ├── schemas/                 # Pydantic: validación de input y output
│   │   └── recipe.py
│   └── services/                # Lógica de negocio + acceso a Supabase
│       └── recipe_service.py
├── .env.example
├── .gitignore
└── requirements.txt
```

## Flujo de datos

```
Request → Endpoint (api/) → Service (services/) → Supabase
                ↕                    ↕
           Schema (schemas/)    Model (models/)
```

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # Rellena tus claves de Supabase
```

## Ejecución en desarrollo

```bash
uvicorn app.main:app --reload
```

Documentación interactiva disponible en: http://localhost:8000/api/v1/docs

## Convención para agregar un nuevo módulo

1. **Model** → `app/models/<módulo>.py` — mapeo de la tabla Supabase
2. **Schema** → `app/schemas/<módulo>.py` — clases `Create`, `Update`, `Response`
3. **Service** → `app/services/<módulo>_service.py` — toda la lógica
4. **Endpoint** → `app/api/v1/endpoints/<módulo>.py` — rutas FastAPI
5. **Registrar** en `app/api/v1/router.py`
