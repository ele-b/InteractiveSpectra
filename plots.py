import plotly.graph_objects as go
import plotly.express as px
import colour
import numpy as np


def reflectance_plot(
    dataframe,
    wavelength_cols,
    wavelengths
):

    fig = go.Figure()

    for _, row in dataframe.iterrows():

        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=[row[c] for c in wavelength_cols],
                mode="lines",
                name=str(row["Data Name"])
            )
        )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Wavelength (nm)",
        yaxis_title="Reflectance (%)",
        height=600
    )

    return fig


def sci_sce_plot(
    sci,
    sce,
    wavelength_cols,
    wavelengths
):

    fig = go.Figure()

    if len(sci):

        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=sci.iloc[0][wavelength_cols],
                name="SCI"
            )
        )

    if len(sce):

        fig.add_trace(
            go.Scatter(
                x=wavelengths,
                y=sce.iloc[0][wavelength_cols],
                name="SCE"
            )
        )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Wavelength (nm)",
        yaxis_title="Reflectance (%)"
    )

    return fig


def lab_plot(lab_df):

    return px.scatter(
        lab_df,
        x="a*",
        y="b*",
        hover_name="Sample",
        title="CIELAB a*b*"
    )


def chromaticity_plot(xy_df):

    return px.scatter(
        xy_df,
        x="x",
        y="y",
        hover_name="Sample",
        title="CIE xy Chromaticity"
    )

import colour
import numpy as np
import plotly.graph_objects as go


def wavelength_to_rgb(wavelength):
    """
    Approximate visible wavelength to RGB.

    Returns values in range 0-255.
    """

    r = g = b = 0.0

    if 380 <= wavelength < 440:
        r = -(wavelength - 440) / (440 - 380)
        g = 0.0
        b = 1.0

    elif 440 <= wavelength < 490:
        r = 0.0
        g = (wavelength - 440) / (490 - 440)
        b = 1.0

    elif 490 <= wavelength < 510:
        r = 0.0
        g = 1.0
        b = -(wavelength - 510) / (510 - 490)

    elif 510 <= wavelength < 580:
        r = (wavelength - 510) / (580 - 510)
        g = 1.0
        b = 0.0

    elif 580 <= wavelength < 645:
        r = 1.0
        g = -(wavelength - 645) / (645 - 580)
        b = 0.0

    elif 645 <= wavelength <= 780:
        r = 1.0
        g = 0.0
        b = 0.0

    factor = 1.0

    if 380 <= wavelength < 420:
        factor = 0.3 + 0.7 * (wavelength - 380) / (420 - 380)

    elif 700 < wavelength <= 780:
        factor = 0.3 + 0.7 * (780 - wavelength) / (780 - 700)

    r = int(255 * r * factor)
    g = int(255 * g * factor)
    b = int(255 * b * factor)

    return f"rgb({r},{g},{b})"


def cie_horseshoe_plot(
    sample_xy=None,
    sample_name=None
):

    cmfs = colour.MSDS_CMFS[
        "CIE 1931 2 Degree Standard Observer"
    ]

    wavelengths = cmfs.wavelengths

    locus = []

    for wl in wavelengths:

        XYZ = cmfs[wl]

        xy = colour.XYZ_to_xy(XYZ)

        locus.append(
            (
                wl,
                xy[0],
                xy[1]
            )
        )

    fig = go.Figure()

    # coloured spectral locus

    for i in range(len(locus) - 1):

        wl, x1, y1 = locus[i]
        _, x2, y2 = locus[i + 1]

        fig.add_trace(
            go.Scatter(
                x=[x1, x2],
                y=[y1, y2],
                mode="lines",
                line=dict(
                    color=wavelength_to_rgb(wl),
                    width=4
                ),
                hoverinfo="text",
                text=[f"{wl:.0f} nm"],
                showlegend=False
            )
        )

    # purple line

    fig.add_trace(
        go.Scatter(
            x=[
                locus[-1][1],
                locus[0][1]
            ],
            y=[
                locus[-1][2],
                locus[0][2]
            ],
            mode="lines",
            line=dict(
                color="purple",
                width=3,
                dash="solid"
            ),
            name="Line of Purples"
        )
    )

    # wavelength labels

    for label_wl in [
        380, 420, 460, 500,
        540, 580, 620, 700
    ]:

        idx = np.argmin(
            np.abs(wavelengths - label_wl)
        )

        _, x, y = locus[idx]

        fig.add_annotation(
            x=x,
            y=y,
            text=f"{label_wl}",
            showarrow=False,
            font=dict(size=10)
        )

    # selected sample

    if sample_xy is not None:

        fig.add_trace(
            go.Scatter(
                x=[sample_xy[0]],
                y=[sample_xy[1]],
                mode="markers+text",
                text=[sample_name],
                textposition="top center",
                marker=dict(
                    size=16,
                    color="black",
                    line=dict(
                        color="white",
                        width=2
                    )
                ),
                name="Selected sample"
            )
        )

    fig.update_layout(
        title="CIE 1931 Chromaticity Diagram",
        template="plotly_white",
        height=650,
        xaxis_title="x",
        yaxis_title="y"
    )

    fig.update_xaxes(
        range=[0, 0.8]
    )

    fig.update_yaxes(
        range=[0, 0.9],
        scaleanchor="x",
        scaleratio=1
    )

    return fig