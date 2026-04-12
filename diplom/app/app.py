from flask import Flask, request, jsonify, session
import folium
from folium import MacroElement
from jinja2 import Template
from route_functions import RouteBuilder
from flask_simple_geoip import GeoIP

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

_first_request = True

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

@app.route("/")
def base():
    global route_coords
    
    if 'start' in session:
        route_coords['start'] = session['start']
    if 'end' in session:
        route_coords['end'] = session['end']
    
    m = folium.Map(location=[55.047929, 82.872188], zoom_start=13)
    m.add_child(LatLngPopup())
    
    info_html = f"""
    <div style="position: fixed; top: 90px; left: 10px; background: white; padding: 15px; z-index: 1000; width: 200px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="margin-bottom: 10px;">
            <b>Начало:</b><br>
            {route_coords['start'] if route_coords['start'] else 'не выбрано'}
        </div>
        <div style="margin-bottom: 10px;">
            <b>Конец:</b><br>
            {route_coords['end'] if route_coords['end'] else 'не выбрано'}
        </div>
        
        <button onclick="window.buildRoute(event)" 
                style="width: 100%; padding: 8px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; margin-bottom: 10px; cursor: pointer;">
                Построить маршрут
        </button>
        
        <button onclick="window.clearAll()" 
                style="width: 100%; padding: 8px; background-color: #f44336; color: white; border: none; border-radius: 4px; margin-bottom: 10px; cursor: pointer;">
                Очистить всё
        </button>
                
        <hr>
        <div style="margin-bottom: 5px;"><b>Маршруты:</b></div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <span style="color: blue; font-size: 20px; margin-right: 10px;">━━━</span>
            <span>Кратчайший</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <span style="color: green; font-size: 20px; margin-right: 10px;">━━━</span>
            <span>Тихий</span>
        </div>
        <div style="display: flex; align-items: center;">
            <span style="color: red; font-size: 20px; margin-right: 10px;">━━━</span>
            <span>Красивый</span>
        </div>
    </div>

    <script>
    // Создаем группы для маршрутов
    window.routeGroups = {{
        standard: L.layerGroup(),
        quiet: L.layerGroup(),
        beautiful: L.layerGroup()
    }};
        
    
    // Функция для добавления маршрутов на карту с поддержкой LayerControl
    window.addRoutesToMap = function(routes) {{
        console.log("Добавление маршрутов на карту:", routes);
        
        // Очищаем все группы
        for (let key in window.routeGroups) {{
            window.routeGroups[key].clearLayers();
        }}
        
        // Цвета для разных типов маршрутов
        const colors = {{
            'standard': 'blue',
            'quiet': 'green',
            'beautiful': 'red'
        }};
        
        // Названия для отображения в LayerControl
        const names = {{
            'standard': 'Кратчайший маршрут',
            'quiet': 'Тихий маршрут',
            'beautiful': 'Красивый маршрут'
        }};
        
        // Добавляем маршруты в соответствующие группы
        for (const [key, route] of Object.entries(routes)) {{
            if (route && route.coords && route.coords.length > 0 && window.routeGroups[key]) {{
                console.log(`Добавление маршрута ${{key}} с ${{route.coords.length}} точками`);
                
                const polyline = L.polyline(route.coords, {{
                    color: colors[key] || 'blue',
                    weight: 5,
                    opacity: 0.8
                }}).bindPopup(route.distance + ' м');
                
                window.routeGroups[key].addLayer(polyline);
            }}
        }}
        
        // Добавляем группы на карту, если их еще нет
        if (!window.layerControlAdded) {{
            // Добавляем группы на карту
            for (let key in window.routeGroups) {{
                window.routeGroups[key].addTo(window.currentMap);
            }}
            
            // Создаем LayerControl
            window.layerControl = L.control.layers(
                {{}},  // Базовые слои (можно оставить пустым)
                {{    // Оверлеи
                    "Кратчайший маршрут": window.routeGroups.standard,
                    "Тихий маршрут": window.routeGroups.quiet,
                    "Красивый маршрут": window.routeGroups.beautiful
                }},
                {{ collapsed: false }}  // Опции: не сворачивать панель
            ).addTo(window.currentMap);
            
            window.layerControlAdded = true;
        }}
        
        // Центрируем карту на первом маршруте
        if (routes.standard && routes.standard.coords && routes.standard.coords.length > 0) {{
            const bounds = L.latLngBounds(routes.standard.coords);
            window.currentMap.fitBounds(bounds.pad(0.1));
        }} else if (routes.quiet && routes.quiet.coords && routes.quiet.coords.length > 0) {{
            const bounds = L.latLngBounds(routes.quiet.coords);
            window.currentMap.fitBounds(bounds.pad(0.1));
        }} else if (routes.beautiful && routes.beautiful.coords && routes.beautiful.coords.length > 0) {{
            const bounds = L.latLngBounds(routes.beautiful.coords);
            window.currentMap.fitBounds(bounds.pad(0.1));
        }}
    }};

    window.buildRoute = function(event) {{            
        fetch('/get_route_coords')
            .then(response => response.json())
            .then(data => {{
                console.log("Данные координат:", data);
                
                if (!data.start || !data.end) {{
                    alert('Сначала выберите начало и конец маршрута!');
                    return;
                }}
                
                const btn = event.target;
                const originalText = btn.innerText;
                btn.innerText = 'Построение...';
                btn.disabled = true;
                                
                fetch('/build_route', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        start: data.start,
                        end: data.end
                    }})
                }})
                .then(response => response.json())
                .then(result => {{
                    if (!result.success) {{
                        alert('Ошибка: ' + result.error);
                    }} else {{
                        console.log("Маршруты построены:", result.routes);
                        // Добавляем маршруты на карту
                        window.addRoutesToMap(result.routes);
                        alert('Маршруты успешно построены!');
                    }}
                    btn.innerText = originalText;
                    btn.disabled = false;
                }})
                .catch(error => {{
                    console.error("Ошибка при запросе:", error);
                    alert('Ошибка соединения: ' + error);
                    btn.innerText = originalText;
                    btn.disabled = false;
                }});
            }})
            .catch(error => {{
                console.error("Ошибка при получении координат:", error);
                alert('Ошибка получения координат: ' + error);
            }});
    }};

    window.clearAll = function() {{
        console.log("clearAll вызвана");
        
        // Очищаем все группы маршрутов
        for (let key in window.routeGroups) {{
            window.routeGroups[key].clearLayers();
        }}
        
        // Очищаем маркеры и круги
        if (window.startMarker) {{
            window.currentMap.removeLayer(window.startMarker);
            window.startMarker = null;
        }}
        if (window.endMarker) {{
            window.currentMap.removeLayer(window.endMarker);
            window.endMarker = null;
        }}
        if (window.accuracyCircle) {{
            window.currentMap.removeLayer(window.accuracyCircle);
            window.accuracyCircle = null;
        }}
        
        fetch('/clear_route', {{
            method: 'POST'
        }})
        .then(() => {{
            return fetch('/clear_session', {{
                method: 'POST'
            }});
        }})
        .then(() => {{
            console.log("Сессия очищена");
            // Обновляем информацию в боковой панели
            location.reload();
        }})
        .catch(error => {{
            console.error("Ошибка при очистке:", error);
            alert('Ошибка при очистке: ' + error);
        }});
    }};

    // Сохраняем ссылку на карту после её загрузки
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            // Ищем переменную карты в глобальном объекте window
            for (let key in window) {{
                if (key.startsWith('map_') && window[key] && window[key]._leaflet_id) {{
                    window.currentMap = window[key];
                    console.log("Карта найдена:", key);
                    
                    // Добавляем маркеры, если они есть в сессии
                    fetch('/get_route_coords')
                        .then(response => response.json())
                        .then(data => {{
                            if (data.start) {{
                                const markerIcon = L.icon({{
                                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                                    iconSize: [25, 41],
                                    iconAnchor: [12, 41],
                                    popupAnchor: [1, -34],
                                    shadowSize: [41, 41]
                                }});
                                
                                window.startMarker = L.marker(data.start, {{icon: markerIcon}})
                                    .addTo(window.currentMap)
                                    .bindPopup("<b>Начало маршрута</b>");
                            }}
                            if (data.end) {{
                                const markerIcon = L.icon({{
                                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
                                    iconSize: [25, 41],
                                    iconAnchor: [12, 41],
                                    popupAnchor: [1, -34],
                                    shadowSize: [41, 41]
                                }});
                                
                                window.endMarker = L.marker(data.end, {{icon: markerIcon}})
                                    .addTo(window.currentMap)
                                    .bindPopup("<b>Конец маршрута</b>");
                            }}
                        }});
                    
                    // Загружаем сохраненные маршруты из сессии
                    fetch('/get_session_routes')
                        .then(response => response.json())
                        .then(data => {{
                            if (data.routes && Object.keys(data.routes).length > 0) {{
                                window.addRoutesToMap(data.routes);
                            }}
                        }});
                    
                    break;
                }}
            }}
            
            if (!window.currentMap) {{
                console.warn("Карта не найдена");
            }}
        }}, 500);
    }});
    
    console.log("Скрипт загружен, функции определены:", {{
        getUserLocation: typeof window.getUserLocation,
        getUserLocationByIP: typeof window.getUserLocationByIP,
        buildRoute: typeof window.buildRoute,
        clearAll: typeof window.clearAll,
        addRoutesToMap: typeof window.addRoutesToMap
    }});
    </script>
    """
    m.get_root().html.add_child(folium.Element(info_html))
    return m._repr_html_()


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
    """Возвращает сохраненные маршруты из сессии"""
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