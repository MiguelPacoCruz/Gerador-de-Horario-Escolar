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
    path3 = "dados_v3/"

    arg = path3

    disciplinas = pd.read_csv(arg+"disciplinas.csv")
    excecoes = pd.read_csv(arg+"disponibilidade_excecoes.csv")
    salas = pd.read_csv(arg+"salas.csv")
    turmas = pd.read_csv(arg+"turmas.csv")
    return disciplinas, excecoes, pd, salas, turmas


@app.cell
def _():
    from ortools.linear_solver import pywraplp

    horario = pywraplp.Solver.CreateSolver('SCIP')

    H = 6 # Horas
    D = 5 # Dias
    return D, H, horario, pywraplp


@app.cell
def _(disciplinas, salas, turmas):
    S = sum(salas.loc[:,"quantidade"])
    P = disciplinas.loc[:,"professor"].nunique()
    T = len(turmas)
    return S, T


@app.cell
def _(excecoes):
    dM = {"Seg":0, "Ter":1, "Qua":2, "Qui":3, "Sex":4}

    exc = {}
    for k in range(len(excecoes)):
        p_exc = excecoes.loc[k,"professor"]
        if p_exc not in exc:
            exc[p_exc] = []
        exc[p_exc].append((dM[excecoes.loc[k,"dia"]],int(excecoes.loc[k,"periodo"])))
    return (exc,)


@app.cell
def _(disciplinas):
    CS = []
    lUC = disciplinas.loc[:,"disciplina"].nunique()
    for i in range(lUC):
        CS.append(int(disciplinas.loc[i,"carga_semanal"]))

    prof = {}

    for i in range(lUC):
        p = disciplinas.loc[i,"professor"]
        if p not in prof:
            prof[p] = []
        prof[p].append(i)
    return CS, lUC, prof


@app.cell
def _(salas):
    # Dá map do tipo da sala (por index) ao número da sala
    salaNum = {}
    counter = 0

    for i4 in range(len(salas)):
        if i4 not in salaNum:
            salaNum[i4] = []

        quantidade = salas.loc[i4,"quantidade"]

        for k3 in range(quantidade):
            salaNum[i4].append(counter)
            counter += 1

    return (salaNum,)


@app.cell
def _(disciplinas, lUC, pd, salas):
    tipoSala = {}
    for i2 in range(lUC):
        se = disciplinas.loc[i2,"sala_especial"]
        if pd.isna(se):
            tipoSala[i2] = 0#salas.index[pd.isna(salas["sala"])][0]
        else:
            tipoSala[i2]= salas.index[salas["sala"] == se][0]
    return (tipoSala,)


@app.cell
def _(salaNum, tipoSala):
    print(salaNum)
    print(tipoSala)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Professores por disciplina
    """)
    return


@app.cell
def _(disciplinas):
    profporUcs = {}
    for i3 in range(len(disciplinas)):
        uc_p = disciplinas.loc[i3,"disciplina"]
        if uc_p not in profporUcs:
            profporUcs[uc_p] = []
        profporUcs[uc_p].append(disciplinas.loc[i3,"professor"])

    print(profporUcs)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    A alterar na matriz: salas - de tipo para tipo e numero
        - (tipo,numero) Ex: (0,3), (1,0)
        - numero, [0-12] 0-8 normal, 9-10, laboratorio, 11-12 ginasio (X)

    Adicionar professor para que possamos ter mais que 1 professor por disciplina
    """)
    return


@app.cell
def _(D, H, S, T, horario, lUC):
    x = {}

    for turma in range(T):
        x[turma] = {}
        for disciplina in range(lUC):
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
def _(D, H, S, T, X, horario, lUC):
    for turma_r1 in range(T):
        for dia_r1 in range(D):
            for hora_r1 in range(H):
                horario.Add(sum([X(turma_r1,uc_r1,dia_r1,hora_r1,s_r1) for uc_r1 in range(lUC) for s_r1 in range(S)])<= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R2. Cada disciplina cumpre exatamente a carga semanal definida em disciplinas.csv, para cada turma.
    """)
    return


@app.cell
def _(CS, D, H, S, T, X, horario, lUC):
    for turma_r2 in range(T):
        for uc_r2 in range(lUC):
            horario.Add(sum([X(turma_r2,uc_r2,d_r2,h_r2,s_r2) for d_r2 in range(D) for h_r2 in range(H) for s_r2 in range(S)]) == CS[uc_r2])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R3. No máximo uma aula da mesma disciplina por dia, por turma — exceto disciplinas de duplo período (ver R4), em que o bloco de 2 tempos conta como uma só ocorrência nesse dia.
    """)
    return


@app.cell
def _(D, H, S, T, X, disciplinas, horario, lUC):
    for turma_r3 in range(T):
        for uc_r3 in range(lUC):
            if disciplinas.loc[uc_r3,"duplo_periodo"] == "nao":
                for d_r3 in range(D):
                    horario.Add(sum([X(turma_r3,uc_r3,d_r3,h_r3,s_r3) for s_r3 in range(S) for h_r3 in range(H)]) <= 1)
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
def _(D, H, S, T, X, disciplinas, horario, lUC):
    for turma_r4 in range(T):
        for uc_r4 in range(lUC):
            if disciplinas.loc[uc_r4, "duplo_periodo"] == "sim":
                for d_r4 in range(D):

                    # 1. Garantir consecutividade NA MESMA SALA s
                    for s in range(S):
                        for h_r4 in range(H):
                            aula_atual = X(turma_r4, uc_r4, d_r4, h_r4, s)

                            if h_r4 == 0:
                                # Se está no 1º tempo, a continuação DEVE ser no tempo 1 NA MESMA SALA s
                                aula_prox = X(turma_r4, uc_r4, d_r4, 1, s)
                                horario.Add(aula_atual <= aula_prox)

                            elif h_r4 == H - 1:
                                # Se está no último tempo, o início DEVE ser no tempo H-2 NA MESMA SALA s
                                aula_ant = X(turma_r4, uc_r4, d_r4, H - 2, s)
                                horario.Add(aula_atual <= aula_ant)

                            else:
                                # Tempo intermédio: exige que a mesma sala s seja usada em h-1 OU h+1
                                aula_ant = X(turma_r4, uc_r4, d_r4, h_r4 - 1, s)
                                aula_prox = X(turma_r4, uc_r4, d_r4, h_r4 + 1, s)
                                horario.Add(aula_atual <= aula_ant + aula_prox)

                    # 2. Limite de 2 horas no dia (considerando todas as salas)
                    total_horas_dia = sum([
                        X(turma_r4, uc_r4, d_r4, h, s) 
                        for h in range(H) 
                        for s in range(S)
                    ])
                    horario.Add(total_horas_dia <= 2)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R5. Um professor não pode dar duas aulas em simultâneo, mesmo que sejam a turmas ou disciplinas diferentes.
    """)
    return


@app.cell
def _(D, H, S, T, X, horario, prof):
    for prof_nome, ucs_do_prof in prof.items():
        for d_r5 in range(D):
            for h_r5 in range(H):
                horario.Add(sum([X(t_r5, uc_r5, d_r5, h_r5, s_r5) for uc_r5 in ucs_do_prof for t_r5 in range(T) for s_r5 in range(S)]) <= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R6. Um professor só pode dar aulas nos tempos em que está disponível (disponibilidade_excecoes.csv).
    """)
    return


@app.cell
def _(S, T, X, exc, horario, prof):
    for prof_nome_r6, excecoes_prof_r6 in exc.items():
        for dia_exc_r6, hora_exc_r6 in excecoes_prof_r6:
            ucs_do_prof_r6 = prof[prof_nome_r6]
            for uc_r6 in ucs_do_prof_r6:
                horario.Add(sum([X(t_r6, uc_r6, dia_exc_r6, hora_exc_r6, s_r6) for t_r6 in range(T) for s_r6 in range(S)]) == 0)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R7. Cada aula ocupa uma sala. Disciplinas com sala_especial só podem usar salas desse tipo; as restantes usam salas normal. Em nenhum tempo o número de aulas a decorrer num tipo de sala pode exceder a quantidade desse tipo definida em salas.csv.
    """)
    return


@app.cell
def _(salaNum, tipoSala):
    print(tipoSala)
    print(salaNum)
    return


@app.cell
def _(D, H, S, T, X, horario, lUC, salaNum, tipoSala):
    # 1. Garantir que a UC só usa o tipo de sala permitido
    for t1_r7 in range(T):
        for uc1_r7 in range(lUC):
            sala_exigida = tipoSala[uc1_r7]
            for d1_r7 in range(D):
                for h1_r7 in range(H):
                    for s1_r7 in range(S):
                        if s1_r7 not in salaNum[sala_exigida]:
                            horario.Add(X(t1_r7, uc1_r7, d1_r7, h1_r7, s1_r7) == 0)

    # 2. Apenas 1 aula por sala em simultâneo
    for d2_r7 in range(D):
        for h2_r7 in range(H):
            for s2_r7 in range(S):
                horario.Add(sum([X(t2_r7, uc2_r7, d2_r7, h2_r7, s2_r7) for t2_r7 in range(T) for uc2_r7 in range(lUC)]) <= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## O1. Minimizar o número total de "buracos" no horário de cada professor — um buraco é um tempo livre, no meio do dia, entre a primeira e a última aula desse professor nesse dia.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Correr o solver
    """)
    return


@app.cell
def _(pywraplp):
    def obter_solucao(horario, X, turmas, disciplinas, salas, T, lUC, D, H, S):
        status = horario.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            print("Solução ótima encontrada!")
        elif status == pywraplp.Solver.FEASIBLE:
            print("Foi encontrada uma solução viável.")
        else:
            print("Não foi encontrada nenhuma solução.")
            return []

        solucao = []

        for t in range(T):
            for uc in range(lUC):
                for d in range(D):
                    for h in range(H):
                        for s in range(S):
                            if X(t, uc, d, h, s).solution_value() == 1:
                                solucao.append({
                                    "turma": turmas.loc[t, "turma"],
                                    "disciplina": disciplinas.loc[uc, "disciplina"],
                                    "professor": disciplinas.loc[uc, "professor"],
                                    "dia": d,
                                    "hora": h,
                                    "sala": s,
                                })

        return solucao

    return (obter_solucao,)


@app.cell
def _(D, H, S, T, X, disciplinas, horario, lUC, obter_solucao, salas, turmas):
    solucao = obter_solucao(
        horario,
        X,
        turmas,
        disciplinas,
        salas,
        T,
        lUC,
        D,
        H,
        S,
    )
    return (solucao,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Representação dos dados
    """)
    return


@app.cell
def _(mo, pd):
    def preparar_horario(solucao):
        return (
            pd.DataFrame(solucao)
            .sort_values(["dia", "hora"])
            .reset_index(drop=True)
        )


    def obter_turmas(horario_df):
        return sorted(horario_df["turma"].unique())


    def obter_professores(horario_df):
        return sorted(horario_df["professor"].unique())


    def criar_dropdown(opcoes, label):
        return mo.ui.dropdown(
            options=opcoes,
            value=opcoes[0],
            label=label,
        )


    def criar_grelha(df, texto, D, H, dias_nomes, horas_nomes):
        df = df.copy()
        df["celula"] = df.apply(texto, axis=1)

        grelha = df.pivot_table(
            index="hora",
            columns="dia",
            values="celula",
            aggfunc=lambda x: " / ".join(x),
        )

        grelha = (
            grelha
            .reindex(index=range(H), columns=range(D))
            .fillna("")
        )

        grelha.index = horas_nomes
        grelha.columns = dias_nomes
        grelha.index.name = "Hora"

        return grelha.reset_index()


    def criar_grelha_turma(horario_df, turma, D, H, dias_nomes, horas_nomes):
        df = horario_df[horario_df["turma"] == turma]

        return criar_grelha(
            df,
            lambda r: f"{r['disciplina']} ({r['sala']}) - {r['professor']}",
            D,
            H,
            dias_nomes,
            horas_nomes,
        )


    def criar_grelha_professor(horario_df, professor, D, H, dias_nomes, horas_nomes):
        df = horario_df[horario_df["professor"] == professor]

        return criar_grelha(
            df,
            lambda r: f"{r['disciplina']} ({r['sala']}) - {r['turma']}",
            D,
            H,
            dias_nomes,
            horas_nomes,
        )


    def criar_tabela(grelha_df, H):
        return mo.ui.table(
            grelha_df,
            selection=None,
            page_size=H,
        )

    return (
        criar_grelha_professor,
        criar_grelha_turma,
        criar_tabela,
        obter_professores,
        obter_turmas,
        preparar_horario,
    )


@app.cell(hide_code=True)
def _(mo, obter_professores, obter_turmas, preparar_horario, solucao):
    # Cell 1
    if solucao:
        horario_df = preparar_horario(solucao)
        lista_turmas = obter_turmas(horario_df)
        lista_professores = obter_professores(horario_df)

        default_turma = lista_turmas[0] if lista_turmas else None
        default_prof = lista_professores[0] if lista_professores else None

        # Use mo.ui.dropdown directly
        turmaUi = mo.ui.dropdown(options=lista_turmas, value=default_turma, label="Turma")
        professorUi = mo.ui.dropdown(options=lista_professores, value=default_prof, label="Professor")
    else:
        horario_df = None
        turmaUi = None
        professorUi = None

    # Avoid checking `if turmaUi:`, check `if turmaUi is not None:` instead
    mo.vstack([turmaUi, professorUi]) if turmaUi is not None else mo.md("⚠️ Sem solução disponível")
    return horario_df, professorUi, turmaUi


@app.cell(hide_code=True)
def _(
    D,
    H,
    criar_grelha_professor,
    criar_grelha_turma,
    criar_tabela,
    horario_df,
    mo,
    professorUi,
    turmaUi,
):
    # Cell 2
    def render_horarios():
        # Explicitly check for None instead of truthiness
        if horario_df is None or turmaUi is None or professorUi is None:
            return mo.md("A aguardar solução...")
    
        if turmaUi.value is None or professorUi.value is None:
            return mo.md("Selecione uma turma e um professor.")

        dias_nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
        horas_nomes = [f"{8 + h}:00" for h in range(H)]

        grelha_turma_df = criar_grelha_turma(
            horario_df,
            turmaUi.value,
            D,
            H,
            dias_nomes,
            horas_nomes,
        )

        grelha_professor_df = criar_grelha_professor(
            horario_df,
            professorUi.value,
            D,
            H,
            dias_nomes,
            horas_nomes,
        )

        tabela_turma = criar_tabela(grelha_turma_df, H)
        tabela_professor = criar_tabela(grelha_professor_df, H)

        return mo.vstack([
            mo.md("### Horário da Turma"),
            tabela_turma,
            mo.md("### Horário do Professor"),
            tabela_professor,
        ])

    render_horarios()
    return


if __name__ == "__main__":
    app.run()
