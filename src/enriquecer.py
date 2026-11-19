"""
Enriquece o clima diario (NASA POWER) com as internacoes do mes (SIH/SUS).

O QUE ESTE SCRIPT RESOLVE
=========================
O clima e as internacoes estao em tabelas separadas. Para comparar
os dois, eles precisam ficar lado a lado. Enriquecer e trazer para
perto o que estava separado. Nao se cria dado aqui.

A ORDEM DO MERGE IMPORTA
========================
A NASA fica a esquerda porque e a tabela mais fina, com uma linha
por dia. O SIH/SUS tem uma linha por mes. O resultado assume o grao
da tabela mais fina: uma linha por dia, com as internacoes do mes
repetidas em cada dia daquele mes.

Por isso, NAO some as colunas de internacoes nesta tabela: cada mes
apareceria cerca de 30 vezes. O resumo por mes e feito na Ouro.

Como executar, a partir da raiz do projeto:
    python src/enriquecer.py
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

import juncao

PRATA = Path("dados/prata")

CLIMA = PRATA / "nasa_power.parquet"
INTERNACOES = PRATA / "sih_sus.parquet"
DESTINO = PRATA / "clima_internacoes.parquet"

CHAVE_CLIMA = "MES"
CHAVE_INTERNACOES = "PERIODO"


def carregar():
    clima = pd.read_parquet(CLIMA)
    internacoes = pd.read_parquet(INTERNACOES)
    print("clima      :", clima.shape)
    print("internacoes:", internacoes.shape)
    print()
    return clima, internacoes


def criar_chave_mes(clima):
    """Cria a coluna MES na NASA: o primeiro dia do mes de cada data.

    O SIH/SUS guarda o mes em PERIODO, sempre no dia 1. Para os dois
    casarem, o conteudo precisa ser igual, mesmo com nomes diferentes.
    Exemplo: 15/01/2010 vira MES = 01/01/2010.
    """
    clima[CHAVE_CLIMA] = clima["DATA"].dt.to_period("M").dt.to_timestamp()
    return clima


def registrar(resultado, sem_par, antes, so_internacoes):
    info = {
        "origem_esquerda": CLIMA.name,
        "origem_direita": INTERNACOES.name,
        "arquivo_prata": DESTINO.name,
        "chave": f"{CHAVE_CLIMA} = {CHAVE_INTERNACOES}",
        "tipo_de_juncao": "left",
        "linhas_esquerda": antes,
        "linhas_resultado": len(resultado),
        "linhas_sem_par": len(sem_par),
        "meses_so_nas_internacoes": [m.strftime("%Y-%m") for m in sorted(so_internacoes)],
        "atributos_derivados": [],
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
    print("proveniencia:", caminho)
    return info


def main():
    clima, internacoes = carregar()
    clima = criar_chave_mes(clima)

    # 1. Conferir as chaves ANTES de juntar.
    #    Estes numeros sao a previsao do que a juncao vai fazer.
    _, so_internacoes, _ = juncao.conferir_chaves(
        clima, internacoes, CHAVE_CLIMA, CHAVE_INTERNACOES
    )
    print()

    # 2. Juntar mantendo tudo do clima.
    #    Muitos dias para um mes: many_to_one.
    antes = len(clima)
    resultado = juncao.juntar(
        clima, internacoes, CHAVE_CLIMA, CHAVE_INTERNACOES, relacao="many_to_one"
    )

    # 3. Validar. A funcao devolve justamente o que nao casou.
    sem_par = juncao.validar(clima, resultado, CHAVE_INTERNACOES)
    print()

    # 4. Quem nao casou do outro lado.
    #    Com left, os meses que so existem nas internacoes nao entram
    #    no resultado, entao validar() nao os ve. Eles vieram do passo 1.
    if so_internacoes:
        print("meses do SIH/SUS sem clima (fora do resultado):")
        print([m.strftime("%Y-%m") for m in sorted(so_internacoes)])
        print()

    # PERIODO e igual a MES depois da juncao; fica so uma das duas.
    resultado = resultado.drop(columns=CHAVE_INTERNACOES)

    # 5. Atributo que so existe depois da juncao: pendente.
    #    No grao diario, qualquer conta que misture o clima do dia com
    #    as internacoes do mes inventaria um valor por dia. Ver README.

    resultado.to_parquet(DESTINO, index=False)
    print("salvo em:", DESTINO, resultado.shape)

    registrar(resultado, sem_par, antes, so_internacoes)


if __name__ == "__main__":
    main()
