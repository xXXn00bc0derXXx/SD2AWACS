// RadarConversion.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <cmath>
#include <sstream>
#include <iomanip>
#include <cstdlib>
#include <ctime>

// WGS84 constants
const double a = 6378137.0;              // Semi-major axis
const double e2 = 6.69437999014e-3;      // First eccentricity squared
const double pi = 3.141592653589793;

// Convert degrees to radians
double deg2rad(double deg) {
    return deg * pi / 180.0;
}

// Convert radar geodetic coordinates to ECEF
void geodeticToECEF(double lat, double lon, double alt,
    double& x, double& y, double& z) {
    lat = deg2rad(lat);
    lon = deg2rad(lon);
    double N = a / sqrt(1 - e2 * sin(lat) * sin(lat));
    x = (N + alt) * cos(lat) * cos(lon);
    y = (N + alt) * cos(lat) * sin(lon);
    z = ((1 - e2) * N + alt) * sin(lat);
}

// Convert radar polar to ENU
void radarToENU(double range, double azimuth, double elevation,
    double& xEast, double& yNorth, double& zUp) {
    azimuth = deg2rad(azimuth);
    elevation = deg2rad(elevation);
    xEast = range * cos(elevation) * sin(azimuth);
    yNorth = range * cos(elevation) * cos(azimuth);
    zUp = range * sin(elevation);
}

// Convert ENU to ECEF offset
void enuToECEFOffset(double xEast, double yNorth, double zUp,
    double lat0, double lon0,
    double& dx, double& dy, double& dz) {
    lat0 = deg2rad(lat0);
    lon0 = deg2rad(lon0);

    double sinLat = sin(lat0), cosLat = cos(lat0);
    double sinLon = sin(lon0), cosLon = cos(lon0);

    dx = -sinLon * xEast - sinLat * cosLon * yNorth + cosLat * cosLon * zUp;
    dy = cosLon * xEast - sinLat * sinLon * yNorth + cosLat * sinLon * zUp;
    dz = cosLat * yNorth + sinLat * zUp;
}

// Convert ECEF to Geodetic
void ecefToGeodetic(double x, double y, double z,
    double& lat, double& lon, double& alt) {
    lon = atan2(y, x);
    double p = sqrt(x * x + y * y);
    lat = atan2(z, p * (1 - e2));
    for (int i = 0; i < 5; ++i) {
        double N = a / sqrt(1 - e2 * sin(lat) * sin(lat));
        alt = p / cos(lat) - N;
        lat = atan2(z, p * (1 - e2 * (N / (N + alt))));
    }
    double N = a / sqrt(1 - e2 * sin(lat) * sin(lat));
    alt = p / cos(lat) - N;
    lat *= 180.0 / pi;
    lon *= 180.0 / pi;
}

int main() {
    std::srand(std::time(nullptr));

    // Radar position
    double radarLat = 28.5;
    double radarLon = -81.2;
    double radarAlt = 50.0;

    // Convert radar position to ECEF
    double x0, y0, z0;
    geodeticToECEF(radarLat, radarLon, radarAlt, x0, y0, z0);

    // Random number of pings
    int numPings = 1 + std::rand() % 10;

    std::ostringstream payload;
    payload << std::fixed << std::setprecision(6);

    for (int i = 0; i < numPings; ++i) {
        // Generate random radar detection values
        double range = 5000.0 + static_cast<double>(std::rand() % 15000);       // 5km - 20km
        double azimuth = static_cast<double>(std::rand() % 360);               // 0 - 360 deg
        double elevation = static_cast<double>((std::rand() % 2000) / 100.0);  // 0 - 20 deg
        double rangeRate = -100.0 + static_cast<double>(std::rand() % 200);    // -100 to +100 m/s

        // Convert detection to ENU
        double xEast, yNorth, zUp;
        radarToENU(range, azimuth, elevation, xEast, yNorth, zUp);

        // Convert ENU to ECEF offset
        double dx, dy, dz;
        enuToECEFOffset(xEast, yNorth, zUp, radarLat, radarLon, dx, dy, dz);

        // Compute target ECEF
        double x = x0 + dx;
        double y = y0 + dy;
        double z = z0 + dz;

        // Convert target ECEF to Geodetic
        double tgtLat, tgtLon, tgtAlt;
        ecefToGeodetic(x, y, z, tgtLat, tgtLon, tgtAlt);

        // Compute velocity in ENU frame (radial direction only)
        double vxEast, vyNorth, vzUp;
        radarToENU(rangeRate, azimuth, elevation, vxEast, vyNorth, vzUp);

        // Append to payload
        payload << "{lat:" << tgtLat << ",lon:" << tgtLon << ",alt:" << tgtAlt
            << ",ve:" << vxEast << ",vn:" << vyNorth << ",vu:" << vzUp << "}";
        if (i < numPings - 1) payload << ",";
    }

    std::cout << "\nRadar Ping Payload: [" << payload.str() << "]\n";

    return 0;
}

// Run program: Ctrl + F5 or Debug > Start Without Debugging menu
// Debug program: F5 or Debug > Start Debugging menu

// Tips for Getting Started: 
//   1. Use the Solution Explorer window to add/manage files
//   2. Use the Team Explorer window to connect to source control
//   3. Use the Output window to see build output and other messages
//   4. Use the Error List window to view errors
//   5. Go to Project > Add New Item to create new code files, or Project > Add Existing Item to add existing code files to the project
//   6. In the future, to open this project again, go to File > Open > Project and select the .sln file
