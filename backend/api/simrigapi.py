from fastapi import (
    WebSocketDisconnect, 
    HTTPException,
    UploadFile,
    WebSocket, 
    FastAPI, 
    Request, 
    File,  
)
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from api.wsconnectionmanager import WebsocketConnectionManager
from starlette.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import FileResponse
from starlette.responses import Response
from starlette.status import HTTP_200_OK
from collections import Counter
from os import path, getenv
from typing import List
import asyncio
import shutil
import redis
import json

from api.ssegenerators import SSEGenerators
from database.database import get_db
from database import crud, schemas

class SimRigAPI:
    """
    Provides the API routes and methods to interact with the entire application
    """
    def __init__(self, queue_manager, logger):
        self.queue_manager = queue_manager
        self.log = logger

        # Load the metadata for documentation tags
        meta_path = path.dirname(path.realpath(__file__))
        tags_metadata = json.load(open(path.join(meta_path, "tags_metadata.json")))

        # Create a manager for websocket connections
        self.ws_connection_manager = WebsocketConnectionManager()

        # Set up the API
        self.api = FastAPI(
            title="SimRig Manager API", 
            openapi_tags=tags_metadata
        )

        # Connect to Redis
        self.redis_store = redis.Redis(
            host=getenv("REDIS_HOST", "127.0.0.1"), 
            charset="utf-8", 
            decode_responses=True
        )

        # Configure CORS
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register endpoints
        self.api.get("/", response_model=schemas.Availability, tags=["availability"])(self.get_root)

        self.api.get("/latest", tags=["iracing data"])(self.get_latest)
        self.api.websocket("/stream")(self.data_stream)

        self.api.get("/drivers", response_model=List[schemas.Driver], tags=["drivers"])(self.get_drivers)
        self.api.post("/drivers", response_model=schemas.Driver, tags=["drivers"])(self.create_driver)
        self.api.patch("/drivers", response_model=schemas.Driver, tags=["drivers"])(self.update_driver)
        self.api.delete("/drivers", response_model=schemas.Driver, tags=["drivers"])(self.delete_driver)

        self.api.get(
            "/driverstats/{driver_id}", 
            response_model=schemas.DriverStats, 
            tags=["driverstats"])(self.get_driver_stats)

        self.api.get("/activedriver", tags=["drivers"], response_model=schemas.Driver)(self.get_active_driver)
        self.api.post("/activedriver", tags=["drivers"], response_model=schemas.Driver)(self.set_active_driver)

        self.api.get("/scores", tags=["scores"], response_model=List[schemas.LapTime])(self.get_scores)
        self.api.post("/scores", tags=["scores"], response_model=schemas.LapTime)(self.create_score)

        self.api.get("/controllers", tags=["controllers"], response_model=List[schemas.LightController])(self.get_controllers)
        self.api.post("/controllers", tags=["controllers"], response_model=schemas.LightController)(self.create_controller)
        self.api.patch("/controllers", tags=["controllers"], response_model=schemas.LightController)(self.update_controller)
        self.api.delete("/controllers", tags=["controllers"], response_model=schemas.LightController)(self.delete_controller)

        self.api.get("/controllersettings", tags=["controllersettings"], response_model=schemas.LightControllerSettings)(self.get_controller_settings)
        self.api.post("/controllersettings", tags=["controllersettings"], response_model=schemas.LightControllerSettings)(self.create_controller_settings)
        self.api.patch("/controllersettings", tags=["controllersettings"], response_model=schemas.LightControllerSettings)(self.update_controller_settings)

        self.api.get("/randomquote", tags=["quotes"], response_model=schemas.Quote)(self.get_random_quote)
        self.api.get("/quotes", tags=["quotes"], response_model=List[schemas.Quote])(self.get_quotes)
        self.api.post("/quotes", tags=["quotes"], response_model=schemas.Quote)(self.create_quote)
        self.api.patch("/quotes", tags=["quotes"], response_model=schemas.Quote)(self.update_quote)
        self.api.delete("/quotes", tags=["quotes"], response_model=schemas.Quote)(self.delete_quote)

        self.api.post("/avatars/{driver_id}", tags=["avatars"])(self.upload_avatar)
        self.api.get("/avatars/{driver_id}", tags=["avatars"])(self.get_avatar)

        self.api.get("/streamlaptimes", tags=["scores"])(self.stream_lap_times)
        self.api.get("/streamactivedriver", tags=["drivers"])(self.stream_active_driver)

    async def get_root(self):
        """
        Availability check 
        """
        return {"active": True}

    async def get_controllers(self, skip: int = 0, limit: int = -1):
        """
        Get all WLED light controllers
        """
        db = next(get_db())
        controllers = crud.get_light_controllers(db, skip=skip, limit=limit)

        return controllers

    async def get_controller_settings(self, controllerId: int, driverId: int):
        """
        Get controller settings linked to a driver profile
        """
        db = next(get_db())
        controller_settings = crud.get_controller_settings(db, controllerId, driverId)

        return controller_settings

    async def create_controller_settings(db, controller_settings: schemas.LightControllerSettingsCreate):
        """
        Create a settings profile for a light controller
        """
        db = next(get_db())
        new_controller_settings = crud.create_controller_settings(
            db, 
            controller_settings
        )

        return new_controller_settings

    async def update_controller_settings(db, controller_settings: schemas.LightControllerSettingsUpdate):
        """
        Update settings profile for a light controller
        """
        db = next(get_db())
        new_controller_settings = crud.update_controller_settings(
            db, 
            controller_settings
        )

        return new_controller_settings

    async def create_controller(self, controller: schemas.LightControllerCreate):
        """
        Create a new WLED light controller
        """
        db = next(get_db())
        new_controller = crud.create_light_controller(db, controller)

        return new_controller

    async def update_controller(self, controller: schemas.LightControllerUpdate):
        """
        Update controller information
        """
        db = next(get_db())
        updated_controller = crud.update_light_controller(db, controller)

        return updated_controller

    async def delete_controller(self, controller: schemas.LightControllerDelete):
        """
        Delete a light controller
        """
        db = next(get_db())
        result = crud.delete_light_controller(db, controller)

        return result

    async def get_latest(self, raw=False):
        """
        Get a snapshot of the latest iRacing data
        """
        return self.__get_iracing_data(raw=raw)

    async def data_stream(self, websocket: WebSocket):
        """
        Stream current iRacing data over a websocket connection. 
        TODO Get framerate from user config.
        """
        await self.ws_connection_manager.connect(websocket)

        try:
            while True:
                await websocket.receive_text()
                
                data = self.__get_iracing_data(raw=True)
                
                if data:
                    await self.ws_connection_manager.send_json(data, websocket)

                await asyncio.sleep(0.03)
        except (
            WebSocketDisconnect, 
            ConnectionClosedError, 
            ConnectionClosedOK, 
            RuntimeError
        ):
            await self.ws_connection_manager.disconnect(websocket)
            return

    async def create_driver(self, driver: schemas.DriverCreate):
        """
        Create a new driver
        """
        db = next(get_db())
        new_driver = crud.create_driver(db, driver)

        return new_driver

    async def get_drivers(self, skip: int = 0, limit: int = -1):
        """
        Get all drivers
        """
        db = next(get_db())
        drivers = crud.get_drivers(db, skip=skip, limit=limit)

        return drivers

    async def update_driver(self, driver: schemas.DriverUpdate):
        """
        Update driver information
        """
        db = next(get_db())
        updated_driver = crud.update_driver(db, driver)

        self.__update_driver_cache(updated_driver)

        return updated_driver

    async def delete_driver(self, driver: schemas.DriverDelete):
        """
        Delete a driver
        """
        db = next(get_db())
        result = crud.delete_driver(db, driver)

        return result

    async def get_active_driver(self):
        """
        Get the active driver, checking for a cached driver in the Redis
        store first. If there is no driver cached, try the database.
        """
        try:
            active_driver = json.loads(self.redis_store.get("active_driver"))
        except (redis.exceptions.ConnectionError, TypeError):
            db = next(get_db())
            active_driver_object = crud.get_active_driver(db)

            if active_driver_object:
                active_driver = active_driver_object.driver
            else:
                # No active driver, empty response
                return Response(status_code=HTTP_200_OK)

        return active_driver

    async def set_active_driver(self, driver: schemas.ActiveDriverCreate):
        """
        Select the active driver
        """
        db = next(get_db())
        crud.delete_active_driver(db)
        new_active_driver = crud.set_active_driver(db, driver)
        self.queue_manager.put("active_driver", new_active_driver.driver)

        # Update cache for worker threads
        self.__update_driver_cache(new_active_driver.driver)

        return new_active_driver.driver

    async def get_driver_stats(self, driver_id: int):
        """
        Get overall stats for a driver:
            - Track time
            - Records held
            - Track with most records
            - TODO laps turned, max speed, favorite tracks
        """
        db = next(get_db())
        track_time = crud.get_driver_by_id(db, driver_id).trackTime
        laptimes = [
            time for time in crud.get_laptimes(db) 
            if time.driverId == driver_id
        ]
        records_held = len(laptimes)
        track_map = Counter(getattr(time, 'trackName') for time in laptimes)
        favorite_track = max(track_map, key=track_map.get)

        return schemas.DriverStats(**{
            "trackTime": track_time, 
            "recordsHeld": records_held, 
            "favoriteTrack": favorite_track
        })

    async def get_scores(self, skip: int = 0, limit: int = -1):
        """
        Get the current best lap times
        """
        db = next(get_db())
        laptimes = crud.get_laptimes(db, skip=skip, limit=limit)

        return laptimes

    async def create_score(self, laptime: schemas.LapTimeCreate):
        """
        Log a new lap time. Only gets commited if it's a personal best.
        """
        db = next(get_db())
        new_laptime = crud.create_laptime(db, laptime)

        # Update redis key for streaming
        try:
            self.redis_store.set(
                "session_best_lap", 
                schemas.LapTime(**new_laptime.__dict__).json()
            )
        except redis.exceptions.ConnectionError:
            self.log.error("Could not connect to Redis server")

        return new_laptime

    async def get_quotes(self, skip: int = 0, limit: int = -1):
        """
        Get all racing quotes
        """
        db = next(get_db())
        quotes = crud.get_quotes(db, skip=skip, limit=limit)

        return quotes

    async def get_random_quote(self):
        """
        Get a random racing quote
        """
        db = next(get_db())
        quote = crud.get_random_quote(db)

        return quote

    async def create_quote(self, quote: schemas.QuoteCreate):
        """
        Create a new quote
        """
        db = next(get_db())
        new_quote = crud.create_quote(db, quote)

        return new_quote

    async def update_quote(self, quote: schemas.QuoteUpdate):
        """
        Update a quote
        """
        db = next(get_db())
        updated_quote = crud.update_quote(db, quote)

        return updated_quote

    async def delete_quote(self, quote: schemas.QuoteDelete):
        """
        Delete a quote
        """
        db = next(get_db())
        result = crud.delete_quote(db, quote)

        return result

    async def upload_avatar(self, driver_id: int, profile_pic: UploadFile=File(...)):
        """
        Upload a new driver profile picture
        """
        file_location = f"userdata/images/{driver_id}-avatar.png"
        
        # Update driver profile with link to new avatar image
        data = {
            "id": driver_id, 
            "profilePic": f"http://127.0.0.1:8000/avatars/{driver_id}"
        }
        driver = schemas.DriverUpdate(**data)
        
        db = next(get_db())
        updated_driver = crud.update_driver(db, driver)

        self.__update_driver_cache(updated_driver)

        # Save the image file
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(profile_pic.file, file_object)

        return {"success": "image upload completed"}

    async def get_avatar(self, driver_id: int):
        """
        Get a driver's profile picture
        """
        avatar_path = f"userdata/images/{driver_id}-avatar.png"
        if not path.exists(avatar_path):
            raise HTTPException(
                status_code=400, 
                detail=f"No avatar found for driver with id {driver_id}"
            )

        return FileResponse(f"userdata/images/{driver_id}-avatar.png")

    async def stream_lap_times(self, request: Request):
        """
        Stream new lap times via server sent events
        """
        event_generator = SSEGenerators.get_generator(request, "laptimes")
        return EventSourceResponse(event_generator)

    async def stream_active_driver(self, request: Request):
        """
        Stream active driver changes via server sent events
        """
        event_generator = SSEGenerators.get_generator(request, "active_driver")
        return EventSourceResponse(event_generator)

    def __get_iracing_data(self, raw=False):
        """
        Helper function to retrieve iRacing data from Redis
        """
        data = {}

        try:
            if raw or raw == "true":
                data = json.loads(self.redis_store.get("session_data_raw"))
            else:
                data = json.loads(self.redis_store.get("session_data_raw"))
        except (redis.exceptions.ConnectionError, TypeError):
            data = {}

        return data

    def __update_driver_cache(self, driver):
        """
        Helper function to update the active driver in the Redis cache
        """
        try:
            self.redis_store.set(
                "active_driver", 
                schemas.Driver(**driver.__dict__).json()
            )
            return True
        except redis.exceptions.ConnectionError:
            self.log.error("Could not connect to Redis server")
            return False
