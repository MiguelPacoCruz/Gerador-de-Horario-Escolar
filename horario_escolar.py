import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
 
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Pretendemos gerar o horário semanal de uma escola, dadas as turmas, discplinas com o professor atribuido, carga, se é aula dupla (duplo_periodo) e necessidade de sala_especial. O tipo e quantidade
    de salas, e as exceções de disponibilidade dos professores.

    Vamos abordar isto com programação inteira, usando o solver usado na aula para a ficha 3.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    As constantes, ao contrário da ficha 3, não estarão todas "hardcoded", pois algumas são afetadas pelo input.
    """)
    return


@app.cell
def _():
    import pandas as pd

    path = "dados/"
    path2 = "dados_v2/"

    disciplinas = pd.read_csv(path+"disciplinas.csv")
    excecoes = pd.read_csv(path+"disponibilidade_excecoes.csv")
    salas = pd.read_csv(path+"salas.csv")
    turmas = pd.read_csv(path+"turmas.csv")
    return disciplinas, salas, turmas


@app.cell
def _():
    from ortools.linear_solver import pywraplp

    horario = pywraplp.Solver.CreateSolver('SCIP')

    H = 6 # Horas
    D = 5 # Dias
    return


@app.cell
def _(disciplinas, salas, turmas):
    S = salas.loc[salas["tipo"] == "normal", "quantidade"].sum()
    P = disciplinas.loc[:,"professor"].nunique()
    T = len(turmas)
    return


if __name__ == "__main__":
    app.run()
