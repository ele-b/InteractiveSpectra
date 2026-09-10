import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from colour_utils import (
    get_wavelength_columns,
    reflectance_to_xyz_lab_xy,
    reflectance_to_rgb,
    lab_to_lch,
    delta_e2000,
)

from plots import (
    reflectance_plot,
    sci_sce_plot,
    cie_horseshoe_plot,
)

from transmission_utils import (
    extract_spectrum,
    calculate_transmittance,
    corrected_material_transmittance,
    transmittance_to_xyz_lab_xy,
    transmittance_to_rgb,
    visible_light_transmittance,
    radiance_glass_material,
    dialux_glass_definition,
)

from exports import (
    generate_radiance_material,
    generate_dialux_material,
)

from reporting import generate_pdf

st.set_page_config(
    page_title="Colour Explorer",
    layout="wide",
)

st.title("CM-26dG Colour Explorer")

illuminant = st.sidebar.selectbox(
    "Illuminant",
    ["E", "D65", "D50", "A", "FL11"],
)

(
    tab_custom,
    tab_import,
    tab_opaque,
    tab_transparent,
    tab_export,
) = st.tabs(
    [
        "Custom material",
        "Import spectra",
        "Opaque material",
        "Transparent material",
        "Export",
    ]
)


# ── shared helper ─────────────────────────────────────────────────────────────


def _show_colour_metrics(Lab, LCH, rgb, xy, sample_name=""):
    """Colour patch + Lab + LCHab + RGB + CIE xy diagram."""

    col_left, col_right = st.columns([1, 2])

    with col_left:

        st.markdown(
            f"""
            <div style="
                width:200px;
                height:200px;
                background:rgb({rgb[0]},{rgb[1]},{rgb[2]});
                border:1px solid #555;
                border-radius:10px;
                margin-bottom:12px;">
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**RGB (0 – 255)**")
        c_r, c_g, c_b = st.columns(3)
        c_r.metric("R", rgb[0])
        c_g.metric("G", rgb[1])
        c_b.metric("B", rgb[2])

        st.markdown("**CIELAB**")
        st.metric("L ∗", f"{Lab[0]:.2f}")
        st.metric("a ∗", f"{Lab[1]:.2f}")
        st.metric("b ∗", f"{Lab[2]:.2f}")

        st.markdown("**CIELCHab**")
        st.metric("L ∗", f"{LCH[0]:.2f}")
        st.metric("C ∗", f"{LCH[1]:.2f}")
        st.metric("h °", f"{LCH[2]:.1f}")

        st.markdown("**CIE xy**")
        st.metric("x", f"{xy[0]:.4f}")
        st.metric("y", f"{xy[1]:.4f}")

    with col_right:

        st.plotly_chart(
            cie_horseshoe_plot(
                sample_xy=xy,
                sample_name=str(sample_name),
            ),
            use_container_width=True,
        )


# ── TAB 1: Custom material ────────────────────────────────────────────────────


with tab_custom:

    st.subheader("Custom Material")
    st.caption(
        "Drag the sliders to shape the reflectance spectrum. "
        "All colour coordinates update instantly."
    )

    CONTROL_WLS = [400, 440, 480, 520, 560, 600, 640, 700]

    slider_cols = st.columns(len(CONTROL_WLS))
    control_values = {}

    for col, wl in zip(slider_cols, CONTROL_WLS):
        with col:
            control_values[wl] = st.slider(
                f"{wl} nm",
                min_value=0,
                max_value=100,
                value=50,
                step=1,
                key=f"custom_wl_{wl}",
            )

    full_wls = list(range(360, 750, 10))
    custom_refl = np.clip(
        np.interp(
            full_wls,
            list(control_values.keys()),
            list(control_values.values()),
        ),
        0,
        100,
    )

    fig_custom = go.Figure()

    fig_custom.add_trace(
        go.Scatter(
            x=full_wls,
            y=custom_refl,
            mode="lines",
            line=dict(color="#333333", width=2),
            name="Spectrum",
        )
    )

    fig_custom.add_trace(
        go.Scatter(
            x=CONTROL_WLS,
            y=list(control_values.values()),
            mode="markers",
            marker=dict(size=10, color="crimson"),
            name="Control points",
        )
    )

    fig_custom.update_layout(
        template="plotly_white",
        xaxis_title="Wavelength (nm)",
        yaxis_title="Reflectance (%)",
        yaxis=dict(range=[0, 105]),
        height=340,
    )

    st.plotly_chart(fig_custom, use_container_width=True)

    XYZ_c, Lab_c, xy_c = reflectance_to_xyz_lab_xy(
        custom_refl.tolist(),
        full_wls,
        illuminant,
    )
    LCH_c = lab_to_lch(Lab_c)
    rgb_c = reflectance_to_rgb(
        custom_refl.tolist(),
        full_wls,
        illuminant,
    )

    _show_colour_metrics(Lab_c, LCH_c, rgb_c, xy_c, "Custom")


# ── TAB 2: Import spectra ─────────────────────────────────────────────────────


with tab_import:

    uploaded_spectra = st.file_uploader(
        "Upload CM-26dG Excel file",
        type=["xlsx"],
        key="spectra_upload",
    )

    if uploaded_spectra is None:
        st.info(
            "Upload an Excel file exported from the CM-26dG "
            "spectrophotometer to view the spectra."
        )
    else:
        df_i = pd.read_excel(uploaded_spectra)
        wls_i, wcols_i = get_wavelength_columns(df_i)

        st.session_state["df"] = df_i
        st.session_state["wavelengths"] = wls_i
        st.session_state["wavelength_cols"] = wcols_i

        st.subheader("Spectra")

        mode_i = st.selectbox(
            "Group",
            sorted(df_i["Group Name"].unique()),
            key="import_mode",
        )

        st.plotly_chart(
            reflectance_plot(
                df_i[df_i["Group Name"] == mode_i],
                wcols_i,
                wls_i,
            ),
            use_container_width=True,
        )

        st.subheader("SCI vs SCE comparison")

        cmp_sample = st.selectbox(
            "Sample",
            sorted(df_i["Data Name"].unique()),
            key="import_comparison",
        )

        sci_cmp = df_i[
            (df_i["Data Name"] == cmp_sample)
            & (df_i["Group Name"] == "SCI")
        ]
        sce_cmp = df_i[
            (df_i["Data Name"] == cmp_sample)
            & (df_i["Group Name"] == "SCE")
        ]

        st.plotly_chart(
            sci_sce_plot(sci_cmp, sce_cmp, wcols_i, wls_i),
            use_container_width=True,
        )


# ── TAB 3: Opaque material ────────────────────────────────────────────────────


with tab_opaque:

    if "df" not in st.session_state:
        st.info("Upload a file in the **Import spectra** tab first.")
    else:
        df_o = st.session_state["df"]
        wls_o = st.session_state["wavelengths"]
        wcols_o = st.session_state["wavelength_cols"]

        sample_o = st.selectbox(
            "Sample",
            sorted(df_o["Data Name"].unique()),
            key="opaque_sample",
        )

        sci_rows_o = df_o[
            (df_o["Data Name"] == sample_o)
            & (df_o["Group Name"] == "SCI")
        ]

        if sci_rows_o.empty:
            st.warning(
                f"No SCI measurement found for '{sample_o}'."
            )
        else:
            row_o = sci_rows_o.iloc[0]
            refl_o = [row_o[c] for c in wcols_o]

            XYZ_o, Lab_o, xy_o = reflectance_to_xyz_lab_xy(
                refl_o, wls_o, illuminant
            )
            LCH_o = lab_to_lch(Lab_o)
            rgb_o = reflectance_to_rgb(refl_o, wls_o, illuminant)

            st.session_state["opaque_reflectance"] = refl_o
            st.session_state["opaque_Lab"] = Lab_o
            st.session_state["opaque_XYZ"] = XYZ_o
            st.session_state["opaque_xy"] = xy_o
            st.session_state["opaque_rgb"] = rgb_o
            st.session_state["opaque_gloss"] = row_o["Gloss"]

            _show_colour_metrics(Lab_o, LCH_o, rgb_o, xy_o, sample_o)


# ── TAB 4: Transparent material ───────────────────────────────────────────────


with tab_transparent:

    st.subheader("Glass / Transparent Material Analysis")

    uploaded_glass = st.file_uploader(
        "Upload CM-26dG Excel file (white reference + glass measurements)",
        type=["xlsx"],
        key="glass_upload",
    )

    if uploaded_glass is None:
        st.info(
            "Upload an Excel file containing the white reference "
            "and glass measurements."
        )
    else:
        df_g = pd.read_excel(uploaded_glass)
        wls_g, wcols_g = get_wavelength_columns(df_g)

        col_ref, col_meas = st.columns(2)

        with col_ref:
            ref_sample = st.selectbox(
                "White Reference",
                sorted(df_g["Data Name"].unique()),
                key="glass_ref",
            )

        with col_meas:
            glass_sample = st.selectbox(
                "Glass Measurement",
                sorted(df_g["Data Name"].unique()),
                key="glass_meas",
            )

        refractive_index = st.number_input(
            "Refractive Index",
            min_value=1.0,
            max_value=2.5,
            value=1.52,
            step=0.01,
        )

        ref_rows_g = df_g[
            (df_g["Data Name"] == ref_sample)
            & (df_g["Group Name"] == "SCI")
        ]
        glass_rows_g = df_g[
            (df_g["Data Name"] == glass_sample)
            & (df_g["Group Name"] == "SCI")
        ]

        if ref_rows_g.empty:
            st.warning(
                f"No SCI measurement found for reference '{ref_sample}'."
            )
        elif glass_rows_g.empty:
            st.warning(
                f"No SCI measurement found for glass '{glass_sample}'."
            )
        else:
            ref_spectrum = extract_spectrum(ref_rows_g.iloc[0], wcols_g)
            glass_spectrum = extract_spectrum(glass_rows_g.iloc[0], wcols_g)

            T_measured = calculate_transmittance(ref_spectrum, glass_spectrum)
            T_material = corrected_material_transmittance(
                T_measured, refractive_index
            )

            fig_t = go.Figure()
            fig_t.add_trace(
                go.Scatter(
                    x=wls_g,
                    y=T_measured * 100,
                    name="Measured",
                )
            )
            fig_t.add_trace(
                go.Scatter(
                    x=wls_g,
                    y=T_material * 100,
                    name="Corrected (Fresnel)",
                )
            )
            fig_t.update_layout(
                title="Glass Transmittance",
                xaxis_title="Wavelength (nm)",
                yaxis_title="Transmittance (%)",
                template="plotly_white",
            )
            st.plotly_chart(fig_t, use_container_width=True)

            XYZ_t, Lab_t, xy_t = transmittance_to_xyz_lab_xy(
                T_material, wls_g, illuminant
            )
            LCH_t = lab_to_lch(Lab_t)
            rgb_t = transmittance_to_rgb(T_material, wls_g, illuminant)
            vlt = (
                visible_light_transmittance(T_material, wls_g, illuminant)
                * 100
            )

            col_metrics, col_plot = st.columns([1, 2])

            with col_metrics:

                st.markdown(
                    f"""
                    <div style="
                        width:180px;
                        height:180px;
                        border:1px solid #555;
                        background:rgb({rgb_t[0]},{rgb_t[1]},{rgb_t[2]});
                        border-radius:8px;
                        margin-bottom:12px;">
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("**RGB (0 – 255)**")
                cr, cg, cb = st.columns(3)
                cr.metric("R", rgb_t[0])
                cg.metric("G", rgb_t[1])
                cb.metric("B", rgb_t[2])

                st.markdown("**CIELAB**")
                st.metric("L ∗", f"{Lab_t[0]:.2f}")
                st.metric("a ∗", f"{Lab_t[1]:.2f}")
                st.metric("b ∗", f"{Lab_t[2]:.2f}")

                st.markdown("**CIELCHab**")
                st.metric("L ∗", f"{LCH_t[0]:.2f}")
                st.metric("C ∗", f"{LCH_t[1]:.2f}")
                st.metric("h °", f"{LCH_t[2]:.1f}")

                st.metric("VLT", f"{vlt:.1f} %")

            with col_plot:

                st.plotly_chart(
                    cie_horseshoe_plot(
                        sample_xy=xy_t,
                        sample_name=str(glass_sample),
                    ),
                    use_container_width=True,
                )

            st.subheader("Simulation Material Export")

            rad_text = radiance_glass_material(
                f"Glass_{glass_sample}",
                T_material,
                wls_g,
            )
            dialux_text = dialux_glass_definition(
                f"Glass_{glass_sample}",
                T_material,
                wls_g,
                illuminant,
                refractive_index,
            )

            exp1, exp2 = st.columns(2)

            with exp1:
                st.text_area("Radiance", rad_text, height=180)
                st.download_button(
                    "Download .rad",
                    rad_text,
                    file_name=f"{glass_sample}.rad",
                )

            with exp2:
                st.text_area("DIALux", dialux_text, height=180)
                st.download_button(
                    "Download .txt",
                    dialux_text,
                    file_name=f"{glass_sample}_dialux.txt",
                )


# ── TAB 5: Export ─────────────────────────────────────────────────────────────


with tab_export:

    if "opaque_rgb" not in st.session_state:
        st.info(
            "Open the **Opaque material** tab and select a sample first."
        )
    else:
        sample_e = st.session_state["opaque_sample"]
        rgb_e = st.session_state["opaque_rgb"]
        refl_e = st.session_state["opaque_reflectance"]
        Lab_e = st.session_state["opaque_Lab"]
        XYZ_e = st.session_state["opaque_XYZ"]
        xy_e = st.session_state["opaque_xy"]
        gloss_e = st.session_state["opaque_gloss"]

        st.subheader(f"Exporting: {sample_e}")

        radiance_e = generate_radiance_material(sample_e, rgb_e)
        dialux_e = generate_dialux_material(sample_e, refl_e, rgb_e, gloss_e)
        pdf_e = generate_pdf(sample_e, Lab_e, XYZ_e, xy_e, rgb_e, gloss_e)

        col_r, col_d, col_p = st.columns(3)

        with col_r:
            st.markdown("**Radiance (.rad)**")
            st.text_area("", radiance_e, height=200, key="export_rad_text")
            st.download_button(
                "Download .rad",
                radiance_e,
                file_name=f"{sample_e}.rad",
            )

        with col_d:
            st.markdown("**DIALux (.txt)**")
            st.text_area("", dialux_e, height=200, key="export_dialux_text")
            st.download_button(
                "Download .txt",
                dialux_e,
                file_name=f"{sample_e}_dialux.txt",
            )

        with col_p:
            st.markdown("**PDF Report**")
            st.download_button(
                "Download PDF",
                pdf_e,
                file_name=f"{sample_e}_report.pdf",
                mime="application/pdf",
            )
