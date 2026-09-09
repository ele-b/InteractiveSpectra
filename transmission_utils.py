import colour
import numpy as np
import pandas as pd


# ==========================================================
# Illuminants
# ==========================================================

ILLUMINANT_MAP = {
    "E": "E",
    "D65": "D65",
    "D50": "D50",
    "A": "A",
    "FL11": "FL11"
}


# ==========================================================
# Spectrum extraction
# ==========================================================

def extract_spectrum(
    row,
    wavelength_cols
):
    return np.asarray(
        [float(row[c]) for c in wavelength_cols],
        dtype=float
    )


# ==========================================================
# Measured transmittance
# ==========================================================

def calculate_transmittance(
    reference_spectrum,
    glass_spectrum
):
    """
    Measured transmittance

    Tmeas = R(glass+white) / R(white)
    """

    reference = np.asarray(
        reference_spectrum,
        dtype=float
    )

    glass = np.asarray(
        glass_spectrum,
        dtype=float
    )

    T = np.divide(
        glass,
        reference,
        out=np.zeros_like(glass),
        where=reference > 0
    )

    return np.clip(T, 0, 1)


# ==========================================================
# Fresnel correction
# ==========================================================

def fresnel_reflectance_normal(
    refractive_index=1.52
):

    n = refractive_index

    return ((n - 1) / (n + 1)) ** 2


def corrected_material_transmittance(
    measured_transmittance,
    refractive_index=1.52
):
    """
    Estimate intrinsic single-pass
    material transmittance.
    """

    Tm = np.asarray(
        measured_transmittance,
        dtype=float
    )

    Rf = fresnel_reflectance_normal(
        refractive_index
    )

    interface_T = 1 - Rf

    Tglass = (
        np.sqrt(Tm)
        /
        (interface_T ** 2)
    )

    return np.clip(
        Tglass,
        0,
        1
    )


# ==========================================================
# Colour calculations
# ==========================================================

def transmittance_to_xyz_lab_xy(
    transmittance,
    wavelengths,
    illuminant_name="D65"
):

    sd = colour.SpectralDistribution(
        dict(
            zip(
                wavelengths,
                transmittance
            )
        )
    )

    cmfs = colour.MSDS_CMFS[
        "CIE 1931 2 Degree Standard Observer"
    ]

    illuminant = (
        colour.SDS_ILLUMINANTS[
            ILLUMINANT_MAP[
                illuminant_name
            ]
        ]
    )

    XYZ = colour.sd_to_XYZ(
        sd,
        cmfs=cmfs,
        illuminant=illuminant
    )

    white_XYZ = colour.sd_to_XYZ(
        illuminant,
        cmfs=cmfs
    )

    white_xy = colour.XYZ_to_xy(
        white_XYZ
    )

    Lab = colour.XYZ_to_Lab(
        XYZ / 100,
        illuminant=white_xy
    )

    xy = colour.XYZ_to_xy(XYZ)

    return (
        np.asarray(XYZ).flatten(),
        np.asarray(Lab).flatten(),
        np.asarray(xy).flatten()
    )


# ==========================================================
# RGB preview
# ==========================================================

def transmittance_to_rgb(
    transmittance,
    wavelengths,
    illuminant_name="D65"
):

    XYZ, _, _ = (
        transmittance_to_xyz_lab_xy(
            transmittance,
            wavelengths,
            illuminant_name
        )
    )

    rgb = colour.XYZ_to_sRGB(
        XYZ / 100
    )

    rgb = np.clip(rgb, 0, 1)

    return tuple(
        (rgb * 255).astype(int)
    )


# ==========================================================
# VLT
# ==========================================================

def visible_light_transmittance(
    transmittance,
    wavelengths,
    illuminant_name="D65"
):

    T = np.asarray(
        transmittance,
        dtype=float
    )

    step = wavelengths[1] - wavelengths[0]

    shape = colour.SpectralShape(
        min(wavelengths),
        max(wavelengths),
        step
    )

    V = (
        colour.SDS_LEFS[
            "CIE 1924 Photopic Standard Observer"
        ]
        .copy()
        .align(shape)
    )

    illuminant = (
        colour.SDS_ILLUMINANTS[
            ILLUMINANT_MAP[
                illuminant_name
            ]
        ]
        .copy()
        .align(shape)
    )

    numerator = np.sum(
        T
        * V.values
        * illuminant.values
    )

    denominator = np.sum(
        V.values
        * illuminant.values
    )

    return float(
        numerator / denominator
    )


# ==========================================================
# Radiance
# ==========================================================

def radiance_glass_material(
    material_name,
    material_transmittance,
    wavelengths
):
    """
    Uses equal-energy illuminant E.
    """

    sd = colour.SpectralDistribution(
        dict(
            zip(
                wavelengths,
                material_transmittance
            )
        )
    )

    cmfs = colour.MSDS_CMFS[
        "CIE 1931 2 Degree Standard Observer"
    ]

    shape = colour.SpectralShape(
        min(wavelengths),
        max(wavelengths),
        wavelengths[1] - wavelengths[0]
    )

    illuminant_E = colour.sd_constant(
        100,
        shape
    )

    XYZ = colour.sd_to_XYZ(
        sd,
        cmfs=cmfs,
        illuminant=illuminant_E
    )

    rgb = colour.XYZ_to_sRGB(
        XYZ / 100
    )

    rgb = np.clip(rgb, 0, 1)

    return f"""void glass {material_name}
0
0
3
{rgb[0]:.4f}
{rgb[1]:.4f}
{rgb[2]:.4f}
"""


# ==========================================================
# DIALux
# ==========================================================

def dialux_glass_definition(
    material_name,
    material_transmittance,
    wavelengths,
    illuminant_name="D65",
    refractive_index=1.52
):

    vlt = (
        visible_light_transmittance(
            material_transmittance,
            wavelengths,
            illuminant_name
        )
        * 100
    )

    avg_t = (
        np.mean(material_transmittance)
        * 100
    )

    return f"""Material Name: {material_name}

Visible Light Transmittance (VLT):
{vlt:.1f} %

Average Spectral Transmittance:
{avg_t:.1f} %

Assumed Refractive Index:
{refractive_index:.2f}
"""