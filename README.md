# ⚡ StormVis: Real-time Lightning Analysis from Meteosat-12 LI

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Leaflet](https://img.shields.io/badge/leaflet-1.9.4-brightgreen.svg)](https://leafletjs.com/)

StormVis is an advanced, interactive web platform for visualizing satellite-based lightning detection data from the **Meteosat-12 (MTG-I1) Lightning Imager**. This tool provides researchers, meteorologists, and enthusiasts with high-fidelity, customizable maps of lightning activity across the globe.

## ✨ Core Features

-   **🌍 Global Visualization:** Select any country within the satellite scanning extent to generate a focused lightning density map.
-   **🎯 High-Resolution Mapping:** Choose between a 5km overview and a detailed 1km high-resolution grid.
-   **📊 Dynamic Data Processing:** A stream-based backend processes satellite data on-demand with live progress updates sent to the client.
-   **🎨 Modern & Responsive UI:** A clean and modern glass-morphism inspired interface with a dark theme that works seamlessly on both desktop and mobile devices.
-   **💾 Intelligent Caching:** An efficient caching mechanism minimizes redundant data processing and accelerates map generation for repeated queries.

## 🚀 Getting Started

To run a local instance of StormVis, please follow the steps below.

### Prerequisites

-   Python 3.8 or higher
-   An active EUMETSAT Data Access (EUMDAC) account. [Register here](https://eoportal.eumetsat.int).
-   Git for cloning the repository.

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/stormvis.git
    cd StormVis
    ```

2.  **Create and Activate a Virtual Environment**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate it
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows:
    # venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file by copying the example template.
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file and add your EUMDAC API credentials:
    ```ini
    EUMDAC_CLIENT_ID="your_client_id_here"
    EUMDAC_CLIENT_SECRET="your_client_secret_here"
    ```

5.  **Run the Application**
    ```bash
    python app.py
    ```
    Once the server is running, navigate to `http://localhost:5000` in your web browser.

## 📖 Usage Guide

Once the application is running in your browser:

1.  **Select a Region:** Click directly on a country on the interactive map to select it.
2.  **Choose Resolution:** Use the control panel to select either `5km` or `1km` map density.
3.  **Pick a Date:** Use the date picker to select the specific day for analysis.
4.  **Generate Map:** Click the "Generate" button to begin processing.
5.  **View Results:** The generated lightning density map will be overlaid onto your selected country.

> **⚠️ Data Availability Notice:**
> The Meteosat-12 Lightning Imager provides operational data from **October 31, 2024, onwards**. Pre-operational data may be available from July 8, 2024, but is not guaranteed to be complete. Please select dates accordingly.

---

## 🗺️ Data Sources

-   **Lightning Data:** EUMETSAT **Meteosat-12 (MTG-I1)** Lightning Imager.
-   **Country Boundaries:** GeoJSON dataset derived from Natural Earth Data.
-   **Base Map Tiles:** Stadia Maps (Alidade Smooth Dark theme).

## 🔮 Roadmap

We have an ambitious roadmap for StormVis. This section will be dynamically updated in the future once detailed conceptology will be ready.

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. We welcome any contributions to enhance StormVis.

If you have a suggestion or a bug fix, please fork the repository and create a pull request. For major changes, please open an issue first to discuss what you would like to change.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📝 License

This project is distributed under the MIT License. See `LICENSE` for more information.

## 🙏 Acknowledgments

-   **EUMETSAT** for providing public access to the invaluable Meteosat-12 (MTG-I1) Lightning Imager data.
-   The development communities behind **Cartopy, Matplotlib, NumPy, Pandas, Xarray,** and **Leaflet.js**.
-   **Stadia Maps** for providing the high-quality base map tiles.
-   **OpenStreetMap** and its contributors for the foundational geographical data that powers modern mapping.
