from flask import Flask, request, jsonify, session, render_template
from folium import MacroElement
from jinja2 import Template
from route_functions import RouteBuilder
import requests

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
_first_request = True
DADATA_API_KEY = "e21592892b6804ed299a4769778bda688d69239b"
DADATA_SECRET = "7d299f0844fc146b35bb79a5bd57ff5c054e4571"


@app.route('/suggest', methods=['GET'])
def suggest_address():
    query = request.args.get('query', '')
    if len(query) < 3:
        return jsonify({'suggestions': []})
    
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    headers = {
        "Authorization": f"Token {DADATA_API_KEY}",
        "X-Secret": DADATA_SECRET,
        "Content-Type": "application/json"
    }
    data = {
        "query": query,
        "count": 5,
        "locations": [
            {
                "city": "Новосибирск"
            }
        ]
    }
        
    try:
        response = requests.post(url, json=data, headers=headers, timeout=3)
        result = response.json()
        
        # Преобразуем в удобный формат
        suggestions = []
        for sugg in result.get('suggestions', []):
            suggestions.append({
                'address': sugg.get('value', ''),
                'unrestricted_value': sugg.get('unrestricted_value', ''),
                'lat': sugg.get('data', {}).get('geo_lat'),
                'lon': sugg.get('data', {}).get('geo_lon')
            })
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        print(f"Ошибка suggest: {e}")
        return jsonify({'suggestions': [], 'error': str(e)})


@app.route('/geocode', methods=['POST'])
def geocode_address():
    data = request.json
    address = data.get('address', '')
    if not address:
        return jsonify({'success': False, 'error': 'Адрес не указан'})
    
    url = "https://cleaner.dadata.ru/api/v1/clean/address"
    headers = {
        "Authorization": f"Token {DADATA_API_KEY}",
        "X-Secret": DADATA_SECRET,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=[address], headers=headers, timeout=5)
        result = response.json()
        
        if result and len(result) > 0:
            item = result[0]
            lat = item.get('geo_lat')
            lon = item.get('geo_lon')
            
            if lat and lon:
                return jsonify({
                    'success': True,
                    'address': item.get('unrestricted_value', address),
                    'lat': float(lat),
                    'lon': float(lon)
                })
        
        return jsonify({'success': False, 'error': 'Адрес не найден'})
    except Exception as e:
        print(f"Ошибка geocode: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/reverse_geocode', methods=['GET'])
def reverse_geocode():
    """Получает короткий адрес по координатам (улица + дом с запятой)"""
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    if not lat or not lng:
        return jsonify({'success': False, 'error': 'Не указаны координаты'})
    
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'addressdetails': 1,
            'zoom': 18
        }
        headers = {'User-Agent': 'FlaskRouteBuilder/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data and 'address' in data:
            address_parts = data['address']
            
            street = None
            house_number = None
            
            if 'house_number' in address_parts:
                house_number = address_parts['house_number']
            
            street = (address_parts.get('road') or 
                     address_parts.get('pedestrian') or 
                     address_parts.get('footway') or 
                     address_parts.get('street'))
            
            # Если улица не найдена, берем 'suburb' или 'neighbourhood'
            if not street:
                street = (address_parts.get('suburb') or 
                         address_parts.get('neighbourhood') or 
                         address_parts.get('city_district'))
            
            # Формируем результат
            result = ''
            if street and house_number:
                result = f"{street}, {house_number}"
            elif street:
                result = street
            elif house_number:
                result = f"дом {house_number}"
            else:
                # Если ничего не нашли, берем название города
                result = address_parts.get('city', 'Новосибирск')
            
            if result:
                return jsonify({'success': True, 'address': result})
        
        return jsonify({'success': False, 'error': 'Адрес не найден'})
    except Exception as e:
        print(f"Ошибка reverse_geocode: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.before_request
def clear_on_first_request():
    global _first_request, route_coords
    if _first_request:
        session.clear()
        route_coords['start'] = None
        route_coords['end'] = None
        _first_request = False
        print("Сессия очищена при запуске")

GRAPH_FILE = 'D:\\project\\diplom\\graphs\\novosibirsk_graph.graphml'
route_builder = RouteBuilder(GRAPH_FILE)

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
                
                var marker_icon = L.icon({
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        });
                
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
                        window.startMarker = L.marker([lat, lng], {icon: marker_icon}).addTo(currentMap);
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
                        window.endMarker = L.marker([lat, lng], {icon: marker_icon}).addTo(currentMap);
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

@app.route('/')
def base():
    start_coords = route_coords.get('start')
    end_coords = route_coords.get('end')
    
    return render_template('index.html', 
                         start=start_coords,
                         end=end_coords,
                         api_key=app.secret_key)


@app.route('/build_route', methods=['POST'])
def build_route():
    try:
        data = request.json
        start = data['start']
        end = data['end']
        
        print(f"Начало: {start}")
        print(f"Конец: {end}")
        
        start_point = (start[0], start[1])
        end_point = (end[0], end[1])
        
        routes = route_builder.build_routes(start_point, end_point)
        
        session['routes'] = routes
        session['start'] = start
        session['end'] = end
        
        print(f"Маршруты построены и сохранены в сессии")
        
        return jsonify({
            'success': True,
            'routes': routes
        })
        
    except Exception as e:
        print(f"Ошибка при построении маршрута: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/save_start', methods=['POST'])
def save_start():
    global route_coords
    data = request.json
    route_coords['start'] = [float(data['lat']), float(data['lng'])]
    session['start'] = route_coords['start']
    print(f"Начало маршрута: {route_coords['start']}")
    return jsonify({'status': 'ok'})

@app.route('/save_end', methods=['POST'])
def save_end():
    global route_coords
    data = request.json
    route_coords['end'] = [float(data['lat']), float(data['lng'])]
    session['end'] = route_coords['end']
    print(f"Конец маршрута: {route_coords['end']}")
    return jsonify({'status': 'ok'})

@app.route('/clear_route', methods=['POST'])
def clear_route():
    global route_coords
    route_coords['start'] = None
    route_coords['end'] = None
    session.pop('start', None)
    session.pop('end', None)
    session.pop('routes', None)
    print("Маршрут очищен")
    return jsonify({'status': 'ok'})

@app.route('/get_markers_count')
def get_markers_count():
    global route_coords
    count = sum(1 for v in route_coords.values() if v is not None)
    return jsonify({'count': count})

@app.route('/get_route_coords')
def get_route_coords():
    global route_coords
    return jsonify({
        'start': route_coords['start'],
        'end': route_coords['end']
    })

@app.route('/get_session_routes')
def get_session_routes():
    routes = session.get('routes', {})
    return jsonify({'routes': routes})

@app.route('/clear_session', methods=['POST'])
def clear_session():
    session.pop('routes', None)
    session.pop('start', None)
    session.pop('end', None)
    return jsonify({'status': 'ok'})

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)