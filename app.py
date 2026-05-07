from dotenv import load_dotenv
from flask import Flask, request, render_template

from weather_service import buscar_clima_por_cidade

load_dotenv()

app = Flask(__name__)

@app.route('/', methods=["GET",])
def home():
    cidade = request.args.get('cidade', '').strip()
    weather = None
    error = None

    if cidade:
        result = buscar_clima_por_cidade(cidade)
        if result["error"]:
            error = result["message"]
        else:
            weather = result["data"]

    return render_template("index.html",
                           weather=weather,
                           error=error,
                           cidade=cidade)

if __name__ == '__main__':
    app.run(debug=True)