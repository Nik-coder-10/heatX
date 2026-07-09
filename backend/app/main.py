import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

# OpenTelemetry (optional - only configured if endpoint is set)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    _otel_available = True
except ImportError:
    _otel_available = False

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0",
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Setup Prometheus metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health", "/health/ready", "/health/live"],
)
instrumentator.instrument(app).expose(app, endpoint="/api/v1/metrics")

# Setup OpenTelemetry
if settings.OTEL_EXPORTER_OTLP_ENDPOINT and _otel_available:
    try:
        resource = Resource.create({
            "service.name": settings.PROJECT_NAME,
            "service.version": "1.0.0",
            "deployment.environment": settings.ENVIRONMENT,
        })
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
    except Exception:
        pass  # OTEL setup failure should not crash the app

# Global exception handlers
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    app_logger = logging.getLogger("app")
    app_logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def root():
    return {
        "message": "Welcome to Urban Heat Mitigation Platform API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
    }
