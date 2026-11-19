"""
Funcoes de juncao que servem a qualquer par de tabelas.

POR QUE UM MODULO NOVO, E NAO MAIS CODIGO NO limpeza.py
=======================================================
O criterio da aula passada foi: se a funcao menciona uma fonte,
fica no script dela; se nao menciona, vai para o modulo.

Agora aparece um segundo criterio. O limpeza.py trata de uma
tabela por vez. Estas funcoes tratam da relacao entre duas. Sao
assuntos diferentes, entao sao modulos diferentes.

Modulo nao e deposito de tudo que e generico. E um conjunto de
funcoes que falam do mesmo assunto.

LOG
===
Este modulo so cria o seu logger; quem liga o log (configurar_log)
e o pipeline.py ou o script que chamou. Por isso nao importa config:
fica na base da hierarquia, sem saber quem esta em cima.

Coloque este arquivo em src e importe com:
    import juncao
"""

import logging

log = logging.getLogger(__name__)


def conferir_chaves(esquerda, direita, col_esq, col_dir):
    """Compara as chaves ANTES de juntar.

    Devolve os tres conjuntos e registra o tamanho de cada um.
    Esses numeros sao a previsao do que a juncao vai fazer:
    anote-os e compare depois.

    Conferir aqui e barato. Depois da juncao fica caro, porque
    voce ja nao distingue quem nao casou de quem casou trazendo
    valor ausente.
    """
    esq = set(esquerda[col_esq].dropna())
    dir_ = set(direita[col_dir].dropna())

    so_esquerda = esq - dir_
    so_direita = dir_ - esq
    nos_dois = esq & dir_

    log.info(
        "chaves: so em %s=%d, so em %s=%d, nos dois=%d",
        col_esq, len(so_esquerda), col_dir, len(so_direita), len(nos_dois),
    )

    if so_esquerda:
        log.info("exemplos so na esquerda: %s", [str(c) for c in sorted(so_esquerda)[:5]])
    if so_direita:
        log.info("exemplos so na direita: %s", [str(c) for c in sorted(so_direita)[:5]])

    return so_esquerda, so_direita, nos_dois


def juntar(esquerda, direita, col_esq, col_dir, relacao="many_to_one"):
    """Junta mantendo todas as linhas da esquerda.

    how='left' de proposito. O que nao casar vira linha com valor
    ausente, e e justamente isso que voce quer ver. Comecar por
    'inner' e apagar o relatorio de erro antes de ler.

    validate declara a relacao esperada entre as tabelas. Se a
    sua expectativa estiver errada, o pandas levanta erro em vez
    de devolver uma tabela inflada em silencio.

        many_to_one  muitas linhas da esquerda para uma da direita
        one_to_one   uma para uma
        one_to_many  uma para muitas
    """
    return esquerda.merge(
        direita,
        left_on=col_esq,
        right_on=col_dir,
        how="left",
        validate=relacao,
    )


def validar(esquerda, resultado, coluna_da_direita):
    """Confere a conta e devolve o que nao casou.

    Tres perguntas, nesta ordem:
      o resultado tem menos linhas?  usou inner e perdeu dado
      o resultado tem mais linhas?   a chave repete na direita
      o resultado tem o mesmo numero? a chave era unica, como
                                      voce esperava

    O retorno sao as linhas sem par. Esse pedaco e o material do
    README: quem nao casou, e por que.
    """
    sem_par = resultado[coluna_da_direita].isna()

    log.info(
        "linhas: esquerda=%d, resultado=%d, sem par=%d",
        len(esquerda), len(resultado), int(sem_par.sum()),
    )

    if len(resultado) < len(esquerda):
        log.warning("o resultado perdeu linhas. Juncao do tipo errado?")
    elif len(resultado) > len(esquerda):
        log.warning("o resultado ganhou linhas. A chave repete na direita.")

    return resultado[sem_par]