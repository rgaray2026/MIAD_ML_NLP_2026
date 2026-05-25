from flask import Flask, request, jsonify, render_template
import ast
import re
import joblib
import pandas as pd
from scipy.sparse import hstack

ARTIFACT_PATH = "movie_genre_model_artifacts.pkl"

app = Flask(__name__)

# El archivo .pkl debe generarse desde el notebook de entrenamiento.
artifacts = joblib.load(ARTIFACT_PATH)

vectorizador_word = artifacts["vectorizador_word"]
vectorizador_char = artifacts["vectorizador_char"]
modelo_lr = artifacts["modelo_lr"]
modelo_nb = artifacts["modelo_nb"]
peso_lr = artifacts.get("peso_lr", 0.7)
peso_nb = artifacts.get("peso_nb", 0.3)
genres = artifacts["genres"]


def limpiar_texto_basico(texto):
    texto = str(texto).lower()
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def crear_texto_enriquecido(df):
    """
    Debe conservar la misma lógica usada durante el entrenamiento:
    title repetido 3 veces + plot + tokens de año, década y longitud.
    """
    df = df.copy()

    if "title" not in df.columns:
        df["title"] = ""
    if "plot" not in df.columns:
        df["plot"] = ""
    if "year" not in df.columns:
        df["year"] = 0

    titulo = df["title"].fillna("").astype(str).apply(limpiar_texto_basico)
    plot = df["plot"].fillna("").astype(str).apply(limpiar_texto_basico)

    year_numeric = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    year_token = " year_" + year_numeric.astype(str)
    decade_token = " decade_" + ((year_numeric // 10) * 10).astype(str)

    title_len = titulo.str.split().apply(len)
    plot_len = plot.str.split().apply(len)

    title_len_bin = pd.cut(
        title_len,
        bins=[-1, 1, 3, 6, 1000],
        labels=[
            "title_len_very_short",
            "title_len_short",
            "title_len_medium",
            "title_len_long",
        ],
    ).astype(str)

    plot_len_bin = pd.cut(
        plot_len,
        bins=[-1, 30, 80, 150, 10000],
        labels=[
            "plot_len_short",
            "plot_len_medium",
            "plot_len_long",
            "plot_len_very_long",
        ],
    ).astype(str)

    texto = (
        titulo + " " +
        titulo + " " +
        titulo + " " +
        plot + " " +
        year_token + " " +
        decade_token + " " +
        title_len_bin + " " +
        plot_len_bin
    )

    return texto


def predict_genres(input_df):
    texto = crear_texto_enriquecido(input_df)

    X_word = vectorizador_word.transform(texto)
    X_char = vectorizador_char.transform(texto)
    X = hstack([X_word, X_char]).tocsr()

    pred_lr = modelo_lr.predict_proba(X)
    pred_nb = modelo_nb.predict_proba(X)
    pred = peso_lr * pred_lr + peso_nb * pred_nb

    return pd.DataFrame(pred, columns=genres)


@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None
    top_genres = None

    if request.method == "POST":
        row = {
            "title": request.form.get("title", ""),
            "plot": request.form.get("plot", ""),
            "year": request.form.get("year", 0),
        }

        pred_df = predict_genres(pd.DataFrame([row]))
        top_genres = (
            pred_df.iloc[0]
            .sort_values(ascending=False)
            .head(8)
            .reset_index()
            .rename(columns={"index": "genre", 0: "probability"})
            .to_dict(orient="records")
        )

        prediction = row

    return render_template("index.html", prediction=prediction, top_genres=top_genres)


@app.route("/predict", methods=["POST"])
def predict():
    """
    Recibe una observación:
    {
      "title": "Toy Story",
      "plot": "A cowboy doll is threatened...",
      "year": 1995
    }

    O una lista de observaciones:
    [
      {"title": "...", "plot": "...", "year": 2001},
      {"title": "...", "plot": "...", "year": 2010}
    ]
    """
    data = request.get_json(force=True)

    if isinstance(data, dict):
        input_df = pd.DataFrame([data])
    elif isinstance(data, list):
        input_df = pd.DataFrame(data)
    else:
        return jsonify({"error": "El cuerpo JSON debe ser un objeto o una lista de objetos."}), 400

    pred_df = predict_genres(input_df)

    response = []
    for idx, row in pred_df.iterrows():
        probabilities = {
            genre: float(probability)
            for genre, probability in row.sort_values(ascending=False).items()
        }
        top_5 = list(probabilities.items())[:5]
        response.append({
            "input_index": int(idx),
            "top_5_genres": [
                {"genre": genre, "probability": probability}
                for genre, probability in top_5
            ],
            "all_probabilities": probabilities
        })

    return jsonify(response)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": True})


if __name__ == "__main__":
    # Para desarrollo local. En EC2 se recomienda ejecutar con gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=False)