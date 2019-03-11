#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 18 11:44:39 2018

@author: sergio
"""
import numpy as np
import matplotlib.pyplot as plt

R_earth = 6371000;

def plotrho(rho_grid, r_array, z_array, save_name = 0, levels = np.arange(1000, 15000, 1000)):
    fig_size = plt.rcParams["figure.figsize"]
 
    fig_size[0] = 10
    fig_size[1] = 5
    plt.rcParams["figure.figsize"] = fig_size
    
    # units
    if np.max(r_array > 10000): r_array = r_array/R_earth
    if np.max(z_array > 10000): z_array = z_array/R_earth
    
    x = r_array
    y = z_array
    X, Y = np.meshgrid(x, y)
    Z = rho_grid.T

    plt.figure()
    plt.axes().set_aspect('equal')
    CS = plt.contour(X, Y, Z, levels = levels)
    plt.clabel(CS, inline=1, fontsize=10)
    plt.xlabel('R (Earth radii)')
    plt.ylabel('z (Earth radii)')
    plt.title('Density (Kg/m^3)')
    
    if save_name != 0:
        plt.savefig(save_name, dpi = 700)
    else:
        plt.show()
    
    
def plotV(V_grid, Rs, save_name = 0):
    fig_size = plt.rcParams["figure.figsize"]
 
    fig_size[0] = 10
    fig_size[1] = 5
    plt.rcParams["figure.figsize"] = fig_size

    N = V_grid.shape[1]
    dr = Rs/(N - 1)

    x = np.arange(0, 2*Rs + 2*dr, dr)
    y = np.arange(0, Rs + dr, dr)
    X, Y = np.meshgrid(x, y)
    Z = V_grid.T

    plt.figure()
    CS = plt.contour(X, Y, Z)
    plt.clabel(CS, inline=1, fontsize=10)
    plt.xlabel('R (Earth radii)')
    plt.ylabel('z (Earth radii)')
    plt.title('Potential (J/Kg)')
    
    if save_name != 0:
        plt.savefig(save_name, dpi = 700)
    else:
        plt.show()
    
def plotdiff(rho_grid1, rho_grid0, rho_s, threshold = 2, save_name = 0):
    
    fig_size = plt.rcParams["figure.figsize"]
 
    fig_size[0] = 10
    fig_size[1] = 5
    plt.rcParams["figure.figsize"] = fig_size

    a = np.abs(rho_grid1 - rho_grid0)/rho_s
    a[a > threshold] = 0
    plt.figure()
    plt.imshow(a.T, cmap='gray', interpolation='nearest', origin='lower')
    plt.colorbar()
    plt.ylabel("z (planet radius)")
    plt.xlabel("R (planet radius)")
    plt.title("difference/rho_surface")
    
    if save_name != 0:
        plt.savefig(save_name, dpi = 700)
    else:
        plt.show()
    