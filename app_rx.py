"""
Distance Protection — Interactive R-X Plane Visualiser  (v2)
=============================================================
FIXES in v2:
  1. Normal Load preset — point correctly placed OUTSIDE all zones (far load region)
  2. PSB animation — only dot moves via fig.update_traces(); background never redraws
  3. PSB locus — correct spiral entering from high-R load region, sweeping through
     Z3→Z2→Z1 and exiting the other side; PSB detection band shown as two
     offset quadrilaterals (ΔR gap) per Image 3
  4. Load blinder — angled resistive lines at load_angle cutting into the quad
     corner (like Image 4), not a vertical line
"""

import streamlit as st
import math, sys, os, time
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(__file__))
from calculations_rx import calculate_all, CONDUCTORS

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Distance Protection — Interactive R-X Visualiser",
    page_icon="⚡", layout="wide", initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;background:#e8f4fa!important;color:#03223a!important;}
.stApp{background:#e8f4fa!important;}
section[data-testid="stSidebar"]{background:#f0f8fc!important;border-right:2px solid #7ab8d4!important;}
section[data-testid="stSidebar"] *{color:#0a2a42!important;}
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stNumberInput input{background:#fff!important;border:1px solid #7ab8d4!important;color:#03223a!important;border-radius:4px;font-family:'IBM Plex Mono',monospace;font-size:12px;}
.main-title{font-family:'IBM Plex Mono',monospace;font-size:21px;font-weight:700;color:#0a2a42;margin-bottom:2px;}
.sub-title{font-size:10px;color:#4a7fa0;font-family:'IBM Plex Mono',monospace;margin-bottom:14px;letter-spacing:1.2px;}
.status-banner{border-radius:8px;padding:12px 18px;margin:6px 0 10px 0;font-family:'IBM Plex Mono',monospace;font-size:15px;font-weight:700;letter-spacing:1px;text-align:center;border:2px solid;}
.status-normal{background:#f0f9ff;border-color:#7ab8d4;color:#0a2a42;}
.status-z1{background:#dbeafe;border-color:#1d4ed8;color:#1e3a8a;}
.status-z2{background:#fef3c7;border-color:#d97706;color:#78350f;}
.status-z3{background:#fee2e2;border-color:#dc2626;color:#7f1d1d;}
.status-z4{background:#ede9fe;border-color:#7c3aed;color:#3b0764;}
.status-load{background:#d1fae5;border-color:#059669;color:#064e3b;}
.status-psb{background:#fef9c3;border-color:#ca8a04;color:#713f12;}
.metric-row{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0;}
.mcard{background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:9px 12px;flex:1;min-width:100px;box-shadow:0 1px 3px rgba(10,42,66,0.07);}
.mcard-lbl{font-size:9px;color:#4a7fa0;font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:2px;}
.mcard-val{font-size:17px;font-weight:700;font-family:'IBM Plex Mono',monospace;color:#0a2a42;}
.mcard-unit{font-size:10px;color:#4a7fa0;font-family:'IBM Plex Mono',monospace;}
.sec-lbl{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;color:#4a7fa0;text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid #b8d8ea;padding-bottom:4px;margin:12px 0 8px 0;}
.stButton>button{background:#0a2a42!important;color:#fff!important;border:none!important;border-radius:6px!important;font-family:'IBM Plex Mono',monospace!important;font-size:11px!important;letter-spacing:1.5px!important;width:100%;}
.stButton>button:hover{background:#0d4f7a!important;}
div[data-baseweb="tab-list"]{background:#f0f8fc!important;border-bottom:2px solid #7ab8d4;}
div[data-baseweb="tab"]{color:#4a7fa0!important;font-family:'IBM Plex Mono',monospace!important;font-size:11px!important;}
div[data-baseweb="tab"][aria-selected="true"]{background:#0a2a42!important;color:#fff!important;border-radius:4px 4px 0 0;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def rotate_pts(pts, angle_deg):
    """Rotate a list of (x,y) tuples by angle_deg."""
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    return [(x*c - y*s, x*s + y*c) for (x, y) in pts]


def quad_polygon(Z_reach_sec, R_fwd_sec, R_rev_sec, line_ang_deg):
    """
    Build quadrilateral zone polygon rotated to line impedance angle.
    The quadrilateral is defined in a 'zone-local' frame:
      - Y-axis = along the line impedance direction (reach axis)
      - X-axis = perpendicular (resistive)
    Local corners:
      Bottom-left:  (-R_rev, 0)
      Bottom-right: (+R_fwd, 0)
      Top-right:    (+R_fwd, Z_reach)
      Top-left:     (-R_rev, Z_reach)
    Then rotated by (line_ang - 90°) to place in R-X plane.
    """
    rot = line_ang_deg - 90.0
    raw = [
        (-R_rev_sec,  -0.04 * Z_reach_sec),
        ( R_fwd_sec,  -0.04 * Z_reach_sec),
        ( R_fwd_sec,   Z_reach_sec),
        (-R_rev_sec,   Z_reach_sec),
        (-R_rev_sec,  -0.04 * Z_reach_sec),  # close
    ]
    rotated = rotate_pts(raw, rot)
    Rs = [p[0] for p in rotated]
    Xs = [p[1] for p in rotated]
    return Rs, Xs


def point_in_quad(R_pt, X_pt, Z_reach_sec, R_fwd_sec, R_rev_sec, line_ang_deg):
    """Check if point lies inside the quadrilateral (un-rotate, then AABB check)."""
    rot = -(line_ang_deg - 90.0)
    rad = math.radians(rot)
    c, s = math.cos(rad), math.sin(rad)
    x_loc =  R_pt * c - X_pt * s
    y_loc =  R_pt * s + X_pt * c
    return (-R_rev_sec <= x_loc <= R_fwd_sec and
            -0.04 * Z_reach_sec <= y_loc <= Z_reach_sec)


def load_blinder_polygon(R_load_sec, load_ang_deg, Z3_sec, R_fwd_Z3, line_ang_deg):
    """
    Draw the load encroachment blinder as two angled lines cutting into the
    quadrilateral corner — exactly like Image 4.
    The blinder is defined by a resistive reach R_load at ±load_ang_deg,
    forming a 'wedge' excluded region on the right side of the R-X diagram.
    Returns two traces: upper blinder line and lower blinder line.
    """
    # Upper blinder: from (R_load, 0) angled up-left at (90° - load_ang_deg) from R axis
    # Lower blinder: mirror below R axis
    # The blinder lines are drawn in R-X coordinates (not rotated — load is axis-aligned)
    # Upper line: direction angle = (180° - load_ang_deg) from positive R axis
    # i.e. it goes left and up from the R_load intercept

    extent = Z3_sec * 2.0   # how far the line extends

    # Upper blinder: starts at (R_load_sec, 0), goes in direction (180° - load_ang_deg)
    ang_up = math.radians(180.0 - load_ang_deg)
    ub_x2 = R_load_sec + extent * math.cos(ang_up)
    ub_y2 = 0.0         + extent * math.sin(ang_up)

    # Lower blinder: mirror of upper (below R axis)
    ang_dn = math.radians(-(180.0 - load_ang_deg))
    lb_x2 = R_load_sec + extent * math.cos(ang_dn)
    lb_y2 = 0.0         + extent * math.sin(ang_dn)

    # Shaded load region polygon (right of both blinder lines)
    shade_R = [R_load_sec, ub_x2, ub_x2 + extent, R_load_sec + extent,
               lb_x2 + extent, lb_x2, R_load_sec]
    shade_X = [0,         ub_y2,  ub_y2,            0,
               lb_y2,            lb_y2,  0]

    upper = ([R_load_sec, ub_x2], [0.0, ub_y2])
    lower = ([R_load_sec, lb_x2], [0.0, lb_y2])
    shade = (shade_R, shade_X)
    return upper, lower, shade


def psb_detection_band(Z3_sec, R_fwd_Z3, R_rev_Z3, Delta_R, line_ang_deg):
    """
    PSB detection band = two offset quadrilaterals (inner and outer),
    like Image 3. The outer quad is Z3 expanded by Delta_R on all resistive sides.
    """
    # Inner boundary = same as Z3 quad
    inner_R, inner_X = quad_polygon(Z3_sec, R_fwd_Z3, R_rev_Z3, line_ang_deg)

    # Outer boundary = Z3 quad expanded by Delta_R on left and right
    outer_R, outer_X = quad_polygon(
        Z3_sec + Delta_R,          # slightly taller too
        R_fwd_Z3 + Delta_R,
        R_rev_Z3 + Delta_R,
        line_ang_deg
    )
    return inner_R, inner_X, outer_R, outer_X


def swing_locus_path(Z3_sec, Z_load_sec, line_ang_deg):
    """
    Power swing locus on the R-X plane.

    Classical equal-source formula:
        Z_app(δ) = Z_total / (1 - e^jδ)
    where Z_total = Z_load_sec (load blinder reach, representative of the
    total system impedance seen during a power swing between two equal sources).

    At δ=0°  → Z_app → ∞  (normal load, far right)
    At δ=90° → Z_app in Z3/Z2 region
    At δ=180°→ Z_app near origin (inside Z1)
    At δ=270°→ Z_app in negative R region

    The locus is rotated by (line_ang - 90°) to align with the line direction.
    Points with |X| > 4*Z3 are clipped (extreme values near δ≈0/360°).
    """
    pts = []
    for d in range(15, 345, 2):   # skip 0° and 360° (→ infinity)
        delta = math.radians(d)
        ed    = complex(math.cos(delta), math.sin(delta))
        denom = 1.0 - ed
        if abs(denom) < 1e-6:
            continue
        z = Z_load_sec / denom
        # Rotate to line angle frame
        z_rot = z * complex(math.cos(math.radians(line_ang_deg - 90)),
                             math.sin(math.radians(line_ang_deg - 90)))
        # Clip extreme excursions (only keep portion near zones)
        if abs(z_rot.imag) < Z3_sec * 4.0:
            pts.append((z_rot.real, z_rot.imag))

    if not pts:
        return [], []
    Rs = [p[0] for p in pts]
    Xs = [p[1] for p in pts]
    return Rs, Xs


def apparent_impedance(V_sec, V_ang_deg, I_sec, I_ang_deg):
    if I_sec < 1e-6:
        return 9999.0, 9999.0
    V = V_sec * complex(math.cos(math.radians(V_ang_deg)), math.sin(math.radians(V_ang_deg)))
    I = I_sec * complex(math.cos(math.radians(I_ang_deg)), math.sin(math.radians(I_ang_deg)))
    Z = V / I
    return Z.real, Z.imag


def classify_zone(R, X, c):
    ang = c["Z1_ang"]
    Z1s, Z2s, Z3s, Z4s = c["Z1r_sec"], c["Z2r_sec"], c["Z3r_sec"], c["Z4r_sec"]

    def rfwd(z): return z * 0.80
    def rrev(z): return z * 0.25

    if point_in_quad(R, X, Z1s, rfwd(Z1s), rrev(Z1s), ang):
        return "ZONE 1  ⚡  TRIP  — 0.0s", "#1d4ed8", c["tZ1"], "z1"
    if point_in_quad(R, X, Z2s, rfwd(Z2s), rrev(Z2s), ang):
        return f"ZONE 2  ⚡  TRIP  — {c['tZ2']}s", "#d97706", c["tZ2"], "z2"
    if point_in_quad(R, X, Z3s, rfwd(Z3s), rrev(Z3s), ang):
        return f"ZONE 3  ⚡  TRIP  — {c['tZ3']}s", "#dc2626", c["tZ3"], "z3"
    if point_in_quad(-R, -X, Z4s, rfwd(Z4s), rrev(Z4s), ang):
        return f"ZONE 4 (REVERSE)  — {c['tZ4']}s", "#7c3aed", c["tZ4"], "z4"
    # PSB detection band
    Delta_R = c["Delta_R"]
    in_outer = point_in_quad(R, X, Z3s + Delta_R, rfwd(Z3s) + Delta_R, rrev(Z3s) + Delta_R, ang)
    in_inner = point_in_quad(R, X, Z3s, rfwd(Z3s), rrev(Z3s), ang)
    if in_outer and not in_inner:
        return "PSB DETECTION BAND  — SWING DETECTED", "#ca8a04", None, "psb"
    # Load blinder check (right side of R-X plane, beyond load R)
    if R > c["Z_blinder_sec"] * 0.85:
        return "LOAD REGION  — BLINDER ACTIVE  (No Trip)", "#059669", None, "load"
    return "✅  NORMAL LOAD FLOW  — NO OPERATION", "#0a2a42", None, "normal"


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="font-family:IBM Plex Mono;font-size:13px;color:#0a2a42;font-weight:700;margin-bottom:2px;">⚡ DISTANCE PROTECTION</div>'
        '<div style="font-family:IBM Plex Mono;font-size:9px;color:#4a7fa0;margin-bottom:14px;letter-spacing:1.5px;">INTERACTIVE R-X VISUALISER v2</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sec-lbl">🏭 Identification</div>', unsafe_allow_html=True)
    sub_name  = st.text_input("Substation", "Biswanath Chairali")
    line_name = st.text_input("Line", "Itanagar Line-1")

    st.markdown('<div class="sec-lbl">⚡ System</div>', unsafe_allow_html=True)
    voltage = st.selectbox("Voltage (kV)", [132, 220, 400, 765], index=2)

    st.markdown('<div class="sec-lbl">📏 Line Parameters</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        line_len = st.number_input("Length (km)", 10.0, 800.0, 180.0, 10.0)
        x1       = st.number_input("X1 (Ω/km)", 0.01, 1.0, 0.40, 0.01, format="%.3f")
        x0       = st.number_input("X0 (Ω/km)", 0.01, 2.0, 1.20, 0.01, format="%.3f")
    with cc2:
        r1        = st.number_input("R1 (Ω/km)", 0.001, 0.5, 0.025, 0.001, format="%.4f")
        r0        = st.number_input("R0 (Ω/km)", 0.001, 1.0, 0.075, 0.001, format="%.4f")
        conductor = st.selectbox("Conductor", list(CONDUCTORS.keys()), index=0)

    st.markdown('<div class="sec-lbl">🔗 CT & VT</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        ct_pri = st.number_input("CT Pri (A)", 100, 4000, 800, 100)
        vt_pri = st.number_input("VT Pri (kV)", 1.0, 800.0, float(voltage), 1.0)
    with cc2:
        ct_sec = st.number_input("CT Sec (A)", 1, 5, 1, 1)
        vt_sec = st.number_input("VT Sec (V)", 100, 200, 110, 5)

    st.markdown('<div class="sec-lbl">⚡ Fault Levels</div>', unsafe_allow_html=True)
    fault_3ph = st.number_input("3ph Fault (A)", 100, 50000, 20000, 500)
    fault_1ph = st.number_input("1ph Remote (A)", 100, 30000, 1500, 100)
    i_nom     = st.number_input("Nominal I (A)", 100, 5000, 1200, 50)

    st.markdown('<div class="sec-lbl">🔌 Adjacent Lines</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns(2)
    with cc1:
        lng_len  = st.number_input("Longest (km)", 10.0, 500.0, 220.0, 10.0)
        lng_z1km = st.number_input("Z1/km (Ω)", 0.01, 1.0, 0.40, 0.01, format="%.3f")
    with cc2:
        sh_len   = st.number_input("Shortest (km)", 5.0, 300.0, 80.0, 5.0)
        sh_z1km  = st.number_input("Z1/km (Ω) ", 0.01, 1.0, 0.40, 0.01, format="%.3f")

    st.markdown('<div class="sec-lbl">🌀 PSB</div>', unsafe_allow_html=True)
    f_swing = st.number_input("Swing Freq (Hz)", 0.1, 5.0, 1.5, 0.1)
    n_cond  = st.number_input("Conductors/phase", 1, 4, 2, 1)

# ── Calculations ───────────────────────────────────────────────────────────────
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

kk        = c["kk"]
Z1_ang    = c["Z1_ang"]
VT_ph_sec = vt_sec / math.sqrt(3)
V_rated   = VT_ph_sec
I_rated   = float(ct_sec)

# Derived zone sizes for plot
Z1s = c["Z1r_sec"]; Z2s = c["Z2r_sec"]
Z3s = c["Z3r_sec"]; Z4s = c["Z4r_sec"]

def rfwd(z): return z * 0.80
def rrev(z): return z * 0.25

# ══════════════════════════════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="main-title">⚡ Distance Protection — Interactive R-X Plane</div>'
    '<div class="sub-title">QUADRILATERAL · SECONDARY Ω · LIVE IMPEDANCE POINT · PSB SWING ANIMATION</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
col_ctrl, col_plot = st.columns([1, 2.4])

with col_ctrl:
    st.markdown('<div class="sec-lbl">🎯 Fault Type Preset</div>', unsafe_allow_html=True)
    preset = st.radio("preset", [
        "Normal Load", "3-ph Fault — 50%", "3-ph Fault — 90%",
        "1-ph Earth Fault", "2-ph Fault", "Heavy Load",
        "Power Swing (animate)", "Manual (sliders)"],
        index=0, label_visibility="collapsed",
    )

    st.markdown('<div class="sec-lbl">📐 Fault Distance & Rf</div>', unsafe_allow_html=True)
    fault_dist_pct = st.slider("Fault Distance (% of line)", 0, 150, 50, 1)
    Rf_pri = st.slider("Fault Resistance Rf (Ω primary)", 0.0, 50.0, 0.0, 0.5,
                       help="Arc/tower footing resistance. Shifts Z_app rightward off line angle.")
    Rf_sec = Rf_pri * kk

    st.markdown('<div class="sec-lbl">🔌 Voltage Phasor</div>', unsafe_allow_html=True)
    V_pct = st.slider("V magnitude (% rated Vph)", 0, 110, 85, 1)
    V_ang = st.slider("V angle φ_V (°)", -180, 180, 0, 1)

    st.markdown('<div class="sec-lbl">⚡ Current Phasor</div>', unsafe_allow_html=True)
    I_pct = st.slider("I magnitude (% rated CT)", 0, 500, 100, 5)
    I_ang = st.slider("I angle φ_I (°)", -90, 90, -75, 1)

    st.markdown('<div class="sec-lbl">🔋 Load Encroachment</div>', unsafe_allow_html=True)
    load_ang = st.slider("Load angle (°)", 15, 45, 30, 1,
                         help="PF angle of load. Blinder lines cut at this angle into the R-X diagram.")

    st.markdown('<div class="sec-lbl">🌀 Power Swing</div>', unsafe_allow_html=True)
    show_swing_locus = st.checkbox("Show swing locus path", value=True)
    animate_swing    = st.button("▶  ANIMATE SWING", use_container_width=True)
    swing_speed      = st.select_slider("Animation speed", ["Slow", "Normal", "Fast"], value="Normal")
    swing_delay      = {"Slow": 0.08, "Normal": 0.04, "Fast": 0.015}[swing_speed]

    st.markdown('<div class="sec-lbl">👁 Visibility</div>', unsafe_allow_html=True)
    show_z4      = st.checkbox("Show Zone 4 (reverse)", value=True)
    show_psb     = st.checkbox("Show PSB detection band", value=True)
    show_load_bl = st.checkbox("Show load blinder", value=True)
    show_phasors = st.checkbox("Show phasor diagram", value=True)


# ══════════════════════════════════════════════════════════════════════════════
# PRESET → APPARENT IMPEDANCE POINT
# ══════════════════════════════════════════════════════════════════════════════
# Normal load: place point FAR in load region (well outside Z3, high R, low angle)
if preset == "Normal Load":
    # Load apparent impedance = V/I at near unity PF
    # Use 2× load blinder so clearly in safe region
    Z_ld = c["Z_blinder_sec"] * 2.2
    R_pt = Z_ld * math.cos(math.radians(load_ang))
    X_pt = Z_ld * math.sin(math.radians(load_ang))

elif preset == "3-ph Fault — 50%":
    dist = (fault_dist_pct / 100.0) * 0.5
    Z_f  = Z1s * dist
    R_pt = Z_f * math.cos(math.radians(Z1_ang)) + Rf_sec
    X_pt = Z_f * math.sin(math.radians(Z1_ang))

elif preset == "3-ph Fault — 90%":
    dist = (fault_dist_pct / 100.0) * 0.9
    Z_f  = Z1s * dist
    R_pt = Z_f * math.cos(math.radians(Z1_ang)) + Rf_sec
    X_pt = Z_f * math.sin(math.radians(Z1_ang))

elif preset == "1-ph Earth Fault":
    dist = fault_dist_pct / 100.0
    Z_f  = Z1s * dist
    Kn_c = complex(c["Kn_mag"] * math.cos(math.radians(c["Kn_ang"])),
                   c["Kn_mag"] * math.sin(math.radians(c["Kn_ang"])))
    Rf_eff = Rf_sec * abs(1.0 + Kn_c)
    R_pt = Z_f * math.cos(math.radians(Z1_ang)) + Rf_eff
    X_pt = Z_f * math.sin(math.radians(Z1_ang))

elif preset == "2-ph Fault":
    dist = fault_dist_pct / 100.0
    Z_f  = Z1s * dist * 0.866
    R_pt = Z_f * math.cos(math.radians(Z1_ang)) + Rf_sec * 0.5
    X_pt = Z_f * math.sin(math.radians(Z1_ang))

elif preset == "Heavy Load":
    # Point close to but just outside load blinder
    Z_ld = c["Z_blinder_sec"] * 1.1
    R_pt = Z_ld * math.cos(math.radians(load_ang))
    X_pt = Z_ld * math.sin(math.radians(load_ang))

elif preset in ("Power Swing (animate)", "Manual (sliders)"):
    V_use = V_rated * (V_pct / 100.0)
    I_use = I_rated * (I_pct / 100.0)
    R_pt, X_pt = apparent_impedance(V_use, V_ang, I_use, I_ang)

else:
    R_pt = c["Z_blinder_sec"] * 2.2 * math.cos(math.radians(load_ang))
    X_pt = c["Z_blinder_sec"] * 2.2 * math.sin(math.radians(load_ang))

# Classify
zone_label, zone_color, trip_time, zone_css = classify_zone(R_pt, X_pt, c)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD BASE FIGURE  (background never changes during animation)
# ══════════════════════════════════════════════════════════════════════════════

def build_base_fig():
    """Build the static background: zones, blinders, locus path. No moving dot."""
    ang = Z1_ang

    z1R, z1X = quad_polygon(Z1s, rfwd(Z1s), rrev(Z1s), ang)
    z2R, z2X = quad_polygon(Z2s, rfwd(Z2s), rrev(Z2s), ang)
    z3R, z3X = quad_polygon(Z3s, rfwd(Z3s), rrev(Z3s), ang)
    z4R_, z4X_ = quad_polygon(Z4s, rfwd(Z4s), rrev(Z4s), ang)
    z4R = [-r for r in z4R_]
    z4X = [-x for x in z4X_]

    # PSB detection band (inner + outer offset quads like Image 3)
    Delta_R = c["Delta_R"]
    psb_inner_R, psb_inner_X = quad_polygon(Z3s, rfwd(Z3s), rrev(Z3s), ang)
    psb_outer_R, psb_outer_X = quad_polygon(
        Z3s + Delta_R * 0.6,
        rfwd(Z3s) + Delta_R, rrev(Z3s) + Delta_R, ang
    )

    # Swing locus path
    sw_Rs, sw_Xs = swing_locus_path(Z3s, c["Z_blinder_sec"], ang)

    # Load blinder lines and shading
    R_load = c["Z_blinder_sec"]
    upper_bl, lower_bl, load_shade = load_blinder_polygon(
        R_load, load_ang, Z3s, rfwd(Z3s), ang
    )

    # Axis limits — generous to show swing excursion
    lim_base = max(Z3s * 1.6, c["Z_blinder_sec"] * 2.5, Delta_R + Z3s + 2)
    swing_max = max(abs(r) for r in sw_Rs) * 1.1 if sw_Rs else lim_base
    lim = max(lim_base, swing_max) * 1.1
    xlim_neg = -max(Z4s * 1.5, Delta_R + rrev(Z3s) + 2, lim * 0.35)

    # Line end
    line_end_R = c["Z1_sec"] * math.cos(math.radians(ang))
    line_end_X = c["Z1_sec"] * math.sin(math.radians(ang))

    traces = []

    # ── PSB detection band (drawn under zones so zones overlay) ──────────────
    if show_psb:
        # Shaded band between inner and outer
        # Build a filled region = outer polygon minus inner polygon
        # Plotly doesn't support subtraction directly, so draw outer filled lightly
        # and inner filled white to punch out
        traces.append(go.Scatter(
            x=psb_outer_R, y=psb_outer_X, fill='toself',
            fillcolor='rgba(6,182,212,0.12)',
            line=dict(color='#0891b2', width=1.8, dash='dash'),
            name=f'PSB Outer  ΔR={Delta_R:.2f}Ω', hoverinfo='skip'
        ))
        # Inner boundary (PSB inner = same as Z3 boundary)
        traces.append(go.Scatter(
            x=psb_inner_R, y=psb_inner_X, fill='toself',
            fillcolor='rgba(240,248,252,1.0)',   # white punch-out
            line=dict(color='#0891b2', width=1.5, dash='dot'),
            name='PSB Inner', hoverinfo='skip', showlegend=True
        ))
        # ΔR annotation arrows (label the gap)
        # Right-side midpoint label
        traces.append(go.Scatter(
            x=[(rfwd(Z3s) + rfwd(Z3s) + Delta_R) / 2 * 0.8],
            y=[Z3s * 0.1],
            mode='text',
            text=[f'ΔR={Delta_R:.1f}Ω'],
            textfont=dict(color='#0891b2', size=9, family='IBM Plex Mono'),
            showlegend=False, hoverinfo='skip'
        ))

    # ── Zones ────────────────────────────────────────────────────────────────
    # Z3 — drawn first (outermost)
    traces.append(go.Scatter(
        x=z3R, y=z3X, fill='toself', fillcolor='rgba(220,38,38,0.06)',
        line=dict(color='#dc2626', width=2, dash='dash'),
        name=f'Zone 3  {Z3s:.3f}Ω  {c["tZ3"]}s',
    ))
    # Z2
    traces.append(go.Scatter(
        x=z2R, y=z2X, fill='toself', fillcolor='rgba(217,119,6,0.08)',
        line=dict(color='#d97706', width=2),
        name=f'Zone 2  {Z2s:.3f}Ω  {c["tZ2"]}s',
    ))
    # Z1
    traces.append(go.Scatter(
        x=z1R, y=z1X, fill='toself', fillcolor='rgba(29,78,216,0.10)',
        line=dict(color='#1d4ed8', width=2.5),
        name=f'Zone 1  {Z1s:.3f}Ω  0.0s',
    ))
    # Z4 reverse
    if show_z4:
        traces.append(go.Scatter(
            x=z4R, y=z4X, fill='toself', fillcolor='rgba(124,58,237,0.07)',
            line=dict(color='#7c3aed', width=1.5, dash='dot'),
            name=f'Zone 4 Rev  {Z4s:.3f}Ω  {c["tZ4"]}s',
        ))

    # ── Load blinder (angled lines like Image 4) ─────────────────────────────
    if show_load_bl:
        # Shaded load region
        traces.append(go.Scatter(
            x=load_shade[0], y=load_shade[1], fill='toself',
            fillcolor='rgba(5,150,105,0.07)',
            line=dict(color='rgba(0,0,0,0)'),
            name='Load region', showlegend=False, hoverinfo='skip'
        ))
        # Upper blinder line
        traces.append(go.Scatter(
            x=upper_bl[0], y=upper_bl[1], mode='lines',
            line=dict(color='#059669', width=2.0, dash='dash'),
            name=f'Load blinder  {R_load:.3f}Ω  ±{load_ang}°',
        ))
        # Lower blinder line
        traces.append(go.Scatter(
            x=lower_bl[0], y=lower_bl[1], mode='lines',
            line=dict(color='#059669', width=2.0, dash='dash'),
            name='Load blinder (lower)', showlegend=False,
        ))
        # Vertical tick at R_load on X axis
        traces.append(go.Scatter(
            x=[R_load, R_load], y=[-lim * 0.05, lim * 0.05],
            mode='lines', line=dict(color='#059669', width=2),
            showlegend=False, hoverinfo='skip'
        ))

    # ── Swing locus path ────────────────────────────────────────────────────
    if show_swing_locus and show_psb:
        traces.append(go.Scatter(
            x=sw_Rs, y=sw_Xs, mode='lines',
            line=dict(color='rgba(6,182,212,0.45)', width=1.8, dash='longdash'),
            name='Swing locus path', hoverinfo='skip'
        ))
        # Arrow markers along path to show direction
        step = max(1, len(sw_Rs) // 8)
        traces.append(go.Scatter(
            x=sw_Rs[::step], y=sw_Xs[::step], mode='markers',
            marker=dict(size=5, color='#0891b2', symbol='arrow-bar-up',
                        angle=[math.degrees(math.atan2(
                            sw_Xs[min(i+1, len(sw_Xs)-1)] - sw_Xs[i],
                            sw_Rs[min(i+1, len(sw_Rs)-1)] - sw_Rs[i]
                        )) for i in range(0, len(sw_Rs), step)]),
            showlegend=False, hoverinfo='skip'
        ))

    # ── Line impedance vector ────────────────────────────────────────────────
    traces.append(go.Scatter(
        x=[0, line_end_R], y=[0, line_end_X],
        mode='lines+markers',
        line=dict(color='#0a2a42', width=2.2),
        marker=dict(size=[0, 10], color='#0a2a42', symbol=['circle', 'diamond']),
        name=f'Line Z1  {c["Z1_sec"]:.3f}Ω  ∠{ang:.1f}°'
    ))
    # MTA reference line
    mta_len = lim * 0.9
    traces.append(go.Scatter(
        x=[0, mta_len * math.cos(math.radians(ang))],
        y=[0, mta_len * math.sin(math.radians(ang))],
        mode='lines', line=dict(color='rgba(10,42,66,0.12)', width=1, dash='longdash'),
        name=f'MTA {ang:.1f}°', hoverinfo='skip'
    ))

    # ── Zone labels ──────────────────────────────────────────────────────────
    annotations = [
        dict(x=z1R[2]*0.55, y=z1X[2]*0.55, text='<b>Z1</b>',
             font=dict(color='#1d4ed8', size=13, family='IBM Plex Mono'), showarrow=False),
        dict(x=z2R[2]*0.58, y=z2X[2]*0.58, text='<b>Z2</b>',
             font=dict(color='#d97706', size=13, family='IBM Plex Mono'), showarrow=False),
        dict(x=z3R[2]*0.60, y=z3X[2]*0.60, text='<b>Z3</b>',
             font=dict(color='#dc2626', size=13, family='IBM Plex Mono'), showarrow=False),
        dict(x=R_load * 1.4, y=Z3s * 0.3, text='<b>LOAD</b>',
             font=dict(color='#059669', size=11, family='IBM Plex Mono'), showarrow=False),
    ]
    if show_z4:
        annotations.append(dict(
            x=z4R[2]*0.55, y=z4X[2]*0.55, text='<b>Z4</b>',
            font=dict(color='#7c3aed', size=12, family='IBM Plex Mono'), showarrow=False
        ))
    if show_psb:
        annotations.append(dict(
            x=psb_outer_R[1] * 0.9, y=-Z3s * 0.25, text='PSB',
            font=dict(color='#0891b2', size=10, family='IBM Plex Mono'), showarrow=False
        ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#f8fbfd',
        font=dict(family='IBM Plex Mono', color='#0a2a42', size=11),
        title=dict(
            text=f"{sub_name} — {line_name} | {voltage}kV {line_len:.0f}km | "
                 f"Z1={c['Z1_sec']:.3f}Ω ∠{ang:.1f}° | kk={kk:.5f}",
            font=dict(color='#0a2a42', size=10), x=0.5
        ),
        xaxis=dict(
            title=dict(text="R (Ω secondary) →", font=dict(color='#4a7fa0', size=11)),
            range=[xlim_neg, lim], zeroline=True,
            zerolinecolor='rgba(10,42,66,0.35)', zerolinewidth=1.5,
            gridcolor='rgba(122,184,212,0.2)',
            tickfont=dict(color='#4a7fa0', size=9), tickformat='.2f',
        ),
        yaxis=dict(
            title=dict(text="X (Ω secondary) →", font=dict(color='#4a7fa0', size=11)),
            range=[-lim * 0.3, lim * 1.05], zeroline=True,
            zerolinecolor='rgba(10,42,66,0.35)', zerolinewidth=1.5,
            gridcolor='rgba(122,184,212,0.2)',
            tickfont=dict(color='#4a7fa0', size=9), tickformat='.2f',
            scaleanchor='x', scaleratio=1,
        ),
        legend=dict(
            bgcolor='rgba(240,248,252,0.95)', bordercolor='#7ab8d4', borderwidth=1,
            font=dict(color='#0a2a42', size=9), x=1.01, xanchor='left', y=1, yanchor='top'
        ),
        annotations=annotations,
        hovermode='closest',
        margin=dict(l=55, r=10, t=40, b=50),
        height=580,
        uirevision='static',   # keeps zoom/pan stable
    )
    return fig


def add_fault_dot(fig, R_f, X_f, css):
    """Add only the impedance dot trace to an existing figure."""
    pt_color = {
        "z1": "#1d4ed8", "z2": "#d97706", "z3": "#dc2626",
        "z4": "#7c3aed", "psb": "#ca8a04", "load": "#059669", "normal": "#334155"
    }.get(css, "#334155")

    fig.add_trace(go.Scatter(
        x=[R_f], y=[X_f], mode='markers',
        marker=dict(size=20, color=pt_color, symbol='circle',
                    line=dict(color='white', width=3)),
        name='Z apparent', showlegend=False,
        hovertemplate=f'R={R_f:.4f}Ω<br>X={X_f:.4f}Ω<extra>Z apparent</extra>'
    ))
    # Dashed line from origin
    fig.add_trace(go.Scatter(
        x=[0, R_f], y=[0, X_f], mode='lines',
        line=dict(color=pt_color, width=1.2, dash='dot'),
        showlegend=False, hoverinfo='skip'
    ))
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# PLOT COLUMN
# ══════════════════════════════════════════════════════════════════════════════
with col_plot:
    # Status banner
    css_map = {
        "normal":"status-normal","z1":"status-z1","z2":"status-z2",
        "z3":"status-z3","z4":"status-z4","load":"status-load","psb":"status-psb"
    }
    icon = {"z1":"⚡","z2":"⚡","z3":"⚡","z4":"⚡","psb":"🌀","load":"🔋","normal":"✅"}.get(zone_css,"✅")
    trip_str = f"  |  Trip in {trip_time:.2f}s" if trip_time is not None else ""
    st.markdown(
        f'<div class="status-banner {css_map[zone_css]}">{icon} {zone_label}{trip_str}</div>',
        unsafe_allow_html=True
    )

    # Metrics
    Z_mag = math.sqrt(R_pt**2 + X_pt**2)
    Z_ang_ = math.degrees(math.atan2(X_pt, R_pt)) if Z_mag > 0 else 0
    st.markdown(
        f'<div class="metric-row">'
        f'<div class="mcard"><div class="mcard-lbl">R apparent</div><div class="mcard-val">{R_pt:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">X apparent</div><div class="mcard-val">{X_pt:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">|Z| apparent</div><div class="mcard-val">{Z_mag:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">∠Z</div><div class="mcard-val">{Z_ang_:.1f}°</div><div class="mcard-unit">degrees</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">Z1 reach</div><div class="mcard-val">{Z1s:.4f}</div><div class="mcard-unit">Ω sec</div></div>'
        f'<div class="mcard"><div class="mcard-lbl">MTA</div><div class="mcard-val">{Z1_ang:.1f}°</div><div class="mcard-unit">line angle</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    plot_placeholder = st.empty()

    # ── ANIMATION — only the dot moves, background is pre-built once ─────────
    if animate_swing or preset == "Power Swing (animate)":
        sw_Rs, sw_Xs = swing_locus_path(Z3s, c["Z_blinder_sec"], Z1_ang)
        base_fig = build_base_fig()

        # Pre-generate all frames as lightweight trace updates
        n = len(sw_Rs)
        step_skip = max(1, n // 120)   # limit to ~120 animation steps

        for i in range(0, n, step_skip):
            sw_R, sw_X = sw_Rs[i], sw_Xs[i]
            _, _, _, sw_css = classify_zone(sw_R, sw_X, c)

            # Clone base data and add dot
            anim_traces = list(base_fig.data)  # all static traces
            dot_color = {
                "z1":"#1d4ed8","z2":"#d97706","z3":"#dc2626",
                "z4":"#7c3aed","psb":"#ca8a04","load":"#059669","normal":"#f59e0b"
            }.get(sw_css, "#f59e0b")

            dot = go.Scatter(
                x=[sw_R], y=[sw_X], mode='markers',
                marker=dict(size=18, color=dot_color, symbol='circle',
                            line=dict(color='white', width=2.5)),
                showlegend=False, hoverinfo='skip',
                name='_swing_dot'
            )
            # Tail (last 5 positions)
            tail_start = max(0, i - 5 * step_skip)
            tail_R = sw_Rs[tail_start:i+1:step_skip]
            tail_X = sw_Xs[tail_start:i+1:step_skip]
            tail = go.Scatter(
                x=tail_R, y=tail_X, mode='lines',
                line=dict(color=dot_color, width=2, dash='solid'),
                showlegend=False, hoverinfo='skip', opacity=0.5,
                name='_swing_tail'
            )

            frame_fig = go.Figure(data=[*anim_traces, tail, dot],
                                  layout=base_fig.layout)
            plot_placeholder.plotly_chart(frame_fig, use_container_width=True,
                                          config={'staticPlot': True})
            time.sleep(swing_delay)
    else:
        fig = build_base_fig()
        fig = add_fault_dot(fig, R_pt, X_pt, zone_css)
        plot_placeholder.plotly_chart(fig, use_container_width=True)

    # ── Phasor diagram (Manual mode only) ────────────────────────────────────
    if show_phasors and preset == "Manual (sliders)":
        V_use = V_rated * (V_pct / 100.0)
        I_use = I_rated * (I_pct / 100.0)
        scale = V_use / max(I_use, 0.001) * 0.6
        V_r = V_use * math.cos(math.radians(V_ang))
        V_i = V_use * math.sin(math.radians(V_ang))
        I_r = I_use * math.cos(math.radians(I_ang)) * scale
        I_i = I_use * math.sin(math.radians(I_ang)) * scale

        fig_ph = go.Figure(data=[
            go.Scatter(x=[0, V_r], y=[0, V_i], mode='lines+markers',
                       line=dict(color='#0d7bbf', width=3),
                       marker=dict(size=[0, 10], color='#0d7bbf'),
                       name=f'V={V_use:.3f}V ∠{V_ang}°'),
            go.Scatter(x=[0, I_r], y=[0, I_i], mode='lines+markers',
                       line=dict(color='#dc2626', width=3),
                       marker=dict(size=[0, 10], color='#dc2626'),
                       name=f'I={I_use:.3f}A ∠{I_ang}° (scaled)'),
        ])
        fig_ph.update_layout(
            paper_bgcolor='#ffffff', plot_bgcolor='#f8fbfd', height=170,
            margin=dict(l=20, r=10, t=28, b=20),
            title=dict(text='Phasor Diagram (secondary)', font=dict(size=10, color='#0a2a42'), x=0.5),
            xaxis=dict(zeroline=True, zerolinecolor='rgba(10,42,66,0.3)',
                       gridcolor='rgba(122,184,212,0.2)', tickfont=dict(size=8)),
            yaxis=dict(zeroline=True, zerolinecolor='rgba(10,42,66,0.3)',
                       gridcolor='rgba(122,184,212,0.2)', tickfont=dict(size=8),
                       scaleanchor='x', scaleratio=1),
            legend=dict(font=dict(size=9), bgcolor='rgba(240,248,252,0.9)',
                        bordercolor='#7ab8d4', borderwidth=1),
            font=dict(family='IBM Plex Mono'),
        )
        st.plotly_chart(fig_ph, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# BOTTOM — REFERENCE TABLE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.expander("📋 Zone Settings Reference — Secondary Ω", expanded=False):
    ca, cb, cc_ = st.columns(3)
    with ca:
        st.markdown(f"""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:12px;
     font-family:IBM Plex Mono;font-size:12px;color:#0a2a42;line-height:1.9;">
<b>ZONE REACHES (sec Ω)</b><br>
Z1 = {Z1s:.5f} Ω &nbsp; t={c['tZ1']}s<br>
Z2 = {Z2s:.5f} Ω &nbsp; t={c['tZ2']}s<br>
Z3 = {Z3s:.5f} Ω &nbsp; t={c['tZ3']}s<br>
Z4 = {Z4s:.5f} Ω &nbsp; t={c['tZ4']}s (Rev)<br>
Line Z1 = {c['Z1_sec']:.5f} Ω ∠{Z1_ang:.2f}°<br>
kk = {kk:.6f}
</div>""", unsafe_allow_html=True)
    with cb:
        st.markdown(f"""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:12px;
     font-family:IBM Plex Mono;font-size:12px;color:#0a2a42;line-height:1.9;">
<b>LOAD & PSB</b><br>
Load R_blinder = {c['Z_blinder_sec']:.5f} Ω<br>
Load angle = {load_ang}° (slider)<br>
PSB ΔR = {c['Delta_R']:.5f} Ω<br>
δ_in = {c['delta_in']:.2f}°  δ_out = {c['delta_out']:.2f}°<br>
Zs_sec = {c['Zs_sec']:.5f} Ω<br>
PSB timer = {c['PSB_timer']} ms
</div>""", unsafe_allow_html=True)
    with cc_:
        st.markdown(f"""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:12px;
     font-family:IBM Plex Mono;font-size:12px;color:#0a2a42;line-height:1.9;">
<b>APPARENT Z POINT</b><br>
R_app = {R_pt:.5f} Ω<br>
X_app = {X_pt:.5f} Ω<br>
|Z|_app = {math.sqrt(R_pt**2+X_pt**2):.5f} Ω<br>
Kn = {c['Kn_mag']:.4f} ∠{c['Kn_ang']:.2f}°<br>
RE/RL={c['RE_RL']:.4f}  XE/XL={c['XE_XL']:.4f}<br>
Rf_sec = {Rf_sec:.5f} Ω
</div>""", unsafe_allow_html=True)

with st.expander("📖 How to Read This Diagram", expanded=False):
    st.markdown("""
<div style="background:#fff;border:1px solid #7ab8d4;border-radius:8px;padding:16px;
     font-family:IBM Plex Sans;font-size:13px;color:#0a2a42;line-height:1.9;">
<b>Quadrilateral Zones</b> — Z1 (blue), Z2 (orange), Z3 (red) are concentric parallelograms
rotated to the line impedance angle (MTA). Z4 (purple) is the reverse zone.
Faults appear inside these zones along the line angle direction.<br><br>
<b>Load Blinder</b> — Two angled green lines at ±load_angle from the R-axis intercept at R_load.
They cut off the right-side corners of Z3, preventing load encroachment from causing a trip.
Normal load impedance appears in the green shaded region — no trip regardless of Z3 reach.<br><br>
<b>PSB Detection Band</b> — Two offset quadrilaterals (teal, dashed).
The gap between inner and outer boundaries = ΔR. When the swing impedance crosses from outer to
inner in >PSB_timer (50ms), it is classified as a power swing → all zones blocked.
If crossing <50ms → fault → zones operate normally.<br><br>
<b>Swing Locus</b> — The cyan dashed path shows the trajectory of the apparent impedance
during a power swing. It enters from the load region (right side), spirals inward through
Z3→Z2→Z1, and exits the left side. Use ANIMATE SWING to see the dot travel this path.<br><br>
<b>Fault Resistance Rf</b> — Shifts Z_apparent rightward off the line angle.
High Rf (arc/tower footing resistance) can push Z_apparent outside Z1 → under-reach.
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-top:12px;padding:9px 16px;background:#f0f8fc;border:1px solid #7ab8d4;
     border-radius:6px;font-family:IBM Plex Mono;font-size:10px;color:#4a7fa0;line-height:1.9;">
⚡ Distance Protection Interactive R-X Visualiser v2 | {sub_name} — {line_name} |
{voltage}kV | {line_len:.0f}km | Z1={c['Z1_sec']:.4f}Ω ∠{Z1_ang:.1f}° |
CTR={ct_pri}/{ct_sec} PTR={c['PTR']:.0f} kk={kk:.5f} | Secondary Ω | Quadrilateral
</div>
""", unsafe_allow_html=True)
