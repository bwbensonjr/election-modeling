"""Fitting and scoring for the Massachusetts legislative margin model.

This package reads the committed race-grain training table and writes
scorecards. It never touches the network or the fetch cache: collection lives
in `maprecinct`, modelling lives here (design.md, D1).
"""
