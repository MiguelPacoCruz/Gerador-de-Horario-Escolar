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
    from ortools.linear_solver import pywraplp

    horario = pywraplp.Solver.CreateSolver('SCIP')

    H = 5 # Horas (5 tempos por dia, como no enunciado)
    D = 5 # Dias
    return D, H, horario, pywraplp


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
def _(disciplinas, salas, turmas):
    S = sum(salas.loc[:,"quantidade"])
    professores = disciplinas.loc[:,"professor"].unique().tolist()
    P = len(professores)
    T = len(turmas)
    return P, S, T, professores


@app.cell
def _(excecoes, professores):
    dM = {"Seg":0, "Ter":1, "Qua":2, "Qui":3, "Sex":4}

    exc = {} ## Prof(str): (Dia(int), Hora(int))
    for k in range(len(excecoes)):
        p_exc = professores.index(excecoes.loc[k,"professor"])
        if p_exc not in exc:
            exc[p_exc] = []
        exc[p_exc].append((dM[excecoes.loc[k,"dia"]],int(excecoes.loc[k,"periodo"])-1))  # no CSV o periodo é 1..5
    return (exc,)


@app.cell
def _(disciplinas, professores):
    #Definir ucs por index
    ucs = disciplinas["disciplina"].unique().tolist()

    profporUcs = {}
    for i3 in range(len(disciplinas)):
        uc_p = ucs.index(disciplinas.loc[i3,"disciplina"])
        if uc_p not in profporUcs:
            profporUcs[uc_p] = []
        profporUcs[uc_p].append(professores.index(disciplinas.loc[i3,"professor"]))

    cargaSemanalUC = []
    lUC = len(ucs)
    for uc in ucs:
        carga = disciplinas[disciplinas["disciplina"] == uc]["carga_semanal"].iloc[0]
        cargaSemanalUC.append(int(carga))

    ucsporProf = {}

    for i in range(lUC):
        p = professores.index(disciplinas.loc[i,"professor"])
        if p not in ucsporProf:
            ucsporProf[p] = []
        ucsporProf[p].append(i)
    return cargaSemanalUC, lUC, profporUcs, ucs, ucsporProf


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
            tipoSala[i2] = salas.index[salas["tipo"] == "normal"][0]
        else:
            tipoSala[i2]= salas.index[salas["sala"] == se][0]
    return (tipoSala,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    A alterar na matriz: salas - de tipo para tipo e numero
        - (tipo,numero) Ex: (0,3), (1,0)
        - numero, [0-12] 0-8 normal, 9-10, laboratorio, 11-12 ginasio (X)

    Adicionar professor para que possamos ter mais que 1 professor por disciplina
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Modelação

    Índices: turmas $t<T$, disciplinas $u<U$, professores $p<P$, dias $d<D$, horas $h<H$, salas $s<S$.

    Parâmetros (vêm dos CSV): $c_u$ é a carga semanal da disciplina $u$ (`carga_semanal`); $\mathit{dup}_u\in\{0,1\}$ indica se é de duplo período;
    $\mathit{Prof}_u$ é o conjunto de professores da disciplina $u$ (`profporUcs`); $\mathit{Sal}_u$ é o conjunto de salas que $u$ pode usar (`salaNum[tipoSala[u]]`);
    $\mathit{Exc}\subseteq P\times D\times H$ são os tempos em que um professor está indisponível (`exc`).

    Variáveis:

    $$x_{t,u,p,d,h,s}=1 \quad \mbox{se e só se} \quad \mbox{a turma $t$ tem a disciplina $u$ com o professor $p$, no dia $d$, à hora $h$, na sala $s$.}$$

    Classificação das restrições: R0, R6 e R7 (tipo de sala) são *proibições* (fixam variáveis a 0); R1, R3, R5 e R7 (uma aula por sala) são *limitações* (máximos);
    R2 é uma *obrigação* (mínimo/igualdade); R4 liga variáveis entre si.
    """)
    return


@app.cell
def _(D, H, P, S, T, horario, lUC):
    x = {}

    for turma in range(T):
        x[turma] = {}
        for disciplina in range(lUC):
            x[turma][disciplina] = {}
            for professor in range(P):
                x[turma][disciplina][professor] = {}
                for dia in range(D):
                    x[turma][disciplina][professor][dia] = {}
                    for hora in range(H):
                        x[turma][disciplina][professor][dia][hora] = {}
                        for sala in range(S):
                            x[turma][disciplina][professor][dia][hora][sala] = horario.IntVar(0,1,'x_%i_%i_%i_%i_%i_%i' % (turma,disciplina,professor,dia,hora,sala))

    def X(t,uc,p,d,h,s):              # abreviatura
        return x[t][uc][p][d][h][s]

    return (X,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Restrição

    ## R0. O professor leciona as disciplinas dele.

    $$\forall_{t<T}\cdot\forall_{u<U}\cdot\forall_{p\notin \mathit{Prof}_u}\cdot \quad \sum_{d<D,\,h<H,\,s<S} x_{t,u,p,d,h,s}=0$$
    """)
    return


@app.cell
def _(D, H, P, S, T, X, horario, lUC, profporUcs):
    for turma_r0 in range(T):
        for uc_r0 in range(lUC):
            for prof_r0 in range(P):
                if prof_r0 not in profporUcs[uc_r0]:
                    horario.Add(sum([X(turma_r0,uc_r0,prof_r0,dia_r0,hora_r0,s_r0) for dia_r0 in range(D) for hora_r0 in range(H) for s_r0 in range(S)]) == 0)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R1. Uma turma não pode ter duas aulas em simultâneo.

    $$\forall_{t<T}\cdot\forall_{d<D}\cdot\forall_{h<H}\cdot \quad \sum_{u<U,\,p<P,\,s<S} x_{t,u,p,d,h,s}\leq 1$$
    """)
    return


@app.cell
def _(D, H, P, S, T, X, horario, lUC):
    for turma_r1 in range(T):
        for dia_r1 in range(D):
            for hora_r1 in range(H):
                horario.Add(sum([X(turma_r1,uc_r1,prof_r1,dia_r1,hora_r1,s_r1) for uc_r1 in range(lUC) for prof_r1 in range(P) for s_r1 in range(S)])<= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R2. Cada disciplina cumpre exatamente a carga semanal definida em disciplinas.csv, para cada turma.

    $$\forall_{t<T}\cdot\forall_{u<U}\cdot \quad \sum_{p<P,\,d<D,\,h<H,\,s<S} x_{t,u,p,d,h,s}=c_u$$
    """)
    return


@app.cell
def _(D, H, P, S, T, X, cargaSemanalUC, horario, lUC):
    for turma_r2 in range(T):
        for uc_r2 in range(lUC):
            horario.Add(sum([X(turma_r2,uc_r2,prof_r2,d_r2,h_r2,s_r2) for prof_r2 in range(P) for d_r2 in range(D) for h_r2 in range(H) for s_r2 in range(S)]) == cargaSemanalUC[uc_r2])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R3. No máximo uma aula da mesma disciplina por dia, por turma — exceto disciplinas de duplo período (ver R4), em que o bloco de 2 tempos conta como uma só ocorrência nesse dia.

    $$\forall_{t<T}\cdot\forall_{u<U}\cdot\forall_{d<D}\cdot \quad \sum_{p<P,\,h<H,\,s<S} x_{t,u,p,d,h,s}\leq 1+\mathit{dup}_u$$
    """)
    return


@app.cell
def _(D, H, P, S, T, X, disciplinas, horario, lUC):
    for turma_r3 in range(T):
        for uc_r3 in range(lUC):
            for d_r3 in range(D):
                max_r3 = 1
                if disciplinas.loc[uc_r3,"duplo_periodo"] == "sim":
                    max_r3 = 2
                horario.Add(sum([X(turma_r3,uc_r3,prof_r3,d_r3,h_r3,s_r3) for prof_r3 in range(P) for s_r3 in range(S) for h_r3 in range(H)]) <= max_r3)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R4. Disciplinas marcadas duplo_periodo=sim só podem ser dadas em blocos de 2 tempos consecutivos, no mesmo dia (nunca um tempo isolado).

    Cada tempo ocupado tem de ter um vizinho imediato (antes ou depois) com o mesmo professor e a mesma sala, com $x_{t,u,p,d,-1,s}=x_{t,u,p,d,H,s}=0$:

    $$\forall_{t<T}\cdot\forall_{u:\,\mathit{dup}_u=1}\cdot\forall_{p<P}\cdot\forall_{d<D}\cdot\forall_{s<S}\cdot\forall_{h<H}\cdot \quad x_{t,u,p,d,h,s}\leq x_{t,u,p,d,h-1,s}+x_{t,u,p,d,h+1,s}$$

    Juntamente com a R3 (no máximo $2$ tempos por dia nestas disciplinas), isto obriga a um único bloco de exatamente 2 tempos consecutivos.
    """)
    return


@app.cell
def _(D, H, P, S, T, X, disciplinas, horario, lUC):
    for turma_r4 in range(T):
        for uc_r4 in range(lUC):
            if disciplinas.loc[uc_r4, "duplo_periodo"] == "sim":
                for prof_r4 in range(P):
                    for d_r4 in range(D):
                        for s_r4 in range(S):
                            for h_r4 in range(H):
                                # cada tempo ocupado tem de ter um vizinho (antes ou depois) com o mesmo professor e sala.
                                # Com R3 (no máximo 2 tempos por dia) isto obriga a um bloco de exatamente 2 tempos consecutivos.
                                antes_r4 = X(turma_r4, uc_r4, prof_r4, d_r4, h_r4 - 1, s_r4) if h_r4 > 0 else 0
                                depois_r4 = X(turma_r4, uc_r4, prof_r4, d_r4, h_r4 + 1, s_r4) if h_r4 < H - 1 else 0
                                horario.Add(X(turma_r4, uc_r4, prof_r4, d_r4, h_r4, s_r4) <= antes_r4 + depois_r4)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R5. Um professor não pode dar duas aulas em simultâneo, mesmo que sejam a turmas ou disciplinas diferentes.

    $$\forall_{p<P}\cdot\forall_{d<D}\cdot\forall_{h<H}\cdot \quad \sum_{t<T,\,u<U,\,s<S} x_{t,u,p,d,h,s}\leq 1$$
    """)
    return


@app.cell
def _(D, H, P, S, T, X, horario, lUC):
    for prof_r5 in range(P):
        for d_r5 in range(D):
            for h_r5 in range(H):
                horario.Add(sum([X(t_r5, uc_r5, prof_r5, d_r5, h_r5, s_r5) for t_r5 in range(T) for uc_r5 in range(lUC) for s_r5 in range(S)]) <= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R6. Um professor só pode dar aulas nos tempos em que está disponível (disponibilidade_excecoes.csv).

    $$\forall_{(p,d,h)\in \mathit{Exc}}\cdot \quad \sum_{t<T,\,u<U,\,s<S} x_{t,u,p,d,h,s}=0$$
    """)
    return


@app.cell
def _(S, T, X, exc, horario, ucsporProf):
    for prof_r6, excecoes_prof_r6 in exc.items():
        for dia_exc_r6, hora_exc_r6 in excecoes_prof_r6:
            ucs_do_prof_r6 = ucsporProf[prof_r6]
            for uc_r6 in ucs_do_prof_r6:
                horario.Add(sum([X(t_r6, uc_r6, prof_r6, dia_exc_r6, hora_exc_r6, s_r6) for t_r6 in range(T) for s_r6 in range(S)]) == 0)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## R7. Cada aula ocupa uma sala. Disciplinas com sala_especial só podem usar salas desse tipo; as restantes usam salas normal. Em nenhum tempo o número de aulas a decorrer num tipo de sala pode exceder a quantidade desse tipo definida em salas.csv.

    1. A disciplina só usa salas do seu tipo (proibição):

    $$\forall_{t<T}\cdot\forall_{u<U}\cdot\forall_{p<P}\cdot\forall_{d<D}\cdot\forall_{h<H}\cdot\forall_{s\notin \mathit{Sal}_u}\cdot \quad x_{t,u,p,d,h,s}=0$$

    2. Cada sala tem, no máximo, uma aula em cada tempo (limitação). Isto implica que o número de aulas num tipo de sala nunca excede a quantidade desse tipo:

    $$\forall_{d<D}\cdot\forall_{h<H}\cdot\forall_{s<S}\cdot \quad \sum_{t<T,\,u<U,\,p<P} x_{t,u,p,d,h,s}\leq 1$$
    """)
    return


@app.cell
def _(D, H, P, S, T, X, horario, lUC, salaNum, tipoSala):
    # 1. Garantir que a UC só usa o tipo de sala permitido
    for t1_r7 in range(T):
        for uc1_r7 in range(lUC):
            sala_exigida = tipoSala[uc1_r7]
            for prof1_r7 in range(P):
                for d1_r7 in range(D):
                    for h1_r7 in range(H):
                        for s1_r7 in range(S):
                            if s1_r7 not in salaNum[sala_exigida]:
                                horario.Add(X(t1_r7, uc1_r7, prof1_r7, d1_r7, h1_r7, s1_r7 ) == 0)

    # 2. Apenas 1 aula por sala em simultâneo
    for d2_r7 in range(D):
        for h2_r7 in range(H):
            for s2_r7 in range(S):
                horario.Add(sum([X(t2_r7, uc2_r7, prof2_r7, d2_r7, h2_r7, s2_r7) for t2_r7 in range(T) for uc2_r7 in range(lUC) for prof2_r7 in range(P)]) <= 1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## O1. Minimizar o número total de "buracos" no horário de cada professor — um buraco é um tempo livre, no meio do dia, entre a primeira e a última aula desse professor nesse dia.

    Seja $y_{p,d,h}=\sum_{t,u,s}x_{t,u,p,d,h,s}\in\{0,1\}$ (o professor $p$ tem aula no tempo $h$ do dia $d$; é 0 ou 1 por R5).
    Para contar os buracos em forma linear, acrescentam-se três famílias de variáveis binárias:

    - $\mathit{pre}_{p,d,h}$: há aula em algum tempo $\leq h$
    - $\mathit{pos}_{p,d,h}$: há aula em algum tempo $\geq h$
    - $\mathit{ent}_{p,d,h}$: o tempo $h$ está entre a primeira e a última aula do dia

    $$\mathit{pre}_{p,d,h}\geq y_{p,d,h},\qquad \mathit{pre}_{p,d,h}\geq \mathit{pre}_{p,d,h-1}$$
    $$\mathit{pos}_{p,d,h}\geq y_{p,d,h},\qquad \mathit{pos}_{p,d,h}\geq \mathit{pos}_{p,d,h+1}$$
    $$\mathit{ent}_{p,d,h}\geq \mathit{pre}_{p,d,h}+\mathit{pos}_{p,d,h}-1$$

    Um buraco é um tempo entre a primeira e a última aula sem aula, logo

    $$\min \sum_{p<P,\,d<D,\,h<H}\big(\mathit{ent}_{p,d,h}-y_{p,d,h}\big)$$

    Como $\sum y$ é constante (pela R2), é equivalente minimizar $\sum \mathit{ent}$.
    """)
    return


@app.cell
def _(D, H, P, S, T, X, horario, lUC, profporUcs):
    # y[p,d,h] = 1 se o professor p tem aula no dia d, à hora h (0 ou 1, por R5)
    # pre = há aula em algum tempo <= h ; pos = há aula em algum tempo >= h
    # ent = o tempo h está entre a primeira e a última aula do dia
    ent_o1 = []

    for p_o1 in range(P):
        # só as disciplinas deste professor (para as outras, x já é 0 por R0)
        ucs_o1 = [uc_o1 for uc_o1 in range(lUC) if p_o1 in profporUcs[uc_o1]]

        for d_o1 in range(D):
            pre_o1 = [horario.IntVar(0, 1, f"pre_{p_o1}_{d_o1}_{h}") for h in range(H)]
            pos_o1 = [horario.IntVar(0, 1, f"pos_{p_o1}_{d_o1}_{h}") for h in range(H)]
            entre_o1 = [horario.IntVar(0, 1, f"ent_{p_o1}_{d_o1}_{h}") for h in range(H)]

            for h_o1 in range(H):
                y_o1 = sum([X(t_o1, uc_o1, p_o1, d_o1, h_o1, s_o1)
                            for t_o1 in range(T) for uc_o1 in ucs_o1 for s_o1 in range(S)])

                horario.Add(pre_o1[h_o1] >= y_o1)
                horario.Add(pos_o1[h_o1] >= y_o1)
                if h_o1 > 0:
                    horario.Add(pre_o1[h_o1] >= pre_o1[h_o1 - 1])
                if h_o1 < H - 1:
                    horario.Add(pos_o1[h_o1] >= pos_o1[h_o1 + 1])
                horario.Add(entre_o1[h_o1] >= pre_o1[h_o1] + pos_o1[h_o1] - 1)

            ent_o1 += entre_o1

    # buracos = soma(ent) - soma(y); a soma(y) é constante (R2), por isso minimiza-se soma(ent)
    horario.Minimize(sum(ent_o1))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Correr o solver
    """)
    return


@app.cell
def _(professores, pywraplp):
    def obter_solucao(horario, X, turmas, ucs, T, lUC, P, D, H, S):
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
                    for p in range(P):
                        for d in range(D):
                            for h in range(H):
                                for s in range(S):
                                    if X(t, uc, p, d, h, s).solution_value() == 1:
                                        solucao.append({
                                            "turma": turmas.loc[t, "turma"],
                                            "disciplina": ucs[uc],
                                            "professor": professores[p],
                                            "dia": d,
                                            "hora": h,
                                            "sala": s,
                                        })

            return solucao

    return (obter_solucao,)


@app.cell
def _(D, H, P, S, T, X, horario, lUC, obter_solucao, turmas, ucs):
    solucao = obter_solucao(
        horario, X, turmas, ucs, T, lUC, P, D, H, S
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
