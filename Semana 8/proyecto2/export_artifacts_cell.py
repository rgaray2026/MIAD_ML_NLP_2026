import joblib

# Ejecutar esta celda/script al final del notebook, después de entrenar:
# - modelo_lr_final
# - modelo_nb_final
# - vectorizador_word_final
# - vectorizador_char_final
# - le
# - mejor_peso_lr
# - mejor_peso_nb

artifacts = {
    "vectorizador_word": vectorizador_word_final,
    "vectorizador_char": vectorizador_char_final,
    "modelo_lr": modelo_lr_final,
    "modelo_nb": modelo_nb_final,
    "peso_lr": float(mejor_peso_lr),
    "peso_nb": float(mejor_peso_nb),
    "genres": list(le.classes_)
}

joblib.dump(artifacts, "movie_genre_model_artifacts.pkl")
print("Artefactos guardados en movie_genre_model_artifacts.pkl")