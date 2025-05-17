from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.ensemble import RandomForestClassifier
import joblib
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import aiohttp
import asyncio
from geopy.distance import great_circle
from shapely.geometry import Point
import geopandas as gpd

app = FastAPI(
    title="Disaster Prediction API",
    description="API for predicting and managing natural disasters"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models and Data Loading
class DisasterModels:
    def __init__(self):
        self.earthquake_model = load_model('models/earthquake_lstm.h5')
        self.flood_model = joblib.load('models/flood_rf.pkl')
        self.wildfire_model = joblib.load('models/wildfire_rf.pkl')
        self.hurricane_model = load_model('models/hurricane_lstm.h5')
        self.regions = gpd.read_file('data/regions.geojson')
        self.evacuation_routes = gpd.read_file('data/evacuation_routes.geojson')
        self.shelters = gpd.read_file('data/shelters.geojson')

models = DisasterModels()

# Data Models
class Location(BaseModel):
    lat: float
    lon: float

class PredictionRequest(BaseModel):
    location: Location
    disaster_type: str  # 'earthquake', 'flood', 'wildfire', 'hurricane'
    time_window: int = 7  # days

class EvacuationRequest(BaseModel):
    start_point: Location
    disaster_type: str
    disaster_radius: float  # in km

# External API Clients
class DataFetcher:
    USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    NOAA_URL = "https://api.weather.gov/alerts/active"

    async def fetch_earthquakes(self, days: int = 1) -> List[Dict]:
        params = {
            "format": "geojson",
            "starttime": (datetime.now() - timedelta(days=days)).isoformat(),
            "minmagnitude": 2.5
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.USGS_URL, params=params) as response:
                data = await response.json()
                return data.get('features', [])

    async def fetch_weather_alerts(self) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.NOAA_URL) as response:
                data = await response.json()
                return data.get('features', [])

# Prediction Services
class PredictionService:
    @staticmethod
    def prepare_earthquake_features(location: Location, dates: List[datetime]) -> np.ndarray:
        """Create time-series features for earthquake prediction"""
        features = []
        for date in dates:
            day_of_year = date.timetuple().tm_yday
            features.append([
                location.lat,
                location.lon,
                day_of_year,
                np.random.uniform(0, 10),  # simulated seismic activity
                np.random.uniform(0, 100)  # simulated depth
            ])
        return np.array([features])  # shape: (1, timesteps, features)

    @staticmethod
    def predict_earthquake(location: Location, dates: List[datetime]) -> List[float]:
        features = PredictionService.prepare_earthquake_features(location, dates)
        predictions = models.earthquake_model.predict(features)[0]
        return [float(p) for p in predictions]

    @staticmethod
    def predict_flood(location: Location) -> float:
        """Predict flood risk using terrain and weather features"""
        point = Point(location.lon, location.lat)
        region = models.regions[models.regions.geometry.contains(point)]

        if len(region) == 0:
            return 0.0

        elevation = region.iloc[0]['elevation']
        river_dist = region.iloc[0]['river_dist']
        soil_moisture = region.iloc[0]['soil_moisture']

        features = [[elevation, river_dist, soil_moisture]]
        return float(models.flood_model.predict_proba(features)[0][1])

# API Endpoints
@app.post("/predict")
async def predict_disaster(request: PredictionRequest):
    """Predict disaster risk for a location"""
    dates = [datetime.now() + timedelta(days=i) for i in range(request.time_window)]

    if request.disaster_type == 'earthquake':
        risks = PredictionService.predict_earthquake(request.location, dates)
        return {
            "disaster": "earthquake",
            "risks": dict(zip([d.isoformat() for d in dates], risks)),
            "unit": "probability"
        }

    elif request.disaster_type == 'flood':
        risk = PredictionService.predict_flood(request.location)
        return {
            "disaster": "flood",
            "risk": risk,
            "unit": "probability"
        }

    else:
        raise HTTPException(status_code=400, detail="Disaster type not supported")

@app.post("/evacuation")
async def get_evacuation_route(request: EvacuationRequest):
    """Calculate optimal evacuation route"""
    start_point = (request.start_point.lat, request.start_point.lon)

    shelters = []
    for _, shelter in models.shelters.iterrows():
        shelter_point = (shelter.geometry.y, shelter.geometry.x)
        distance = great_circle(start_point, shelter_point).km
        if distance > request.disaster_radius:
            shelters.append({
                "id": shelter['id'],
                "location": {"lat": shelter_point[0], "lon": shelter_point[1]},
                "distance_km": distance,
                "capacity": shelter['capacity']
            })

    shelters = sorted(shelters, key=lambda x: (x['distance_km'], -x['capacity']))

    if not shelters:
        raise HTTPException(status_code=404, detail="No safe shelters found within parameters")

    return {
        "recommended_shelter": shelters[0],
        "alternative_shelters": shelters[1:4],
        "disaster_type": request.disaster_type
    }

@app.get("/alerts")
async def get_realtime_alerts():
    """Fetch real-time disaster alerts"""
    data_fetcher = DataFetcher()
    earthquakes = await data_fetcher.fetch_earthquakes()
    weather_alerts = await data_fetcher.fetch_weather_alerts()

    return {
        "earthquakes": [{
            "magnitude": e['properties']['mag'],
            "location": {
                "lat": e['geometry']['coordinates'][1],
                "lon": e['geometry']['coordinates'][0]
            },
            "time": datetime.fromtimestamp(e['properties']['time'] / 1000).isoformat()
        } for e in earthquakes],
        "weather_alerts": [{
            "event": a['properties']['event'],
            "severity": a['properties']['severity'],
            "area": a['properties']['areaDesc']
        } for a in weather_alerts]
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
