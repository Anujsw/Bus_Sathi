from flask import Flask, request, jsonify, send_from_directory
import mysql.connector
import datetime

app = Flask(__name__, static_folder='static')

# update these if you changed credentials
dbconfig = {
    'user': 'root',
    'password': 'anuj',
    'host': '127.0.0.1',
    'database': 'busdb'
}

def get_db_connection():
    return mysql.connector.connect(**dbconfig)

def make_json_friendly(row_dict):
    """Convert any datetime.time or datetime.timedelta values in the row to strings."""
    out = {}
    for k, v in row_dict.items():
        if isinstance(v, datetime.timedelta):
            # Convert timedelta to time string like "08:30:00"
            # timedelta may represent a time-of-day from midnight
            total_seconds = int(v.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            out[k] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        elif isinstance(v, datetime.time):
            out[k] = v.strftime("%H:%M:%S")
        else:
            out[k] = v
    return out

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/search')
def search_buses():
    source = (request.args.get('source') or '').strip()
    destination = (request.args.get('destination') or '').strip()
    if not source or not destination:
        return jsonify({'error': 'Provide both source and destination'}), 400

    query = """
    SELECT
      b.bus_number,
      b.route_name,
      s_src.stop_name AS source,
      s_dst.stop_name AS destination,
      s_src.arrival_time AS departure_time_at_source
    FROM buses b
    JOIN stops s_src ON b.bus_id = s_src.bus_id
    JOIN stops s_dst ON b.bus_id = s_dst.bus_id
    WHERE LOWER(s_src.stop_name) = LOWER(%s)
      AND LOWER(s_dst.stop_name) = LOWER(%s)
      AND s_src.stop_order < s_dst.stop_order
    ORDER BY s_src.arrival_time ASC;
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (source, destination))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # convert rows to JSON-friendly dicts
        json_rows = [make_json_friendly(r) for r in rows]

        print(f"[SEARCH] source='{source}' destination='{destination}' results={len(json_rows)}")
        return jsonify(json_rows)
    except Exception as e:
        print("DB error:", e)
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
