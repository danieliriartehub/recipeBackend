from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    profiles,
    wallet,
    recyclings,
    notifications,
    marketplace,
    centers,
    scans,
    rankings,
    missions,
    aliados,
    simulator,
    coupons,
    payments,
)

api_router = APIRouter()

api_router.include_router(auth.router,          prefix="/auth",          tags=["auth"])
api_router.include_router(profiles.router,      prefix="/profiles",      tags=["profiles"])
api_router.include_router(wallet.router,        prefix="/wallet",        tags=["wallet"])
api_router.include_router(recyclings.router,    prefix="/recyclings",    tags=["recyclings"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(marketplace.router,   prefix="/marketplace",   tags=["marketplace"])
api_router.include_router(centers.router,       prefix="/centers",       tags=["centers"])
api_router.include_router(scans.router,         prefix="/scans",         tags=["scans"])
api_router.include_router(rankings.router,      prefix="/rankings",      tags=["rankings"])
api_router.include_router(missions.router,      prefix="/missions",      tags=["missions"])
api_router.include_router(aliados.router,       prefix="/aliados",       tags=["aliados"])
api_router.include_router(simulator.router,     prefix="/simulator",     tags=["simulator"])
api_router.include_router(coupons.router,       prefix="/coupons",       tags=["coupons"])
api_router.include_router(payments.router,      prefix="/payments",      tags=["payments"])
