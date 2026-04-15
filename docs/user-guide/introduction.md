# Introduction

**Pointy** is a desktop application for georectifying imagery using Ground Control Points (GCPs). It supports manual and automatic GCP placement, sensor model fitting, and orthorectification.

## What is Georectification?

Georectification is the process of assigning geographic coordinates to pixels in an image. This is done by identifying known locations (Ground Control Points) in the image and using them to fit a mathematical model that maps image pixels to geographic coordinates.

## Key Concepts

- **Ground Control Point (GCP)**: A point with known image coordinates and geographic coordinates (latitude, longitude).
- **Sensor Model**: A mathematical model that maps image pixels to geographic coordinates. Pointy supports Affine, TPS (Thin-Plate Spline), and RPC (Rational Polynomial Coefficient) models.
- **Orthorectification**: Warping an image to a geographic projection using the fitted sensor model.
- **Auto GCP Picker**: An automatic pipeline that uses feature matching (AKAZE, ORB) to find GCPs without manual input.
