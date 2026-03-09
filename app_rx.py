"""
app.py — Interactive Distance Protection R-X Plane Visualiser
=============================================================
Standalone Streamlit app.
Quadrilateral characteristics for Z1/Z2/Z3/Z4.
Live apparent impedance point driven by V, I, angle sliders.
Fault type presets, fault distance slider, Rf slider.
Load encroachment with load angle slider.
PSB blinders + animated power swing locus.
Light-blue theme: bg #e8f4fa, cards #fff, borders #7ab8d4, text #03223a.
"""

import streamlit as st
import math
import sys, os
import plotly.graph_objects as go
import time

sys.path.insert(0, os.path.dirname(__file__))
from calculations_rx import calculate_all, CONDUCTORS

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Distance Protection — Interactive R-X Visualiser",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background: #e8f4fa !important;
    color: #03223a !important;
}
.stApp { background: #e8f4fa !important; }

section[data-testid="stSidebar"] {
    background: #f0f8fc !important;
    border-right: 2px solid #7ab8d4 !important;
}
section[data-testid="stSidebar"] * { color: #0a2a42 !important; }
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stNumberInput input,
section[data-testid="stSidebar"] .stSelectbox select {
    background: #fff !important; border: 1px solid #7ab8d4 !important;
    color: #03223a !important; border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace; font-size: 12px;
}

.main-title {
    font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 700;
    color: #0a2a42; letter-spacing: -0.3px; margin-bottom: 2px;
}
.sub-title {
    font-size: 11px; color: #4a7fa0;
    font-family: 'IBM Plex Mono', monospace; margin-bottom: 16px; letter-spacing: 1px;
}

/* STATUS BANNER */
.status-banner {
    border-radius: 8px; padding: 14px 20px; margin: 8px 0 14px 0;
    font-family: 'IBM Plex Mono', monospace; font-size: 16px; font-weight: 700;
    letter-spacing: 1px; text-align: center; border: 2px solid;
    transition: all 0.2s;
}
.status-normal  { background:#f0f9ff; border-color:#7ab8d4; color:#0a2a42; }
.status-z1      { background:#dbeafe; border-color:#1d4ed8; color:#1e3a8a; }
.status-z2      { background:#fef3c7; border-color:#d97706; color:#78350f; }
.status-z3      { background:#fee2e2; border-color:#dc2626; color:#7f1d1d; }
.status-z4      { background:#ede9fe; border-color:#7c3aed; color:#3b0764; }
.status-load    { background:#d1fae5; border-color:#059669; color:#064e3b; }
.status-psb     { background:#fef9c3; border-color:#ca8a04; color:#713f12; }

/* METRIC CARDS */
.metric-row { display:flex; gap:10px; flex-wrap:wrap; margin:8px 0; }
.mcard {
    background:#fff; border:1px solid #7ab8d4; border-radius:8px;
    padding:10px 14px; flex:1; min-width:110px;
    box-shadow:0 1px 3px rgba(10,42,66,0.07);
}
.mcard-lbl { font-size:9px; color:#4a7fa0; font-family:'IBM Plex Mono',monospace;
    text-transform:uppercase; letter-spacing:1px; margin-bottom:2px; }
.mcard-val { font-size:18px; font-weight:700; font-family:'IBM Plex Mono',monospace;
    color:#0a2a42; }
.mcard-unit { font-size:10px; color:#4a7fa0; font-family:'IBM Plex Mono',monospace; }

/* SECTION LABEL */
.sec-lbl {
    font-family:'IBM Plex Mono',monospace; font-size:10px; font-weight:700;
    color:#4a7fa0; text-transform:uppercase; letter-spacing:2px;
    border-bottom:1px solid #b8d8ea; padding-bottom:4px; margin:12px 0 8px 0;
}

/* PHASOR BOX */
.phasor-box {
    background:#fff; border:1px solid #7ab8d4; border-radius:8px; padding:10px;
    margin-top:6px; font-family:'IBM Plex Mono',monospace; font-size:11px; color:#0a2a42;
}

/* SLIDER OVERRIDES */
.stSlider > div > div > div > div { background: #0a2a42 !important; }

/* BUTTON */
.stButton > button {
    background: #0a2a42 !important; color: #fff !important;
    border: none !important; border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; letter-spacing: 1.5px !important;
    width: 100%;
}
.stButton > button:hover { background: #0d4f7a !important; }

/* TABS */
div[data-baseweb="tab-list"] { background: #f0f8fc !important; border-bottom: 2px solid #7ab8d4; }
div[data-baseweb="tab"] { color: #4a7fa0 !important; font-family:'IBM Plex Mono',monospace !important; font-size:11px !important; }
div[data-baseweb="tab"][aria-selected="true"] {
    background: #0a2a42 !important; color: #fff !important; border-radius: 4px 4px 0 0;
}
div[data-baseweb="tab-panel"] { background: #f0f8fc !important; border-radius: 0 0 6px 6px; }

.stExpander { background: #f0f8fc !important; border: 1px solid #7ab8d4 !important; border-radius:6px !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def quad_polygon(X_reach, R_fwd, R_rev, line_ang_deg, n=2):
    """
    Quadrilateral zone polygon in secondary Ω.
    Corners: (−R_rev, 0), (R_fwd, 0), (R_fwd, X_reach), (−R_rev, X_reach)
    Rotated by line_ang_deg around origin to align with line impedance angle.
    """
    a = math.radians(line_ang_deg)
    pts = [
        (-R_rev,    -0.05 * X_reach),
        ( R_fwd,    -0.05 * X_reach),
        ( R_fwd,     X_reach),
        (-R_rev,     X_reach),
        (-R_rev,    -0.05 * X_reach),   # close
    ]
    # Rotate each point by (line_ang - 90) so X-reach aligns with line angle
    rot = line_ang_deg - 90
    rad = math.radians(rot)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    Rs, Xs = [], []
    for (x, y) in pts:
        Rs.append(x * cos_r - y * sin_r)
        Xs.append(x * sin_r + y * cos_r)
    return Rs, Xs

def point_in_quad(R_pt, X_pt, X_reach_sec, R_fwd_sec, R_rev_sec, line_ang_deg):
    """
    Check if point (R_pt, X_pt) is inside the quadrilateral zone.
    Transform point to quad local frame (un-rotate by rot angle).
    """
    rot = math.radians(line_ang_deg - 90)
    cos_r, sin_r = math.cos(-rot), math.sin(-rot)
    # Un-rotate point
    x_loc =  R_pt * cos_r - X_pt * sin_r
    y_loc =  R_pt * sin_r + X_pt * cos_r
    in_zone = (
        -R_rev_sec <= x_loc <= R_fwd_sec and
        -0.05 * X_reach_sec <= y_loc <= X_reach_sec
    )
    return in_zone

def swing_locus_points(Zs_sec, RLdInFw, n_pts=200):
    """
    Generate the power swing (equal-area) elliptical locus on R-X plane.
    The swing locus is a circle centred at (0, Zs/2) with radius Zs/2 + RLdInFw.
    Simplified model: straight-line locus from (-Zs, 0) to (Zs, 0) rotated 90°
    (the classical model — circle passing through ±Zs on imaginary axis).
    Classical power-swing locus: circle centred at jZs/2, radius |Zs/2|
    for equal source impedances each side.
    """
    cx = 0.0
    cy = Zs_sec / 2.0
    r  = Zs_sec / 2.0 + 0.5 * RLdInFw   # slightly larger to show encroachment
    angles = [i * 2 * math.pi / n_pts for i in range(n_pts + 1)]
    Rs = [cx + r * math.cos(a) for a in angles]
    Xs = [cy + r * math.sin(a) for a in angles]
    return Rs, Xs

def apparent_impedance(V_mag_sec, V_ang_deg, I_mag_sec, I_ang_deg):
    """
    Z_app = V_phasor / I_phasor  (in secondary Ω)
    V and I already in secondary units.
    """
    if I_mag_sec < 1e-6:
        return 9999.0, 9999.0
    V = complex(V_mag_sec * math.cos(math.radians(V_ang_deg)),
                V_mag_sec * math.sin(math.radians(V_ang_deg)))
    I = complex(I_mag_sec * math.cos(math.radians(I_ang_deg)),
                I_mag_sec * math.sin(math.radians(I_ang_deg)))
    Z = V / I
    return Z.real, Z.imag

def classify_zone(R, X, c, R_fwd_extra=None):
    """
    Returns: zone name, colour, trip time, css class
    Priority: Z1 > Z2 > Z3 > Z4 (reverse) > PSB > Load blinder > Normal
    """
    ang = c["Z1_ang"]
    kk  = c["kk"]

    # R-reach for each zone (secondary): use Z_sec projected onto R axis + margin
    def r_fwd(z_sec): return z_sec * 1.0     # for quadrilateral R_fwd = Z_reach (approx)
    def r_rev(z_sec): return z_sec * 0.25

    Z1s = c["Z1r_sec"]
    Z2s = c["Z2r_sec"]
    Z3s = c["Z3r_sec"]
    Z4s = c["Z4r_sec"]

    # Zone 1
    if point_in_quad(R, X, Z1s, r_fwd(Z1s), r_rev(Z1s), ang):
        return "ZONE 1  —  TRIP", "#1d4ed8", c["tZ1"], "z1"
    # Zone 2
    if point_in_quad(R, X, Z2s, r_fwd(Z2s), r_rev(Z2s), ang):
        return f"ZONE 2  —  TRIP  ({c['tZ2']}s)", "#d97706", c["tZ2"], "z2"
    # Zone 3
    if point_in_quad(R, X, Z3s, r_fwd(Z3s), r_rev(Z3s), ang):
        return f"ZONE 3  —  TRIP  ({c['tZ3']}s)", "#dc2626", c["tZ3"], "z3"
    # Zone 4 reverse — negative R region
    if point_in_quad(-R, -X, Z4s, r_fwd(Z4s), r_rev(Z4s), ang):
        return f"ZONE 4 (REVERSE)  —  TRIP  ({c['tZ4']}s)", "#7c3aed", c["tZ4"], "z4"
    # PSB outer blinder (simple: |R| < RLdOutFw and X between -Zs and +Zs)
    if abs(R) < c["RLdOutFw"] and abs(X) < c["Zs_sec"] * 1.5:
        if abs(R) > c["RLdInFw"]:
            return "PSB OUTER BLINDER  —  SWING DETECTED", "#ca8a04", None, "psb"
    # Load blinder
    if R > c["Z_blinder_sec"] * 0.8:
        return "LOAD REGION  —  BLINDER ACTIVE", "#059669", None, "load"
    return "NORMAL LOAD FLOW  —  NO OPERATION", "#0a2a42", None, "normal"


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — LINE SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="font-family:IBM Plex Mono;font-size:14px;color:#0a2a42;font-weight:700;'
        'margin-bottom:2px;">⚡ DISTANCE PROTECTION</div>'
        '<div style="font-family:IBM Plex Mono;font-size:9px;color:#4a7fa0;margin-bottom:14px;'
        'letter-spacing:1.5px;">INTERACTIVE R-X VISUALISER</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-lbl">🏭 Identification</div>', unsafe_allow_html=True)
    sub_name  = st.text_input("Substation", "Biswanath Chairali")
    line_name = st.text_input("Line", "Itanagar Line-1")

    st.markdown('<div class="sec-lbl">⚡ System</div>', unsafe_allow_html=True)
    voltage = st.selectbox("Voltage (kV)", [132, 220, 400, 765], index=2)

    st.markdown('<div class="sec-lbl">📏 Line Parameters</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        line_len = st.number_input("Length (km)", 10.0, 800.0, 180.0, 10.0)
        x1       = st.number_input("X1 (Ω/km)", 0.01, 1.0, 0.40, 0.01, format="%.3f")
        x0       = st.number_input("X0 (Ω/km)", 0.01, 2.0, 1.20, 0.01, format="%.3f")
    with c2:
        r1       = st.number_input("R1 (Ω/km)", 0.001, 0.5, 0.025, 0.001, format="%.4f")
        r0       = st.number_input("R0 (Ω/km)", 0.001, 1.0, 0.075, 0.001, format="%.4f")
        conductor = st.selectbox("Conductor", list(CONDUCTORS.keys()), index=0)

    st.markdown('<div class="sec-lbl">🔗 CT & VT</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        ct_pri = st.number_input("CT Pri (A)", 100, 4000, 800, 100)
        vt_pri = st.number_input("VT Pri (kV)", 1.0, 800.0, float(voltage), 1.0)
    with c2:
        ct_sec = st.number_input("CT Sec (A)", 1, 5, 1, 1)
        vt_sec = st.number_input("VT Sec (V)", 100, 200, 110, 5)

    st.markdown('<div class="sec-lbl">⚡ Fault Levels</div>', unsafe_allow_html=True)
    fault_3ph = st.number_input("3ph Fault (A)", 100, 50000, 20000, 500)
    fault_1ph = st.number_input("1ph Remote (A)", 100, 30000, 1500, 100)
    i_nom     = st.number_input("Nominal I (A)", 100, 5000, 1200, 50)

    st.markdown('<div class="sec-lbl">🔌 Adjacent Lines</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        lng_len  = st.number_input("Longest (km)", 10.0, 500.0, 220.0, 10.0)
        lng_z1km = st.number_input("Z1/km (Ω)", 0.01, 1.0, 0.40, 0.01, format="%.3f")
    with c2:
        sh_len   = st.number_input("Shortest (km)", 5.0, 300.0, 80.0, 5.0)
        sh_z1km  = st.number_input("Z1/km (Ω) ", 0.01, 1.0, 0.40, 0.01, format="%.3f")

    st.markdown('<div class="sec-lbl">🌀 PSB</div>', unsafe_allow_html=True)
    f_swing  = st.number_input("Swing Freq (Hz)", 0.1, 5.0, 1.5, 0.1)
    n_cond   = st.number_input("Conductors/phase", 1, 4, 2, 1)

# ── Build calculation inputs ───────────────────────────────────────────────
inp = dict(
    line_length=line_len, x1=x1, r1=r1, x0=x0, r0=r0,
    voltage_kv=voltage, ct_primary=ct_pri, ct_secondary=ct_sec,
    pt_primary_kv=vt_pri, pt_secondary_v=vt_sec,
    fault_3ph_local=fault_3ph, fault_1ph_remote=fault_1ph,
    num_conductors=n_cond, conductor_name=conductor,
    nominal_current=i_nom, swing_freq=f_swing,
    longest_remote_length=lng_len, longest_remote_z1km=lng_z1km,
    shortest_remote_length=sh_len, shortest_remote_z1km=sh_z1km,
)
c = calculate_all(inp)

kk      = c["kk"]
Z1_ang  = c["Z1_ang"]
VT_sec  = vt_sec          # secondary VT voltage (line-to-line V)
CT_sec  = ct_sec          # secondary CT current base (A)
VT_ph_sec = vt_sec / math.sqrt(3)   # phase voltage secondary (V)

# Secondary rated values
V_rated_sec = VT_ph_sec          # V (phase)
I_rated_sec = CT_sec             # A (secondary)

# ══════════════════════════════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="main-title">⚡ Distance Protection — Interactive R-X Plane</div>'
    '<div class="sub-title">QUADRILATERAL CHARACTERISTIC · SECONDARY Ω · '
    'LIVE IMPEDANCE POINT · PSB SWING ANIMATION</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE CONTROLS  (two columns: left=controls, right=plot)
# ══════════════════════════════════════════════════════════════════════════════
col_ctrl, col_plot = st.columns([1, 2.2])

with col_ctrl:
    # ── FAULT TYPE PRESETS ──────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">🎯 Fault Type Preset</div>', unsafe_allow_html=True)
    preset = st.radio(
        "Select operating condition",
        ["Normal Load", "3-ph Fault — 50% reach", "3-ph Fault — 90% reach",
         "1-ph Earth Fault", "2-ph Fault", "Heavy Load",
         "Power Swing (animate)", "Manual (use sliders)"],
        index=0, label_visibility="collapsed",
    )

    st.markdown('<div class="sec-lbl">📐 Fault Distance & Resistance</div>', unsafe_allow_html=True)
    fault_dist_pct = st.slider("Fault Distance (% of line)", 0, 150, 50, 1,
        help="0% = busbar fault, 100% = remote end, >100% = beyond remote end")
    Rf_primary = st.slider("Fault Resistance Rf (Ω primary)", 0.0, 50.0, 0.0, 0.5,
        help="Shifts apparent impedance rightward (off line angle). Significant for earth faults.")
    Rf_sec = Rf_primary * kk

    st.markdown('<div class="sec-lbl">🔌 Voltage Phasor</div>', unsafe_allow_html=True)
    V_pct  = st.slider("V magnitude (% of rated Vph)", 0, 110, 85, 1,
        help="Relay measured phase voltage as % of rated secondary Vph")
    V_ang  = st.slider("V angle φ_V (°)", -180, 180, 0, 1,
        help="Voltage phasor angle in degrees")

    st.markdown('<div class="sec-lbl">⚡ Current Phasor</div>', unsafe_allow_html=True)
    I_pct  = st.slider("I magnitude (% of rated CT sec)", 0, 500, 100, 5,
        help="Relay measured current as % of CT secondary rating")
    I_ang  = st.slider("I angle φ_I (°)", -90, 90, -75, 1,
        help="Current phasor angle (negative = lagging, typical for faults)")

    st.markdown('<div class="sec-lbl">🔋 Load Encroachment</div>', unsafe_allow_html=True)
    load_ang_slider = st.slider("Load angle (°)", 15, 45, 30, 1,
        help="Power factor angle of load. 30° typical for heavy transmission load.")

    st.markdown('<div class="sec-lbl">🌀 Power Swing Animation</div>', unsafe_allow_html=True)
    show_swing_locus = st.checkbox("Show swing locus", value=True)
    animate_swing = st.button("▶  ANIMATE SWING", use_container_width=True)
    swing_speed   = st.select_slider("Swing speed", ["Slow", "Normal", "Fast"], value="Normal")
    swing_delay   = {"Slow": 0.12, "Normal": 0.06, "Fast": 0.02}[swing_speed]

    st.markdown('<div class="sec-lbl">👁 Visibility</div>', unsafe_allow_html=True)
    show_z4      = st.checkbox("Show Zone 4 (reverse)", value=True)
    show_psb     = st.checkbox("Show PSB blinders", value=True)
    show_load_bl = st.checkbox("Show load blinder", value=True)
    show_phasors = st.checkbox("Show phasor diagram", value=True)

# ── APPLY PRESETS ──────────────────────────────────────────────────────────
# Override sliders when a preset is active
Z1s = c["Z1r_sec"]
Z2s = c["Z2r_sec"]
Z3s = c["Z3r_sec"]

if preset == "Normal Load":
    # Normal load: high R, moderate X, load angle
    V_use = V_rated_sec * 1.0
    I_use = I_rated_sec * (I_pct / 100.0)
    # Place point in load region
    Z_load_sec = c["Z_blinder_sec"] * 1.4
    R_pt = Z_load_sec * math.cos(math.radians(load_ang_slider))
    X_pt = Z_load_sec * math.sin(math.radians(load_ang_slider))
elif preset == "3-ph Fault — 50% reach":
    d = fault_dist_pct / 100.0
    Z_fault = Z1s * d * 0.5 / 0.8   # 50% reach relative to Z1 secondary
    R_pt = Z_fault * math.cos(math.radians(Z1_ang)) + Rf_sec
    X_pt = Z_fault * math.sin(math.radians(Z1_ang))
elif preset == "3-ph Fault — 90% reach":
    d = fault_dist_pct / 100.0
    Z_fault = Z1s * d * 0.9 / 0.8
    R_pt = Z_fault * math.cos(math.radians(Z1_ang)) + Rf_sec
    X_pt = Z_fault * math.sin(math.radians(Z1_ang))
elif preset == "1-ph Earth Fault":
    # Earth fault — impedance along line angle + Rf shifts it right
    d = fault_dist_pct / 100.0
    Z_fault = Z1s * d
    Kn = complex(c["Kn_mag"] * math.cos(math.radians(c["Kn_ang"])),
                 c["Kn_mag"] * math.sin(math.radians(c["Kn_ang"])))
    # Apparent Z for earth fault = Z_line_to_fault + Rf*(1+Kn) [simplified]
    Rf_effect = Rf_sec * abs(1 + Kn)
    R_pt = Z_fault * math.cos(math.radians(Z1_ang)) + Rf_effect
    X_pt = Z_fault * math.sin(math.radians(Z1_ang))
elif preset == "2-ph Fault":
    d = fault_dist_pct / 100.0
    Z_fault = Z1s * d * 0.866   # 2-ph apparent Z ≈ 0.866 × 3ph
    R_pt = Z_fault * math.cos(math.radians(Z1_ang)) + Rf_sec * 0.5
    X_pt = Z_fault * math.sin(math.radians(Z1_ang))
elif preset == "Heavy Load":
    # Apparent impedance near/inside load blinder
    Z_load_sec = c["Z_blinder_sec"] * (0.5 + (100 - I_pct) / 200.0)
    R_pt = Z_load_sec * math.cos(math.radians(load_ang_slider))
    X_pt = Z_load_sec * math.sin(math.radians(load_ang_slider))
elif preset == "Power Swing (animate)":
    # Midpoint of swing — will be overridden by animation
    R_pt = 0.0
    X_pt = c["Zs_sec"] * 0.5
elif preset == "Manual (use sliders)":
    V_use  = V_rated_sec * (V_pct / 100.0)
    I_use  = I_rated_sec * (I_pct / 100.0)
    R_pt, X_pt = apparent_impedance(V_use, V_ang, I_use, I_ang)
else:
    R_pt = c["Z_blinder_sec"] * 1.4 * math.cos(math.radians(30))
    X_pt = c["Z_blinder_sec"] * 1.4 * math.sin(math.radians(30))

# ── Classify zone ──────────────────────────────────────────────────────────
zone_label, zone_color, trip_time, zone_css = classify_zone(R_pt, X_pt, c)

# ══════════════════════════════════════════════════════════════════════════════
# BUILD PLOTLY FIGURE
# ══════════════════════════════════════════════════════════════════════════════

def build_fig(R_fault, X_fault, swing_step=None):
    ang = c["Z1_ang"]

    # --- Zone polygons (quadrilateral) ---
    Z1s = c["Z1r_sec"]; Z2s = c["Z2r_sec"]
    Z3s = c["Z3r_sec"]; Z4s = c["Z4r_sec"]

    def rfwd(z): return z * 0.80
    def rrev(z): return z * 0.25

    z1R, z1X = quad_polygon(Z1s, rfwd(Z1s), rrev(Z1s), ang)
    z2R, z2X = quad_polygon(Z2s, rfwd(Z2s), rrev(Z2s), ang)
    z3R, z3X = quad_polygon(Z3s, rfwd(Z3s), rrev(Z3s), ang)
    z4R, z4X = quad_polygon(Z4s, rfwd(Z4s), rrev(Z4s), ang)
    # Flip Z4 to reverse (negative direction)
    z4R = [-r for r in z4R]
    z4X = [-x for x in z4X]

    # --- Swing locus ---
    sw_Rs, sw_Xs = swing_locus_points(c["Zs_sec"], c["RLdInFw"])

    # --- Load impedance arc ---
    load_r  = c["Z_blinder_sec"] * 1.0
    # Arc from load_ang_slider - 15° to load_ang_slider + 15° at Rload_sec radius
    R_load_pt = load_r * math.cos(math.radians(load_ang_slider))
    X_load_pt = load_r * math.sin(math.radians(load_ang_slider))

    # --- Line impedance vector ---
    line_end_R = c["Z1_sec"] * math.cos(math.radians(ang))
    line_end_X = c["Z1_sec"] * math.sin(math.radians(ang))

    # --- Axis limits ---
    lim = max(Z3s, c["RLdOutFw"], c["Z_blinder_sec"] * 1.5) * 1.3
    xlim_neg = -max(Z4s * 1.2, c["RLdOutFw"] * 0.8, lim * 0.4)

    traces = []

    # Zone 3 (outermost — drawn first so inner zones overlay)
    traces.append(go.Scatter(
        x=z3R, y=z3X, fill='toself', fillcolor='rgba(220,38,38,0.06)',
        line=dict(color='#dc2626', width=2, dash='dash'),
        name=f'Zone 3  {c["Z3r_sec"]:.3f}Ω  {c["tZ3"]}s',
        hovertemplate='R:%{x:.3f} X:%{y:.3f}<extra>Zone 3</extra>'
    ))

    # Zone 2
    traces.append(go.Scatter(
        x=z2R, y=z2X, fill='toself', fillcolor='rgba(217,119,6,0.08)',
        line=dict(color='#d97706', width=2),
        name=f'Zone 2  {c["Z2r_sec"]:.3f}Ω  {c["tZ2"]}s',
        hovertemplate='R:%{x:.3f} X:%{y:.3f}<extra>Zone 2</extra>'
    ))

    # Zone 1
    traces.append(go.Scatter(
        x=z1R, y=z1X, fill='toself', fillcolor='rgba(29,78,216,0.10)',
        line=dict(color='#1d4ed8', width=2.5),
        name=f'Zone 1  {c["Z1r_sec"]:.3f}Ω  0.0s',
        hovertemplate='R:%{x:.3f} X:%{y:.3f}<extra>Zone 1</extra>'
    ))

    # Zone 4 reverse
    if show_z4:
        traces.append(go.Scatter(
            x=z4R, y=z4X, fill='toself', fillcolor='rgba(124,58,237,0.08)',
            line=dict(color='#7c3aed', width=1.5, dash='dot'),
            name=f'Zone 4 Rev  {c["Z4r_sec"]:.3f}Ω  {c["tZ4"]}s',
            hovertemplate='R:%{x:.3f} X:%{y:.3f}<extra>Zone 4 Rev</extra>'
        ))

    # PSB blinders (vertical lines)
    if show_psb:
        for blinder_R, blinder_label, blinder_col in [
            (c["RLdInFw"],  "PSB Inner", "#0891b2"),
            (-c["RLdInFw"], "PSB Inner (rev)", "#0891b2"),
            (c["RLdOutFw"],  "PSB Outer", "#06b6d4"),
            (-c["RLdOutFw"], "PSB Outer (rev)", "#06b6d4"),
        ]:
            traces.append(go.Scatter(
                x=[blinder_R, blinder_R], y=[-lim * 0.3, lim],
                mode='lines', line=dict(color=blinder_col, width=1.2, dash='dashdot'),
                name=blinder_label, showlegend=(blinder_R > 0),
                hoverinfo='skip'
            ))

        # Swing locus
        if show_swing_locus:
            traces.append(go.Scatter(
                x=sw_Rs, y=sw_Xs, mode='lines',
                line=dict(color='rgba(6,182,212,0.35)', width=1.5, dash='longdash'),
                name='Swing locus', hoverinfo='skip'
            ))

    # Load blinder (vertical line at Rload_sec)
    if show_load_bl:
        traces.append(go.Scatter(
            x=[c["Z_blinder_sec"], c["Z_blinder_sec"]], y=[-lim * 0.3, lim],
            mode='lines', line=dict(color='#059669', width=1.8, dash='dash'),
            name=f'Load blinder  {c["Z_blinder_sec"]:.3f}Ω',
            hoverinfo='skip'
        ))
        # Load region shading
        traces.append(go.Scatter(
            x=[c["Z_blinder_sec"], lim, lim, c["Z_blinder_sec"], c["Z_blinder_sec"]],
            y=[-lim * 0.3, -lim * 0.3, lim, lim, -lim * 0.3],
            fill='toself', fillcolor='rgba(5,150,105,0.05)',
            line=dict(color='rgba(0,0,0,0)'), name='Load region', showlegend=False,
            hoverinfo='skip'
        ))

    # Line impedance vector
    traces.append(go.Scatter(
        x=[0, line_end_R], y=[0, line_end_X],
        mode='lines+markers',
        line=dict(color='#0a2a42', width=2),
        marker=dict(size=[0, 10], color='#0a2a42', symbol=['circle', 'diamond']),
        name=f'Line Z1  {c["Z1_sec"]:.3f}Ω  ∠{ang:.1f}°'
    ))

    # Line angle reference line (MTA)
    mta_len = Z3s * 1.25
    traces.append(go.Scatter(
        x=[0, mta_len * math.cos(math.radians(ang))],
        y=[0, mta_len * math.sin(math.radians(ang))],
        mode='lines', line=dict(color='rgba(10,42,66,0.15)', width=1, dash='longdash'),
        name=f'MTA {ang:.1f}°', hoverinfo='none'
    ))

    # --- Animated swing point ---
    if swing_step is not None:
        sw_idx = int(swing_step) % len(sw_Rs)
        traces.append(go.Scatter(
            x=[sw_Rs[sw_idx]], y=[sw_Xs[sw_idx]],
            mode='markers',
            marker=dict(size=16, color='#f59e0b', symbol='circle',
                        line=dict(color='#92400e', width=2)),
            name='Swing point', showlegend=False,
            hovertemplate=f'R:{sw_Rs[sw_idx]:.3f} X:{sw_Xs[sw_idx]:.3f}<extra>Swing</extra>'
        ))
    else:
        # Static fault impedance point
        # Determine marker colour by zone
        pt_color = {
            "z1": "#1d4ed8", "z2": "#d97706", "z3": "#dc2626",
            "z4": "#7c3aed", "psb": "#ca8a04", "load": "#059669", "normal": "#334155"
        }.get(zone_css, "#334155")

        traces.append(go.Scatter(
            x=[R_fault], y=[X_fault],
            mode='markers',
            marker=dict(size=18, color=pt_color, symbol='circle',
                        line=dict(color='white', width=2.5)),
            name='Z_apparent', showlegend=False,
            hovertemplate=f'R_app: {R_fault:.4f} Ω<br>X_app: {X_fault:.4f} Ω<extra>Z apparent</extra>'
        ))

        # Dashed line from origin to fault point
        traces.append(go.Scatter(
            x=[0, R_fault], y=[0, X_fault],
            mode='lines', line=dict(color=pt_color, width=1.2, dash='dot'),
            showlegend=False, hoverinfo='none'
        ))

    # Labels at zone corners
    annotations = [
        dict(x=z1R[2]*0.6, y=z1X[2]*0.65, text='Z1',
             font=dict(color='#1d4ed8', size=13, family='IBM Plex Mono'), showarrow=False),
        dict(x=z2R[2]*0.62, y=z2X[2]*0.62, text='Z2',
             font=dict(color='#d97706', size=13, family='IBM Plex Mono'), showarrow=False),
        dict(x=z3R[2]*0.64, y=z3X[2]*0.64, text='Z3',
             font=dict(color='#dc2626', size=13, family='IBM Plex Mono'), showarrow=False),
    ]
    if show_z4:
        annotations.append(
            dict(x=z4R[2]*0.6, y=z4X[2]*0.6, text='Z4',
                 font=dict(color='#7c3aed', size=12, family='IBM Plex Mono'), showarrow=False)
        )

    fig = go.Figure(data=traces)
    fig.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#f8fbfd',
        font=dict(family='IBM Plex Mono', color='#0a2a42', size=11),
        title=dict(
            text=f"{sub_name} — {line_name} | {voltage}kV {line_len}km | "
                 f"Z1={c['Z1_sec']:.3f}Ω ∠{ang:.1f}° | kk={kk:.5f}",
            font=dict(color='#0a2a42', size=11), x=0.5
        ),
        xaxis=dict(
            title=dict(text="R (Ω secondary) — Resistance", font=dict(color='#4a7fa0')),
            range=[xlim_neg, lim], zeroline=True,
            zerolinecolor='rgba(10,42,66,0.3)', zerolinewidth=1.5,
            gridcolor='rgba(122,184,212,0.25)',
            tickfont=dict(color='#4a7fa0'), tickformat='.2f'
        ),
        yaxis=dict(
            title=dict(text="X (Ω secondary) — Reactance", font=dict(color='#4a7fa0')),
            range=[-lim * 0.35, lim * 1.05], zeroline=True,
            zerolinecolor='rgba(10,42,66,0.3)', zerolinewidth=1.5,
            gridcolor='rgba(122,184,212,0.25)',
            tickfont=dict(color='#4a7fa0'), tickformat='.2f',
            scaleanchor='x', scaleratio=1
        ),
        legend=dict(
            bgcolor='rgba(240,248,252,0.95)', bordercolor='#7ab8d4',
            borderwidth=1, font=dict(color='#0a2a42', size=9),
            x=1.01, xanchor='left', y=1, yanchor='top'
        ),
        annotations=annotations,
        hovermode='closest',
        margin=dict(l=55, r=10, t=44, b=50),
        height=560,
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# MAIN PLOT AREA
# ══════════════════════════════════════════════════════════════════════════════
with col_plot:
    # Status banner
    css_map = {
        "normal": "status-normal", "z1": "status-z1", "z2": "status-z2",
        "z3": "status-z3", "z4": "status-z4", "load": "status-load", "psb": "status-psb"
    }
    st.markdown(
        f'<div class="status-banner {css_map[zone_css]}">'
        f'{"⚡" if zone_css not in ["normal","load"] else ("🔋" if zone_css=="load" else "✅")} '
        f'{zone_label}'
        f'{"" if trip_time is None else f"  |  Trip in {trip_time:.2f}s"}'
        f'</div>',
        unsafe_allow_html=True
    )

    # Metrics row
    Z_app_mag = math.sqrt(R_pt**2 + X_pt**2)
    Z_app_ang = math.degrees(math.atan2(X_pt, R_pt)) if Z_app_mag > 0 else 0
    st.markdown(
        f'<div class="metric-row">'
        f'<div class="mcard"><div class="mcard-lbl">R apparent</div>'
        f'<div class="mcard-val">{R_pt:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">X apparent</div>'
        f'<div class="mcard-val">{X_pt:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">|Z| apparent</div>'
        f'<div class="mcard-val">{Z_app_mag:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">∠Z apparent</div>'
        f'<div class="mcard-val">{Z_app_ang:.1f}°</div><div class="mcard-unit">degrees</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">Z1 sec</div>'
        f'<div class="mcard-val">{c["Z1r_sec"]:.4f}</div><div class="mcard-unit">Ω</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">Line ∠</div>'
        f'<div class="mcard-val">{Z1_ang:.1f}°</div><div class="mcard-unit">MTA</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── STATIC PLOT or ANIMATION ──────────────────────────────────────────
    plot_placeholder = st.empty()

    if animate_swing or preset == "Power Swing (animate)":
        sw_Rs, sw_Xs = swing_locus_points(c["Zs_sec"], c["RLdInFw"])
        n_pts = len(sw_Rs)
        n_frames = n_pts
        for step in range(n_frames):
            fig = build_fig(sw_Rs[step], sw_Xs[step], swing_step=step)
            # Update status for swing point position
            sw_R, sw_X = sw_Rs[step], sw_Xs[step]
            _, _, _, sw_css = classify_zone(sw_R, sw_X, c)
            plot_placeholder.plotly_chart(fig, use_container_width=True)
            time.sleep(swing_delay)
    else:
        fig = build_fig(R_pt, X_pt)
        plot_placeholder.plotly_chart(fig, use_container_width=True)

    # ── PHASOR MINI-DIAGRAM ───────────────────────────────────────────────
    if show_phasors and preset == "Manual (use sliders)":
        V_use = V_rated_sec * (V_pct / 100.0)
        I_use = I_rated_sec * (I_pct / 100.0)
        V_r = V_use * math.cos(math.radians(V_ang))
        V_i = V_use * math.sin(math.radians(V_ang))
        I_r = I_use * math.cos(math.radians(I_ang)) * (V_use / max(I_use, 0.001)) * 0.5
        I_i = I_use * math.sin(math.radians(I_ang)) * (V_use / max(I_use, 0.001)) * 0.5

        fig_ph = go.Figure()
        # V phasor
        fig_ph.add_trace(go.Scatter(
            x=[0, V_r], y=[0, V_i], mode='lines+markers',
            line=dict(color='#0d7bbf', width=3),
            marker=dict(size=[0, 10], color='#0d7bbf', symbol=['circle', 'arrow']),
            name=f'V = {V_use:.3f}V ∠{V_ang}°'
        ))
        # I phasor (scaled)
        fig_ph.add_trace(go.Scatter(
            x=[0, I_r], y=[0, I_i], mode='lines+markers',
            line=dict(color='#dc2626', width=3),
            marker=dict(size=[0, 10], color='#dc2626', symbol=['circle', 'arrow']),
            name=f'I = {I_use:.3f}A ∠{I_ang}° (scaled)'
        ))
        fig_ph.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#f8fbfd',
            height=180, margin=dict(l=20, r=10, t=30, b=20),
            title=dict(text='Phasor Diagram (V & I secondary)', font=dict(size=11, color='#0a2a42'), x=0.5),
            xaxis=dict(zeroline=True, zerolinecolor='rgba(10,42,66,0.3)',
                       gridcolor='rgba(122,184,212,0.25)', tickfont=dict(color='#4a7fa0', size=9)),
            yaxis=dict(zeroline=True, zerolinecolor='rgba(10,42,66,0.3)',
                       gridcolor='rgba(122,184,212,0.25)', tickfont=dict(color='#4a7fa0', size=9),
                       scaleanchor='x', scaleratio=1),
            legend=dict(font=dict(size=9, color='#0a2a42'), bgcolor='rgba(240,248,252,0.9)',
                        bordercolor='#7ab8d4', borderwidth=1),
            font=dict(family='IBM Plex Mono'),
        )
        st.plotly_chart(fig_ph, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BOTTOM — SETTINGS REFERENCE TABLE + EXPLANATION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.expander("📋 Zone Settings Reference — Secondary Ω", expanded=False):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:12px;
     font-family:IBM Plex Mono;font-size:12px;color:#0a2a42;">
<b>ZONE REACHES (Secondary Ω)</b><br><br>
Z1 = {c['Z1r_sec']:.5f} Ω &nbsp; t={c['tZ1']}s<br>
Z2 = {c['Z2r_sec']:.5f} Ω &nbsp; t={c['tZ2']}s<br>
Z3 = {c['Z3r_sec']:.5f} Ω &nbsp; t={c['tZ3']}s<br>
Z4 = {c['Z4r_sec']:.5f} Ω &nbsp; t={c['tZ4']}s (Rev)<br><br>
Line Z1 = {c['Z1_sec']:.5f} Ω ∠{c['Z1_ang']:.2f}°<br>
kk (CTR/PTR) = {kk:.6f}<br>
</div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:12px;
     font-family:IBM Plex Mono;font-size:12px;color:#0a2a42;">
<b>LOAD & PSB</b><br><br>
Load blinder = {c['Z_blinder_sec']:.5f} Ω<br>
Load angle   = {c['load_angle']}° (fixed) / {load_ang_slider}° (slider)<br>
PSB Inner    = {c['RLdInFw']:.5f} Ω<br>
PSB Outer    = {c['RLdOutFw']:.5f} Ω<br>
ΔR (sep.)    = {c['Delta_R']:.5f} Ω<br>
δ_in         = {c['delta_in']:.2f}°<br>
δ_out        = {c['delta_out']:.2f}°<br>
Zs_sec       = {c['Zs_sec']:.5f} Ω<br>
</div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:12px;
     font-family:IBM Plex Mono;font-size:12px;color:#0a2a42;">
<b>EARTH COMPENSATION</b><br><br>
Kn = {c['Kn_mag']:.4f} ∠{c['Kn_ang']:.2f}°<br>
RE/RL = {c['RE_RL']:.4f}<br>
XE/XL = {c['XE_XL']:.4f}<br><br>
<b>CURRENT POINT</b><br><br>
R_apparent = {R_pt:.5f} Ω<br>
X_apparent = {X_pt:.5f} Ω<br>
|Z|_apparent = {math.sqrt(R_pt**2+X_pt**2):.5f} Ω<br>
Fault Rf (sec) = {Rf_sec:.5f} Ω<br>
</div>""", unsafe_allow_html=True)

with st.expander("📖 How to Read This Diagram", expanded=False):
    st.markdown("""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:16px;
     font-family:IBM Plex Sans;font-size:13px;color:#0a2a42;line-height:1.8;">

<b>R-X Plane Basics</b><br>
The relay continuously measures apparent impedance Z = V/I. This point is plotted on the R-X diagram.
Normal load → high R, moderate X (right side, low angle).
Faults → low R and X (close to origin), along the line impedance angle.

<br><b>Quadrilateral Characteristic</b><br>
The quadrilateral zone is defined by four boundaries: X-reach (top), R-forward reach (right),
R-reverse reach (left), and a lower X boundary (slightly below origin). The zone is rotated to align
with the line impedance angle (MTA). If the impedance point falls inside the polygon → the zone picks up.

<br><b>Zone Priority</b><br>
Z1 (blue): Instantaneous trip — 0.0s. Set to 80% of line to avoid overreach.<br>
Z2 (orange): Time-delayed trip. Covers 100% own line + remote busbar backup.<br>
Z3 (red): Remote backup. Covers adjacent line. Longest timer.<br>
Z4 (purple): Reverse zone — looks backward toward busbar for current reversal guard.

<br><b>Load Blinder (green dashed)</b><br>
Vertical resistive boundary at Rload_sec. Prevents Zone 3 from tripping during heavy load.
If impedance is to the right of this line → classified as load → tripping blocked.

<br><b>PSB Blinders (teal)</b><br>
Two parallel vertical lines (inner and outer). If impedance crosses from outer to inner blinder
in >50ms → Power Swing → all zones blocked. <50ms crossing → Fault → zones operate normally.

<br><b>Power Swing Locus (cyan dashed ellipse)</b><br>
Shows the trajectory the impedance point traces during a power swing.
It sweeps from the load region (right side), crosses the R-axis, and enters the zone characteristics.
Use the ANIMATE SWING button to see this motion live.

<br><b>Fault Resistance Rf</b><br>
For earth faults, the fault resistance shifts the apparent impedance rightward off the line angle.
High Rf (arc resistance, tower footing resistance) can push the point outside Zone 1 — causing under-reach.

</div>
""", unsafe_allow_html=True)

# Footer
st.markdown(f"""
<div style="margin-top:14px;padding:10px 16px;background:#f0f8fc;border:1px solid #7ab8d4;
     border-radius:6px;font-family:IBM Plex Mono;font-size:10px;color:#4a7fa0;line-height:1.9;">
⚡ Distance Protection Interactive R-X Visualiser | {sub_name} — {line_name} |
{voltage}kV | {line_len}km | Z1={c['Z1_sec']:.4f}Ω ∠{Z1_ang:.1f}° |
CTR={ct_pri}/{ct_sec} PTR={c['PTR']:.0f} kk={kk:.5f} | Secondary Ω | Quadrilateral Characteristic
</div>
""", unsafe_allow_html=True)
