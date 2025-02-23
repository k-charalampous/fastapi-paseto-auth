from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi_paseto_auth import AuthPASETO
from fastapi_paseto_auth.exceptions import AuthPASETOException
from pydantic import BaseModel

app = FastAPI()


class User(BaseModel):
    username: str
    password: str


class Settings(BaseModel):
    authpaseto_secret_key: str = "secret"


@AuthPASETO.load_config
def get_config():
    return Settings()


@app.exception_handler(AuthPASETOException)
def authpaseto_exception_handler(request: Request, exc: AuthPASETOException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.post("/login")
def login(user: User, Authorize: AuthPASETO = Depends()):
    if user.username != "test" or user.password != "test":
        raise HTTPException(status_code=401, detail="Bad username or password")

    access_token = Authorize.create_access_token(subject=user.username)
    return {"access_token": access_token}


@app.get("/protected", operation_id="authorize")
def protected(Authorize: AuthPASETO = Depends()):
    Authorize.paseto_required()

    current_user = Authorize.get_subject()
    return {"user": current_user}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Custom title",
        version="2.5.0",
        description="This is a very custom OpenAPI schema",
        routes=app.routes,
    )

    # Custom documentation fastapi-paseto-auth
    headers = {
        "name": "Authorization",
        "in": "header",
        "required": True,
        "schema": {"title": "Authorization", "type": "string"},
    }

    # Get routes from index 4 because before that fastapi define router for /openapi.json, /redoc, /docs, etc
    # Get all router where operation_id is authorize
    router_authorize = [
        route for route in app.routes[4:] if route.operation_id == "authorize"
    ]

    for route in router_authorize:
        method = list(route.methods)[0].lower()
        try:
            # If the router has another parameter
            openapi_schema["paths"][route.path][method]["parameters"].append(headers)
        except Exception:
            # If the router doesn't have a parameter
            openapi_schema["paths"][route.path][method].update(
                {"parameters": [headers]}
            )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
