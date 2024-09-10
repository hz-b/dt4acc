#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 14:50:13 2024

@author: Teresia Olsson, teresia.olsson@helmholtz-berlin.de
"""

import at

# Power supply name: names of connected magnets
quad_power_supplies = { \
    'Q1PDR': ['Q1M1D1R', 'Q1M2D1R', 'Q1M1D2R', 'Q1M2D2R', 'Q1M1D3R', 'Q1M2D3R', 'Q1M1D4R', 'Q1M2D4R', 'Q1M1D5R',
              'Q1M2D5R', 'Q1M1D6R', 'Q1M2D6R', 'Q1M1D7R', 'Q1M2D7R', 'Q1M1D8R', 'Q1M2D8R'], \
    'Q1PTR': ['Q1M1T1R', 'Q1M2T1R', 'Q1M1T2R', 'Q1M2T2R', 'Q1M1T3R', 'Q1M2T3R', 'Q1M1T4R', 'Q1M2T4R', 'Q1M1T5R',
              'Q1M2T5R', 'Q1M1T6R', 'Q1M2T6R', 'Q1M1T7R', 'Q1M2T7R', 'Q1M1T8R', 'Q1M2T8R'], \
    'Q2PDR': ['Q2M1D1R', 'Q2M2D1R', 'Q2M1D2R', 'Q2M2D2R', 'Q2M1D3R', 'Q2M2D3R', 'Q2M1D4R', 'Q2M2D4R', 'Q2M1D5R',
              'Q2M2D5R', 'Q2M1D6R', 'Q2M2D6R', 'Q2M1D7R', 'Q2M2D7R', 'Q2M1D8R', 'Q2M2D8R'], \
    'Q2PTR': ['Q2M1T1R', 'Q2M2T1R', 'Q2M1T2R', 'Q2M2T2R', 'Q2M1T3R', 'Q2M2T3R', 'Q2M1T4R', 'Q2M2T4R', 'Q2M1T5R',
              'Q2M2T5R', 'Q2M1T6R', 'Q2M2T6R', 'Q2M1T7R', 'Q2M2T7R', 'Q2M1T8R', 'Q2M2T8R'], \
    'Q3PD1R': ['Q3M1D1R', 'Q3M2D1R'], \
    'Q3PD2R': ['Q3M1D2R', 'Q3M2D2R'], \
    'Q3PD3R': ['Q3M1D3R', 'Q3M2D3R'], \
    'Q3PD4R': ['Q3M1D4R', 'Q3M2D4R'], \
    'Q3PD5R': ['Q3M1D5R', 'Q3M2D5R'], \
    'Q3PD6R': ['Q3M1D6R', 'Q3M2D6R'], \
    'Q3PD7R': ['Q3M1D7R', 'Q3M2D7R'], \
    'Q3PD8R': ['Q3M1D8R', 'Q3M2D8R'], \
    'Q3P1T1R': ['Q3M1T1R'], \
    'Q3P2T1R': ['Q3M2T1R'], \
    'Q3PT2R': ['Q3M1T2R', 'Q3M2T2R'], \
    'Q3PT3R': ['Q3M1T3R', 'Q3M2T3R'], \
    'Q3PT4R': ['Q3M1T4R', 'Q3M2T4R'], \
    'Q3PT5R': ['Q3M1T5R', 'Q3M2T5R'], \
    'Q3P1T6R': ['Q3M1T6R'], \
    'Q3P2T6R': ['Q3M2T6R'], \
    'Q3PT7R': ['Q3M1T7R', 'Q3M2T7R'], \
    'Q3P1T8R': ['Q3M1T8R'], \
    'Q3P2T8R': ['Q3M2T8R'], \
    'Q4PD1R': ['Q4M1D1R', 'Q4M2D1R'], \
    'Q4PD2R': ['Q4M1D2R', 'Q4M2D2R'], \
    'Q4PD3R': ['Q4M1D3R', 'Q4M2D3R'], \
    'Q4PD4R': ['Q4M1D4R', 'Q4M2D4R'], \
    'Q4PD5R': ['Q4M1D5R', 'Q4M2D5R'], \
    'Q4PD6R': ['Q4M1D6R', 'Q4M2D6R'], \
    'Q4PD7R': ['Q4M1D7R', 'Q4M2D7R'], \
    'Q4PD8R': ['Q4M1D8R', 'Q4M2D8R'], \
    'Q4P1T1R': ['Q4M1T1R'], \
    'Q4P2T1R': ['Q4M2T1R'], \
    'Q4PT2R': ['Q4M1T2R', 'Q4M2T2R'], \
    'Q4PT3R': ['Q4M1T3R', 'Q4M2T3R'], \
    'Q4PT4R': ['Q4M1T4R', 'Q4M2T4R'], \
    'Q4PT5R': ['Q4M1T5R', 'Q4M2T5R'], \
    'Q4P1T6R': ['Q4M1T6R'], \
    'Q4P2T6R': ['Q4M2T6R'], \
    'Q4PT7R': ['Q4M1T7R', 'Q4M2T7R'], \
    'Q4P1T8R': ['Q4M1T8R'], \
    'Q4P2T8R': ['Q4M2T8R'], \
    'Q5P1T1R': ['Q5M1T1R'], \
    'Q5P2T1R': ['Q5M2T1R'], \
    'Q5PT2R': ['Q5M1T2R', 'Q5M2T2R'], \
    'Q5PT3R': ['Q5M1T3R', 'Q5M2T3R'], \
    'Q5PT4R': ['Q5M1T4R', 'Q5M2T4R'], \
    'Q5PT5R': ['Q5M1T5R', 'Q5M2T5R'], \
    'Q5P1T6R': ['Q5M1T6R'], \
    'Q5P2T6R': ['Q5M2T6R'], \
    'Q5PT7R': ['Q5M1T7R', 'Q5M2T7R'], \
    'Q5P1T8R': ['Q5M1T8R'], \
    'Q5P2T8R': ['Q5M2T8R'], \
    'PQIPT6R': ['QIT6R'], \
    }

# Power supply name: names of connected magnets
sext_power_supplies = { \
    'S1PR': ['S1MD1R', 'S1MT1R', 'S1MD2R', 'S1MT2R', 'S1MD3R', 'S1MT3R', 'S1MD4R', 'S1MT4R', 'S1MD5R', 'S1MT5R',
             'S1MD6R', 'S1MT6R', 'S1MD7R', 'S1MT7R', 'S1MD8R', 'S1MT8R'], \
    'S2PDR': ['S2M1D1R', 'S2M2D1R', 'S2M1D2R', 'S2M2D2R', 'S2M1D3R', 'S2M2D3R', 'S2M1D4R', 'S2M2D4R', 'S2M1D5R',
              'S2M2D5R', 'S2M1D6R', 'S2M2D6R', 'S2M1D7R', 'S2M2D7R', 'S2M1D8R', 'S2M2D8R'], \
    'S2PTR': ['S2M1T1R', 'S2M2T1R', 'S2M1T2R', 'S2M2T2R', 'S2M1T3R', 'S2M2T3R', 'S2M1T4R', 'S2M2T4R', 'S2M1T5R',
              'S2M2T5R', 'S2M1T6R', 'S2M2T6R', 'S2M1T7R', 'S2M2T7R', 'S2M1T8R', 'S2M2T8R'], \
    'S3PDR': ['S3M1D2R', 'S3M2D2R', 'S3M1D3R', 'S3M2D3R', 'S3M1D4R', 'S3M2D4R', 'S3M1D5R', 'S3M2D5R', 'S3M1D6R',
              'S3M2D6R', 'S3M1D7R', 'S3M2D7R', 'S3M1D8R', 'S3M2D8R'], \
    'S3PTR': ['S3M1T1R', 'S3M2T1R', 'S3M1T2R', 'S3M2T2R', 'S3M1T3R', 'S3M2T3R', 'S3M1T4R', 'S3M2T4R', 'S3M1T5R',
              'S3M2T5R', 'S3M1T7R', 'S3M2T7R', 'S3M1T8R', 'S3M2T8R'], \
    'S4PDR': ['S4M1D2R', 'S4M2D2R', 'S4M1D3R', 'S4M2D3R', 'S4M1D4R', 'S4M2D4R', 'S4M1D5R', 'S4M2D5R', 'S4M1D6R',
              'S4M2D6R', 'S4M1D7R', 'S4M2D7R', 'S4M1D8R', 'S4M2D8R'], \
    'S4PTR': ['S4M1T1R', 'S4M2T1R', 'S4M1T2R', 'S4M2T2R', 'S4M1T3R', 'S4M2T3R', 'S4M1T4R', 'S4M2T4R', 'S4M1T5R',
              'S4M2T5R', 'S4M1T7R', 'S4M2T7R', 'S4M1T8R', 'S4M2T8R'], \
    'S3PD1R': ['S3M1D1R', 'S3M2D1R'], \
    'S4PD1R': ['S4M1D1R', 'S4M2D1R'], \
    'S3P1T6R': ['S3M1T6R'], \
    'S3P2T6R': ['S3M2T6R'], \
    'S4P1T6R': ['S4M1T6R'], \
    'S4P2T6R': ['S4M2T6R'], \
    }


def set_values(ring: at.Lattice, ps_map: dict, field: str, new_values: dict):
    for ps, magnets in ps_map.items():
        for element in magnets:

            # Add check so element exists in ring otherwise it will not be set.
            if len(ring[element]) == 0:
                raise Exception('Element {} does not exist in ring.'.format(element))

            ring.set_value_refpts(element, field, new_values[ps])


def get_power_supply_config() -> list:
    return [quad_power_supplies, sext_power_supplies]


def steerer_power_supplies():
    return {
        'HS1PD1R': ['HS1MD1R'],
        'HS1PD2R': ['HS1MD2R'],
        'HS1PD3R': ['HS1MD3R'],
        'HS1PD4R': ['HS1MD4R'],
        'HS1PD5R': ['HS1MD5R'],
        'HS1PD6R': ['HS1MD6R'],
        'HS1PD7R': ['HS1MD7R'],
        'HS1PD8R': ['HS1MD8R'],
        'HS1PT1R': ['HS1MT1R'],
        'HS1PT2R': ['HS1MT2R'],
        'HS1PT3R': ['HS1MT3R'],
        'HS1PT4R': ['HS1MT4R'],
        'HS1PT5R': ['HS1MT5R'],
        'HS1PT6R': ['HS1MT6R'],
        'HS1PT7R': ['HS1MT7R'],
        'HS1PT8R': ['HS1MT8R'],
        'HS4P1D1R': ['HS4M1D1R'],
        'HS4P1D2R': ['HS4M1D2R'],
        'HS4P1D3R': ['HS4M1D3R'],
        'HS4P1D4R': ['HS4M1D4R'],
        'HS4P1D5R': ['HS4M1D5R'],
        'HS4P1D6R': ['HS4M1D6R'],
        'HS4P1D7R': ['HS4M1D7R'],
        'HS4P1D8R': ['HS4M1D8R'],
        'HS4P1T1R': ['HS4M1T1R'],
        'HS4P1T2R': ['HS4M1T2R'],
        'HS4P1T3R': ['HS4M1T3R'],
        'HS4P1T4R': ['HS4M1T4R'],
        'HS4P1T5R': ['HS4M1T5R'],
        'HS4P1T6R': ['HS4M1T6R'],
        'HS4P1T7R': ['HS4M1T7R'],
        'HS4P1T8R': ['HS4M1T8R'],
        'HS4P2D1R': ['HS4M2D1R'],
        'HS4P2D2R': ['HS4M2D2R'],
        'HS4P2D3R': ['HS4M2D3R'],
        'HS4P2D4R': ['HS4M2D4R'],
        'HS4P2D5R': ['HS4M2D5R'],
        'HS4P2D6R': ['HS4M2D6R'],
        'HS4P2D7R': ['HS4M2D7R'],
        'HS4P2D8R': ['HS4M2D8R'],
        'HS4P2T1R': ['HS4M2T1R'],
        'HS4P2T2R': ['HS4M2T2R'],
        'HS4P2T3R': ['HS4M2T3R'],
        'HS4P2T4R': ['HS4M2T4R'],
        'HS4P2T5R': ['HS4M2T5R'],
        'HS4P2T6R': ['HS4M2T6R'],
        'HS4P2T7R': ['HS4M2T7R'],
        'HS4P2T8R': ['HS4M2T8R'],
        'VS2P1D1R': ['VS2M1D1R'],
        'VS2P1D2R': ['VS2M1D2R'],
        'VS2P1D3R': ['VS2M1D3R'],
        'VS2P1D4R': ['VS2M1D4R'],
        'VS2P1D5R': ['VS2M1D5R'],
        'VS2P1D6R': ['VS2M1D6R'],
        'VS2P1D7R': ['VS2M1D7R'],
        'VS2P1D8R': ['VS2M1D8R'],
        'VS2P1T1R': ['VS2M1T1R'],
        'VS2P1T2R': ['VS2M1T2R'],
        'VS2P1T3R': ['VS2M1T3R'],
        'VS2P1T4R': ['VS2M1T4R'],
        'VS2P1T5R': ['VS2M1T5R'],
        'VS2P1T6R': ['VS2M1T6R'],
        'VS2P1T7R': ['VS2M1T7R'],
        'VS2P1T8R': ['VS2M1T8R'],
        'VS2P2D1R': ['VS2M2D1R'],
        'VS2P2D2R': ['VS2M2D2R'],
        'VS2P2D3R': ['VS2M2D3R'],
        'VS2P2D4R': ['VS2M2D4R'],
        'VS2P2D5R': ['VS2M2D5R'],
        'VS2P2D6R': ['VS2M2D6R'],
        'VS2P2D7R': ['VS2M2D7R'],
        'VS2P2D8R': ['VS2M2D8R'],
        'VS2P2T1R': ['VS2M2T1R'],
        'VS2P2T2R': ['VS2M2T2R'],
        'VS2P2T3R': ['VS2M2T3R'],
        'VS2P2T4R': ['VS2M2T4R'],
        'VS2P2T5R': ['VS2M2T5R'],
        'VS2P2T6R': ['VS2M2T6R'],
        'VS2P2T7R': ['VS2M2T7R'],
        'VS2P2T8R': ['VS2M2T8R'],
        'VS3P1D1R': ['VS3M1D1R'],
        'VS3P1D2R': ['VS3M1D2R'],
        'VS3P1D3R': ['VS3M1D3R'],
        'VS3P1D4R': ['VS3M1D4R'],
        'VS3P1D5R': ['VS3M1D5R'],
        'VS3P1D6R': ['VS3M1D6R'],
        'VS3P1D7R': ['VS3M1D7R'],
        'VS3P1D8R': ['VS3M1D8R'],
        'VS3P1T1R': ['VS3M1T1R'],
        'VS3P1T2R': ['VS3M1T2R'],
        'VS3P1T3R': ['VS3M1T3R'],
        'VS3P1T4R': ['VS3M1T4R'],
        'VS3P1T5R': ['VS3M1T5R'],
        'VS3P1T6R': ['VS3M1T6R'],
        'VS3P1T7R': ['VS3M1T7R'],
        'VS3P1T8R': ['VS3M1T8R'],
        'VS3P2D1R': ['VS3M2D1R'],
        'VS3P2D2R': ['VS3M2D2R'],
        'VS3P2D3R': ['VS3M2D3R'],
        'VS3P2D4R': ['VS3M2D4R'],
        'VS3P2D5R': ['VS3M2D5R'],
        'VS3P2D6R': ['VS3M2D6R'],
        'VS3P2D7R': ['VS3M2D7R'],
        'VS3P2D8R': ['VS3M2D8R'],
        'VS3P2T1R': ['VS3M2T1R'],
        'VS3P2T2R': ['VS3M2T2R'],
        'VS3P2T3R': ['VS3M2T3R'],
        'VS3P2T4R': ['VS3M2T4R'],
        'VS3P2T5R': ['VS3M2T5R'],
        'VS3P2T6R': ['VS3M2T6R'],
        'VS3P2T7R': ['VS3M2T7R'],
        'VS3P2T8R': ['VS3M2T8R']
    }


def sext_power_supplies():
    return {
        'S1PR': ['S1MD1R', 'S1MT1R', 'S1MD2R', 'S1MT2R', 'S1MD3R', 'S1MT3R', 'S1MD4R', 'S1MT4R', 'S1MD5R', 'S1MT5R',
                 'S1MD6R', 'S1MT6R', 'S1MD7R', 'S1MT7R', 'S1MD8R', 'S1MT8R'],
        'S2PDR': ['S2M1D1R', 'S2M2D1R', 'S2M1D2R', 'S2M2D2R', 'S2M1D3R', 'S2M2D3R', 'S2M1D4R', 'S2M2D4R', 'S2M1D5R',
                  'S2M2D5R', 'S2M1D6R', 'S2M2D6R', 'S2M1D7R', 'S2M2D7R', 'S2M1D8R', 'S2M2D8R'],
        'S2PTR': ['S2M1T1R', 'S2M2T1R', 'S2M1T2R', 'S2M2T2R', 'S2M1T3R', 'S2M2T3R', 'S2M1T4R', 'S2M2T4R', 'S2M1T5R',
                  'S2M2T5R', 'S2M1T6R', 'S2M2T6R', 'S2M1T7R', 'S2M2T7R', 'S2M1T8R', 'S2M2T8R'],
        'S3PDR': ['S3M1D2R', 'S3M2D2R', 'S3M1D3R', 'S3M2D3R', 'S3M1D4R', 'S3M2D4R', 'S3M1D5R', 'S3M2D5R', 'S3M1D6R',
                  'S3M2D6R', 'S3M1D7R', 'S3M2D7R', 'S3M1D8R', 'S3M2D8R'],
        'S3PTR': ['S3M1T1R', 'S3M2T1R', 'S3M1T2R', 'S3M2T2R', 'S3M1T3R', 'S3M2T3R', 'S3M1T4R', 'S3M2T4R', 'S3M1T5R',
                  'S3M2T5R', 'S3M1T7R', 'S3M2T7R', 'S3M1T8R', 'S3M2T8R'],
        'S4PDR': ['S4M1D2R', 'S4M2D2R', 'S4M1D3R', 'S4M2D3R', 'S4M1D4R', 'S4M2D4R', 'S4M1D5R', 'S4M2D5R', 'S4M1D6R',
                  'S4M2D6R', 'S4M1D7R', 'S4M2D7R', 'S4M1D8R', 'S4M2D8R'],
        'S4PTR': ['S4M1T1R', 'S4M2T1R', 'S4M1T2R', 'S4M2T2R', 'S4M1T3R', 'S4M2T3R', 'S4M1T4R', 'S4M2T4R', 'S4M1T5R',
                  'S4M2T5R', 'S4M1T7R', 'S4M2T7R', 'S4M1T8R', 'S4M2T8R'],
        'S3PD1R': ['S3M1D1R', 'S3M2D1R'],
        'S4PD1R': ['S4M1D1R', 'S4M2D1R'],
        'S3P1T6R': ['S3M1T6R'],
        'S3P2T6R': ['S3M2T6R'],
        'S4P1T6R': ['S4M1T6R'],
        'S4P2T6R': ['S4M2T6R']
    }


def quad_power_supplies():
    return {
        'Q1PDR': ['Q1M1D1R', 'Q1M2D1R', 'Q1M1D2R', 'Q1M2D2R', 'Q1M1D3R', 'Q1M2D3R', 'Q1M1D4R', 'Q1M2D4R', 'Q1M1D5R',
                  'Q1M2D5R', 'Q1M1D6R', 'Q1M2D6R', 'Q1M1D7R', 'Q1M2D7R', 'Q1M1D8R', 'Q1M2D8R'],
        'Q1PTR': ['Q1M1T1R', 'Q1M2T1R', 'Q1M1T2R', 'Q1M2T2R', 'Q1M1T3R', 'Q1M2T3R', 'Q1M1T4R', 'Q1M2T4R', 'Q1M1T5R',
                  'Q1M2T5R', 'Q1M1T6R', 'Q1M2T6R', 'Q1M1T7R', 'Q1M2T7R', 'Q1M1T8R', 'Q1M2T8R'],
        'Q2PDR': ['Q2M1D1R', 'Q2M2D1R', 'Q2M1D2R', 'Q2M2D2R', 'Q2M1D3R', 'Q2M2D3R', 'Q2M1D4R', 'Q2M2D4R', 'Q2M1D5R',
                  'Q2M2D5R', 'Q2M1D6R', 'Q2M2D6R', 'Q2M1D7R', 'Q2M2D7R', 'Q2M1D8R', 'Q2M2D8R'],
        'Q2PTR': ['Q2M1T1R', 'Q2M2T1R', 'Q2M1T2R', 'Q2M2T2R', 'Q2M1T3R', 'Q2M2T3R', 'Q2M1T4R', 'Q2M2T4R', 'Q2M1T5R',
                  'Q2M2T5R', 'Q2M1T6R', 'Q2M2T6R', 'Q2M1T7R', 'Q2M2T7R', 'Q2M1T8R', 'Q2M2T8R'],
        'Q3PD1R': ['Q3M1D1R', 'Q3M2D1R'],
        'Q3PD2R': ['Q3M1D2R', 'Q3M2D2R'],
        'Q3PD3R': ['Q3M1D3R', 'Q3M2D3R'],
        'Q3PD4R': ['Q3M1D4R', 'Q3M2D4R'],
        'Q3PD5R': ['Q3M1D5R', 'Q3M2D5R'],
        'Q3PD6R': ['Q3M1D6R', 'Q3M2D6R'],
        'Q3PD7R': ['Q3M1D7R', 'Q3M2D7R'],
        'Q3PD8R': ['Q3M1D8R', 'Q3M2D8R'],
        'Q3P1T1R': ['Q3M1T1R'],
        'Q3P2T1R': ['Q3M2T1R'],
        'Q3PT2R': ['Q3M1T2R', 'Q3M2T2R'],
        'Q3PT3R': ['Q3M1T3R', 'Q3M2T3R'],
        'Q3PT4R': ['Q3M1T4R', 'Q3M2T4R'],
        'Q3PT5R': ['Q3M1T5R', 'Q3M2T5R'],
        'Q3P1T6R': ['Q3M1T6R'],
        'Q3P2T6R': ['Q3M2T6R'],
        'Q3PT7R': ['Q3M1T7R', 'Q3M2T7R'],
        'Q3P1T8R': ['Q3M1T8R'],
        'Q3P2T8R': ['Q3M2T8R'],
        'Q4PD1R': ['Q4M1D1R', 'Q4M2D1R'],
        'Q4PD2R': ['Q4M1D2R', 'Q4M2D2R'],
        'Q4PD3R': ['Q4M1D3R', 'Q4M2D3R'],
        'Q4PD4R': ['Q4M1D4R', 'Q4M2D4R'],
        'Q4PD5R': ['Q4M1D5R', 'Q4M2D5R'],
        'Q4PD6R': ['Q4M1D6R', 'Q4M2D6R'],
        'Q4PD7R': ['Q4M1D7R', 'Q4M2D7R'],
        'Q4PD8R': ['Q4M1D8R', 'Q4M2D8R'],
        'Q4P1T1R': ['Q4M1T1R'],
        'Q4P2T1R': ['Q4M2T1R'],
        'Q4PT2R': ['Q4M1T2R', 'Q4M2T2R'],
        'Q4PT3R': ['Q4M1T3R', 'Q4M2T3R'],
        'Q4PT4R': ['Q4M1T4R', 'Q4M2T4R'],
        'Q4PT5R': ['Q4M1T5R', 'Q4M2T5R'],
        'Q4P1T6R': ['Q4M1T6R'],
        'Q4P2T6R': ['Q4M2T6R'],
        'Q4PT7R': ['Q4M1T7R', 'Q4M2T7R'],
        'Q4P1T8R': ['Q4M1T8R'],
        'Q4P2T8R': ['Q4M2T8R'],
        'Q5P1T1R': ['Q5M1T1R'],
        'Q5P2T1R': ['Q5M2T1R'],
        'Q5PT2R': ['Q5M1T2R', 'Q5M2T2R'],
        'Q5PT3R': ['Q5M1T3R', 'Q5M2T3R'],
        'Q5PT4R': ['Q5M1T4R', 'Q5M2T4R'],
        'Q5PT5R': ['Q5M1T5R', 'Q5M2T5R'],
        'Q5P1T6R': ['Q5M1T6R'],
        'Q5P2T6R': ['Q5M2T6R'],
        'Q5PT7R': ['Q5M1T7R', 'Q5M2T7R'],
        'Q5P1T8R': ['Q5M1T8R'],
        'Q5P2T8R': ['Q5M2T8R'],
        'PQIPT6R': ['QIT6R']
    }


# ----------------------------------------------------------------------------
# Standard user settings from old MADX reference file    
# ---------------------------------------------------------------------------- 

def set_standard_user_madx(ring):
    # ---- Quadrupole setting per power supply ----
    quad_values = { \
        'Q1PDR': 2.44045585, \
        'Q1PDR': 2.44045585, \
        'Q1PTR': 2.44045585, \
        'Q2PDR': -1.8536747, \
        'Q2PTR': -1.8536747, \
        'Q3PD1R': -2.02322285, \
        'Q3PD2R': -2.12441276, \
        'Q3PD3R': -2.12608143, \
        'Q3PD4R': -2.1282793, \
        'Q3PD5R': -2.1211438, \
        'Q3PD6R': -2.11223413, \
        'Q3PD7R': -2.11883984, \
        'Q3PD8R': -2.13404738, \
        'Q3P1T1R': -2.50764398, \
        'Q3P2T1R': -2.46682595, \
        'Q3PT2R': -2.45526041, \
        'Q3PT3R': -2.43119165, \
        'Q3PT4R': -2.44037407, \
        'Q3PT5R': -2.44818682, \
        'Q3P1T6R': -2.69386876, \
        'Q3P2T6R': -2.32789462, \
        'Q3PT7R': -2.43591598, \
        'Q3P1T8R': -2.47132446, \
        'Q3P2T8R': -2.51228342, \
        'Q4PD1R': 1.40046286, \
        'Q4PD2R': 1.4802205, \
        'Q4PD3R': 1.48692991, \
        'Q4PD4R': 1.4883633, \
        'Q4PD5R': 1.48010676, \
        'Q4PD6R': 1.48545637, \
        'Q4PD7R': 1.47643621, \
        'Q4PD8R': 1.49055699, \
        'Q4P1T1R': 2.63205252, \
        'Q4P2T1R': 2.56505973, \
        'Q4PT2R': 2.57722952, \
        'Q4PT3R': 2.57917393, \
        'Q4PT4R': 2.58038995, \
        'Q4PT5R': 2.57768425, \
        'Q4P1T6R': 2.25837798, \
        'Q4P2T6R': 2.55873747, \
        'Q4PT7R': 2.58020271, \
        'Q4P1T8R': 2.56384946, \
        'Q4P2T8R': 2.64079373, \
        'Q5P1T1R': -2.52154146, \
        'Q5P2T1R': -2.51058167, \
        'Q5PT2R': -2.5831049, \
        'Q5PT3R': -2.62044465, \
        'Q5PT4R': -2.59546801, \
        'Q5PT5R': -2.58439541, \
        'Q5P1T6R': -1.09078314, \
        'Q5P2T6R': -2.42521942, \
        'Q5PT7R': -2.60426005, \
        'Q5P1T8R': -2.50807154, \
        'Q5P2T8R': -2.50807154, \
        'PQIPT6R': -1.08082489, \
        }

    # ---- Sextupole setting per power supply ----
    sext_values = { \
        'S1PR': 53.71159807 / 2, \
        'S2PDR': -44.968873 / 2, \
        'S2PTR': -44.968873 / 2, \
        'S3PDR': -47.03 / 2, \
        'S3PTR': -52.2 / 2, \
        'S4PDR': 42.31 / 2, \
        'S4PTR': 64.87 / 2, \
        'S3PD1R': -29.55 / 2, \
        'S4PD1R': 28.02 / 2, \
        'S3P1T6R': -52.2 / 2, \
        'S3P2T6R': -52.2 / 2, \
        'S4P1T6R': 64.87 / 2, \
        'S4P2T6R': 64.87 / 2, \
        }

    # ---- Set quad values ----
    set_values(ring, quad_power_supplies, 'K', quad_values)

    # ---- Set sext values ----
    set_values(ring, sext_power_supplies, 'H', sext_values)


# ----------------------------------------------------------------------------
# Standard user settings extracted from machine and converted with MML  
# ----------------------------------------------------------------------------     

def set_standard_user_nominal(ring):
    """
    Nominal settings from the machine for standard user mode.
    
    """

    # ---- Quadrupole setting per power supply ----
    quad_values = { \
        'Q1PDR': 2.440181534345, \
        'Q1PTR': 2.440181534345, \
        'Q2PDR': -1.855681344824, \
        'Q2PTR': -1.855681344824, \
        'Q3PD1R': -2.007857286189, \
        'Q3PD2R': -2.122170742556, \
        'Q3PD3R': -2.121819614416, \
        'Q3PD4R': -2.122392154569, \
        'Q3PD5R': -2.120515898876, \
        'Q3PD6R': -2.120926138670, \
        'Q3PD7R': -2.118377664044, \
        'Q3PD8R': -2.120057264258, \
        'Q3P1T1R': -2.531967021976, \
        'Q3P2T1R': -2.439162936288, \
        'Q3PT2R': -2.435266007021, \
        'Q3PT3R': -2.436471036971, \
        'Q3PT4R': -2.436534284400, \
        'Q3PT5R': -2.433986633603, \
        'Q3P1T6R': -2.683891647707, \
        'Q3P2T6R': -2.294749084585, \
        'Q3PT7R': -2.436547735132, \
        'Q3P1T8R': -2.437025974458, \
        'Q3P2T8R': -2.536093281066, \
        'Q4PD1R': 1.400723860813, \
        'Q4PD2R': 1.482596970405, \
        'Q4PD3R': 1.483513045668, \
        'Q4PD4R': 1.485985486838, \
        'Q4PD5R': 1.484018985756, \
        'Q4PD6R': 1.486561641525, \
        'Q4PD7R': 1.485480950637, \
        'Q4PD8R': 1.485378333105, \
        'Q4P1T1R': 2.612056221575, \
        'Q4P2T1R': 2.579778157204, \
        'Q4PT2R': 2.577652441388, \
        'Q4PT3R': 2.578370780600, \
        'Q4PT4R': 2.578347065060, \
        'Q4PT5R': 2.577862711505, \
        'Q4P1T6R': 2.226293166958, \
        'Q4P2T6R': 2.561542193564, \
        'Q4PT7R': 2.580066918445, \
        'Q4P1T8R': 2.579996828406, \
        'Q4P2T8R': 2.625312416875, \
        'Q5P1T1R': -2.413008936012, \
        'Q5P2T1R': -2.600804177955, \
        'Q5PT2R': -2.600804177955, \
        'Q5PT3R': -2.600804177955, \
        'Q5PT4R': -2.600804177955, \
        'Q5PT5R': -2.600804177955, \
        'Q5P1T6R': -1.025563067010, \
        'Q5P2T6R': -2.487373110285, \
        'Q5PT7R': -2.600804177955, \
        'Q5P1T8R': -2.600804177955, \
        'Q5P2T8R': -2.423061236067, \
        'PQIPT6R': -1.648783404317, \
        }

    # ---- Sextupole setting per power supply ----
    sext_values = { \
        'S1PR': 27.545736528836, \
        'S2PDR': -23.488373938219, \
        'S2PTR': -23.488373938219, \
        'S3PDR': -24.622641767174, \
        'S3PTR': -27.187145930591, \
        'S4PDR': 22.304759941500, \
        'S4PTR': 33.715314509799, \
        'S3PD1R': -22.182560150607, \
        'S4PD1R': 17.586982181658, \
        'S3P1T6R': -21.231341142551, \
        'S3P2T6R': -20.955609439401, \
        'S4P1T6R': 17.614531662263, \
        'S4P2T6R': 21.742937520605, \
        }

    # ---- Set quad values ----
    set_values(ring, quad_power_supplies, 'K', quad_values)

    # ---- Set sext values ----
    set_values(ring, sext_power_supplies, 'H', sext_values)


# ----------------------------------------------------------------------------
# Standard user settings extracted from LOCO 
# ----------------------------------------------------------------------------     

def set_standard_user_loco(ring):
    """
    Settings fitted with LOCO for standard user mode.
    
    """

    # ---- Quadrupole setting per power supply ----
    quad_values = { \
        'Q1PDR': 2.436378510478, \
        'Q1PTR': 2.442744469284, \
        'Q2PDR': -1.857400277420, \
        'Q2PTR': -1.846186515892, \
        'Q3PD1R': -2.025921017529, \
        'Q3PD2R': -2.137015029574, \
        'Q3PD3R': -2.132523238456, \
        'Q3PD4R': -2.141070794445, \
        'Q3PD5R': -2.130174588469, \
        'Q3PD6R': -2.115907383144, \
        'Q3PD7R': -2.121082385515, \
        'Q3PD8R': -2.144266518879, \
        'Q3P1T1R': -2.533255113747, \
        'Q3P2T1R': -2.483636760205, \
        'Q3PT2R': -2.475849818289, \
        'Q3PT3R': -2.453370746751, \
        'Q3PT4R': -2.460216516724, \
        'Q3PT5R': -2.473072169965, \
        'Q3P1T6R': -2.699684425862, \
        'Q3P2T6R': -2.371055789598, \
        'Q3PT7R': -2.452848377941, \
        'Q3P1T8R': -2.492168566436, \
        'Q3P2T8R': -2.537970509381, \
        'Q4PD1R': 1.401817365853, \
        'Q4PD2R': 1.477391095048, \
        'Q4PD3R': 1.484526951605, \
        'Q4PD4R': 1.493104680279, \
        'Q4PD5R': 1.479428032029, \
        'Q4PD6R': 1.482565198291, \
        'Q4PD7R': 1.474765465160, \
        'Q4PD8R': 1.492925021277, \
        'Q4P1T1R': 2.636552949711, \
        'Q4P2T1R': 2.567696910782, \
        'Q4PT2R': 2.581388047846, \
        'Q4PT3R': 2.579115169770, \
        'Q4PT4R': 2.581538714161, \
        'Q4PT5R': 2.579130257516, \
        'Q4P1T6R': 2.263202996600, \
        'Q4P2T6R': 2.565678466554, \
        'Q4PT7R': 2.583850522152, \
        'Q4P1T8R': 2.565406220726, \
        'Q4P2T8R': 2.642899567170, \
        'Q5P1T1R': -2.501994096088, \
        'Q5P2T1R': -2.511531191164, \
        'Q5PT2R': -2.577447573373, \
        'Q5PT3R': -2.613318049382, \
        'Q5PT4R': -2.589995337836, \
        'Q5PT5R': -2.576267191023, \
        'Q5P1T6R': -1.071032161447, \
        'Q5P2T6R': -2.439246229761, \
        'Q5PT7R': -2.595152788921, \
        'Q5P1T8R': -2.498907430301, \
        'Q5P2T8R': -2.489743155393, \
        'PQIPT6R': -1.085662132916, \
        }

    # ---- Set quad values ----
    set_values(ring, quad_power_supplies, 'K', quad_values)


def set_low_alpha(ring):
    # TODO
    pass
