
import React, ( useState, useEffect ) from 'react';
import Map, (Marker, Source, Layer ) from 'react-map-gl';
import axios from 'axios';
import (format )from 'date-fns';

type Location = {
  lat: number;
  lon: number;
};

type DisasterPrediction = {
  disaster: string;
  risks: Record<string, number>;
  unit: string;
};

type Shelter = {
  id: string;
  location: Location;
  distance_km: number;
  capacity: number;
};

type EvacuationRoute = {
  recommended_shelter: Shelter;
  alternative_shelters: Shelter[];
  disaster_type: string;
};

const MAPBOX_TOKEN = 'your_mapbox_token';

const DisasterPredictionSystem: React.FC = () => {
  const [location, setLocation] = useState<Location | null>(null);
  const [predictions, setPredictions] = useState<DisasterPrediction | null>(null);
  const [route, setRoute] = useState<EvacuationRoute | null>(null);
  const [disasterType, setDisasterType] = useState<string>('earthquake');
  const [alerts, setAlerts] = useState<any[]>([]);
  const [viewState, setViewState] = useState({
    longitude: -98.5795,
    latitude: 39.8283,
    zoom: 3,
  });

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 300000); // every 5 mins
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await axios.get('http://localhost:8000/alerts');
      setAlerts([
        ...response.data.earthquakes.map((e: any) => ({ ...e, type: 'earthquake' })),
        ...response.data.weather_alerts.map((w: any) => ({ ...w, type: 'weather' })),
      ]);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  };

  const handleMapClick = async (e: any) => {
    const clickedLocation = {
      lat: e.lngLat.lat,
      lon: e.lngLat.lng,
    };
    setLocation(clickedLocation);

    try {
      const response = await axios.post('http://localhost:8000/predict', {
        location: clickedLocation,
        disaster_type: disasterType,
        time_window: 7,
      });
      setPredictions(response.data);
    } catch (error) {
      console.error('Error fetching predictions:', error);
    }
  };

  const calculateEvacuation = async () => {
    if (!location) return;
    try {
      const response = await axios.post('http://localhost:8000/evacuation', {
        start_point: location,
        disaster_type: disasterType,
        disaster_radius: 50,
      });
      setRoute(response.data);
    } catch (error) {
      console.error('Error calculating evacuation:', error);
    }
  };

  const renderRiskChart = () => {
    if (!predictions) return null;
    return (
      <div className="risk-chart">
        <h3>{predictions.disaster.toUpperCase()} Risk Prediction</h3>
        <ul>
          {Object.entries(predictions.risks).map(([date, risk]) => (
            <li key={date}>
              {format(new Date(date), 'MMM dd')}: {(risk * 100).toFixed(1)}%
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="app-container">
      <div className="sidebar">
        <h1>Disaster Prediction System</h1>
        <div className="controls">
          <select value={disasterType} onChange={(e) => setDisasterType(e.target.value)}>
            <option value="earthquake">Earthquake</option>
            <option value="flood">Flood</option>
            <option value="wildfire">Wildfire</option>
            <option value="hurricane">Hurricane</option>
          </select>

          {location && (
            <>
              <p>Selected: {location.lat.toFixed(4)}, {location.lon.toFixed(4)}</p>
              <button onClick={calculateEvacuation}>Calculate Evacuation Route</button>
              {renderRiskChart()}
            </>
          )}

          {route && (
            <div className="evacuation-info">
              <h3>Recommended Shelter</h3>
              <p>{route.recommended_shelter.distance_km.toFixed(1)} km away</p>
              <p>Capacity: {route.recommended_shelter.capacity} people</p>
            </div>
          )}
        </div>

        <div className="alerts">
          <h3>Recent Alerts</h3>
          {alerts.slice(0, 5).map((alert, i) => (
            <div key={i} className="alert-item">
              <strong>{alert.type.toUpperCase()}</strong>: {alert.event || `M${alert.magnitude}`}
            </div>
          ))}
        </div>
      </div>

      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        onClick={handleMapClick}
        mapStyle="mapbox://styles/mapbox/dark-v10"
        mapboxAccessToken={MAPBOX_TOKEN}
        style={{ width: '100%', height: '100vh' }}
      >
        {location && (
          <Marker longitude={location.lon} latitude={location.lat}>
            <div className="marker selected" />
          </Marker>
        )}

        {alerts.map((alert, i) => (
          <Marker
            key={i}
            longitude={alert.location?.lon || alert.geometry?.coordinates[0]}
            latitude={alert.location?.lat || alert.geometry?.coordinates[1]}
          >
            <div className={`marker ${alert.type}`} />
          </Marker>
        ))}

        {route && (
          <>
            <Marker
              longitude={route.recommended_shelter.location.lon}
              latitude={route.recommended_shelter.location.lat}
            >
              <div className="marker shelter" />
            </Marker>
            <Source
              id="route"
              type="geojson"
              data={{
                type: 'Feature',
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [location.lon, location.lat],
                    [route.recommended_shelter.location.lon, route.recommended_shelter.location.lat],
                  ],
                },
              }}
            >
              <Layer
                id="route"
                type="line"
                paint={{
                  'line-color': '#ff0000',
                  'line-width': 3,
                }}
              />
            </Source>
          </>
        )}
      </Map>
    </div>
  );
};

export default DisasterPredictionSystem;
