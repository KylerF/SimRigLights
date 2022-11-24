from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from os import path
import json

from database import schemas
from api.utils import get_redis_store
from api.routers.rest import (
    controllers, 
    laptimes, 
    avatars, 
    drivers, 
    iracing,
    quotes,
)
from api.routers.graphql.root import graphql_app

class SimRigAPI:
    """
    Provides the API routes and methods to interact with the entire application
    """
    def __init__(self, logger):
        self.log = logger

        # Load the metadata for documentation tags
        meta_path = path.dirname(path.realpath(__file__))
        tags_metadata = json.load(
            open(
                path.join(
                    meta_path, "tags_metadata.json"
                )
            )
        )

        # Connect to Redis
        self.redis_store = get_redis_store()

        # Set up the API
        self.api = FastAPI(
            title="SimRig Manager API", 
            openapi_tags=tags_metadata
        )

        # Configure CORS
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register root endpoint
        self.api.get(
            "/", 
            response_model=schemas.Availability, 
            tags=["availability"]
        )(
            self.get_root
        )

        # Register REST routers
        self.api.include_router(avatars.router)
        self.api.include_router(controllers.router)
        self.api.include_router(drivers.router)
        self.api.include_router(iracing.router)
        self.api.include_router(laptimes.router)
        self.api.include_router(quotes.router)

        # Register GraphQL router
        self.api.include_router(graphql_app, prefix="/graphql")

    async def get_root(self):
        """
        Availability check 
        """
        return {"active": True}
