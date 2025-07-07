// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    const map = L.map('map', {
        center: [52.0, 19.5],
        zoom: 6,
        zoomControl: false,
        attributionControl: false,
        
        zoomAnimation: true,
        zoomAnimationThreshold: 4,
        
        scrollWheelZoom: true,
        doubleClickZoom: true,
        boxZoom: true,
        
        dragging: true,
        
        touchZoom: true,
        tap: true
    });

    L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
        maxZoom: 20,
        attribution: '© <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> © <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
    }).addTo(map);
        
    L.control.zoom({ position: 'topright' }).addTo(map);

    let dataLayer = null;
    let geojsonLayer = null;
    let selectedCountryLayer = null;
    let selectedCountryName = null;
    let selectedCountryBounds = null;
    let selectedCountryISOCode = null;

    const selectedCountryDisplay = document.getElementById('selected-country');

    const defaultStyle = {
        weight: 0,
        opacity: 0,
        fillOpacity: 0
    };
    const hoverStyle = {
        weight: 2,
        color: '#FFFFFF',
        opacity: 1,
        fillOpacity: 0.1
    };
    const selectedStyle = {
        weight: 2.5,
        color: '#38bdf8',
        opacity: 1,
        fillOpacity: 0.15
    };

    function getFlagEmoji(isoCode) {
        if (!isoCode || isoCode.length !== 2) return '';
        return String.fromCodePoint(...isoCode.toUpperCase().split('').map(char => char.charCodeAt(0) + 127397));
    }

    fetch('/static/data/countries.geojson')
        .then(response => response.json())
        .then(data => {
            geojsonLayer = L.geoJson(data, {
                style: defaultStyle,
                onEachFeature: (feature, layer) => {
                    layer.on({
                        mouseover: (e) => {
                            if (layer !== selectedCountryLayer) {
                                layer.setStyle(hoverStyle);
                                layer.bringToFront();
                            }
                        },
                        mouseout: (e) => {
                            if (layer !== selectedCountryLayer) {
                                layer.setStyle(defaultStyle);
                            }
                        },
                        click: (e) => {
                            if (selectedCountryLayer && selectedCountryLayer !== layer) {
                                selectedCountryLayer.setStyle(defaultStyle);
                            }

                            if (selectedCountryLayer === layer) {
                                layer.setStyle(defaultStyle);
                                selectedCountryLayer = null;
                                selectedCountryName = null;
                                selectedCountryBounds = null;
                                selectedCountryISOCode = null; 
                                selectedCountryDisplay.classList.add('hidden');
                            } else {
                                layer.setStyle(selectedStyle);
                                layer.bringToFront();
                                selectedCountryLayer = layer;
                                
                                const props = feature.properties;

                                selectedCountryName = props.name || 'Unknown';
                                selectedCountryISOCode = props['ISO3166-1-Alpha-2']; 
                                
                                selectedCountryBounds = layer.getBounds();

                                const flag = getFlagEmoji(selectedCountryISOCode);
                                selectedCountryDisplay.innerHTML = `<span class="flag-emoji">${flag}</span> ${selectedCountryName}`;
                                selectedCountryDisplay.classList.remove('hidden');
                                updateGenerateButtonState();
                            }
                        }
                    });
                }
            }).addTo(map);
        });

    const form = document.getElementById('generator-form');
    const resolutionSelect = document.getElementById('resolution'); 
    const dateInput = document.getElementById('date');
    const generateBtn = document.getElementById('generate-btn');
    const mapLoader = document.getElementById('map-loader');
    const progressText = document.getElementById('progress-text');
    const mapContainer = document.getElementById('map');
    const mapInteractionBlocker = document.getElementById('map-interaction-blocker');
    const floatingControls = document.querySelector('.floating-controls');
    const controlToggleBtn = document.getElementById('control-toggle');

    const tableModal = document.getElementById('table-modal');
    const modalBackdrop = document.getElementById('modal-backdrop');
    const modalClose = document.getElementById('modal-close');
    const tableContainer = document.getElementById('result-table-container');

    controlToggleBtn.addEventListener('click', function() {
        floatingControls.classList.toggle('panel-hidden');
    });

    dateInput.addEventListener('change', updateGenerateButtonState);

    if (!dateInput.value) {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        dateInput.valueAsDate = yesterday;
    }

    updateGenerateButtonState();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const params = buildRequestParams();
        await generateVisualization(params);
    });

    function buildRequestParams() {
        const params = new URLSearchParams();
        const resolution = resolutionSelect.value;

        if (resolution === 'hires') {
            params.append('product', 'daily_hires_density');
        } else {
            params.append('product', 'daily_lowres_density');
        }

        const [year, month, day] = dateInput.value.split('-');
        params.append('year', year);
        params.append('month', month);
        params.append('day', day);
        
        if (selectedCountryISOCode) {
            params.append('country', selectedCountryISOCode);
        }
        
        return params;
    }

    function updateGenerateButtonState() {
        if (selectedCountryISOCode && dateInput.value) {
            generateBtn.disabled = false;
            generateBtn.title = '';
        } else {
            generateBtn.disabled = true;
            generateBtn.title = 'Please select a country and a date first.';
        }
    }

    function displayImageOverlay(url) {
        if (dataLayer) {
            map.removeLayer(dataLayer);
            dataLayer = null;
        }
        
        const boundsToUse = selectedCountryBounds || [[48.8, 13.8], [55.2, 24.2]];

        dataLayer = L.imageOverlay(`${url}?t=${Date.now()}`, boundsToUse, {
            opacity: 0.8,
            interactive: false
        }).addTo(map);
        
        map.fitBounds(boundsToUse, { 
            padding: [50, 50]
        });
    }
    
    async function generateVisualization(params) {
        showLoadingState();
        
        const url = `/stream-generate?${params.toString()}`;
        const source = new EventSource(url);
        
        source.onmessage = (event) => handleStreamUpdate(event, source);
        source.onerror = (err) => handleError(err, source);
    }

    function handleStreamUpdate(event, source) {
        const data = JSON.parse(event.data);
        
        if (progressText.textContent !== data.status) {
            progressText.style.opacity = '0';
            setTimeout(() => {
                progressText.textContent = data.status || 'Processing...';
                progressText.style.opacity = '1';
            }, 150);
        }

        if (data.error) {
            progressText.textContent = `error: ${data.status}`;
            source.close();
            hideLoadingState(false);
            return;
        }

        if (data.done) {
            source.close();
            progressText.textContent = 'complete!';
            
            setTimeout(() => {
                if (data.type === 'image') {
                    displayImageOverlay(data.url);
                } else if (data.type === 'table') {
                    displayTableResults(data.data);
                }
                hideLoadingState(true);
            }, 500);
        }
    }

    function handleError(err, source) {
        console.error("eventSource failed:", err);
        progressText.textContent = 'connection error occurred';
        source.close();
        hideLoadingState(false);
    }

    function showLoadingState() {
        generateBtn.disabled = true;
        generateBtn.classList.add('loading');
        generateBtn.textContent = 'Processing...';
        mapContainer.classList.add('map-faded');
        mapLoader.classList.remove('hidden');
        mapInteractionBlocker.classList.remove('hidden');
        if (dataLayer) {
            dataLayer.setOpacity(0);
        }
    }

    function hideLoadingState(success) {
        generateBtn.disabled = false;
        generateBtn.classList.remove('loading');
        generateBtn.textContent = 'Generate';
        mapContainer.classList.remove('map-faded');
        mapInteractionBlocker.classList.add('hidden');
        setTimeout(() => {
            mapLoader.classList.add('hidden');
        }, 300);
        if (!success && dataLayer) {
            dataLayer.setOpacity(0);
        }
    }

    function displayTableResults(data) {
        renderTable(data);
        showModal();
    }

    function showModal() {
        modalBackdrop.classList.remove('hidden');
        tableModal.classList.remove('hidden');
        modalBackdrop.style.cssText = `...`;
        tableModal.style.cssText = `...`;
        setTimeout(() => {
            modalBackdrop.style.opacity = '1';
            tableModal.style.transform = 'translate(-50%, -50%) scale(1)';
            tableModal.style.opacity = '1';
        }, 10);
    }

    function hideModal() {
        modalBackdrop.style.opacity = '0';
        tableModal.style.transform = 'translate(-50%, -50%) scale(0.9)';
        tableModal.style.opacity = '0';
        setTimeout(() => {
            modalBackdrop.classList.add('hidden');
            tableModal.classList.add('hidden');
        }, 300);
    }

    modalClose.addEventListener('click', hideModal);
    modalBackdrop.addEventListener('click', hideModal);
    tableModal.addEventListener('click', (e) => e.stopPropagation());
});