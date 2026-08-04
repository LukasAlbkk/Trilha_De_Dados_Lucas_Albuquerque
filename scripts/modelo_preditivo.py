"""
sprint 4

Modelo simples de regressao linear para previsao do faturamento diario,
usado para estimar o faturamento do proximo mes (Janeiro/2026) a partir do
historico de vendas de 2025 (database/ecommerce.db).
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "ecommerce.db"
REPORTS_DIR = BASE_DIR / "reports"

DIAS_TESTE = 30
DIAS_PREVISAO = 31  # Janeiro/2026
COLUNAS_CATEGORICAS = ["dia_semana", "mes"]
# Sem feature de tendencia linear (dia_ordinal): a EDA da Sprint 2 ja mostrou
# que o faturamento mensal nao tem tendencia de crescimento real (dados
# simulados aleatoriamente) e extrapolar uma reta de tendencia para meses
# fora do intervalo de treino distorcia a previsao. As features ficam
# limitadas ao padrao sazonal (dia da semana / mes / fim de semana), que
# generaliza bem para datas futuras porque as categorias ja foram vistas.
COLUNAS_NUMERICAS = ["fim_de_semana"]


def carregar_faturamento_diario(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT Data_Venda, Faturamento FROM vendas",
        conn,
        parse_dates=["Data_Venda"],
    )
    diario = (
        df.groupby(df["Data_Venda"].dt.normalize())["Faturamento"]
        .sum()
        .asfreq("D", fill_value=0)
        .rename("faturamento")
        .reset_index()
        .rename(columns={"Data_Venda": "data"})
    )
    return diario


def construir_features(diario: pd.DataFrame) -> pd.DataFrame:
    df = diario.copy()
    df["dia_semana"] = df["data"].dt.dayofweek.astype(str)
    df["mes"] = df["data"].dt.month.astype(str)
    df["fim_de_semana"] = (df["data"].dt.dayofweek >= 5).astype(int)
    return df


def dividir_treino_teste(dados: pd.DataFrame, dias_teste: int = DIAS_TESTE):
    treino = dados.iloc[:-dias_teste].reset_index(drop=True)
    teste = dados.iloc[-dias_teste:].reset_index(drop=True)
    return treino, teste


def montar_pipeline() -> Pipeline:
    pre_processador = ColumnTransformer(
        transformers=[
            ("categoricas", OneHotEncoder(handle_unknown="ignore"), COLUNAS_CATEGORICAS),
        ],
        remainder="passthrough",
    )
    return Pipeline([
        ("pre", pre_processador),
        ("modelo", LinearRegression()),
    ])


def avaliar(y_real: pd.Series, y_previsto: np.ndarray) -> dict:
    return {
        "mae": round(mean_absolute_error(y_real, y_previsto), 2),
        "rmse": round(mean_squared_error(y_real, y_previsto) ** 0.5, 2),
        "mape": round(mean_absolute_percentage_error(y_real, y_previsto) * 100, 2),
        "r2": round(r2_score(y_real, y_previsto), 3),
    }


def prever_periodo_futuro(modelo: Pipeline, ultima_data: pd.Timestamp, n_dias: int) -> pd.DataFrame:
    datas_futuras = pd.date_range(ultima_data + pd.Timedelta(days=1), periods=n_dias, freq="D")
    futuro = construir_features(pd.DataFrame({"data": datas_futuras}))
    colunas_x = COLUNAS_CATEGORICAS + COLUNAS_NUMERICAS
    futuro["faturamento_previsto"] = modelo.predict(futuro[colunas_x]).clip(min=0)
    return futuro[["data", "faturamento_previsto"]]


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        diario = carregar_faturamento_diario(conn)
    finally:
        conn.close()

    dados = construir_features(diario)
    colunas_x = COLUNAS_CATEGORICAS + COLUNAS_NUMERICAS

    treino, teste = dividir_treino_teste(dados)

    modelo = montar_pipeline()
    modelo.fit(treino[colunas_x], treino["faturamento"])
    previsao_teste = modelo.predict(teste[colunas_x])

    metricas_modelo = avaliar(teste["faturamento"], previsao_teste)
    metricas_baseline = avaliar(teste["faturamento"], np.full(len(teste), treino["faturamento"].mean()))

    resultado_teste = teste[["data", "faturamento"]].copy()
    resultado_teste["faturamento_previsto"] = previsao_teste

    # reajusta com todo o historico para gerar a previsao do proximo mes
    modelo_final = montar_pipeline()
    modelo_final.fit(dados[colunas_x], dados["faturamento"])
    previsao_mensal = prever_periodo_futuro(modelo_final, dados["data"].max(), DIAS_PREVISAO)

    metricas = pd.DataFrame([
        {"modelo": "regressao_linear", **metricas_modelo},
        {"modelo": "baseline_media_historica", **metricas_baseline},
    ])

    metricas.to_csv(REPORTS_DIR / "modelo_metricas.csv", index=False)
    resultado_teste.to_csv(REPORTS_DIR / "modelo_previsao_teste.csv", index=False)
    previsao_mensal.to_csv(REPORTS_DIR / "modelo_previsao_proximo_mes.csv", index=False)

    faturamento_previsto_mes = previsao_mensal["faturamento_previsto"].sum()
    media_mensal_historica = diario.set_index("data")["faturamento"].resample("MS").sum().mean()

    print("=== Modelo preditivo concluido ===")
    print(f"\nPeriodo de treino: {treino['data'].min().date()} a {treino['data'].max().date()} ({len(treino)} dias)")
    print(f"Periodo de teste:  {teste['data'].min().date()} a {teste['data'].max().date()} ({len(teste)} dias)")
    print("\nMetricas (holdout de teste):")
    print(metricas.to_string(index=False))
    print(f"\nFaturamento previsto para {previsao_mensal['data'].min().strftime('%B/%Y')}: "
          f"R$ {faturamento_previsto_mes:,.2f}")
    print(f"Media mensal historica (2025): R$ {media_mensal_historica:,.2f}")
    print(f"\nRelatorios salvos em: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
