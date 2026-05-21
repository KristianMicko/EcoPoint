from flask import Flask, request, jsonify
from datetime import datetime
import plotly.graph_objects as go
from flask import render_template_string
import csv
import os

app = Flask(__name__)

DATA_DIR = "data"

FLOORS = [1, 2, 3, 4, 5]

SENSORS = {
    "co2": "co2.csv",
    "vox": "vox.csv",
    "nox": "nox.csv",
    "temperature": "temperature.csv",
    "humidity": "humidity.csv",
    "pm10": "pm10.csv",
    "pm2_5": "pm2_5.csv",
    "pm1": "pm1.csv"
}


def init_directories():
    os.makedirs(DATA_DIR, exist_ok=True)

    for floor in FLOORS:
        floor_dir = os.path.join(DATA_DIR, f"floor_{floor}")
        os.makedirs(floor_dir, exist_ok=True)

        for filename in SENSORS.values():
            path = os.path.join(floor_dir, filename)

            if not os.path.exists(path):
                with open(path, "w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(["timestamp", "value"])


def get_sensor_path(floor, sensor):
    return os.path.join(
        DATA_DIR,
        f"floor_{floor}",
        SENSORS[sensor]
    )


def save_value(floor, sensor, value):
    path = get_sensor_path(floor, sensor)

    timestamp = datetime.utcnow().isoformat()

    with open(path, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, value])

    return timestamp


@app.route("/api/<int:floor>/<sensor>", methods=["POST"])
def add_sensor_value(floor, sensor):

    if floor not in FLOORS:
        return jsonify({"error": "Invalid floor"}), 404

    if sensor not in SENSORS:
        return jsonify({"error": "Unknown sensor"}), 404

    data = request.get_json()

    if not data or "value" not in data:
        return jsonify({"error": "Missing value"}), 400

    try:
        value = float(data["value"])
    except ValueError:
        return jsonify({"error": "Value must be numeric"}), 400

    timestamp = save_value(floor, sensor, value)

    return jsonify({
        "floor": floor,
        "sensor": sensor,
        "value": value,
        "timestamp": timestamp,
        "status": "saved"
    }), 201


@app.route("/api/<int:floor>/<sensor>", methods=["GET"])
def get_sensor_values(floor, sensor):

    if floor not in FLOORS:
        return jsonify({"error": "Invalid floor"}), 404

    if sensor not in SENSORS:
        return jsonify({"error": "Unknown sensor"}), 404

    path = get_sensor_path(floor, sensor)

    timestamps = []
    values = []

    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            timestamps.append(row["timestamp"])
            values.append(float(row["value"]))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode="lines+markers",
        name=sensor
    ))

    fig.update_layout(
        title=f"{sensor.upper()} - Floor {floor}",
        xaxis_title="Timestamp",
        yaxis_title="Value",
        template="plotly_white"
    )

    graph_html = fig.to_html(full_html=False)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sensor Graph</title>
    </head>
    <body>
        <h1>Timeseries graf</h1>
        {{ graph|safe }}
    </body>
    </html>
    """

    return render_template_string(html, graph=graph_html)


@app.route("/api/<int:floor>", methods=["POST"])
def add_multiple_values(floor):

    if floor not in FLOORS:
        return jsonify({"error": "Invalid floor"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    saved = []

    for sensor, value in data.items():

        if sensor not in SENSORS:
            continue

        try:
            numeric_value = float(value)
        except ValueError:
            continue

        timestamp = save_value(floor, sensor, numeric_value)

        saved.append({
            "sensor": sensor,
            "value": numeric_value,
            "timestamp": timestamp
        })

    return jsonify({
        "floor": floor,
        "saved": saved,
        "count": len(saved)
    }), 201

@app.route("/ecopoint", methods=["GET"])
def ecopoint():

    html = """
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ecopoint Dashboard</title>

        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f4f6f8;
            }

            .container {
                max-width: 1100px;
                margin: 0 auto;
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }

            h1 {
                margin-top: 0;
                text-align: center;
            }

            .form-row {
                display: flex;
                gap: 16px;
                margin-bottom: 20px;
            }

            .form-group {
                flex: 1;
                display: flex;
                flex-direction: column;
            }

            label {
                margin-bottom: 6px;
                font-weight: bold;
            }

            select, button {
                padding: 12px;
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 8px;
            }

            button {
                background: #2e7d32;
                color: white;
                cursor: pointer;
                border: none;
            }

            button:hover {
                background: #256628;
            }

            iframe {
                width: 100%;
                height: 650px;
                border: 1px solid #ddd;
                border-radius: 10px;
                background: white;
            }

            @media (max-width: 700px) {
                .form-row {
                    flex-direction: column;
                }

                iframe {
                    height: 500px;
                }
            }
        </style>
    </head>

    <body>
        <div class="container">
            <h1>Ecopoint Dashboard</h1>

            <form id="sensorForm">
                <div class="form-row">
                    <div class="form-group">
                        <label for="floor">Poschodie</label>
                        <select id="floor" name="floor">
                            {% for floor in floors %}
                                <option value="{{ floor }}">Poschodie {{ floor }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="sensor">Senzor</label>
                        <select id="sensor" name="sensor">
                            {% for sensor in sensors %}
                                <option value="{{ sensor }}">{{ sensor.upper() }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="form-group">
                        <label>&nbsp;</label>
                        <button type="submit">Zobraziť graf</button>
                    </div>
                </div>
            </form>

            <iframe id="graphFrame" src="/api/1/co2"></iframe>
        </div>

        <script>
            const form = document.getElementById("sensorForm");
            const iframe = document.getElementById("graphFrame");

            form.addEventListener("submit", function(event) {
                event.preventDefault();

                const floor = document.getElementById("floor").value;
                const sensor = document.getElementById("sensor").value;

                iframe.src = `/api/${floor}/${sensor}`;
            });
        </script>
    </body>
    </html>
    """

    return render_template_string(
        html,
        floors=FLOORS,
        sensors=SENSORS.keys()
    )

@app.route("/")
def index():
    return jsonify({
        "message": "Environmental Monitoring API",
        "floors": FLOORS,
        "sensors": list(SENSORS.keys())
    })


if __name__ == "__main__":
    init_directories()
    app.run(host="0.0.0.0", port=7000, debug=True)
