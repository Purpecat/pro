from flask import Flask, request, jsonify
import folium
from folium import MacroElement
from jinja2 import Template

app = Flask(__name__)


route_coords = {
    'start': None,
    'end': None
}

class LatLngPopup(MacroElement):
    _template = Template(u"""
            {% macro script(this, kwargs) %}
                var currentMap = {{this._parent.get_name()}};
                var {{this.get_name()}} = L.popup();
                
                var markersCount = 0;
                
                function latLngPop(e) {
                    var lat = e.latlng.lat.toFixed(6);
                    var lng = e.latlng.lng.toFixed(6);
                    
                    var buttonText = '';
                    var buttonAction = '';
                    
                    fetch('/get_markers_count')
                        .then(response => response.json())
                        .then(data => {
                            markersCount = data.count;
                            
                            if (markersCount === 0) {
                                buttonText = 'Установить начало маршрута';
                                buttonAction = 'saveAsStart';
                            } else if (markersCount === 1) {
                                buttonText = 'Установить конец маршрута';
                                buttonAction = 'saveAsEnd';
                            } else {
                                // Если уже есть оба маркера, показываем сообщение
                                {{this.get_name()}}
                                    .setLatLng(e.latlng)
                                    .setContent(
                                        '<div style="font-size: 14px; padding: 15px; text-align: center;">' +
                                        '<b>Маршрут уже построен</b><br><br>' +
                                        '</div>'
                                    )
                                    .openOn(currentMap);
                                return;
                            }
                            
                            {{this.get_name()}}
                                .setLatLng(e.latlng)
                                .setContent(
                                    '<div style="font-size: 14px; padding: 15px;">' +
                                    '<b>Координаты:</b><br>' +
                                    lat + ', ' + lng + '<br><br>' +
                                    '<button onclick="' + buttonAction + '(\\'' + lat + '\\', \\'' + lng + '\\')" ' +
                                    'style="padding: 8px 15px; background-color: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; width: 100%;">' +
                                    buttonText +
                                    '</button>' +
                                    '</div>'
                                )
                                .openOn(currentMap);
                        });
                }
                
                currentMap.on('click', latLngPop);
                
                function saveAsStart(lat, lng) {
                    fetch('/save_start', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({lat: lat, lng: lng})
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (currentMap) {
                            currentMap.closePopup();
                        }
                        var startIcon = L.icon({
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        });
                        
                        window.startMarker = L.marker([lat, lng], {icon: startIcon}).addTo(currentMap);
                        window.startMarker.bindPopup("<b>Начало маршрута</b>");
                        
                    });
                }
                
                function saveAsEnd(lat, lng) {
                    fetch('/save_end', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({lat: lat, lng: lng})
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (currentMap) {
                            currentMap.closePopup();
                        }
                        var endIcon = L.icon({
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        });
                        
                        window.endMarker = L.marker([lat, lng], {icon: endIcon}).addTo(currentMap);
                        window.endMarker.bindPopup("<b>Конец маршрута</b>");
                                               
                    });
                }
                
                function clearRoute() {
                    fetch('/clear_route', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (window.startMarker) currentMap.removeLayer(window.startMarker);
                        if (window.endMarker) currentMap.removeLayer(window.endMarker);
                        if (window.routeLine) currentMap.removeLayer(window.routeLine);
                        
                        currentMap.closePopup();
                        location.reload();
                    });
                }
            {% endmacro %}
            """)

    def __init__(self):
        super(LatLngPopup, self).__init__()
        self._name = 'LatLngPopup'

@app.route("/")
def base():
    m = folium.Map(location=[55.047929, 82.872188], zoom_start=13)
    m.add_child(LatLngPopup())
    
    standard_group = folium.FeatureGroup(name='Кратчайший маршрут', show=True)
    quiet_group = folium.FeatureGroup(name='Тихий маршрут', show=True)
    beautiful_group = folium.FeatureGroup(name='Красивый маршрут', show=True)
    
    info_html = f"""
    <div style="position: fixed; top: 90px; left: 10px; background: white; padding: 15px;  z-index: 1000; width: 200px; height : 220px">
        <div style="display: flex; gap: 5px;">
            <button style="flex: 1; padding: 5px; background-color: red; color: white; border: none; border-radius: 3px; margin-bottom: 10px;">
                Построить маршрут
            </button>
        </div>
        <div style="display: flex; gap: 5px;">
            <button onclick="fetch('/clear_route', {{method: 'POST'}}).then(() => location.reload())"
                    style="flex: 1; padding: 5px; background-color: red; color: white; border: none; border-radius: 3px; margin-bottom: 5px;">
                Очистить
            </button>
        </div>

        <div style="margin-bottom: 10px; font-size: 14px; color: #333;">
            <b>Маршруты:</b>
        </div>
        
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="color: blue; font-size: 20px; line-height: 1; margin-left: 5px; margin-right: 12px;">━━━</span>
            <span style="font-size: 13px;"><b>Кратчайший</b></span>
        </div>
        
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="color: green; font-size: 20px; line-height: 1; margin-left: 5px; margin-right: 12px;">━━━</span>
            <span style="font-size: 13px;"><b>Тихий</b></span>
        </div>
        
        <div style="display: flex; align-items: center;">
            <span style="color: red; font-size: 20px; line-height: 1; margin-left: 5px; margin-right: 12px;">━━━</span>
            <span style="font-size: 13px;"><b>Красивый</b></span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))
    
    if route_coords['start'] and route_coords['end']:
        # folium.PolyLine(standard_coords, color='blue', weight=5, 
        #  popup=f'{distance}м').add_to(standard_group)
        # folium.PolyLine(quiet_coords, color='green', weight=5,
        #         popup=f'{quiet_distance}м').add_to(quiet_group)
        # folium.PolyLine(beautiful_coords, color='red', weight=5,
        #         popup=f'{beautiful_distance}м').add_to(beautiful_group)
        pass
    
    standard_group.add_to(m)
    quiet_group.add_to(m)
    beautiful_group.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m._repr_html_()

@app.route('/save_start', methods=['POST'])
def save_start():
    global route_coords
    data = request.json
    route_coords['start'] = [float(data['lat']), float(data['lng'])]
    print(f"Начало маршрута: {route_coords['start']}")
    return jsonify({'status': 'ok'})

@app.route('/save_end', methods=['POST'])
def save_end():
    global route_coords
    data = request.json
    route_coords['end'] = [float(data['lat']), float(data['lng'])]
    print(f"Конец маршрута: {route_coords['end']}")
    return jsonify({'status': 'ok'})

@app.route('/clear_route', methods=['POST'])
def clear_route():
    global route_coords
    route_coords['start'] = None
    route_coords['end'] = None
    print("Маршрут очищен")
    return jsonify({'status': 'ok'})

@app.route('/get_markers_count')
def get_markers_count():
    global route_coords
    count = sum(1 for v in route_coords.values() if v is not None)
    return jsonify({'count': count})

if __name__ == "__main__":
    app.run(debug=True, port=5000)