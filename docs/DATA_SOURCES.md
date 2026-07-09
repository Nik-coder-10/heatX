# Urban Heat Mitigation Platform — Data Sources

## Landsat 8/9 (NASA/USGS)

### Overview
The Landsat program provides the longest continuous space-based record of Earth's land surface. Landsat 8 (LDCM, launched 2013) and Landsat 9 (launched 2021) carry the Operational Land Imager (OLI) and Thermal Infrared Sensor (TIRS).

### Bands

| Band | Name | Wavelength (um) | Resolution (m) | Landsat 8 | Landsat 9 |
|---|---|---|---|---|---|
| 1 | Coastal / Aerosol | 0.43-0.45 | 30 | OLI | OLI-2 |
| 2 | Blue | 0.45-0.51 | 30 | OLI | OLI-2 |
| 3 | Green | 0.53-0.59 | 30 | OLI | OLI-2 |
| 4 | Red | 0.64-0.67 | 30 | OLI | OLI-2 |
| 5 | Near-Infrared (NIR) | 0.85-0.88 | 30 | OLI | OLI-2 |
| 6 | Shortwave IR 1 (SWIR1) | 1.57-1.65 | 30 | OLI | OLI-2 |
| 7 | Shortwave IR 2 (SWIR2) | 2.11-2.29 | 30 | OLI | OLI-2 |
| 8 | Panchromatic | 0.50-0.68 | 15 | OLI | OLI-2 |
| 9 | Cirrus | 1.36-1.38 | 30 | OLI | OLI-2 |
| 10 | Thermal IR 1 (TIRS1) | 10.60-11.19 | 100 | TIRS | TIRS-2 |
| 11 | Thermal IR 2 (TIRS2) | 11.50-12.51 | 100 | TIRS | TIRS-2 |

### Resolution
- Multispectral: 30m
- Panchromatic: 15m
- Thermal: 100m (resampled to 30m in USGS products)

### Temporal Resolution
- 16-day revisit (each satellite)
- 8-day combined Landsat 8 + 9

### Access
- **USGS EarthExplorer**: https://earthexplorer.usgs.gov/
- **USGS ESPA API**: https://espa.cr.usgs.gov/
- **AWS Open Data**: s3://usgs-landsat/ (Requester Pays for some regions)
- **Google Cloud**: gs://gcp-public-data-landsat/
- **STAC API**: https://landsatlook.usgs.gov/stac/

### Products Used
- **Collection 2 Level-1**: Radiometrically calibrated and orthorectified
- **Collection 2 Level-2**: Surface reflectance (atmospherically corrected) and surface temperature
- **LandsatLook**: Browse images and metadata

## Sentinel-2 (ESA)

### Overview
Sentinel-2 is a European Space Agency (ESA) mission providing high-resolution multispectral imagery. Sentinel-2A (launched 2015) and Sentinel-2B (launched 2017) carry the MultiSpectral Instrument (MSI).

### Bands

| Band | Name | Wavelength (um) | Resolution (m) |
|---|---|---|---|
| 1 | Coastal / Aerosol | 0.443 | 60 |
| 2 | Blue | 0.490 | 10 |
| 3 | Green | 0.560 | 10 |
| 4 | Red | 0.665 | 10 |
| 5 | Vegetation Red Edge 1 | 0.705 | 20 |
| 6 | Vegetation Red Edge 2 | 0.740 | 20 |
| 7 | Vegetation Red Edge 3 | 0.783 | 20 |
| 8 | Near-Infrared (NIR) | 0.842 | 10 |
| 8A | Narrow NIR | 0.865 | 20 |
| 9 | Water Vapour | 0.945 | 60 |
| 10 | SWIR - Cirrus | 1.375 | 60 |
| 11 | SWIR 1 | 1.610 | 20 |
| 12 | SWIR 2 | 2.190 | 20 |

### Resolution
- 10m: B2, B3, B4, B8
- 20m: B5, B6, B7, B8A, B11, B12
- 60m: B1, B9, B10

### Temporal Resolution
- 5-day revisit at equator (combined A + B)
- 2-3 day revisit at mid-latitudes

### Access
- **ESA Copernicus Open Access Hub**: https://scihub.copernicus.eu/
- **AWS Open Data**: s3://sentinel-s2-l2a/
- **Google Cloud**: gs://gcp-public-data-sentinel-2/
- **Microsoft Planetary Computer**: https://planetarycomputer.microsoft.com/
- **STAC API**: https://earth-search.aws.element84.com/v1

### Products Used
- **Level-1C**: Top-of-atmosphere reflectance (orthorectified)
- **Level-2A**: Bottom-of-atmosphere reflectance (atmospherically corrected via Sen2Cor)

### Note on Thermal Infrared
Sentinel-2 MSI does not have thermal bands. For LST retrieval, Sentinel-2 data must be paired with Landsat TIR data or downscaled using thermal sharpening methods.

## ISRO Bhuvan

### Overview
Bhuvan is the Indian Geo-Platform of ISRO (Indian Space Research Organisation), providing satellite imagery and geospatial data products for the Indian subcontinent.

### Data Products

| Product | Source Satellite | Resolution | Coverage |
|---|---|---|---|
| Ortho imagery | Resourcesat-2/2A LISS-IV | 5.8m | India |
| Multi-spectral | Resourcesat-2/2A LISS-III | 23.5m | India |
| Multi-spectral | Resourcesat-2/2A AWiFS | 56m | India |
| Hyperspectral | HySIS | 30m | India |
| Thermal | Resourcesat-2 TIS | Not publicly available | India |
| CartoDEM v3 | Cartosat-1 | 10m | India + global |
| Land Use / Land Cover | Multi-source | 1:50,000 scale | India |
| Wasteland | Multi-source | 1:50,000 scale | India |
| Urban sprawl | Multi-source | 1:50,000 scale | India (major cities) |

### Access
- **Bhuvan Portal**: https://bhuvan.nrsc.gov.in/
- **Bhuvan API**: https://bhuvan.nrsc.gov.in/api/
- **Web Map Services (WMS/WMTS)**: OGC-compliant services for visualization
- **Data download**: Requires registration; some products restricted
- **ISRO's VEDAS**: https://vedas.sac.gov.in/ (visualization and analytics)

### Licensing
Bhuvan data is free for non-commercial research and educational use within India. Commercial use requires licensing through NSRC (National Remote Sensing Centre).

## OpenStreetMap (Land Use / Land Cover)

### Overview
OpenStreetMap (OSM) is a collaborative, open-source geographic database providing vector data for land use, land cover, buildings, roads, waterways, and administrative boundaries.

### Data Used
- **Land use polygons**: residential, commercial, industrial, agricultural, forest, park, recreational
- **Buildings**: footprints, height (where available), type
- **Roads**: classification, width, surface type
- **Water bodies**: rivers, lakes, reservoirs, ponds
- **Green spaces**: parks, gardens, tree cover
- **Administrative boundaries**: ward, district, city boundaries

### Access Methods
- **Overpass API**: `https://overpass-api.de/api/interpreter` (query-based extraction)
- **Planet.osm**: Full planet dump (weekly)
- **BBBike**: Regional extracts at https://download.bbbike.org/osm/
- **Geofabrik**: Regional extracts at https://download.geofabrik.de/
- **Osmosis**: Command-line tool for processing OSM data
- **OSMnx**: Python library for downloading and analyzing OSM data

### Resolution / Accuracy
- Varies by region; typically 5-20m positional accuracy in urban areas
- Completeness is high (90%+) for urban areas, lower for rural
- Building footprints: 70-95% complete depending on city

### Licensing
OpenStreetMap data is licensed under the Open Database License (ODbL). Attribution required: "(c) OpenStreetMap contributors". Derived data must share-alike if the database is redistributed.

## SRTM / DEM (Topography)

### Overview
The Shuttle Radar Topography Mission (SRTM) provides near-global elevation data at 30m resolution. Used for computing slope, aspect, elevation, and topographic wetness index.

### Data Products

| Product | Resolution | Coverage | Vertical Accuracy |
|---|---|---|---|
| SRTM 1-arc-second (NASA) | 30m | Global (60N-56S) | 16m (90% linear error) |
| SRTM 3-arc-second (NASA) | 90m | Global (60N-56S) | 16m |
| NASADEM | 30m | Global | Improved (MERGE of SRTM + ICE-Sat + PRISM) |
| Copernicus GLO-30 | 30m | Global (60N-60S) | 7m (90% linear error) |
| ALOS World 3D (AW3D30) | 30m | Global (82N-82S) | 5m |
| CartoDEM v3 (ISRO) | 10m | India + 6 km beyond border | 8m |

### Access
- **USGS EarthExplorer**: SRTM, NASADEM
- **OpenTopography**: https://opentopography.org/
- **ESA Copernicus**: https://panda.copernicus.eu/ (GLO-30)
- **JAXA**: https://www.eorc.jaxa.jp/ALOS/en/aw3d30/ (AW3D30)
- **ISRO Bhuvan**: CartoDEM (registration required)

## Weather Data (OpenWeatherMap)

### Overview
OpenWeatherMap provides current weather data, forecasts, and historical weather data via REST API. Used for atmospheric correction parameters and UHI contextualization.

### Data Used

| Data Type | Endpoint | Resolution | Coverage |
|---|---|---|---|
| Current weather | /weather | Station-based | Global |
| 5-day forecast | /forecast | 3-hour | Global |
| Historical | /onecall/timemachine | 1-hour | Global (back to 1979) |
| Air pollution | /air_pollution | Station-based | Global |
| Weather stations | /stations | N/A | Network |

### Relevant Parameters for Atmospheric Correction
- Surface air temperature (K)
- Atmospheric pressure (hPa)
- Relative humidity (%)
- Wind speed (m/s)
- Visibility (m)
- Cloud cover (%)

### Access
- **API**: https://api.openweathermap.org/
- **One Call API 3.0**: Recommended for historical data
- **Rate limits**: Free tier: 60 calls/min, 1,000 calls/day

### Licensing
Free tier: Non-commercial use with attribution. Commercial use requires paid subscription. Historical data access is limited on free tier.

## Data Licensing Terms Summary

| Dataset | License | Attribution Required | Commercial Use | Redistribution |
|---|---|---|---|---|
| Landsat (USGS) | Public Domain | Recommended | Yes | Yes |
| Sentinel-2 (ESA) | Copernicus License | Required (ESA Copernicus) | Yes | Yes |
| Bhuvan (ISRO) | NRSC License | Required | Restricted | Restricted |
| OSM | ODbL | Required | Yes | Share-alike |
| SRTM (NASA) | Public Domain | Recommended | Yes | Yes |
| Copernicus DEM (ESA) | Copernicus License | Required | Yes | Yes |
| OpenWeatherMap | CC BY-SA 4.0 | Required | Restricted | No |

## Citation Requirements

### General Citation Format
When publishing results derived from these data sources, include the following citations:

**Landsat**: Landsat data courtesy of the U.S. Geological Survey. DOI: 10.5066/F7SB43ZP (for Collection 2).

**Sentinel-2**: Contains modified Copernicus Sentinel data [year], processed by ESA. DOI: 10.5270/SENTINEL-2.

**Bhuvan**: Data processed by NRSC/ISRO, Government of India. Accessed via Bhuvan portal (https://bhuvan.nrsc.gov.in/).

**OSM**: (c) OpenStreetMap contributors. Available at https://www.openstreetmap.org/.

**SRTM/DEM**: NASA SRTM data. Available at https://lpdaac.usgs.gov/products/srtmgl1v003/.

**OpenWeatherMap**: Weather data (c) OpenWeatherMap. Available at https://openweathermap.org/.
