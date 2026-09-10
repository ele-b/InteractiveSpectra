import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from colour_utils import (
    get_wavelength_columns,
    reflectance_to_xyz_lab_xy,
    reflectance_to_rgb,
    delta_e2000
)

from plots import (
    reflectance_plot,
    sci_sce_plot,
    lab_plot,
    chromaticity_plot,
    cie_horseshoe_plot
)

from transmission_utils import (
    extract_spectrum,
    calculate_transmittance,
    corrected_material_transmittance,
    transmittance_to_xyz_lab_xy,
    transmittance_to_rgb,
    visible_light_transmittance,
    radiance_glass_material,
    dialux_glass_definition
)

from exports import (
    generate_radiance_material,
    generate_dialux_material
)

from reporting import generate_pdf

st.set_page_config(
    page_title="Colour Explorer",
    layout="wide"
)

st.title(
    "CM-26dG Colour Explorer"
)

uploaded_file = st.file_uploader(
    "Upload Excel file",
    type=["xlsx"]
)

if uploaded_file is None:
    st.stop()

df = pd.read_excel(uploaded_file)

wavelengths, wavelength_cols = (
    get_wavelength_columns(df)
)

illuminant = st.sidebar.selectbox(
    "Illuminant",
    ["E", "D65", "D50", "A", "FL11"]
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Spectra",
        "Colour",
        "Compare",
        "Glass",
        "Export",
        "Report"
    ]
)

with tab1:

    mode = st.selectbox(
        "SCI/SCE",
        sorted(df["Group Name"].unique())
    )

    filtered = df[
        df["Group Name"] == mode
    ]

    st.plotly_chart(
        reflectance_plot(
            filtered,
            wavelength_cols,
            wavelengths
        ),
        use_container_width=True
    )

with tab2:

    sample = st.selectbox(
        "Sample",
        sorted(df["Data Name"].unique())
    )

    sci_rows = df[
        (df["Data Name"] == sample)
        &
        (df["Group Name"] == "SCI")
    ]

    if sci_rows.empty:
        st.warning(f"No SCI measurement found for '{sample}'.")
        st.stop()

    row = sci_rows.iloc[0]

    reflectance = [
        row[c]
        for c in wavelength_cols
    ]

    XYZ, Lab, xy = (
        reflectance_to_xyz_lab_xy(
            reflectance,
            wavelengths,
            illuminant
        )
    )

    rgb = reflectance_to_rgb(
        reflectance,
        wavelengths,
        illuminant
    )

    col1, col2 = st.columns([1, 2])

    with col1:

        st.markdown(
            f"""
            <div style="
                width:220px;
                height:220px;
                background:rgb({rgb[0]},{rgb[1]},{rgb[2]});
                border:1px solid black;
                border-radius:10px;">
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### CIELAB")

        st.metric(
            "L*",
            f"{Lab[0]:.2f}"
        )

        st.metric(
            "a*",
            f"{Lab[1]:.2f}"
        )

        st.metric(
            "b*",
            f"{Lab[2]:.2f}"
        )

        st.markdown("### CIE xy")

        st.metric(
            "x",
            f"{xy[0]:.4f}"
        )

        st.metric(
            "y",
            f"{xy[1]:.4f}"
        )

    with col2:

        st.plotly_chart(
            cie_horseshoe_plot(
                sample_xy=xy,
                sample_name=str(sample)
            ),
            use_container_width=True
        )

with tab3:

    comparison_sample = st.selectbox(
        "SCI/SCE comparison sample",
        sorted(df["Data Name"].unique())
    )

    sci = df[
        (df["Data Name"] == comparison_sample)
        &
        (df["Group Name"] == "SCI")
    ]

    sce = df[
        (df["Data Name"] == comparison_sample)
        &
        (df["Group Name"] == "SCE")
    ]

    st.plotly_chart(
        sci_sce_plot(
            sci,
            sce,
            wavelength_cols,
            wavelengths
        ),
        use_container_width=True
    )

with tab4:

    st.header("Glass Analysis")

    col1, col2 = st.columns(2)

    with col1:

        reference_sample = st.selectbox(
            "White Reference",
            sorted(df["Data Name"].unique()),
            key="glass_ref"
        )

    with col2:

        glass_sample = st.selectbox(
            "Glass Measurement",
            sorted(df["Data Name"].unique()),
            key="glass_meas"
        )

    refractive_index = st.number_input(
        "Refractive Index",
        min_value=1.0,
        max_value=2.5,
        value=1.52,
        step=0.01
    )

    ref_rows = df[
        (df["Data Name"] == reference_sample)
        &
        (df["Group Name"] == "SCI")
    ]
    glass_rows = df[
        (df["Data Name"] == glass_sample)
        &
        (df["Group Name"] == "SCI")
    ]

    if ref_rows.empty:
        st.warning(f"No SCI measurement found for reference '{reference_sample}'.")
        st.stop()
    if glass_rows.empty:
        st.warning(f"No SCI measurement found for glass '{glass_sample}'.")
        st.stop()

    reference_row = ref_rows.iloc[0]
    glass_row = glass_rows.iloc[0]

    reference_spectrum = extract_spectrum(
        reference_row,
        wavelength_cols
    )

    glass_spectrum = extract_spectrum(
        glass_row,
        wavelength_cols
    )

    T_measured = calculate_transmittance(
        reference_spectrum,
        glass_spectrum
    )

    T_material = (
        corrected_material_transmittance(
            T_measured,
            refractive_index
        )
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=T_measured * 100,
            name="Measured"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=wavelengths,
            y=T_material * 100,
            name="Corrected"
        )
    )

    fig.update_layout(
        title="Glass Transmittance",
        xaxis_title="Wavelength (nm)",
        yaxis_title="Transmittance (%)",
        template="plotly_white"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    XYZ_t, Lab_t, xy_t = (
        transmittance_to_xyz_lab_xy(
            T_material,
            wavelengths,
            illuminant
        )
    )

    rgb_t = transmittance_to_rgb(
        T_material,
        wavelengths,
        illuminant
    )

    c1, c2 = st.columns([1, 2])

    with c1:

        st.markdown(
            f"""
            <div style="
                width:180px;
                height:180px;
                border:1px solid black;
                background:rgb({rgb_t[0]},{rgb_t[1]},{rgb_t[2]});
            ">
            </div>
            """,
            unsafe_allow_html=True
        )

        st.metric(
            "L*",
            f"{Lab_t[0]:.2f}"
        )

        st.metric(
            "a*",
            f"{Lab_t[1]:.2f}"
        )

        st.metric(
            "b*",
            f"{Lab_t[2]:.2f}"
        )

        vlt = (
            visible_light_transmittance(
                T_material,
                wavelengths,
                illuminant
            )
            * 100
        )

        st.metric(
            "VLT",
            f"{vlt:.1f}%"
        )

    with c2:

        st.plotly_chart(
            cie_horseshoe_plot(
                sample_xy=xy_t,
                sample_name=str(glass_sample)
            ),
            use_container_width=True
        )

    st.subheader(
        "Simulation Material Export"
    )

    rad_text = radiance_glass_material(
        f"Glass_{glass_sample}",
        T_material,
        wavelengths
    )

    dialux_text = dialux_glass_definition(
        f"Glass_{glass_sample}",
        T_material,
        wavelengths,
        illuminant,
        refractive_index
    )

    export1, export2 = st.columns(2)

    with export1:

        st.text_area(
            "Radiance",
            rad_text,
            height=180
        )

        st.download_button(
            "Download .rad",
            rad_text,
            file_name=f"{glass_sample}.rad"
        )

    with export2:

        st.text_area(
            "DIALux",
            dialux_text,
            height=180
        )

        st.download_button(
            "Download .txt",
            dialux_text,
            file_name=f"{glass_sample}_dialux.txt"
        )

with tab5:

    radiance = generate_radiance_material(
        sample,
        rgb
    )

    dialux = generate_dialux_material(
        sample,
        reflectance,
        rgb,
        row["Gloss"]
    )

    st.subheader("Radiance")

    st.text_area(
        "",
        radiance,
        height=180
    )

    st.download_button(
        "Download Radiance",
        radiance,
        file_name=f"{sample}.rad"
    )

    st.subheader("DIALux")

    st.text_area(
        "",
        dialux,
        height=180
    )

    st.download_button(
        "Download DIALux",
        dialux,
        file_name=f"{sample}_dialux.txt"
    )

with tab6:

    pdf = generate_pdf(
        sample,
        Lab,
        XYZ,
        xy,
        rgb,
        row["Gloss"]
    )

    st.download_button(
        "Download PDF",
        pdf,
        file_name=f"{sample}_report.pdf",
        mime="application/pdf"
    )
