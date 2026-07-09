from dataclasses import dataclass, field

from .exceptions import AlgorithmNotAvailableError


@dataclass
class AlgorithmDefinition:
    name: str
    description: str
    equation: str
    assumptions: list[str]
    limitations: list[str]
    expected_accuracy: str
    urban_heat_applicability: str
    required_inputs: list[str]
    optional_inputs: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.tags = self._derive_tags()

    def _derive_tags(self) -> list[str]:
        tags = ["thermal"]
        name_lower = self.name.lower()
        if "single" in name_lower:
            tags.append("single_channel")
        if "sw" in name_lower or "split" in name_lower:
            tags.append("split_window")
        if "rt" in name_lower or "radiative" in name_lower:
            tags.append("radiative_transfer")
        return tags


ALGORITHM_REGISTRY: dict[str, AlgorithmDefinition] = {}


def register_algorithm(alg: AlgorithmDefinition) -> None:
    ALGORITHM_REGISTRY[alg.name.lower()] = alg


def get_algorithm(name: str) -> AlgorithmDefinition:
    key = name.lower()
    if key not in ALGORITHM_REGISTRY:
        raise AlgorithmNotAvailableError(
            f"Algorithm '{name}' not found. Available: {list(ALGORITHM_REGISTRY)}"
        )
    return ALGORITHM_REGISTRY[key]


def list_algorithms() -> list[AlgorithmDefinition]:
    return list(ALGORITHM_REGISTRY.values())


register_algorithm(AlgorithmDefinition(
    name="SingleChannel",
    description="Single-Channel Algorithm (Jiménez-Muñoz & Sobrino 2003, 2010). "
                "Retrieves LST from a single thermal band using atmospheric correction "
                "via water vapor-dependent functions and surface emissivity.",
    equation=(
        "LST = T_b / [1 + (λ * T_b / ρ) * ln(ε)]\n"
        "where T_b = K2 / ln(K1/L + 1), λ = effective wavelength, "
        "ρ = hc/σ = 14387.77 μm·K, ε = surface emissivity"
    ),
    assumptions=[
        "Surface is Lambertian in TIR",
        "Atmospheric effects can be parameterized by water vapor content",
        "Surface emissivity known or estimated from NDVI",
        "Cloud-free atmospheric conditions",
    ],
    limitations=[
        "Requires accurate atmospheric water vapor data",
        "Single-band limits separation of temperature and emissivity",
        "Assumes uniform atmospheric conditions across scene",
        "Accuracy degrades at high water vapor (>3 g/cm²)",
    ],
    expected_accuracy="±1.5-3.0 K with good atmospheric data; ±3-5 K with default parameters",
    urban_heat_applicability="Standard approach for urban LST retrieval from Landsat data. "
                             "Adequate for UHI intensity mapping. "
                             "Urban-specific emissivity tables improve accuracy.",
    required_inputs=["thermal_radiance", "ndvi", "emissivity"],
    optional_inputs=["water_vapor", "air_temperature"],
))

register_algorithm(AlgorithmDefinition(
    name="SingleChannelRTE",
    description="Radiative Transfer Equation-based Single Channel. "
                "Inverts the full radiative transfer equation using atmospheric "
                "parameters (transmissivity, upwelling/downwelling radiance).",
    equation=(
        "L_sensor = [ε*B(T_s) + (1-ε)*L↓]*τ + L↑\n"
        "Inverted: B(T_s) = (L_sensor - L↑ - τ*(1-ε)*L↓) / (τ*ε)\n"
        "T_s = c2 / [λ * ln(c1/(λ^5 * B(T_s)) + 1)]"
    ),
    assumptions=[
        "Atmospheric profiles available or modeled",
        "Surface is Lambertian",
        "Cloud-free conditions",
    ],
    limitations=[
        "Requires atmospheric profiles (radiosonde, reanalysis, or RT model)",
        "Computationally more expensive",
        "Overly complex for many urban applications",
    ],
    expected_accuracy="±1.0-2.0 K with in-situ atmospheric profiles",
    urban_heat_applicability="Best accuracy for urban LST when atmospheric data available. "
                             "Recommended for validation studies.",
    required_inputs=["thermal_radiance", "emissivity", "transmissivity",
                     "upwelling_radiance", "downwelling_radiance"],
))

register_algorithm(AlgorithmDefinition(
    name="SplitWindow",
    description="Split-Window Algorithm (Becker & Li 1990, Wan & Dozier 1996). "
                "Uses two thermal bands to correct for atmospheric effects "
                "without external atmospheric data.",
    equation=(
        "LST = T_i + a*(T_i - T_j) + b*(T_i - T_j)^2 + c*(ε_i - ε_j) + d\n"
        "where T_i, T_j are brightness temperatures in two thermal bands, "
        "ε_i, ε_j are band-specific emissivities, a-d are coefficients"
    ),
    assumptions=[
        "Differential atmospheric absorption between two TIR bands",
        "Surface emissivity known for both bands",
        "Cloud-free conditions",
    ],
    limitations=[
        "Requires two thermal bands (not available for Landsat TIRS single-band users)",
        "Coefficients are region and atmosphere dependent",
        "Accuracy varies with viewing angle",
    ],
    expected_accuracy="±0.5-1.5 K with locally calibrated coefficients; ±2-3 K with global coefficients",
    urban_heat_applicability="Preferred for MODIS/ASTER LST. "
                             "Limited Landsat applicability (Band 11 has calibration issues).",
    required_inputs=["tir_band_i_radiance", "tir_band_j_radiance", "emissivity_i", "emissivity_j"],
    optional_inputs=["viewing_angle", "water_vapor"],
))

register_algorithm(AlgorithmDefinition(
    name="TES",
    description="Temperature-Emissivity Separation Algorithm (Gillespie et al. 1998). "
                "Simultaneously retrieves LST and emissivity from multiple TIR bands "
                "using the emissivity normalization technique.",
    equation=(
        "Iterative solution using NEM, RAT, and MMD modules.\n"
        "NEM: Estimate T from max emissivity\n"
        "RAT: Calculate alpha/residual spectrum\n"
        "MMD: Empirical relationship between spectral contrast and min emissivity"
    ),
    assumptions=[
        "Five or more thermal bands available",
        "Empirical MMD-emissivity relationship valid for scene",
        "No atmospheric effects (or atmospherically corrected)",
    ],
    limitations=[
        "Requires multiple thermal bands",
        "MMD relationship is scene-dependent",
        "Computationally intensive",
    ],
    expected_accuracy="±1.0-2.0 K for ASTER; requires ≥5 bands",
    urban_heat_applicability="Best for ASTER-based urban LST. "
                             "Not applicable to Landsat single-band data.",
    required_inputs=["tir_bands_radiance"],
))

register_algorithm(AlgorithmDefinition(
    name="MonoWindow",
    description="Mono-Window Algorithm (Qin et al. 2001). "
                "Uses near-surface air temperature and water vapor "
                "as atmospheric correction parameters.",
    equation=(
        "LST = [a*(1-C-D) + (b*(1-C-D) + C + D)*T_b - D*T_a] / C\n"
        "where C = ε*τ, D = (1-τ)*(1+(1-ε)*τ), "
        "a, b = regression coefficients, T_a = effective mean atmospheric temperature"
    ),
    assumptions=[
        "Near-surface air temperature available",
        "Atmospheric transmissivity estimated from water vapor",
        "Atmospheric temperature profile linear",
    ],
    limitations=[
        "Sensitive to air temperature accuracy",
        "Assumes linear atmospheric temperature profile",
        "Less accurate in urban-rural temperature gradients",
    ],
    expected_accuracy="±1.5-3.5 K depending on air temperature accuracy",
    urban_heat_applicability="Useful when air temperature data available from urban weather stations. "
                             "Alternative to single-channel for UHI studies.",
    required_inputs=["thermal_radiance", "emissivity", "air_temperature", "water_vapor"],
))
