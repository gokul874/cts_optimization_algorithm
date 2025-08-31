// Healthcare Provider Finder JavaScript

let map;
let userMarker;
let userLat = null;
let userLon = null;
let providerMarkers = [];
let selectedProvider = null; // store provider info for feedback

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
    initializeMap();
    setupEventListeners();
});

function initializeMap() {
    map = L.map('map').setView([39.8283, -98.5795], 4);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    map.on('click', function (e) {
        setUserLocation(e.latlng.lat, e.latlng.lng);
    });
}

function setupEventListeners() {
    document.getElementById('getLocationBtn').addEventListener('click', getUserLocation);
    document.getElementById('searchBtn').addEventListener('click', searchProviders);

    // enable search when provider type changes
    document.getElementById('providerTypeSelect').addEventListener('change', searchProviders);

    // Feedback modal send button
    const feedbackBtn = document.getElementById('sendFeedbackBtn');
    if (feedbackBtn) {
        feedbackBtn.addEventListener('click', sendFeedback);
    }
}

function getUserLocation() {
    const btn = document.getElementById('getLocationBtn');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Getting Location...';
    btn.disabled = true;

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function (position) {
                setUserLocation(position.coords.latitude, position.coords.longitude);
                resetGetLocationBtn(btn);
            },
            function (error) {
                showError('Error getting your location: ' + getGeolocationErrorMessage(error.code));
                resetGetLocationBtn(btn);
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
        );
    } else {
        showError('Geolocation is not supported by this browser. Please click on the map to set your location.');
        resetGetLocationBtn(btn);
    }
}

function resetGetLocationBtn(btn) {
    btn.innerHTML = '<i class="fas fa-location-arrow me-2"></i>Get My Location';
    btn.disabled = false;
}

function setUserLocation(lat, lon) {
    userLat = lat;
    userLon = lon;

    if (userMarker) {
        map.removeLayer(userMarker);
    }

    userMarker = L.marker([lat, lon], {
        icon: L.divIcon({
            className: 'user-location-marker',
            html: '<i class="fas fa-user-circle" style="color: #007bff; font-size: 24px;"></i>',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        })
    }).addTo(map);

    map.setView([lat, lon], 12);

    document.getElementById('locationInfo').style.display = 'block';
    document.getElementById('locationCoords').textContent = `Lat: ${lat.toFixed(6)}, Lon: ${lon.toFixed(6)}`;
    document.getElementById('searchBtn').disabled = false;

    hideError();
}

function searchProviders() {
    if (!userLat || !userLon) {
        showError('Please set your location first.');
        return;
    }

    const providerType = document.getElementById('providerTypeSelect').value;
    const loadingSpinner = document.getElementById('loadingSpinner');
    const searchResults = document.getElementById('searchResults');
    const searchBtn = document.getElementById('searchBtn');

    loadingSpinner.style.display = 'block';
    searchResults.style.display = 'none';
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Searching...';

    clearProviderMarkers();

    const formData = new FormData();
    formData.append('latitude', userLat);
    formData.append('longitude', userLon);
    formData.append('provider_type', providerType);

    fetch('/search_providers', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            loadingSpinner.style.display = 'none';
            resetSearchBtn(searchBtn);

            if (data.success) {
                displaySearchResults(data.providers, data.count);
                addProviderMarkersToMap(data.providers);
            } else {
                showError('Search failed: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            loadingSpinner.style.display = 'none';
            resetSearchBtn(searchBtn);
            showError('Network error: ' + error.message);
        });
}

function resetSearchBtn(btn) {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-search me-2"></i>Search Providers';
}

function displaySearchResults(providers, count) {
    const searchResults = document.getElementById('searchResults');
    const providersList = document.getElementById('providersList');
    const resultsCount = document.getElementById('resultsCount');

    resultsCount.textContent = `${count} provider${count !== 1 ? 's' : ''} found`;

    if (providers.length === 0) {
        providersList.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-exclamation-circle fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No providers found</h5>
                <p class="text-muted">No healthcare providers found within 15km of your location.</p>
            </div>
        `;
    } else {
        providersList.innerHTML = providers.map((provider, index) => {
            const rating = provider.cms_rating || 0;
            return `
                <div class="provider-card card mb-3 fade-in" style="animation-delay: ${index * 0.1}s;">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-8">
                                <h5 class="card-title mb-2">${escapeHtml(provider.name)}</h5>
                                <p class="card-text text-muted mb-2">
                                    <i class="fas fa-map-marker-alt me-1"></i>
                                    ${escapeHtml(provider.full_address)}
                                </p>
                                <div class="d-flex flex-wrap gap-2 mb-2">
                                    <span class="badge provider-type bg-secondary">${escapeHtml(provider.type)}</span>
                                    <span class="badge rating-badge rating-${Math.floor(rating)}">
                                        <i class="fas fa-star me-1"></i>
                                        ${rating}/5
                                    </span>
                                </div>
                                <div class="row text-sm">
                                    <div class="col-sm-4">
                                        <i class="fas fa-dollar-sign me-1"></i>
                                        <span class="cost-tag">$${provider.cost}</span>
                                    </div>
                                    <div class="col-sm-4">
                                        <span class="availability-tag">${provider.availability} availability</span>
                                    </div>
                                    <div class="col-sm-4">
                                        <i class="fas fa-route me-1"></i>
                                        <span class="distance-tag">${provider.distance} km</span>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="d-grid gap-2">
                                    <button class="btn btn-primary btn-sm" onclick="openGoogleMaps(${provider.latitude}, ${provider.longitude})">
                                        <i class="fas fa-directions me-2"></i>
                                        Get Directions
                                    </button>
                                    <button class="btn btn-outline-secondary btn-sm" onclick="callProvider('${provider.contact}')">
                                        <i class="fas fa-phone me-2"></i>
                                        ${provider.contact}
                                    </button>
                                    <button class="btn btn-warning btn-sm" onclick="openFeedbackModal('${escapeHtml(provider.name)}')">
                                        <i class="fas fa-comment-dots me-2"></i>
                                        Feedback
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    searchResults.style.display = 'block';
    searchResults.scrollIntoView({ behavior: 'smooth' });
}

function openFeedbackModal(providerName) {
    document.getElementById("feedback-provider").value = providerName;
    const modal = new bootstrap.Modal(document.getElementById("feedbackModal"));
    modal.show();
}

function sendFeedback() {
    const provider = document.getElementById("feedback-provider").value;
    const message = document.getElementById("feedback-message").value.trim();

    if (!message) {
        alert("⚠️ Please type a message before sending.");
        return;
    }

    fetch("/send_feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            provider: provider,
            feedback: message
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert("✅ Feedback sent successfully!");
                const modal = bootstrap.Modal.getInstance(document.getElementById("feedbackModal"));
                modal.hide();
            } else {
                alert("⚠️ Error: " + data.error);
            }
        })
        .catch(() => {
            alert("❌ Server error. Try again later.");
        });
}

function addProviderMarkersToMap(providers) {
    providers.forEach((provider, index) => {
        const marker = L.marker([provider.latitude, provider.longitude], {
            icon: L.divIcon({
                className: 'provider-marker',
                html: `<div style="background: var(--bs-primary); color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">${index + 1}</div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            })
        });

        const rating = provider.cms_rating || 0;
        marker.bindPopup(`
            <div class="text-center">
                <strong>${escapeHtml(provider.name)}</strong><br>
                <small class="text-muted">${escapeHtml(provider.type)}</small><br>
                <span class="badge bg-primary mt-1">Rating: ${rating}/5</span><br>
                <button class="btn btn-sm btn-primary mt-2" onclick="openGoogleMaps(${provider.latitude}, ${provider.longitude})">
                    Get Directions
                </button>
            </div>
        `);

        marker.addTo(map);
        providerMarkers.push(marker);
    });

    if (providers.length > 0) {
        const group = new L.featureGroup([userMarker, ...providerMarkers]);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function clearProviderMarkers() {
    providerMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    providerMarkers = [];
}

function openGoogleMaps(lat, lon) {
    const url = `https://www.google.com/maps/dir/${userLat},${userLon}/${lat},${lon}/@${lat},${lon},15z`;
    window.open(url, '_blank');
}

function callProvider(phoneNumber) {
    if (phoneNumber && phoneNumber !== 'N/A') {
        window.open(`tel:${phoneNumber}`, '_self');
    } else {
        showError('Phone number not available for this provider.');
    }
}

function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
    errorAlert.scrollIntoView({ behavior: 'smooth' });

    setTimeout(() => {
        hideError();
    }, 10000);
}

function hideError() {
    document.getElementById('errorAlert').style.display = 'none';
}

function getGeolocationErrorMessage(code) {
    switch (code) {
        case 1: return 'Location access denied by user.';
        case 2: return 'Location information unavailable.';
        case 3: return 'Location request timed out.';
        default: return 'An unknown error occurred.';
    }
}

function escapeHtml(text) {
    if (!text) return "";
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, function (m) { return map[m]; });
}
