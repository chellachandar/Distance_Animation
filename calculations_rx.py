import math

CONDUCTORS = {
    "ACSR Moose": 707, "ACSR Zebra": 625, "ACSR Snowbird": 703,
    "ACSR Bersimis": 817, "ACSR Lapwing": 899, "ACSR Panther": 422,
    "AAAC Moose Equiv.": 726, "ACSR Drake": 900, "ACSR Cardinal": 996,
}

def calculate_all(inp):
    L       = inp["line_length"]
    X1      = inp["x1"]; R1 = inp["r1"]
    X0      = inp["x0"]; R0 = inp["r0"]
    VkV     = inp["voltage_kv"]
    CTR     = inp["ct_primary"] / inp["ct_secondary"]
    PTR     = (inp["pt_primary_kv"] * 1000) / inp["pt_secondary_v"]
    kk      = CTR / PTR
    If3L    = inp["fault_3ph_local"]
    If1R    = inp["fault_1ph_remote"]
    n_cond  = inp["num_conductors"]
    cond    = inp["conductor_name"]
    I_nom   = inp["nominal_current"]
    f_sw    = inp.get("swing_freq", 1.5)
    Z1_lng  = inp["longest_remote_z1km"] * inp["longest_remote_length"]
    Z1_sh   = inp["shortest_remote_z1km"] * inp["shortest_remote_length"]

    # 1. TOTAL LINE IMPEDANCES
    R1t = R1 * L;  X1t = X1 * L
    R0t = R0 * L;  X0t = X0 * L
    Z1_mag = math.sqrt(R1t**2 + X1t**2)
    Z1_ang = math.degrees(math.atan2(X1t, R1t))
    Z0_mag = math.sqrt(R0t**2 + X0t**2)
    Z0_ang = math.degrees(math.atan2(X0t, R0t))
    Z1_sec = Z1_mag * kk

    # 2. EARTH COMPENSATION
    Z1c = complex(R1t, X1t); Z0c = complex(R0t, X0t)
    Kn  = (Z0c - Z1c) / (3 * Z1c)
    Kn_mag = abs(Kn); Kn_ang = math.degrees(math.atan2(Kn.imag, Kn.real))
    RE_RL = (R0 - R1) / (3 * R1)
    XE_XL = (X0 - X1) / (3 * X1)

    # 3. SHORT LINE CHECK
    short_line = L <= 30

    # 4. ZONE REACHES
    Z1_pct = 0.80
    Z1r_pri = Z1_pct * Z1_mag
    Z1r_sec = Z1r_pri * kk
    tZ1 = 0.0

    Z2_pct = 1.20
    Z2r_pri = Z2_pct * Z1_mag
    Z2r_sec = Z2r_pri * kk
    Z2_check = Z1_mag * (Z2_pct - 1.0)
    tZ2 = 0.35 if Z2_check < 0.6 * Z1_sh else 0.50

    Z3_opt1 = Z1_mag + 1.10 * Z1_lng
    Z3_opt2 = Z1_mag + 0.50 * Z1_sh
    Z3r_pri = max(Z3_opt1, Z3_opt2)
    Z3_pct  = Z3r_pri / Z1_mag
    Z3r_sec = Z3r_pri * kk
    tZ3 = 1.0 if VkV >= 400 else 0.8

    Z4_line_pct = 0.20 if L <= 100 else 0.10
    Z4r_pri = Z4_line_pct * Z1_mag
    Z4r_sec = Z4r_pri * kk
    tZ4 = 0.5

    # 5. FAULT MVA
    FMVA = math.sqrt(3) * VkV * If3L / 1000

    # 6. CONDUCTOR THERMAL / MIN LOAD
    thermal = CONDUCTORS.get(cond, 700) * n_cond
    I_max   = 1.5 * min(thermal, I_nom)
    V_ph    = 0.85 * VkV * 1000 / math.sqrt(3)
    Rload_pri = V_ph / I_max
    Rload_sec = Rload_pri * kk
    load_angle = 30

    # 7. DEF
    Is_pri = 300 if VkV >= 765 else 200
    Is_sec = Is_pri / CTR
    t_op   = tZ3 + 0.1
    ratio  = If1R / Is_pri
    TMS    = t_op * (ratio**0.02 - 1) / 0.14
    IN_char_angle = -45
    IN_polarisation = "Negative Sequence"
    I2pol  = 50
    V2pol  = round((inp["pt_secondary_v"] / math.sqrt(3)) * 0.05, 3)

    # 8. LOAD ENCROACHMENT
    numerator     = math.cos(math.radians(load_angle + 90 - Z1_ang))
    denominator   = math.cos(math.radians(90 - Z1_ang))
    Z_blinder_pri = Rload_pri * (numerator / denominator)
    Z_blinder_sec = Z_blinder_pri * kk
    Z_blinder_simple_sec = Rload_sec
    Z3_vs_load = Z3r_sec / Z_blinder_simple_sec
    load_encroach_risk = Z3_vs_load > 0.8

    # 9. PSB
    Vbase = VkV * 1000 / math.sqrt(3)
    Zs_pri = Vbase / If3L
    Zs_sec = Zs_pri * kk
    R3Ph_sec = Z_blinder_simple_sec
    RLdInFw  = R3Ph_sec / 2
    delta_ang = f_sw * 0.005 * 180
    tan_in    = Zs_sec / (2 * RLdInFw)
    delta_in  = 2 * math.degrees(math.atan(tan_in))
    delta_out = delta_in - delta_ang
    if abs(math.tan(math.radians(delta_out / 2))) > 1e-9:
        RLdOutFw = Zs_sec / (2 * math.tan(math.radians(abs(delta_out) / 2)))
    else:
        RLdOutFw = RLdInFw * 6
    Delta_R  = RLdOutFw - RLdInFw
    PSB_timer = 50

    Z7 = Z3r_sec
    Z8 = RLdInFw
    Alpha = Z1_ang

    return {
        "R1t": R1t, "X1t": X1t, "Z1_mag": Z1_mag, "Z1_ang": Z1_ang,
        "R0t": R0t, "X0t": X0t, "Z0_mag": Z0_mag, "Z0_ang": Z0_ang,
        "Z1_sec": Z1_sec, "kk": kk, "CTR": CTR, "PTR": PTR,
        "Kn_mag": Kn_mag, "Kn_ang": Kn_ang,
        "RE_RL": RE_RL, "XE_XL": XE_XL,
        "Z1_lng": Z1_lng, "Z1_sh": Z1_sh,
        "short_line": short_line,
        "Z1_pct": Z1_pct, "Z1r_pri": Z1r_pri, "Z1r_sec": Z1r_sec, "tZ1": tZ1,
        "Z2_pct": Z2_pct, "Z2r_pri": Z2r_pri, "Z2r_sec": Z2r_sec, "tZ2": tZ2,
        "Z2_check": Z2_check, "Z2_60pct_sh": 0.6 * Z1_sh,
        "Z3_opt1": Z3_opt1, "Z3_opt2": Z3_opt2,
        "Z3_pct": Z3_pct, "Z3r_pri": Z3r_pri, "Z3r_sec": Z3r_sec, "tZ3": tZ3,
        "Z4_line_pct": Z4_line_pct, "Z4r_pri": Z4r_pri, "Z4r_sec": Z4r_sec, "tZ4": tZ4,
        "FMVA": FMVA, "thermal": thermal, "I_max": I_max,
        "Rload_pri": Rload_pri, "Rload_sec": Rload_sec,
        "Is_pri": Is_pri, "Is_sec": Is_sec, "t_op": t_op,
        "If1R": If1R, "ratio": ratio, "TMS": TMS,
        "IN_char_angle": IN_char_angle, "IN_polarisation": IN_polarisation,
        "I2pol": I2pol, "V2pol": V2pol,
        "Z_blinder_sec": Z_blinder_simple_sec,
        "Z3_vs_load": Z3_vs_load, "load_encroach_risk": load_encroach_risk,
        "load_angle": load_angle,
        "Zs_pri": Zs_pri, "Zs_sec": Zs_sec,
        "RLdInFw": RLdInFw, "RLdOutFw": RLdOutFw,
        "Delta_R": Delta_R, "delta_in": delta_in, "delta_out": delta_out,
        "PSB_timer": PSB_timer, "f_sw": f_sw,
        "Z7": Z7, "Z8": Z8, "Alpha": Alpha,
    }
