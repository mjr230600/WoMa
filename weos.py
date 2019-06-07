#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  1 10:38:18 2019

@author: Sergio Ruiz-Bonilla
"""
# ============================================================================ #
# ===================== Libraries and constants ============================== #
# ============================================================================ #

import numpy as np
import matplotlib.pyplot as plt
from numba import jit
import os
import sys

import warnings
warnings.filterwarnings("ignore")

G       = 6.67408E-11
R_earth = 6371000
M_earth = 5.972E24
R_gas   = 8.3145     # Gas constant (J K^-1 mol^-1)

# Go to the WoMa directory
dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir)
sys.path.append(dir)

# Material IDs, same as SWIFT ( = type_id * type_factor + unit_id)
type_factor = 100
Di_mat_type = {
    "idg"       : 0,
    "Til"       : 1,
    "HM80"      : 2,
    "SESAME"    : 3,
    }
Di_mat_id   = {
    # Ideal Gas
    "idg_HHe"       : Di_mat_type["idg"]*type_factor,
    "idg_N2"        : Di_mat_type["idg"]*type_factor + 1,
    "idg_CO2"       : Di_mat_type["idg"]*type_factor + 2,
    # Tillotson
    "Til_iron"      : Di_mat_type["Til"]*type_factor,
    "Til_granite"   : Di_mat_type["Til"]*type_factor + 1,
    "Til_water"     : Di_mat_type["Til"]*type_factor + 2,
    # Hubbard & MacFarlane (1980) Uranus/Neptune
    "HM80_HHe"      : Di_mat_type["HM80"]*type_factor,      # Hydrogen-helium atmosphere
    "HM80_ice"      : Di_mat_type["HM80"]*type_factor + 1,  # H20-CH4-NH3 ice mix
    "HM80_rock"     : Di_mat_type["HM80"]*type_factor + 2,  # SiO2-MgO-FeS-FeO rock mix
    # SESAME
    "SESAME_iron"   : Di_mat_type["SESAME"]*type_factor,        # 2140
    "SESAME_basalt" : Di_mat_type["SESAME"]*type_factor + 1,    # 7530
    "SESAME_water"  : Di_mat_type["SESAME"]*type_factor + 2,    # 7154
    "SS08_water"    : Di_mat_type["SESAME"]*type_factor + 3,    # Senft & Stewart (2008)
    "SESAME_H2"     : Di_mat_type["SESAME"]*type_factor + 4,    # 5251
    "SESAME_N2"     : Di_mat_type["SESAME"]*type_factor + 5,    # 5000
    "SESAME_steam"  : Di_mat_type["SESAME"]*type_factor + 6,    # 7152
    "SESAME_CO2"    : Di_mat_type["SESAME"]*type_factor + 7,    # 5212
    }
# Separate variables because numba can't handle dictionaries
# Types
type_idg    = Di_mat_type["idg"]
type_Til    = Di_mat_type["Til"]
type_HM80   = Di_mat_type["HM80"]
type_SESAME = Di_mat_type["SESAME"]
# IDs
id_idg_HHe          = Di_mat_id["idg_HHe"]
id_idg_N2           = Di_mat_id["idg_N2"]
id_idg_CO2          = Di_mat_id["idg_CO2"]
id_Til_iron         = Di_mat_id["Til_iron"]
id_Til_granite      = Di_mat_id["Til_granite"]
id_Til_water        = Di_mat_id["Til_water"]
id_HM80_HHe         = Di_mat_id["HM80_HHe"]
id_HM80_ice         = Di_mat_id["HM80_ice"]
id_HM80_rock        = Di_mat_id["HM80_rock"]
id_SESAME_iron      = Di_mat_id["SESAME_iron"]
id_SESAME_basalt    = Di_mat_id["SESAME_basalt"]
id_SESAME_water     = Di_mat_id["SESAME_water"]
id_SS08_water       = Di_mat_id["SS08_water"]
id_SESAME_H2        = Di_mat_id["SESAME_H2"]
id_SESAME_N2        = Di_mat_id["SESAME_N2"]
id_SESAME_steam     = Di_mat_id["SESAME_steam"]
id_SESAME_CO2       = Di_mat_id["SESAME_CO2"]

# T-rho relation types
type_rho_pow    = 1
type_adb        = 2

# Local data files
dir_data    = "data/"
# Cold curves
Fp_u_cold_Til_iron      = dir_data + "u_cold_array_Til_iron.npy"
Fp_u_cold_Til_granite   = dir_data + "u_cold_array_Til_granite.npy"
Fp_u_cold_Til_water     = dir_data + "u_cold_array_Til_water.npy"
# SESAME tables
Fp_SESAME_iron      = dir_data + "SESAME_iron_2140.txt"
Fp_SESAME_basalt    = dir_data + "SESAME_basalt_7530.txt"
Fp_SESAME_water     = dir_data + "SESAME_water_7154.txt"
Fp_SS08_water       = dir_data + "SS08_water.txt"
Fp_SESAME_H2        = dir_data + "SESAME_H2_5251.txt"
Fp_SESAME_N2        = dir_data + "SESAME_N2_5000.txt"
Fp_SESAME_steam     = dir_data + "SESAME_steam_7152.txt"
Fp_SESAME_CO2       = dir_data + "SESAME_CO2_5212.txt"

# Misc utilities (move to separate file...) / this function is also in woma.py
def check_end(string, end):
    """ Check that a string ends with the required characters and append them
        if not.
    """
    if string[-len(end):] != end:
        string  += end

    return string

@jit(nopython=True)
def find_index_and_interp(x, A1_x):
   """ Return the index and interpolation factor of a value in an array.

       Allows x outside A1_x. If so then intp will be < 0 or > 1.

       Args:
           x (float)
               The value to find.

           A1_x ([float])
               The array to search.

       Returns:
           idx (int)
               The index of the last array element smaller than the value.

               0               If x is below A1_x.
               len(A1_x) - 2   If x is above A1_x.

           intp (float)
               The interpolation factor for how far the values is from the
               indexed array value to the next.

               < 0     If x is below A1_x.
               > 1     If x is above A1_x.
   """
   idx = np.searchsorted(A1_x, x) - 1
   # Return error values if outside the array
   if idx == -1:
       idx = 0
   elif idx >= len(A1_x) - 1:
       idx = len(A1_x) - 2
   intp    = (x - A1_x[idx]) / (A1_x[idx + 1] - A1_x[idx])

   return np.array([idx, intp])

# SESAME
def load_table_SESAME(Fp_table):
    """ Load and return the table file data.

        # header (five lines)
        num_rho  num_T
        A1_rho
        A1_T
        A2_u[0, 0]              A2_P[0, 0]      A2_c[0, 0]      A2_s[0, 0]
        A2_u[1, 0]              ...
        ...                     ...
        A2_u[num_rho, 0]        ...
        A2_u[0, 1]              ...
        ...                     ...
        A2_u[num_rho, 1]        ...
        ...                     ...
        A2_u[num_rho, num_u]    ...

        Args:
            Fp_table (str)
                The table file path.

        Returns:
            # num_rho, num_T (int)
            #     Number of densities and temperatures for the arrays.

            # rho_min, rho_max (float)
            #     Penultimate minimin and maximum values of the temperature
            #     array (K).

            # T_min, T_max (float)
            #     Penultimate minimin and maximum values of the density array
            #     (kg m^-3).

            # A1_rho, A1_T ([float])
            #     1D arrays of density (kg m^-3) and temperature (K).

            A2_u, A2_P, A2_s, # A2_c ([[float]])
                2D arrays of sp. int. energy (J kg^-1), pressure (Pa),
                # sp. entropy (J kg^-1 K^-1), and sound speed (m s^-1).

            A1_log_rho, A1_log_T ([float])
                1D arrays of natural logs of density (kg m^-3) and
                temperature (K).

            A2_log_u, # A2_log_P, A2_log_c ([[float]])
                2D arrays of natural logs of sp. int. energy (J kg^-1),
                pressure (Pa), sound speed (m s^-1).
    """
    # Load
    Fp_table    = check_end(Fp_table, ".txt")
    with open(Fp_table) as f:
        for i in range(5):
            f.readline()
        num_rho, num_T  = np.array(f.readline().split(), dtype=int)
        A2_u    = np.empty((num_rho, num_T))
        A2_P    = np.empty((num_rho, num_T))
        A2_c    = np.empty((num_rho, num_T))
        A2_s    = np.empty((num_rho, num_T))

        A1_rho  = np.array(f.readline().split(), dtype=float)
        A1_T    = np.array(f.readline().split(), dtype=float)

        for i_T in range(num_T):
            for i_rho in range(num_rho):
                A2_u[i_rho, i_T], A2_P[i_rho, i_T], A2_c[i_rho, i_T], \
                    A2_s[i_rho, i_T]    = np.array(f.readline().split(),
                                                   dtype=float)

    return A2_u, A2_P, A2_s, np.log(A1_rho), np.log(A1_T), np.log(A2_u)

# ============================================================================ #
# ===================== Functions ============================================ #
# ============================================================================ #

@jit(nopython=True)
def _P_u_rho_SESAME(u, rho, mat_id):
    """ Computes pressure for the SESAME EoS.

        Args:
            u (double)
                Specific internal energy (SI).

            rho (double)
                Density (SI).

            mat_id (int)
                Material id.

        Returns:
            P (double)
                Pressure (SI).
    """
    # Choose the arrays from the global variables
    if (mat_id == id_SESAME_iron):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_iron, A1_log_rho_SESAME_iron, A2_log_u_SESAME_iron
            )
    elif (mat_id == id_SESAME_basalt):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_basalt, A1_log_rho_SESAME_basalt, A2_log_u_SESAME_basalt
            )
    elif (mat_id == id_SESAME_water):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_water, A1_log_rho_SESAME_water, A2_log_u_SESAME_water
            )
    elif (mat_id == id_SS08_water):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SS08_water, A1_log_rho_SS08_water, A2_log_u_SS08_water
            )
    elif (mat_id == id_SESAME_H2):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_H2, A1_log_rho_SESAME_H2, A2_log_u_SESAME_H2
            )
    elif (mat_id == id_SESAME_N2):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_N2, A1_log_rho_SESAME_N2, A2_log_u_SESAME_N2
            )
    elif (mat_id == id_SESAME_steam):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_steam, A1_log_rho_SESAME_steam, A2_log_u_SESAME_steam
            )
    elif (mat_id == id_SESAME_CO2):
        A2_P, A1_log_rho, A2_log_u = (
            A2_P_SESAME_CO2, A1_log_rho_SESAME_CO2, A2_log_u_SESAME_CO2
            )
    else:
       raise ValueError("Invalid material ID")

    # Ignore the first elements of rho = 0, T = 0
    A2_P        = A2_P[1:, 1:]
    A2_log_u    = A2_log_u[1:, 1:]

    # Convert to log
    log_rho = np.log(rho)
    log_u   = np.log(u)

    # 2D interpolation (bilinear with log(rho), log(u)) to find P(rho, u).
    # If rho and/or u are below or above the table, then use the interpolation
    # formula to extrapolate using the edge and edge-but-one values.

    # Density
    idx_rho_intp_rho   = find_index_and_interp(log_rho, A1_log_rho[1:])
    idx_rho     = int(idx_rho_intp_rho[0])
    intp_rho    = idx_rho_intp_rho[1]

    # u (in this and the next density slice of the 2D u array)
    idx_u_1_intp_u_1   = find_index_and_interp(log_u, A2_log_u[idx_rho])
    idx_u_1            = int(idx_u_1_intp_u_1[0])
    intp_u_1           = idx_u_1_intp_u_1[1]
    idx_u_2_intp_u_2   = find_index_and_interp(log_u, A2_log_u[idx_rho + 1])
    idx_u_2            = int(idx_u_2_intp_u_2[0])
    intp_u_2           = idx_u_2_intp_u_2[1]

    P_1 = A2_P[idx_rho, idx_u_1]
    P_2 = A2_P[idx_rho, idx_u_1 + 1]
    P_3 = A2_P[idx_rho + 1, idx_u_2]
    P_4 = A2_P[idx_rho + 1, idx_u_2 + 1]

    # If more than two table values are non-positive then return zero
    num_non_pos = np.sum(np.array([P_1, P_2, P_3, P_4]) < 0)
    #num_non_pos = np.sum([int(P_i <= 0) for P_i in [P_1, P_2, P_3, P_4]])
    if num_non_pos > 2:
        return 0.

    # If just one or two are non-positive then replace them with a tiny value
    # Unless already trying to extrapolate in which case return zero
    if num_non_pos > 0:
        if intp_rho < 0 or intp_u_1 < 0 or intp_u_2 < 0:
            return 0.
        else:
            #P_tiny  = np.amin(A2_P[A2_P > 0]) * 1e-3
            P_tiny  = np.amin(np.abs(A2_P)) * 1e-3
            if P_1 <= 0:
                P_1 = P_tiny
            if P_2 <= 0:
                P_2 = P_tiny
            if P_3 <= 0:
                P_3 = P_tiny
            if P_4 <= 0:
                P_4 = P_tiny

    # Interpolate with the log values
    P_1 = np.log(P_1)
    P_2 = np.log(P_2)
    P_3 = np.log(P_3)
    P_4 = np.log(P_4)

    # P(rho, u)
    P   = ((1 - intp_rho) * ((1 - intp_u_1) * P_1 + intp_u_1 * P_2)
           + intp_rho * ((1 - intp_u_2) * P_3 + intp_u_2 * P_4))

    # Convert back from log
    return np.exp(P)

@jit(nopython=True)
def u_rho_T_SESAME(rho, T, mat_id):
    """ Calculate the specific internal energy as a function of density and
        temperature for the SESAME EoS.

        Args:
            T (double)
                Temperature (SI).

            rho (double)
                Density (SI).

            mat_id (int)
                Material id.

        Returns:
            u (double)
                Specific internal energy (SI).
    """
    # Choose the arrays from the global variables
    if (mat_id == id_SESAME_iron):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_iron, A1_log_rho_SESAME_iron, A1_log_T_SESAME_iron
            )
    elif (mat_id == id_SESAME_basalt):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_basalt, A1_log_rho_SESAME_basalt,
            A1_log_T_SESAME_basalt
            )
    elif (mat_id == id_SESAME_water):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_water, A1_log_rho_SESAME_water,
            A1_log_T_SESAME_water
            )
    elif (mat_id == id_SS08_water):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SS08_water, A1_log_rho_SS08_water, A1_log_T_SS08_water
            )
    elif (mat_id == id_SESAME_H2):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_H2, A1_log_rho_SESAME_H2, A1_log_T_SESAME_H2
            )
    elif (mat_id == id_SESAME_N2):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_N2, A1_log_rho_SESAME_N2, A1_log_T_SESAME_N2
            )
    elif (mat_id == id_SESAME_steam):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_steam, A1_log_rho_SESAME_steam,
            A1_log_T_SESAME_steam
            )
    elif (mat_id == id_SESAME_CO2):
        A2_u, A1_log_rho, A1_log_T = (
            A2_u_SESAME_CO2, A1_log_rho_SESAME_CO2, A1_log_T_SESAME_CO2
            )
    else:
       raise ValueError("Invalid material ID")

    # Ignore the first elements of rho = 0, T = 0
    A2_u    = A2_u[1:, 1:]

    # Convert to log
    log_rho = np.log(rho)
    log_T   = np.log(T * 1) ### why is numba so weird?

    # 2D interpolation (bilinear with log(rho), log(T)) to find u(rho, T).
    # If rho and/or T are below or above the table, then use the interpolation
    # formula to extrapolate using the edge and edge-but-one values.

    # Density
    idx_rho_intp_rho   = find_index_and_interp(log_rho, A1_log_rho[1:])
    idx_rho     = int(idx_rho_intp_rho[0])
    intp_rho    = idx_rho_intp_rho[1]

    # Temperature
    idx_T_intp_T   = find_index_and_interp(log_T, A1_log_T[1:])
    idx_T = int(idx_T_intp_T[0])
    intp_T = idx_T_intp_T[1]

    u_1 = A2_u[idx_rho, idx_T]
    u_2 = A2_u[idx_rho, idx_T + 1]
    u_3 = A2_u[idx_rho + 1, idx_T]
    u_4 = A2_u[idx_rho + 1, idx_T + 1]

    # If more than two table values are non-positive then return zero
    num_non_pos = np.sum(np.array([u_1, u_2, u_3, u_4]) < 0)
    if num_non_pos > 2:
        return 0.

    # If just one or two are non-positive then replace them with a tiny value
    # Unless already trying to extrapolate in which case return zero
    if num_non_pos > 0:
        if intp_rho < 0 or intp_T < 0:
            return 0.
        else:
            u_tiny  = np.amin(np.abs(A2_u)) * 1e-3
            if u_1 <= 0:
                u_1 = u_tiny
            if u_2 <= 0:
                u_2 = u_tiny
            if u_3 <= 0:
                u_3 = u_tiny
            if u_4 <= 0:
                u_4 = u_tiny

    # Interpolate with the log values
    u_1 = np.log(u_1)
    u_2 = np.log(u_2)
    u_3 = np.log(u_3)
    u_4 = np.log(u_4)

    # u(rho, T)
    u   = ((1 - intp_rho) * ((1 - intp_T) * u_1 + intp_T * u_2)
           + intp_rho * ((1 - intp_T) * u_3 + intp_T * u_4))

    # Convert back from log
    return np.exp(u)

@jit(nopython=True)
def s_rho_T_SESAME(rho, T, mat_id):
    """ Calculate the specific entropy as a function of density and
        temperature for the SESAME EoS.

        Args:
            rho (double)
                Density (SI).

            T (double)
                Temperature (SI).

            mat_id (int)
                Material id.

        returns:
            s (double)
                Specific internal energy (SI).
    """
    # Choose the arrays from the global variables
    if (mat_id == id_SESAME_iron):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_iron, A1_log_rho_SESAME_iron, A1_log_T_SESAME_iron
            )
    elif (mat_id == id_SESAME_basalt):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_basalt, A1_log_rho_SESAME_basalt,
            A1_log_T_SESAME_basalt
            )
    elif (mat_id == id_SESAME_water):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_water, A1_log_rho_SESAME_water,
            A1_log_T_SESAME_water
            )
    elif (mat_id == id_SS08_water):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SS08_water, A1_log_rho_SS08_water, A1_log_T_SS08_water
            )
    elif (mat_id == id_SESAME_H2):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_H2, A1_log_rho_SESAME_H2, A1_log_T_SESAME_H2
            )
    elif (mat_id == id_SESAME_N2):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_N2, A1_log_rho_SESAME_N2, A1_log_T_SESAME_N2
            )
    elif (mat_id == id_SESAME_steam):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_steam, A1_log_rho_SESAME_steam,
            A1_log_T_SESAME_steam
            )
    elif (mat_id == id_SESAME_CO2):
        A2_s, A1_log_rho, A1_log_T = (
            A2_s_SESAME_CO2, A1_log_rho_SESAME_CO2, A1_log_T_SESAME_CO2
            )
    else:
       raise ValueError("Invalid material ID")

    # Ignore the first elements of rho = 0, T = 0
    A2_s    = A2_s[1:, 1:]

    # Convert to log
    log_rho = np.log(rho)
    log_T   = np.log(T)

    # 2D interpolation (bilinear with log(rho), log(T)) to find s(rho, T).
    # If rho and/or T are below or above the table, then use the interpolation
    # formula to extrapolate using the edge and edge-but-one values.

    # Density
    idx_rho_intp_rho   = find_index_and_interp(log_rho, A1_log_rho[1:])
    idx_rho     = int(idx_rho_intp_rho[0])
    intp_rho    = idx_rho_intp_rho[1]

    # Temperature
    idx_T_intp_T   = find_index_and_interp(log_T, A1_log_T[1:])
    idx_T = int(idx_T_intp_T[0])
    intp_T = idx_T_intp_T[1]

    s_1 = A2_s[idx_rho, idx_T]
    s_2 = A2_s[idx_rho, idx_T + 1]
    s_3 = A2_s[idx_rho + 1, idx_T]
    s_4 = A2_s[idx_rho + 1, idx_T + 1]

    # If more than two table values are non-positive then return zero
    num_non_pos = np.sum(np.array([s_1, s_2, s_3, s_4]) < 0)
    if num_non_pos > 2:
        return 0.

    # If just one or two are non-positive then replace them with a tiny value
    # Unless already trying to extrapolate in which case return zero
    if num_non_pos > 0:
        if intp_rho < 0 or intp_T < 0:
            return 0.
        else:
            s_tiny  = np.amin(np.abs(A2_s)) * 1e-3
            if s_1 <= 0:
                s_1 = s_tiny
            if s_2 <= 0:
                s_2 = s_tiny
            if s_3 <= 0:
                s_3 = s_tiny
            if s_4 <= 0:
                s_4 = s_tiny

    # s(rho, T)
    s   = ((1 - intp_rho) * ((1 - intp_T) * s_1 + intp_T * s_2)
           + intp_rho * ((1 - intp_T) * s_3 + intp_T * s_4))

    return s

@jit(nopython=True)
def T_rho_s_SESAME(rho, s, mat_id):
    """ Calculate the temperature as a function of density and
        specific entropy for the SESAME EoS.

        Args:
            rho (double)
                Density (SI).

            s (double)
                Specific entropy (SI).

            mat_id (int)
                Material id.

        Returns:
            T (double)
                Temperature (SI).
    """
    # Choose the arrays from the global variables
    if (mat_id == id_SESAME_iron):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_iron, A1_log_rho_SESAME_iron, A2_s_SESAME_iron
            )
    elif (mat_id == id_SESAME_basalt):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_basalt, A1_log_rho_SESAME_basalt, A2_s_SESAME_basalt
            )
    elif (mat_id == id_SESAME_water):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_water, A1_log_rho_SESAME_water, A2_s_SESAME_water
            )
    elif (mat_id == id_SS08_water):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SS08_water, A1_log_rho_SS08_water, A2_s_SS08_water
            )
    elif (mat_id == id_SESAME_H2):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_H2, A1_log_rho_SESAME_H2, A2_s_SESAME_H2
            )
    elif (mat_id == id_SESAME_N2):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_N2, A1_log_rho_SESAME_N2, A2_s_SESAME_N2
            )
    elif (mat_id == id_SESAME_steam):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_steam, A1_log_rho_SESAME_steam, A2_s_SESAME_steam
            )
    elif (mat_id == id_SESAME_CO2):
        A1_log_T, A1_log_rho, A2_s  = (
            A1_log_T_SESAME_CO2, A1_log_rho_SESAME_CO2, A2_s_SESAME_CO2
            )
    else:
       raise ValueError("Invalid material ID")

    # Convert to log
    log_rho = np.log(rho)

    idx_rho_intp_rho   = find_index_and_interp(log_rho, A1_log_rho)
    idx_rho     = int(idx_rho_intp_rho[0])
    intp_rho    = idx_rho_intp_rho[1]

    # s (in this and the next density slice of the 2D s array)
    idx_s_1_intp_s_1   = find_index_and_interp(s, A2_s[idx_rho])
    idx_s_1            = int(idx_s_1_intp_s_1[0])
    intp_s_1           = idx_s_1_intp_s_1[1]
    idx_s_2_intp_s_2   = find_index_and_interp(s, A2_s[idx_rho + 1])
    idx_s_2            = int(idx_s_2_intp_s_2[0])
    intp_s_2           = idx_s_2_intp_s_2[1]

    # Normal interpolation
    log_T   = ((1 - intp_rho) * ((1 - intp_s_1) * A1_log_T[idx_s_1]
                                 + intp_s_1 * A1_log_T[idx_s_1 + 1])
               + intp_rho * ((1 - intp_s_2) * A1_log_T[idx_s_2]
                             + intp_s_2 * A1_log_T[idx_s_2 + 1]))

    # Convert back from log
    return np.exp(log_T)

@jit(nopython=True)
def _P_u_rho_Till(u, rho, mat_id):
    """ Computes pressure for Tillotson EoS.

        Args:
            u (double)
                Specific internal energy (SI).

            rho (double)
                Density (SI).

            mat_id (int)
                Material id.

        Returns:
            P (double)
                Pressure (SI).
    """
    # Material constants for Tillotson EoS
    # mat_id, rho0, a, b, A, B, u_0, u_iv, u_cv, alpha, beta, eta_min, P_min, eta_zero
    iron    = np.array([id_Til_iron, 7800, 0.5, 1.5, 1.28e11, 1.05e11, 9.5e9, 2.4e9, 8.67e9, 5, 5, 0, 0, 0])
    granite = np.array([id_Til_granite, 2680, 0.5, 1.3, 1.8e10, 1.8e10, 1.6e10, 3.5e9, 1.8e10, 5, 5, 0, 0, 0])
    water   = np.array([id_Til_water, 998, 0.7, 0.15, 2.18e9, 1.325e10, 7.0e9, 4.19e8, 2.69e9, 10, 5, 0.925, 0, 0.875])

    if (mat_id == id_Til_iron):
        material = iron
    elif (mat_id == id_Til_granite):
        material = granite
    elif (mat_id == id_Til_water):
        material = water
    else:
        raise ValueError("Invalid material ID")

    rho0     = material[1]
    a        = material[2]
    b        = material[3]
    A        = material[4]
    B        = material[5]
    u_0      = material[6]
    u_iv     = material[7]
    u_cv     = material[8]
    alpha    = material[9]
    beta     = material[10]
    eta_min  = material[11]
    P_min    = material[12]
    eta_zero = material[13]

    eta      = rho/rho0
    eta_sq   = eta*eta
    mu       = eta - 1.
    nu       = 1./eta - 1.
    w        = u/(u_0*eta_sq) + 1.
    w_inv    = 1./w

    P_c = 0.
    P_e = 0.
    P   = 0.

    # Condensed or cold
    P_c = (a + b*w_inv)*rho*u + A*mu + B*mu*mu

    if eta < eta_zero:
        P_c = 0.
    elif eta < eta_min:
        P_c *= (eta - eta_zero) / (eta_min - eta_zero)

    # Expanded and hot
    P_e = a*rho*u + (b*rho*u*w_inv + A*mu*np.exp(-beta*nu))                   \
                     *np.exp(-alpha*nu*nu)


    # Condensed or cold state
    if (1. < eta) or (u < u_iv):
        P = P_c

    # Expanded and hot state
    elif ((eta < 1) and (u_cv < u)):
        P = P_e

    # Hybrid state
    else:
        P = ((u - u_iv) * P_e + (u_cv - u) * P_c) /                           \
                                (u_cv - u_iv)

    # Minimum pressure
    if (P < P_min):
        P = P_min

    return P

@jit(nopython=True)
def _P_u_rho_idg(u, rho, mat_id):
    """ Computes pressure for the ideal gas EoS.

        Args:
            u (double)
                Specific internal energy (SI).

            rho (double)
                Density (SI).

            mat_id (int)
                Material id.

        Returns:
            P (double)
                Pressure (SI).
    """
    # Material constants for ideal gas EoS
    # mat_id, gamma
    HHe = np.array([id_idg_HHe, 1.4])
    N2  = np.array([id_idg_N2, 1.4])
    CO2 = np.array([id_idg_CO2, 1.29])

    if (mat_id == id_idg_HHe):
        material = HHe
    elif (mat_id == id_idg_N2):
        material = N2
    elif (mat_id == id_idg_CO2):
        material = CO2
    else:
        raise ValueError("Invalid material ID")

    gamma    = material[1]

    P = (gamma - 1)*u*rho

    return P

@jit(nopython=True)
def P_EoS(u, rho, mat_id):
    """ Computes pressure for a given material.

        Args:
            u (double)
                Specific internal energy (SI).

            rho (double)
                Density (SI).

            mat_id (int)
                Material id.

        Returns:
            P (double)
                Pressure (SI).
    """
    mat_type    = mat_id // type_factor
    if (mat_type == type_idg):
        return _P_u_rho_idg(u, rho, mat_id)
    elif (mat_type == type_Til):
        return _P_u_rho_Till(u, rho, mat_id)
    elif (mat_type == type_SESAME):
        return _P_u_rho_SESAME(u, rho, mat_id)
    else:
        raise ValueError("Invalid material ID")

@jit(nopython=True)
def _rho_0_material(mat_id):
    """ Returns rho0 for a given material id. u_{cold}(rho0) = 0

        Args:
            mat_id (int)
                Material id.

        Returns:
            rho0 (double)
                Density (SI).

    """
    mat_type    = mat_id // type_factor
    if (mat_type in [type_idg, type_SESAME]):
        return 0.
    elif (mat_id == id_Til_iron):
        return 7800.
    elif (mat_id == id_Til_granite):
        return 2680.
    elif (mat_id == id_Til_water):
        return 998.
    else:
        raise ValueError("Invalid material ID")

@jit(nopython=True)
def _C_V(mat_id):
    """ Returns specific heat capacity for a given material id (SI)

        Args:
            mat_id (int)
                Material id.

        Returns:
            C_V (double)
                Specific heat capacity (SI).

    """
    mat_type    = mat_id // type_factor
    if mat_id == id_idg_HHe:
        return 9093.98
    elif mat_id == id_idg_N2:
        return 742.36
    elif mat_id == id_idg_CO2:
        return 661.38
    elif (mat_id == id_Til_iron):
        return 449.
    elif (mat_id == id_Til_granite):
        return 790.
    elif (mat_id == id_Til_water):
        return 4186.
    elif (mat_type == type_SESAME):
        return 0.
    else:
        raise ValueError("Invalid material ID")

@jit(nopython=True)
def u_cold(rho, mat_id, N):
    """ Computes internal energy cold.

        Args:
            rho (float)
                Density (SI).

            mat_id (int)
                Material id.

            N (int)
                Number of subdivisions for the numerical integral.

        Returns:
            u_cold (float)
                Cold Specific internal energy (SI).
    """
    mat_type    = mat_id // type_factor
    if (mat_type in [type_idg, type_SESAME]):
        return 0.
    elif (mat_type == type_Til):
        rho0 = _rho_0_material(mat_id)
        drho = (rho - rho0)/N
        x = rho0
        u_cold = 1e-9

        for j in range(N):
            x += drho
            u_cold += P_EoS(u_cold, x, mat_id)*drho/x**2

    return u_cold

@jit(nopython=True)
def T_rho(rho, T_rho_type, T_rho_args, mat_id):
    """ Computes temperature given density (T = f(rho)).

        Args:
            rho (float)
                Density (SI).

            T_rho_type (int)
                Relation between T and rho to be used. See woma.Planet.

            T_rho_args (list)
                Extra arguments to determine the relation. See woma.Planet.

            mat_id (int)]
                The material ID.

        Returns:
            Temperature (SI)
    """
    mat_type    = mat_id // type_factor

    # T = K*rho**alpha, T_rho_args = [K, alpha]
    if (T_rho_type == type_rho_pow):
        K       = T_rho_args[0]
        alpha   = T_rho_args[1]
        return K * rho**alpha

    # Adiabatic, T_rho_args = [s_adb]
    elif T_rho_type == type_adb:
        s_adb   = T_rho_args[0]
        if (mat_type == type_SESAME):
            return T_rho_s_SESAME(rho, s_adb, mat_id)
        elif (mat_type == type_idg):
            raise ValueError("Entropy not implemented for this material type")
        elif (mat_type == type_Til):
            raise ValueError("Entropy not implemented for this material type")

    else:
        raise ValueError("T_rho_type not implemented")

@jit(nopython=True)
def P_rho(rho, mat_id, T_rho_type, T_rho_args):
    """ Computes pressure using Tillotson EoS, and
        internal energy = internal energy cold + C_V*Temperature
        (which depends on rho and the relation between temperature and density).

        Args:
            rho (float)
                Density (SI).

            mat_id ([float])
                Material id.

            T_rho_type (int)
                Relation between T and rho to be used.

            T_rho_args (list):
                Extra arguments to determine the relation

        Returns:
            P (float):
                Pressure (SI).
    """

    N = 10000
    C_V = _C_V(mat_id)
    u = u_cold(rho, mat_id, N) + C_V*T_rho(rho, T_rho_type, T_rho_args, mat_id)
    P = P_EoS(u, rho, mat_id)

    return P

@jit(nopython=True)
def _create_u_cold_array(mat_id):
    """ Computes values of the cold internal energy and stores it to save
        computation time in future calculations.
        It ranges from density = 100 kg/m^3 to 100000 kg/m^3

        Args:
            mat_id (int):
                Material id.

        Returns:
            u_cold_array ([float])
    """
    N_row = 10000
    u_cold_array = np.zeros((N_row,))
    rho_min = 100
    rho_max = 100000
    N_u_cold = 10000

    rho = rho_min
    drho = (rho_max - rho_min)/(N_row - 1)

    for i in range(N_row):
        u_cold_array[i] = u_cold(rho, mat_id, N_u_cold)
        rho = rho + drho

    return u_cold_array

@jit(nopython=True)
def _u_cold_tab(rho, mat_id, u_cold_array):
    """ Fast computation of cold internal energy using the table previously
        computed.

        Args:
            rho (float):
                Density (SI).

            mat_id (int):
                Material id.

            u_cold_array ([float])
                Precomputed values of cold internal energy for a particular material
                with function _create_u_cold_array() (SI).

        Returns:
            interpolation (float):
                cold Specific internal energy (SI).
    """
    mat_id = int(mat_id)    ###why?

    mat_type    = mat_id // type_factor
    if (mat_type in [type_idg, type_SESAME]):
        return 0.

    elif (mat_type == type_Til):
        N_row = u_cold_array.shape[0]
        rho_min = 100
        rho_max = 100000

        drho = (rho_max - rho_min)/(N_row - 1)

        a = int(((rho - rho_min)/drho))
        b = a + 1

        if a >= 0 and a < (N_row - 1):
            interpolation = u_cold_array[a]
            interpolation += ((u_cold_array[b] - u_cold_array[a])/drho)*(rho - rho_min - a*drho)

        elif rho < rho_min:
            interpolation = u_cold_array[0]
        else:
            interpolation = u_cold_array[int(N_row - 1)]
            interpolation += ((u_cold_array[int(N_row - 1)] - u_cold_array[int(N_row) - 2])/drho)*(rho - rho_max)

        return interpolation

    else:
        raise ValueError("Invalid material ID")

@jit(nopython=True)
def _find_rho(P_s, mat_id, T_rho_type, T_rho_args, rho0, rho1, u_cold_array):
    """ Root finder of the density for EoS using
        tabulated values of cold internal energy

        Args:
            P_s (float):
                Pressure (SI).

            mat_id (int):
                Material id.

            T_rho_type (int)
                Relation between T and rho to be used.

            T_rho_args (list):
                Extra arguments to determine the relation.

            rho0 (float):
                Lower bound for where to look the root (SI).

            rho1 (float):
                Upper bound for where to look the root (SI).

            u_cold_array ([float])
                Precomputed values of cold internal energy
                with function _create_u_cold_array() (SI).

        Returns:
            rho2 (float):
                Value of the density which satisfies P(u(rho), rho) = 0
                (SI).
    """
    #C_V       = _C_V(mat_id)
    tolerance = 1E-5

    T0 = T_rho(rho0, T_rho_type, T_rho_args, mat_id)
    u0 = _find_u(rho0, mat_id, T0, u_cold_array)
    P0 = P_EoS(u0, rho0, mat_id)
    T1 = T_rho(rho1, T_rho_type, T_rho_args, mat_id)
    u1 = _find_u(rho1, mat_id, T1, u_cold_array)
    P1 = P_EoS(u1, rho1, mat_id)
    rho2 = (rho0 + rho1)/2.
    T2   = T_rho(rho2, T_rho_type, T_rho_args, mat_id)
    u2   = _find_u(rho2, mat_id, T2, u_cold_array)
    P2   = P_EoS(u2, rho2, mat_id)

    rho_aux = rho0 + 1e-6
    T_aux = T_rho(rho_aux, T_rho_type, T_rho_args, mat_id)
    u_aux   = _find_u(rho_aux, mat_id, T_aux, u_cold_array)
    P_aux   = P_EoS(u_aux, rho_aux, mat_id)

    if ((P0 < P_s and P_s < P1) or (P0 > P_s and P_s > P1)):
        while np.abs(rho1 - rho0) > tolerance:
            T0 = T_rho(rho0, T_rho_type, T_rho_args, mat_id)
            u0 = _find_u(rho0, mat_id, T0, u_cold_array)
            P0 = P_EoS(u0, rho0, mat_id)
            T1 = T_rho(rho1, T_rho_type, T_rho_args, mat_id)
            u1 = _find_u(rho1, mat_id, T1, u_cold_array)
            P1 = P_EoS(u1, rho1, mat_id)
            T2 = T_rho(rho2, T_rho_type, T_rho_args, mat_id)
            u2 = _find_u(rho2, mat_id, T2, u_cold_array)
            P2 = P_EoS(u2, rho2, mat_id)

            f0 = P_s - P0
            f2 = P_s - P2

            if f0*f2 > 0:
                rho0 = rho2
            else:
                rho1 = rho2

            rho2 = (rho0 + rho1)/2.

        return rho2

    elif (P0 == P_s and P_aux == P_s and P1 != P_s):
        while np.abs(rho1 - rho0) > tolerance:
            rho2 = (rho0 + rho1)/2.
            T0 = T_rho(rho0, T_rho_type, T_rho_args, mat_id)
            u0 = _find_u(rho0, mat_id, T0, u_cold_array)
            P0 = P_EoS(u0, rho0, mat_id)
            T1 = T_rho(rho1, T_rho_type, T_rho_args, mat_id)
            u1 = _find_u(rho1, mat_id, T1, u_cold_array)
            P1 = P_EoS(u1, rho1, mat_id)
            rho2 = (rho0 + rho1)/2.
            T2 = T_rho(rho2, T_rho_type, T_rho_args, mat_id)
            u2 = _find_u(rho2, mat_id, T2, u_cold_array)
            P2 = P_EoS(u2, rho2, mat_id)

            if P2 == P_s:
                rho0 = rho2
            else:
                rho1 = rho2

            rho2 = rho2 = (rho0 + rho1)/2.

        return rho2

    elif P_s < P0 and P0 < P1:
        #print("Exception 1\n")
        #print("P0: %.2f P1 %.2f P_s %.2f" %(round(P0/1e9,2), round(P1/1e9,2), round(P_s/1e9,2)))
        return rho0
    elif P_s > P1 and P0 < P1:
        #print("Exception 2\n")
        #print("P0: %.2f P1 %.2f P_s %.2f" %(round(P0/1e9,2), round(P1/1e9,2), round(P_s/1e9,2)))
        return rho1
    else:
        #print("Exception 3\n")
        #print("P0: %.2f P1 %.2f P_s %.2f" %(round(P0/1e9,2), round(P1/1e9,2), round(P_s/1e9,2)))
        return rho2

def load_u_cold_array(mat_id):
    """ Load precomputed values of cold internal energy for a given material.

        Returns:
            u_cold_array ([float]):
                Precomputed values of cold internal energy
                with function _create_u_cold_array() (SI).
    """
    mat_type    = mat_id // type_factor
    if (mat_type in [type_idg, type_SESAME]):
        return np.array([0.])
    elif mat_id == id_Til_iron:
        u_cold_array = np.load(Fp_u_cold_Til_iron)
    elif mat_id == id_Til_granite:
        u_cold_array = np.load(Fp_u_cold_Til_granite)
    elif mat_id == id_Til_water:
        u_cold_array = np.load(Fp_u_cold_Til_water)
    else:
        raise ValueError("Invalid material ID")

    return u_cold_array

def find_rho_fixed_P_T(P, T, mat_id):
    """ Root finder of the density for EoS using
        tabulated values of cold internal energy

        Args:
            P (float):
                Pressure (SI).

            T (float):
                Temperature (SI).

            mat_id (int):
                Material id (SI).

        Returns:
            rho2 (float):
                Value of the density which satisfies P(u(rho), rho) = 0
                (SI).
    """
    P = float(P)
    T = float(T)

    rho_min     = 1e-3
    rho_max     = 1e5
    u_cold_array = load_u_cold_array(mat_id)

    return _find_rho(P, mat_id, 1, [T, 0.], rho_min, rho_max, u_cold_array)

@jit(nopython=True)
def _find_rho_fixed_P_T(P, T, mat_id, u_cold_array):
    """ Root finder of the density for EoS using
        tabulated values of cold internal energy

        Args:
            P (float):
                Pressure (SI).

            T (float):
                Temperature (SI).

            mat_id (int):
                Material id (SI).

            u_cold_array ([float]):
                Precomputed values of cold internal energy
                with function _create_u_cold_array() (SI).

        Returns:
            rho2 (float):
                Value of the density which satisfies P(u(rho), rho) = 0
                (SI).
    """
    P = float(P)
    T = float(T)

    rho_min     = 1e-9
    rho_max     = 1e15

    return _find_rho(P, mat_id, 1, [T, 0.], rho_min, rho_max, u_cold_array)

def find_P_fixed_T_rho(T, rho, mat_id):
    """ Finder of the pressure for EoS using
        tabulated values of cold internal energy

        Args:
            T (float):
                Temperature (SI).

            rho (float):
                Density (SI).

            mat_id (int):
                Material id (SI).

        Returns:
            P (float):
                Value of the pressure P(u(rho) + C_V*T, rho)
                (SI).
    """
    T = float(T)
    rho = float(rho)

    u = u_cold(rho, mat_id, 10000) + _C_V(mat_id)*T
    P = P_EoS(u, rho, mat_id)

    rho_test = rho + 1e-5
    u_test = u_cold(rho_test, mat_id, 10000) + _C_V(mat_id)*T
    P_test = P_EoS(u_test, rho_test, mat_id)

    if P != P_test:
        return P

    elif P == P_test and P == 0:
        print("This is a flat region of the EoS, where the pressure is 0")
        print("Please consider a higher rho value.")
        return 0

    return -1

def plot_eos_P_vs_rho_fixed_T(mat_id, T_array=np.linspace(0, 1000, 4), rho_min=1, rho_max=10000):

    rho_array = np.linspace(rho_min, rho_max, 100)

    fig, ax = plt.subplots(1,1, figsize=(12,12))
    #ax.set_xscale('log')
    #ax.set_yscale('log')

    for T in T_array:
        P_array = np.zeros(rho_array.shape)
        for i, rho in enumerate(rho_array):
            u = u_cold(rho, mat_id, 10000) + _C_V(mat_id)*T
            P_array[i] = P_EoS(u, rho, mat_id)
        ax.plot(rho_array, P_array, label=str(int(T)) + ' K')

    ax.legend()
    ax.set_xlabel(r"$\rho$ $[Kg/m^3]$")
    ax.set_ylabel(r"$P$ $[Pa]$")
    plt.show()

    return 0

def plot_eos_T_vs_rho_fixed_P(mat_id, P_array=np.logspace(6, 11, 4),
                              T_min=0, T_max=1000):

    T_array = np.linspace(T_min, T_max, 100)

    fig, ax = plt.subplots(1,1, figsize=(12,12))
    #ax.set_xscale('log')
    #ax.set_yscale('log')

    for P in P_array:
        rho_array = np.zeros(T_array.shape)
        for i, T in enumerate(T_array):
            rho_array[i] = find_rho_fixed_P_T(P, T, mat_id)
        ax.plot(T_array, rho_array, label="{:.2e}".format(P) + ' Pa')

    ax.legend()
    ax.set_xlabel(r"$T$ $[K]$")
    ax.set_ylabel(r"$\rho$ $[Kg/m^3]$")
    plt.show()

    return 0

@jit(nopython=True)
def _find_u(rho, mat_id, T, u_cold_array):
    mat_type    = mat_id // type_factor
    if (mat_type == type_SESAME):
        u   = u_rho_T_SESAME(rho, T, mat_id)

    elif (mat_type == type_idg):
        u = _C_V(mat_id)*T

    elif (mat_type == type_Til):
        C_V = _C_V(mat_id)

        u = _u_cold_tab(rho, mat_id, u_cold_array) + C_V*T

    return u

@jit(nopython=True)
def s_rho_T(rho, T, mat_id):
    """ Calculate the specific entropy.

        Args:
            rho (double)
                Density (SI).

            T (double)
                Temperature (SI).

            mat_id (int)
                Material id.

        returns:
            s (double)
                Specific internal energy (SI).
    """
    mat_type    = mat_id // type_factor
    if (mat_type == type_SESAME):
        return s_rho_T_SESAME(T, rho, mat_id)
    elif (mat_type == type_idg):
        raise ValueError("Entropy not implemented for this material")
    elif (mat_type == type_Til):
        raise ValueError("Entropy not implemented for this material")

@jit(nopython=True)
def set_T_rho_args(T, rho, T_rho_type, T_rho_args, mat_id):
    """ Set any parameters for the T-rho relation.

        Args:
            T (float)
                Temperature (K)

            rho (float)
                Density (kg m^-3)

            T_rho_type (int)
                T-rho relation ID. See woma.Planet.

            T_rho_args ([float])
                T-rho parameters (for a single layer). See woma.Planet.

            mat_id (int)
                Material ID

        Returns:
            T_rho_args ([float])
                T-rho parameters (for a single layer). See woma.Planet.
    """
    # T = K*rho**alpha, T_rho_args = [K, alpha]
    if T_rho_type == type_rho_pow:
        T_rho_args[0]   = T * rho**(-T_rho_args[1])

    # Adiabatic, T_rho_args = [s_adb]
    elif T_rho_type == type_adb:
        T_rho_args[0]   = s_rho_T(rho, T, mat_id)

    else:
        raise ValueError("T-rho relation not implemented")

    return T_rho_args

# Set up equation of state data
def set_up():
    """ Create tabulated values of cold internal energy if they don't exist,
        and save the results in the data/ folder.
    """
    # Make the directory if it doesn't already exist
    if not os.path.isdir("data"):
        os.mkdir("data")

    # Make the files if they don't already exist

    # Internal energy cold curves for Tillotson mateials
    if not os.path.isfile(Fp_u_cold_Til_iron):
        print('Creating u cold curve for material Til_iron... ', end='')
        sys.stdout.flush()
        u_cold_array = _create_u_cold_array(id_Til_iron)
        np.save(Fp_u_cold_Til_iron, u_cold_array)
        del u_cold_array
        print("Done")

    if not os.path.isfile(Fp_u_cold_Til_granite):
        print('Creating u cold curve for material Til_granite... ', end='')
        sys.stdout.flush()
        u_cold_array = _create_u_cold_array(id_Til_granite)
        np.save(Fp_u_cold_Til_granite, u_cold_array)
        del u_cold_array
        print("Done")

    if not os.path.isfile(Fp_u_cold_Til_water):
        print('Creating u cold curve for material Til_water... ', end='')
        sys.stdout.flush()
        u_cold_array = _create_u_cold_array(id_Til_water)
        np.save(Fp_u_cold_Til_water, u_cold_array)
        del u_cold_array
        print("Done")

    # SESAME tables
    ###TO DO
    if not os.path.isfile(Fp_SESAME_iron):
        print('Downloading SESAME iron table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SESAME_basalt):
        print('Downloading SESAME basalt table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SESAME_water):
        print('Downloading SESAME water table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SS08_water):
        print('Downloading SS08 water table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SESAME_H2):
        print('Downloading SESAME H2 table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SESAME_N2):
        print('Downloading SESAME N2 table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SESAME_steam):
        print('Downloading SESAME steam table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

    if not os.path.isfile(Fp_SESAME_CO2):
        print('Downloading SESAME CO2 table... ', end='')
        sys.stdout.flush()
        # Do stuff
        print("Done")

set_up()

# Load SESAME tables as global variables
(A2_u_SESAME_iron, A2_P_SESAME_iron, A2_s_SESAME_iron, A1_log_rho_SESAME_iron,
 A1_log_T_SESAME_iron, A2_log_u_SESAME_iron
 )  = load_table_SESAME(Fp_SESAME_iron)
(A2_u_SESAME_basalt, A2_P_SESAME_basalt, A2_s_SESAME_basalt,
 A1_log_rho_SESAME_basalt, A1_log_T_SESAME_basalt, A2_log_u_SESAME_basalt
 )  = load_table_SESAME(Fp_SESAME_basalt)
(A2_u_SESAME_water, A2_P_SESAME_water, A2_s_SESAME_water,
 A1_log_rho_SESAME_water, A1_log_T_SESAME_water, A2_log_u_SESAME_water
 )  = load_table_SESAME(Fp_SESAME_water)
(A2_u_SS08_water, A2_P_SS08_water, A2_s_SS08_water, A1_log_rho_SS08_water,
 A1_log_T_SS08_water, A2_log_u_SS08_water
 )  = load_table_SESAME(Fp_SS08_water)
(A2_u_SESAME_H2, A2_P_SESAME_H2, A2_s_SESAME_H2, A1_log_rho_SESAME_H2,
 A1_log_T_SESAME_H2, A2_log_u_SESAME_H2
 )  = load_table_SESAME(Fp_SESAME_H2)
(A2_u_SESAME_N2, A2_P_SESAME_N2, A2_s_SESAME_N2, A1_log_rho_SESAME_N2,
 A1_log_T_SESAME_N2, A2_log_u_SESAME_N2
 )  = load_table_SESAME(Fp_SESAME_N2)
(A2_u_SESAME_steam, A2_P_SESAME_steam, A2_s_SESAME_steam,
 A1_log_rho_SESAME_steam, A1_log_T_SESAME_steam, A2_log_u_SESAME_steam
 )  = load_table_SESAME(Fp_SESAME_steam)
(A2_u_SESAME_CO2, A2_P_SESAME_CO2, A2_s_SESAME_CO2, A1_log_rho_SESAME_CO2,
 A1_log_T_SESAME_CO2, A2_log_u_SESAME_CO2
 )  = load_table_SESAME(Fp_SESAME_CO2)
