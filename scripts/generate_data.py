"""
gera o dataset simulado de e-commerce (bruto)

produz um CSV com >= 5.000 linhas contendo "sujeira" proposital
(nulos, duplicados, formatos inconsistentes de data/moeda/texto) 
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

N_LINHAS = 6000
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "ecom_data.csv"

PRODUTOS = {
    "Eletrônicos": ["Smartphone X10", "Notebook Prime", "Fone Bluetooth", "Smart TV 50\"", "Caixa de Som"],
    "Moda": ["Camiseta Básica", "Calça Jeans", "Jaqueta Corta-Vento", "Tênis Esportivo", "Vestido Casual"],
    "Casa": ["Jogo de Panelas", "Aspirador de Pó", "Liquidificador", "Kit Cama", "Luminária LED"],
    "Livros": ["Romance Best-Seller", "Livro Técnico Python", "Quadrinho Clássico", "Biografia", "Livro Infantil"],
    "Esporte": ["Bicicleta Aro 29", "Halteres 5kg", "Bola de Futebol", "Corda de Pular", "Tapete de Yoga"],
}

CIDADES_ESTADOS = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Curitiba", "PR"), ("Porto Alegre", "RS"), ("Salvador", "BA"),
    ("Recife", "PE"), ("Fortaleza", "CE"), ("Brasília", "DF"), ("Manaus", "AM"),
]

METODOS_PAGAMENTO = ["Cartao de Credito", "cartao de credito", "PIX", "pix", "Boleto", "Cartao de Debito"]
STATUS_PEDIDO = ["Concluido", "concluido", "Cancelado", "Em Processamento", "Devolvido"]

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)


def data_aleatoria_formatada() -> str:
    delta_dias = (END_DATE - START_DATE).days
    data = START_DATE + timedelta(days=random.randint(0, delta_dias))
    formato = random.choice(DATE_FORMATS)
    return data.strftime(formato)


def valor_formatado(valor: float) -> str:
    """Simula inconsistência de moeda: às vezes 'R$ 1.234,56', às vezes '1234.56'."""
    estilo = random.random()
    if estilo < 0.4:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{valor:.2f}"


def gerar_linha(transacao_id: int) -> dict:
    categoria = random.choice(list(PRODUTOS.keys()))
    produto = random.choice(PRODUTOS[categoria])
    cidade, estado = random.choice(CIDADES_ESTADOS)
    quantidade = random.randint(1, 5)
    valor_unitario = round(random.uniform(15, 3500), 2)

    # ~3% de nulos espalhados em colunas não críticas
    cliente_id = f"CLI{random.randint(1, 1200):05d}"
    if random.random() < 0.02:
        cliente_id = None

    quantidade_val = quantidade
    if random.random() < 0.015:
        quantidade_val = None

    metodo_pagamento = random.choice(METODOS_PAGAMENTO)
    if random.random() < 0.02:
        metodo_pagamento = None

    localidade = f"{cidade}/{estado}/Brasil" if random.random() > 0.3 else f"{cidade.upper()} - {estado}"

    return {
        "ID_Transacao": f"TRX{transacao_id:06d}",
        "Data_Venda": data_aleatoria_formatada(),
        "ID_Cliente": cliente_id,
        "Nome_Produto": produto,
        "Categoria_Produto": categoria if random.random() > 0.1 else categoria.upper(),
        "Valor_Unitario": valor_formatado(valor_unitario),
        "Quantidade": quantidade_val,
        "Localidade_Venda": localidade,
        "Metodo_Pagamento": metodo_pagamento,
        "Status_Pedido": random.choice(STATUS_PEDIDO),
    }


def main():
    linhas = [gerar_linha(i) for i in range(1, N_LINHAS + 1)]
    df = pd.DataFrame(linhas)

    # injeta duplicados propositais (~2%)
    duplicatas = df.sample(frac=0.02, random_state=42)
    df = pd.concat([df, duplicatas], ignore_index=True)

    df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # embaralha

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset bruto gerado: {OUTPUT_PATH} ({len(df)} linhas)")


if __name__ == "__main__":
    main()
