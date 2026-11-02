from fastapi import APIRouter

from app.modules.access.operations import router as access_operations_router
from app.modules.catalog.router import router as catalog_router
from app.modules.devices.router import router as devices_router
from app.modules.dining.operations import router as dining_operations_router
from app.modules.dining.router import router as dining_router
from app.modules.operations.admin import router as administration_router
from app.modules.operations.router import router as operations_router
from app.modules.orders.router import router as orders_router
from app.modules.rooms.operations import router as rooms_operations_router
from app.modules.rooms.router import router as rooms_router
from app.modules.tickets.router import router as tickets_router
from app.modules.payments.router import router as payments_router
from app.modules.wallet.router import router as wallet_router

api_router = APIRouter()
api_router.include_router(catalog_router)
api_router.include_router(wallet_router)
api_router.include_router(payments_router)
api_router.include_router(orders_router)
api_router.include_router(tickets_router)
api_router.include_router(rooms_router)
api_router.include_router(dining_router)
api_router.include_router(dining_operations_router)
api_router.include_router(devices_router)
api_router.include_router(operations_router)
api_router.include_router(rooms_operations_router)
api_router.include_router(access_operations_router)
api_router.include_router(administration_router)
