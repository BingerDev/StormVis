# app.py

import os
import json
from flask import Flask, render_template, request, Response, stream_with_context, url_for
from dotenv import load_dotenv
import map_generator
import traceback

load_dotenv()
app = Flask(__name__)

PRODUCT_GENERATORS = {
    'daily_lowres_density': map_generator.generate_daily_lowres_density,
    'daily_hires_density': map_generator.generate_daily_hires_density,
}

@app.route('/')
def index():
    """render the main application page"""
    return render_template('index.html')

@app.route('/stream-generate', methods=['GET'])
def stream_generate():
    """handles the map generation request and streams progress updates to the client"""
    try:
        product_id = request.args.get('product')
        country_code = request.args.get('country')
        year = int(request.args.get('year'))
        month = int(request.args.get('month'))
        day = int(request.args.get('day'))

        if not all([product_id, country_code, year, month, day]):
            raise ValueError("missing required parameters.")
            
    except (TypeError, ValueError) as e:
        error_json = json.dumps({
            "status": f"invalid request: {e}", "progress": 100, 
            "done": True, "error": True
        })
        return Response(f"data: {error_json}\n\n", mimetype='text/event-stream')

    def event_stream():
        """the generator function that yields server-sent events"""
        try:
            generator_func = PRODUCT_GENERATORS.get(product_id)

            if not generator_func:
                update = {'status': 'invalid product specified.', 'error': True}
            else:
                generator = generator_func(year, month, day, country_code)
                for update in generator:
                    if update.get("done") and not update.get("error"):
                        if "result" in update:
                            update['url'] = url_for('static', filename=update.pop('result'))
                            update['type'] = 'image'
                    
                    yield f"data: {json.dumps(update)}\n\n"
                return

            yield f"data: {json.dumps({**update, 'done': True, 'progress': 100})}\n\n"

        except Exception as e:
            traceback.print_exc()
            error_update = {
                'status': 'an unexpected server error occurred.', 
                'error': True, 'done': True, 'progress': 100
            }
            yield f"data: {json.dumps(error_update)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)