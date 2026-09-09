import numpy as np


def generate_radiance_material(
    sample,
    rgb
):

    r = rgb[0] / 255
    g = rgb[1] / 255
    b = rgb[2] / 255

    return f"""void plastic {sample}
0
0
5
{r:.3f}
{g:.3f}
{b:.3f}
0
0
"""


def generate_dialux_material(
    sample,
    reflectance,
    rgb,
    gloss
):

    average_reflectance = np.mean(
        reflectance
    )

    return f"""Material Name: {sample}

Reflectance:
{average_reflectance:.1f} %

RGB:
{rgb[0]}, {rgb[1]}, {rgb[2]}

Gloss:
{gloss:.1f}
"""