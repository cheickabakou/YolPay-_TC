let map = null;
function initMap(elementId, lat = 40.4597, lng = 39.4826, zoom = 8) {
  map = L.map(elementId, { zoomControl: true }).setView([lat, lng], zoom);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap © CartoDB', subdomains: 'abcd', maxZoom: 19
  }).addTo(map);
  return map;
}
function addTripMarkers(trips) {
  if (!map) return;
  const bounds = [];
  trips.forEach(trip => {
    if (trip.departure_lat && trip.departure_lat != 0) {
      const depIcon = L.divIcon({ className: '', html: `<div style="background:#6c63ff;width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 8px rgba(108,99,255,0.6)"></div>`, iconSize:[12,12], iconAnchor:[6,6] });
      const destIcon = L.divIcon({ className: '', html: `<div style="background:#00d4aa;width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 8px rgba(0,212,170,0.6)"></div>`, iconSize:[12,12], iconAnchor:[6,6] });
      L.marker([trip.departure_lat, trip.departure_lng], { icon: depIcon })
        .bindPopup(`<div style="font-family:DM Sans,sans-serif;padding:10px;min-width:160px"><strong style="color:#6c63ff">🚀 ${trip.departure}</strong><br><span style="color:#888;font-size:12px">→ ${trip.destination}</span><br><span style="color:#888;font-size:12px">📅 ${trip.date} ⏰ ${trip.time}</span><br><span style="font-weight:600">💰 ${trip.price}₺</span></div>`)
        .addTo(map);
      if (trip.destination_lat && trip.destination_lat != 0) {
        L.marker([trip.destination_lat, trip.destination_lng], { icon: destIcon })
          .bindPopup(`<strong style="color:#00d4aa">🏁 ${trip.destination}</strong>`).addTo(map);
        L.polyline([[trip.departure_lat, trip.departure_lng],[trip.destination_lat, trip.destination_lng]], { color: '#6c63ff', weight: 2, opacity: 0.6, dashArray: '6, 8' }).addTo(map);
        bounds.push([trip.departure_lat, trip.departure_lng]);
        bounds.push([trip.destination_lat, trip.destination_lng]);
      }
    }
  });
  if (bounds.length > 0) map.fitBounds(bounds, { padding: [40, 40] });
}
async function loadAndDisplayTrips(mapId) {
  try {
    const resp = await fetch('/api/trips');
    const trips = await resp.json();
    if (!map) initMap(mapId);
    addTripMarkers(trips);
    return trips;
  } catch(e) { console.error('Error:', e); }
}
