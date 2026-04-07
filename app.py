import os
from flask import Flask, Response
from config import HOST, PORT

app = Flask(__name__)

# Dynamic path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "data", "filtered_vless.txt")

@app.route('/filtered-vless')
def serve_vless():
    if not os.path.exists(FILE_PATH):
        return Response("Data file not found. Wait for loader to run.", status=404, mimetype='text/plain')
    
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        data = f.read()
    
    return Response(data, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host=HOST, port=PORT)