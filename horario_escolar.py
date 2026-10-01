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

    print(disciplinas)
    return disciplinas, salas, turmas


@app.cell
def _():
    from ortools.linear_solver import pywraplp

    horario = pywraplp.Solver.CreateSolver('SCIP')

    H = 6 # Horas
    D = 5 # Dias
    return D, H, horario


@app.cell
def _(disciplinas, salas, turmas):
    S = salas.loc[salas["tipo"] == "normal", "quantidade"].sum()
    P = disciplinas.loc[:,"professor"].nunique()
    T = len(turmas)
    return S, T


@app.cell
def _(disciplinas):
    UC = []
    for i in range(len(disciplinas)):
        UC.append(int(disciplinas.loc[i,"carga_semanal"]))
    return (UC,)


@app.cell
def _(D, H, S, T, UC, horario):
    x = {}

    for turma in range(T):
        x[turma] = {}
        for disciplina in range(len(UC)):
            x[turma][disciplina] = {}
            for dia in range(D):
                x[turma][disciplina][dia] = {}
                for hora in range(H):
                    x[turma][disciplina][dia][hora] = {}
                    for sala in range(S):
                        x[turma][disciplina][dia][hora][sala] = horario.IntVar(0,1,'x_%i_%i_%i_%i_%i' % (turma,disciplina,dia,hora,sala))

    def X(t,uc,d,h,s):              # abreviatura
        return x[t][uc][d][h][s]

    return (X,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Restrição
    ## R1. Uma turma não pode ter duas aulas em simultâneo.
    """)
    return


@app.cell
def _(D, H, S, T, UC, X, horario):
    for turma_r1 in range(T):
        for dia_r1 in range(D):
            for hora_r1 in range(H):
                horario.Add(sum([X(turma_r1,uc_r1,dia_r1,hora_r1,s_r1) for uc_r1 in range(len(UC)) for s_r1 in range(S)])<= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R2. Cada disciplina cumpre exatamente a carga semanal definida em disciplinas.csv, para cada turma.
    """)
    return


@app.cell
def _(D, H, S, T, UC, X, horario):
    for turma_r2 in range(T):
        for uc_r2 in range(len(UC)):
            horario.Add(sum([X(turma_r2,uc_r2,d_r2,h_r2,s_r2) for d_r2 in range(D) for h_r2 in range(H) for s_r2 in range(S)]) == UC[uc_r2])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R3. No máximo uma aula da mesma disciplina por dia, por turma — exceto disciplinas de duplo período (ver R4), em que o bloco de 2 tempos conta como uma só ocorrência nesse dia.
    """)
    return


@app.cell
def _(D, H, S, T, UC, X, disciplinas, horario):
    for turma_r3 in range(T):
        for uc_r3 in range(len(UC)):
            if disciplinas.loc[uc_r3,"duplo_periodo"] == "nao":
                for d_r3 in range(D):
                    for h_r3 in range(H):
                        horario.Add(sum([X(turma_r3,uc_r3,d_r3,h_r3,s_r3) for s_r3 in range(S)]) <= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
 
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R4. Disciplinas marcadas duplo_periodo=sim só podem ser dadas em blocos de 2 tempos consecutivos, no mesmo dia (nunca um tempo isolado).
    """)
    return


@app.cell
def _(D, H, S, T, UC, X, disciplinas, horario):
    for turma_r4 in range(T):
        for uc_r4 in range(len(UC)):
            if disciplinas.loc[uc_r4, "duplo_periodo"] == "sim":
                for d_r4 in range(D):
                
                    # 1. Garantir consecutividade entre os tempos h
                    for h_r4 in range(H):
                        aulas_atual = sum([X(turma_r4, uc_r4, d_r4, h_r4, s) for s in range(S)])
                    
                        if h_r4 == 0:
                            # Se h=0, exige aula em h=1
                            aulas_prox = sum([X(turma_r4, uc_r4, d_r4, 1, s) for s in range(S)])
                            horario.Add(aulas_atual <= aulas_prox)
                        
                        elif h_r4 == H - 1:
                            # Se é o último slot, exige aula em h=H-2
                            aulas_ant = sum([X(turma_r4, uc_r4, d_r4, H - 2, s) for s in range(S)])
                            horario.Add(aulas_atual <= aulas_ant)
                        
                        else:
                            # Slot intermédio: exige aula em h-1 OU h+1
                            aulas_ant = sum([X(turma_r4, uc_r4, d_r4, h_r4 - 1, s) for s in range(S)])
                            aulas_prox = sum([X(turma_r4, uc_r4, d_r4, h_r4 + 1, s) for s in range(S)])
                            horario.Add(aulas_atual <= aulas_ant + aulas_prox)

                    # 2. Impedir blocos com mais de 2 tempos no mesmo dia (opcional, se cada bloco for max 2h)
                    total_horas_dia = sum([X(turma_r4, uc_r4, d_r4, h, s) for h in range(H) for s in range(S)])
                    horario.Add(total_horas_dia <= 2)
    return


if __name__ == "__main__":
    app.run()
