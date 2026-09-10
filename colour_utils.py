import colour
import numpy as np
import pandas as pd
import re


def get_wavelength_columns(df):

    cols = []

    for c in df.columns:

        m = re.match(r"(\d+)\[nm\]", str(c))

        if m:

            wl = int(m.group(1))

            cols.append((wl, c))

    cols.sort()

    wavelengths = [x[0] for x in cols]
    wavelength_cols = [x[1] for x in cols]

    return wavelengths, wavelength_cols


def reflectance_to_xyz_lab_xy(
    reflectance,
    wavelengths,
    illuminant_name="D65"
):

    values = np.asarray(
        reflectance,
        dtype=float
    ) / 100

    sd = colour.SpectralDistribution(
        dict(zip(wavelengths, values))
    )

    cmfs = colour.MSDS_CMFS[
        "CIE 1931 2 Degree Standard Observer"
    ]

    illuminant = colour.SDS_ILLUMINANTS[
        illuminant_name
    ]

    XYZ = colour.sd_to_XYZ(
        sd,
        cmfs=cmfs,
        illuminant=illuminant
    )

    whitepoint = (
        colour.CCS_ILLUMINANTS[
            "CIE 1931 2 Degree Standard Observer"
        ][illuminant_name]
    )

    Lab = colour.XYZ_to_Lab(
        XYZ / 100,
        whitepoint
    )

    xy = colour.XYZ_to_xy(XYZ)

    XYZ = np.asarray(XYZ).flatten()
    Lab = np.asarray(Lab).flatten()
    xy = np.asarray(xy).flatten()

    return XYZ, Lab, xy


def reflectance_to_rgb(
    reflectance,
    wavelengths,
    illuminant_name="D65"
):

    XYZ, _, _ = reflectance_to_xyz_lab_xy(
        reflectance,
        wavelengths,
        illuminant_name
    )

    rgb = colour.XYZ_to_sRGB(
        XYZ / 100
    )

    rgb = np.clip(rgb, 0, 1)

    return tuple(
        (rgb * 255).astype(int)
    )


def lab_to_lch(Lab):
    """Convert CIELAB to CIELCHab. Returns [L*, C*, h°]."""
    L, a, b = Lab[0], Lab[1], Lab[2]
    C = float(np.sqrt(a ** 2 + b ** 2))
    h = float(np.degrees(np.arctan2(b, a)) % 360)
    return np.array([L, C, h])


def delta_e2000(
    lab1,
    lab2
):

    return colour.delta_E(
        lab1,
        lab2,
        method="CIE 2000"
    )
