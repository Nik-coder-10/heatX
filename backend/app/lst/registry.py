from dataclasses import dataclass, field
from .exceptions import SatelliteNotSupportedError


@dataclass
class ThermalBandInfo:
    band_name: str
    effective_wavelength: float
    k1: float
    k2: float
    ml: float
    al: float
    resolution: float


@dataclass
class SatelliteDefinition:
    name: str
    full_name: str
    thermal_bands: dict[str, ThermalBandInfo] = field(default_factory=dict)
    reference: str = ""
    notes: str = ""


SATELLITE_REGISTRY: dict[str, SatelliteDefinition] = {}


def _register(sat: SatelliteDefinition) -> None:
    SATELLITE_REGISTRY[sat.name.lower()] = sat
    if sat.name.lower() != sat.full_name.lower():
        SATELLITE_REGISTRY[sat.full_name.lower()] = sat


_register(SatelliteDefinition(
    name="landsat8",
    full_name="Landsat-8",
    reference="USGS Landsat 8-9 Collection 2 Level 2 Science Product Guide, 2024",
    notes="TIRS Band 10 at 100 m, resampled to 30 m in Collection 2",
    thermal_bands={
        "Band10": ThermalBandInfo(
            band_name="Band10",
            effective_wavelength=10.895,
            k1=774.8853,
            k2=1321.0789,
            ml=3.3420e-4,
            al=0.1,
            resolution=100.0,
        ),
        "Band11": ThermalBandInfo(
            band_name="Band11",
            effective_wavelength=12.005,
            k1=480.8883,
            k2=1201.1442,
            ml=3.3420e-4,
            al=0.1,
            resolution=100.0,
        ),
    },
))

_register(SatelliteDefinition(
    name="landsat9",
    full_name="Landsat-9",
    reference="USGS Landsat 8-9 Collection 2 Level 2 Science Product Guide, 2024",
    notes="TIRS-2 Band 10 at 100 m, resampled to 30 m in Collection 2",
    thermal_bands={
        "Band10": ThermalBandInfo(
            band_name="Band10",
            effective_wavelength=10.895,
            k1=774.8853,
            k2=1321.0789,
            ml=3.3420e-4,
            al=0.1,
            resolution=100.0,
        ),
        "Band11": ThermalBandInfo(
            band_name="Band11",
            effective_wavelength=12.005,
            k1=480.8883,
            k2=1201.1442,
            ml=3.3420e-4,
            al=0.1,
            resolution=100.0,
        ),
    },
))

_register(SatelliteDefinition(
    name="ecostress",
    full_name="ECOSTRESS",
    reference="ECOSTRESS L2 LSTE Algorithm Specification, NASA/JPL",
    notes="Thermal infrared at 70 m resolution, multiple bands",
    thermal_bands={
        "thermal": ThermalBandInfo(
            band_name="thermal",
            effective_wavelength=10.6,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=70.0,
        ),
    },
))

_register(SatelliteDefinition(
    name="modis",
    full_name="MODIS",
    reference="Wan Z., MODIS Land Surface Temperature Products Users Guide, NASA",
    notes="Bands 31 and 32 at 1 km resolution",
    thermal_bands={
        "Band31": ThermalBandInfo(
            band_name="Band31",
            effective_wavelength=11.03,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=1000.0,
        ),
        "Band32": ThermalBandInfo(
            band_name="Band32",
            effective_wavelength=12.02,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=1000.0,
        ),
    },
))

_register(SatelliteDefinition(
    name="aster",
    full_name="ASTER",
    reference="Gillespie A. et al., ASTER Temperature/Emissivity Separation Algorithm, IEEE 1998",
    notes="5 TIR bands at 90 m resolution, TES algorithm",
    thermal_bands={
        "Band10": ThermalBandInfo(
            band_name="Band10",
            effective_wavelength=8.291,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=90.0,
        ),
        "Band11": ThermalBandInfo(
            band_name="Band11",
            effective_wavelength=8.634,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=90.0,
        ),
        "Band12": ThermalBandInfo(
            band_name="Band12",
            effective_wavelength=9.075,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=90.0,
        ),
        "Band13": ThermalBandInfo(
            band_name="Band13",
            effective_wavelength=10.657,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=90.0,
        ),
        "Band14": ThermalBandInfo(
            band_name="Band14",
            effective_wavelength=11.318,
            k1=0.0,
            k2=0.0,
            ml=0.0,
            al=0.0,
            resolution=90.0,
        ),
    },
))


def get_satellite(name: str) -> SatelliteDefinition:
    key = name.lower()
    if key not in SATELLITE_REGISTRY:
        raise SatelliteNotSupportedError(
            f"Satellite '{name}' not supported. Available: "
            f"{', '.join(sorted(SATELLITE_REGISTRY))}"
        )
    return SATELLITE_REGISTRY[key]


def get_thermal_band(satellite: str, band: str = "Band10") -> ThermalBandInfo:
    sat = get_satellite(satellite)
    for bkey, info in sat.thermal_bands.items():
        if bkey.lower() == band.lower() or info.band_name.lower() == band.lower():
            return info
    raise SatelliteNotSupportedError(
        f"Thermal band '{band}' not found for '{satellite}'. "
        f"Available: {list(sat.thermal_bands)}"
    )


def list_supported_satellites() -> list[str]:
    return sorted({s.name for s in SATELLITE_REGISTRY.values()})
