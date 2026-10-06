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
    Pretendemos gerar o horário semanal de uma escola, dadas as turmas, disciplinas com o professor atribuído, carga, se é aula dupla (duplo_periodo) e necessidade de sala_especial. O tipo e quantidade
    de salas, e as exceções de disponibilidade dos professores.

    Vamos abordar isto com programação inteira, usando o solver usado na aula para a ficha 3 (SCIP via `pywraplp`).

    **Estrutura do notebook:** o modelo é construído por uma função `construir(dados, ...)` em vez de células com estado global. Isto é necessário para o R9: temos de poder construir
    (e resolver) o modelo várias vezes, com dados diferentes e com partes do horário fixadas.
    """)
    return


@app.cell
def _():
    import copy
    import time
    from collections import Counter, defaultdict
    from dataclasses import dataclass

    import pandas as pd
    from ortools.linear_solver import pywraplp

    H = 6  # Horas
    D = 5  # Dias
    DIAS = {"Seg": 0, "Ter": 1, "Qua": 2, "Qui": 3, "Sex": 4}
    COLS = ["turma", "disciplina", "professor", "dia", "hora", "sala"]
    return COLS, Counter, D, DIAS, H, copy, dataclass, defaultdict, pd, pywraplp, time


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Dados

    Os CSV são lidos para um objeto `Dados` que usa **nomes** (turma, disciplina, professor, sala) e não índices. Assim, um mesmo identificador (ex.: o professor "Ana", a sala `laboratorio_1`)
    significa o mesmo em `H0` e em `H1`, mesmo que o conjunto de professores/salas/turmas mude, o que é indispensável para comparar horários.

    Uma **aula** é o tuplo `(turma, disciplina, professor, dia, hora, sala)`, uma linha por tempo letivo (uma aula dupla são duas linhas).
    """)
    return


@app.cell
def _(D, DIAS, H, dataclass, pd):
    @dataclass
    class Dados:
        turmas: list
        ucs: list
        carga: dict  # uc -> tempos por semana
        duplo: dict  # uc -> bool
        profs_uc: dict  # uc -> [professores que a podem lecionar]
        salas: list  # nomes de todas as salas, ex. "laboratorio_1"
        salas_uc: dict  # uc -> [salas permitidas] (R7)
        indisp_prof: set  # {(professor, dia, hora)}
        indisp_sala: set  # {(sala, dia, hora)}  -- avarias, etc.


    def carregar(pasta):
        disc = pd.read_csv(pasta + "disciplinas.csv")
        exc = pd.read_csv(pasta + "disponibilidade_excecoes.csv")
        sal = pd.read_csv(pasta + "salas.csv")
        tur = pd.read_csv(pasta + "turmas.csv")

        por_tipo = {}
        for _, r in sal.iterrows():
            por_tipo[r["sala"]] = [f"{r['sala']}_{k + 1}" for k in range(int(r["quantidade"]))]
        normais = por_tipo[sal.loc[sal["tipo"] == "normal", "sala"].iloc[0]]

        ucs = disc["disciplina"].unique().tolist()
        carga, duplo, profs_uc, salas_uc = {}, {}, {}, {}
        for u in ucs:
            linhas = disc[disc["disciplina"] == u]
            l0 = linhas.iloc[0]
            carga[u] = int(l0["carga_semanal"])
            duplo[u] = l0["duplo_periodo"] == "sim"
            profs_uc[u] = linhas["professor"].unique().tolist()
            salas_uc[u] = normais if pd.isna(l0["sala_especial"]) else por_tipo[l0["sala_especial"]]

        indisp = set()
        for _, r in exc.iterrows():
            d, h = DIAS[r["dia"]], int(r["periodo"])
            assert 0 <= h < H, f"periodo fora de [0,{H - 1}] em {pasta}: {r.to_dict()}"
            indisp.add((r["professor"], d, h))

        return Dados(
            turmas=tur["turma"].tolist(),
            ucs=ucs,
            carga=carga,
            duplo=duplo,
            profs_uc=profs_uc,
            salas=[s for lst in por_tipo.values() for s in lst],
            salas_uc=salas_uc,
            indisp_prof=indisp,
            indisp_sala=set(),
        )

    return Dados, carregar


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Alterações de recursos

    Funções que derivam um `Dados` novo a partir de um existente. Cobrem os tipos de alteração pedidos no R9 além de `dados_v2/` (que é só ler outro CSV).
    O resto do código (`incremental`) trabalha sobre `Dados` e nunca assume qual foi a alteração.
    """)
    return


@app.cell
def _(D, H, copy):
    def prof_indisponivel(d0, prof, tempos):  # tempos: [(dia, hora), ...]
        n = copy.deepcopy(d0)
        n.indisp_prof |= {(prof, d, h) for d, h in tempos}
        return n


    def prof_disponivel(d0, prof, tempos=None):  # None = remove todas as exceções do professor
        n = copy.deepcopy(d0)
        n.indisp_prof = {
            (p, d, h) for (p, d, h) in n.indisp_prof
            if p != prof or (tempos is not None and (d, h) not in set(tempos))
        }
        return n


    def sala_indisponivel(d0, sala, tempos=None):  # None = sala inteira, todos os tempos
        n = copy.deepcopy(d0)
        tempos = [(d, h) for d in range(D) for h in range(H)] if tempos is None else tempos
        n.indisp_sala |= {(sala, d, h) for d, h in tempos}
        return n


    def nova_turma(d0, nome):
        n = copy.deepcopy(d0)
        n.turmas.append(nome)
        return n


    def substituir_prof(d0, antigo, novo, uc=None):  # uc=None: em todas as disciplinas do antigo
        n = copy.deepcopy(d0)
        for u in ([uc] if uc else n.ucs):
            n.profs_uc[u] = [novo if p == antigo else p for p in n.profs_uc[u]]
        return n

    return nova_turma, prof_disponivel, prof_indisponivel, sala_indisponivel, substituir_prof


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Modelo

    ## Análise do problema

    Este é um problema de alocação: *compromissos* (as aulas de uma disciplina a uma turma) são alocados a *recursos* (um professor, uma sala e um tempo).
    Índices: turmas $t<T$, disciplinas $u<U$, professores $p<P$, dias $d<D$, horas $h<H$, salas $s<S$.

    **Parâmetros** (vêm dos CSV): $c_u$ é a carga semanal de $u$; $\mathit{dup}_u\in\{0,1\}$ indica se $u$ é de duplo período; $\mathit{Prof}_u$ é o conjunto de professores de $u$;
    $\mathit{Sal}_u$ é o conjunto de salas que $u$ pode usar (o tipo `sala_especial`, ou as salas normais); $\mathit{Ind}\subseteq P\times D\times H$ são as exceções de disponibilidade
    (`disponibilidade_excecoes.csv`); $\mathit{IndS}\subseteq S\times D\times H$ são as salas indisponíveis (avarias).

    **Variáveis.** Uma família de variáveis binárias com a semântica

    $$x_{t,u,p,d,h,s}=1 \quad \mbox{se e só se} \quad \mbox{a turma $t$ tem a disciplina $u$ com o professor $p$, no dia $d$, à hora $h$, na sala $s$.}$$

    **Proibições** (fixam variáveis a 0)

    - **R0.** O professor só leciona as suas disciplinas:
    $\;\forall_{t,u}\ \forall_{p\notin \mathit{Prof}_u}\cdot \sum_{d,h,s} x_{t,u,p,d,h,s}=0$
    - **R6.** Disponibilidade do professor:
    $\;\forall_{(p,d,h)\in \mathit{Ind}}\cdot \sum_{t,u,s} x_{t,u,p,d,h,s}=0$
    - **R7a.** Tipo de sala:
    $\;\forall_{t,u,p,d,h}\ \forall_{s\notin \mathit{Sal}_u}\cdot x_{t,u,p,d,h,s}=0$
    - **R7c.** Sala indisponível:
    $\;\forall_{(s,d,h)\in \mathit{IndS}}\cdot \sum_{t,u,p} x_{t,u,p,d,h,s}=0$

    **Limitações** (limites máximos)

    - **R1.** Uma turma não tem duas aulas em simultâneo:
    $\;\forall_{t,d,h}\cdot \sum_{u,p,s} x_{t,u,p,d,h,s}\leq 1$
    - **R3.** No máximo uma ocorrência da disciplina por dia (2 tempos se for duplo período):
    $\;\forall_{t,u,d}\cdot \sum_{p,h,s} x_{t,u,p,d,h,s}\leq 1+\mathit{dup}_u$
    - **R5.** Um professor não dá duas aulas em simultâneo:
    $\;\forall_{p,d,h}\cdot \sum_{t,u,s} x_{t,u,p,d,h,s}\leq 1$
    - **R7b.** Uma aula por sala em cada tempo:
    $\;\forall_{s,d,h}\cdot \sum_{t,u,p} x_{t,u,p,d,h,s}\leq 1$

    **Obrigações** (limites mínimos)

    - **R2.** Cada disciplina cumpre exatamente a carga semanal, para cada turma:
    $\;\forall_{t,u}\cdot \sum_{p,d,h,s} x_{t,u,p,d,h,s}=c_u$

    **Ligação entre variáveis**

    - **R4.** Duplo período só em blocos de 2 tempos consecutivos, no mesmo dia, com o mesmo professor e sala, nos pares $(0,1),(2,3),(4,5)$:
    $\;\forall_{t,u:\,\mathit{dup}_u=1}\ \forall_{p,d,s}\ \forall_{b<H/2}\cdot x_{t,u,p,d,2b,s}=x_{t,u,p,d,2b+1,s}$

    ## Objetivo O1: minimizar os buracos

    Seja $y_{p,d,h}=\sum_{t,u,s}x_{t,u,p,d,h,s}\in\{0,1\}$ (o professor $p$ tem aula no tempo $h$ do dia $d$, por R5). Um tempo é um buraco se está entre a primeira e a última aula do dia
    e não tem aula. Para o expressar linearmente, acrescentam-se três famílias de binárias:
    $\mathit{pre}_{p,d,h}$ (há aula em algum tempo $\leq h$), $\mathit{pos}_{p,d,h}$ (há aula em algum tempo $\geq h$) e $\mathit{ent}_{p,d,h}$ ($h$ está entre a primeira e a última aula):

    $$\mathit{pre}_{p,d,h}\geq y_{p,d,h},\quad \mathit{pre}_{p,d,h}\geq \mathit{pre}_{p,d,h-1},\quad \mathit{pos}_{p,d,h}\geq y_{p,d,h},\quad \mathit{pos}_{p,d,h}\geq \mathit{pos}_{p,d,h+1},\quad \mathit{ent}_{p,d,h}\geq \mathit{pre}_{p,d,h}+\mathit{pos}_{p,d,h}-1$$

    $$\min \sum_{p,d,h}\big(\mathit{ent}_{p,d,h}-y_{p,d,h}\big)$$

    Como $\sum y$ é constante (pela R2), minimizar $\sum \mathit{ent}$ é equivalente, e como é uma minimização o solver nunca põe $\mathit{pre},\mathit{pos},\mathit{ent}$ a 1 sem necessidade.
    Não é preciso a disjunção "primeiro/último" da formulação com `OnlyEnforceIf`, que o `pywraplp` não tem.

    ## Implementação

    A matriz densa $T\times U\times P\times D\times H\times S$ é enorme e quase toda forçada a 0 pelas proibições. Por isso `construir` **só cria as variáveis permitidas**,
    o que é equivalente a R0, R6, R7a e R7c. Para R4, em disciplinas de duplo período cria-se uma única variável $z_{t,u,p,d,b,s}$ por bloco, que ocupa os tempos $2b$ e $2b+1$
    (a igualdade fica verdadeira por construção). As restantes restrições são adicionadas assim, com $n_u=1+\mathit{dup}_u$:

    | Restrição | Código |
    |---|---|
    | R1, R5, R7b | `Σ x ≤ 1` por (turma, dia, hora), (professor, dia, hora), (sala, dia, hora); uma variável de bloco conta nos 2 tempos |
    | R2 | `Σ n_u · x == c_u − fixas` por (turma, disciplina) |
    | R3 | `Σ x ≤ 1` por (turma, disciplina, dia); como cada variável é um tempo ou um bloco, 1 variável ⇔ ≤ $1+\mathit{dup}_u$ tempos |
    """)
    return


@app.cell
def _(Counter, D, H, defaultdict, pywraplp, time):
    def construir(dados, fixas=(), objetivo=None, ref=None, dica=False):
        """Devolve o modelo, ou None se for trivialmente impossível."""
        sv = pywraplp.Solver.CreateSolver("SCIP")

        # Recursos já ocupados pelas aulas fixas
        oc_t, oc_p, oc_s, dia_feito, feitas = set(), set(), set(), set(), Counter()
        for (t, u, p, d, h, s) in fixas:
            oc_t.add((t, d, h)); oc_p.add((p, d, h)); oc_s.add((s, d, h))
            dia_feito.add((t, u, d)); feitas[(t, u)] += 1

        # Variáveis: x[(t,u,p,d,h0,s)] = 1 se a turma t tem a uc u com o prof p no dia d,
        # a partir do tempo h0 (n tempos seguidos: 2 se duplo_periodo), na sala s
        x = {}
        for t in dados.turmas:
            for u in dados.ucs:
                if dados.carga[u] - feitas[(t, u)] <= 0:
                    continue
                n = 2 if dados.duplo[u] else 1
                for d in range(D):
                    if (t, u, d) in dia_feito:  # R3 já saturado por uma aula fixa
                        continue
                    for h0 in range(0, H - n + 1, n):  # R4: blocos alinhados
                        hs = range(h0, h0 + n)
                        if any((t, d, h) in oc_t for h in hs):
                            continue
                        for p in dados.profs_uc[u]:  # R0
                            if any((p, d, h) in oc_p or (p, d, h) in dados.indisp_prof for h in hs):  # R5, R6
                                continue
                            for s in dados.salas_uc[u]:  # R7 (tipo)
                                if any((s, d, h) in oc_s or (s, d, h) in dados.indisp_sala for h in hs):
                                    continue
                                x[(t, u, p, d, h0, s)] = sv.BoolVar("")

        por_t, por_p, por_s = defaultdict(list), defaultdict(list), defaultdict(list)
        por_tu, por_tud = defaultdict(list), defaultdict(list)
        for (t, u, p, d, h0, s), v in x.items():
            n = 2 if dados.duplo[u] else 1
            for h in range(h0, h0 + n):
                por_t[(t, d, h)].append(v)
                por_p[(p, d, h)].append(v)
                por_s[(s, d, h)].append(v)
            por_tu[(t, u)].append((n, v))
            por_tud[(t, u, d)].append(v)

        for vs in por_t.values():  # R1
            sv.Add(sv.Sum(vs) <= 1)
        for (t, u), lst in por_tu.items():  # R2
            sv.Add(sv.Sum([n * v for n, v in lst]) == dados.carga[u] - feitas[(t, u)])
        for t in dados.turmas:  # (t,u) que precisam de aulas mas não têm nenhuma posição possível
            for u in dados.ucs:
                if dados.carga[u] - feitas[(t, u)] > 0 and (t, u) not in por_tu:
                    return None
        for vs in por_tud.values():  # R3
            sv.Add(sv.Sum(vs) <= 1)
        for vs in por_p.values():  # R5
            sv.Add(sv.Sum(vs) <= 1)
        for vs in por_s.values():  # R7 (uma aula por sala)
            sv.Add(sv.Sum(vs) <= 1)

        if objetivo == "manter":
            # maximizar tempos que ficam exatamente onde estavam em ref (ignora o professor)
            coef = {}
            for k, v in x.items():
                t, u, p, d, h0, s = k
                n = 2 if dados.duplo[u] else 1
                c = sum((t, u, d, h, s) in ref for h in range(h0, h0 + n))
                if c:
                    coef[k] = c
            if coef:
                sv.Maximize(sv.Sum([c * x[k] for k, c in coef.items()]))
        elif objetivo == "o1":
            assert not fixas
            ent_total = []
            for p in {p for ps in dados.profs_uc.values() for p in ps}:
                for d in range(D):
                    if not any((p, d, h) in por_p for h in range(H)):
                        continue
                    pre = [sv.BoolVar("") for _ in range(H)]  # há aula em algum tempo <= h
                    pos = [sv.BoolVar("") for _ in range(H)]  # há aula em algum tempo >= h
                    ent = [sv.BoolVar("") for _ in range(H)]  # h está entre a 1ª e a última aula
                    for h in range(H):
                        if (p, d, h) in por_p:
                            a = sv.Sum(por_p[(p, d, h)])
                            sv.Add(pre[h] >= a)
                            sv.Add(pos[h] >= a)
                        if h > 0:
                            sv.Add(pre[h] >= pre[h - 1])
                        if h < H - 1:
                            sv.Add(pos[h] >= pos[h + 1])
                        sv.Add(ent[h] >= pre[h] + pos[h] - 1)
                    ent_total += ent
            # buracos = Σ ent − nº total de aulas; o 2º termo é constante (R2) e não afeta o argmin
            sv.Minimize(sv.Sum(ent_total))

        if dica and ref:  # warm start: a solução anterior como ponto de partida
            vs, vals = [], []
            for (t, u, p, d, h0, s), v in x.items():
                n = 2 if dados.duplo[u] else 1
                ok = all(ref.get((t, u, d, h, s)) == p for h in range(h0, h0 + n))
                vs.append(v); vals.append(1.0 if ok else 0.0)
            sv.SetHint(vs, vals)

        return {"sv": sv, "x": x, "fixas": list(fixas), "dados": dados}


    def resolver(m, limite_s=120):
        sv = m["sv"]
        sv.SetTimeLimit(int(limite_s * 1000))
        st = sv.Solve()
        if st not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            return None, "impossível" if st == pywraplp.Solver.INFEASIBLE else "sem solução (limite de tempo)"
        rows = list(m["fixas"])
        for (t, u, p, d, h0, s), v in m["x"].items():
            if v.solution_value() > 0.5:
                for h in range(h0, h0 + (2 if m["dados"].duplo[u] else 1)):
                    rows.append((t, u, p, d, h, s))
        return rows, ("ótima" if st == pywraplp.Solver.OPTIMAL else "viável (limite de tempo)")


    def correr(dados, fixas=(), objetivo=None, ref=None, dica=False, limite_s=120):
        """Constrói e resolve; devolve (aulas|None, info)."""
        t0 = time.perf_counter()
        m = construir(dados, fixas, objetivo, ref, dica)
        t1 = time.perf_counter()
        if m is None:
            return None, {"estado": "impossível (pré-verificação)", "t_build": t1 - t0, "t_solve": 0.0}
        if not m["x"]:  # nada para decidir: as fixas já são o horário completo
            return list(m["fixas"]), {"estado": "ótima", "t_build": t1 - t0, "t_solve": 0.0}
        rows, estado = resolver(m, limite_s)
        return rows, {"estado": estado, "t_build": t1 - t0, "t_solve": time.perf_counter() - t1}

    return construir, correr, resolver


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Verificação independente e comparação de horários

    `validar` confere R0–R7 diretamente sobre a lista de aulas, sem passar pelo modelo, por isso serve de prova de que `H1` é válido.
    `diferencas` conta as aulas que mudam de tempo/sala: uma aula de `H0` é "alterada" se o tuplo `(turma, disciplina, dia, hora, sala)` já não existe em `H1`
    (a troca de professor numa substituição é obrigatória e não conta; fica numa coluna à parte).
    """)
    return


@app.cell
def _(Counter, defaultdict):
    def validar(dados, aulas):
        e = []
        c_t, c_p, c_s = Counter(), Counter(), Counter()
        cont, hs = Counter(), defaultdict(list)
        for (t, u, p, d, h, s) in aulas:
            if t not in dados.turmas or u not in dados.ucs:
                e.append(("turma/disciplina desconhecida", t, u)); continue
            if p not in dados.profs_uc[u]: e.append(("R0", t, u, p))
            if (p, d, h) in dados.indisp_prof: e.append(("R6", p, d, h))
            if s not in dados.salas_uc[u]: e.append(("R7 tipo", u, s))
            if (s, d, h) in dados.indisp_sala: e.append(("R7 sala indisponível", s, d, h))
            c_t[(t, d, h)] += 1; c_p[(p, d, h)] += 1; c_s[(s, d, h)] += 1
            cont[(t, u)] += 1; hs[(t, u, d)].append((h, p, s))
        e += [("R1", k) for k, v in c_t.items() if v > 1]
        e += [("R5", k) for k, v in c_p.items() if v > 1]
        e += [("R7 sala ocupada", k) for k, v in c_s.items() if v > 1]
        for t in dados.turmas:
            for u in dados.ucs:
                if cont[(t, u)] != dados.carga[u]: e.append(("R2", t, u, cont[(t, u)], dados.carga[u]))
        for (t, u, d), lst in hs.items():
            if dados.duplo[u]:  # R3 + R4: um único bloco alinhado, mesmo prof e sala
                hh = sorted(h for h, _, _ in lst)
                if len(hh) != 2 or hh[0] % 2 or hh[1] != hh[0] + 1 or len({(p, s) for _, p, s in lst}) != 1:
                    e.append(("R3/R4", t, u, d, hh))
            elif len(lst) > 1:
                e.append(("R3", t, u, d))
        return e


    def diferencas(dados1, h0, h1):
        k0 = {(a[0], a[1], a[3], a[4], a[5]): a[2] for a in h0 if a[0] in dados1.turmas and a[1] in dados1.ucs}
        k1 = {(a[0], a[1], a[3], a[4], a[5]): a[2] for a in h1}
        return {
            "aulas_h0": len(k0),
            "alteradas": sum(k not in k1 for k in k0),
            "so_professor": sum(k in k1 and k1[k] != p for k, p in k0.items()),
        }

    return diferencas, validar


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # R9: construção incremental

    ## Formalização

    Seja $A_0$ o conjunto de aulas de $H_0$, cada uma $a=(t,u,p_a,d,h,s)$, e $\mathit{ok}(a)$ o predicado "a aula $a$ continua válida com os novos dados":

    $$\mathit{ok}(a)\;\equiv\; p_a\in \mathit{Prof}_u\ \wedge\ (p_a,d,h)\notin \mathit{Ind}'\ \wedge\ s\in \mathit{Sal}'_u\ \wedge\ (s,d,h)\notin \mathit{IndS}'$$

    (isto é R0, R6 e R7 com os dados novos, assinalados com $'$). As aulas **afetadas** são $I=\{a\in A_0:\neg\,\mathit{ok}(a)\}$, mais todas as aulas de $(t,u)$ cuja carga $c'_u$ desceu.
    As aulas agrupam-se em *unidades* (um tempo, ou um bloco de 2 se $\mathit{dup}_u=1$) para nunca partir um bloco.

    Seja $L$ uma vizinhança de unidades livres, com $I\subseteq L$. A **fixação** impõe, para todas as aulas não livres,

    $$\forall_{a=(t,u,p_a,d,h,s)\in A_0\setminus L}\cdot x_{t,u,p_a,d,h,s}=1$$

    Com estas variáveis a 1, R1, R5 e R7b forçam a 0 todas as variáveis que usem a mesma turma, professor ou sala nesse tempo, e R2 e R3 reduzem a carga a colocar a $c_u-|\{\mbox{fixas de }(t,u)\}|$.
    É por isso que o código trata as fixas como constantes e não cria essas variáveis (o modelo resultante é o mesmo, só mais pequeno).

    **Objetivo (minimizar as aulas alteradas).** Uma aula de $H_0$ fica *mantida* se existe uma aula em $H_1$ na mesma turma, disciplina, dia, hora e sala (o professor pode mudar, numa substituição):

    $$\mathit{mant}_a=\sum_{p} x_{t,u,p,d,h,s}\in\{0,1\},\qquad \max \sum_{a\in A_0\cap L}\mathit{mant}_a\quad\Longleftrightarrow\quad \min\ \underbrace{\big|\{a\in A_0:\mathit{mant}_a=0\}\big|}_{\mbox{aulas alteradas}}$$

    ## Algoritmo

    1. Calcular $I$ e as unidades. Nível 0: $L=I$.
    2. Resolver o modelo acima com R0–R7 sobre os dados novos, fixações e objetivo. Se for **impossível**, alargar $L$ e repetir:
       nível 1 junta as unidades das turmas e dos professores já envolvidos, nível 2 repete uma vez, nível 3 usa $L=A_0$ (modelo completo, com $H_0$ como *hint*).
    3. O nível 3 não tem fixações, logo é o problema completo: **se existe $H_1$ válido o método encontra-o**.

    Compromisso: nos níveis 0–2 o número de alterações é ótimo *dentro de $L$*, não necessariamente o mínimo global. A tabela de resultados compara com o nível global (método B).
    """)
    return


@app.cell
def _(Counter, correr, defaultdict, time):
    def aulas_afetadas(dados1, h0):
        """Agrupa H0 em unidades e devolve (unidades, unidades inválidas)."""
        unidades = defaultdict(list)
        cont = Counter()
        for a in h0:
            t, u, p, d, h, s = a
            if t in dados1.turmas and u in dados1.carga:  # aulas de turmas/disciplinas removidas desaparecem
                unidades[(t, u, d, h // 2 if dados1.duplo[u] else h)].append(a)
                cont[(t, u)] += 1

        def invalida(a):
            t, u, p, d, h, s = a
            return (
                p not in dados1.profs_uc[u]  # R0 (ex.: professor substituído)
                or (p, d, h) in dados1.indisp_prof  # R6
                or s not in dados1.salas_uc[u]  # R7 (sala deixou de existir/servir)
                or (s, d, h) in dados1.indisp_sala  # R7 (avaria)
            )

        inv = set()
        for k, rows in unidades.items():
            if any(invalida(a) for a in rows) or cont[(k[0], k[1])] > dados1.carga[k[1]]:
                inv.add(k)
        return dict(unidades), inv


    def expandir(dados1, unidades, livres):
        """Junta à vizinhança as unidades das turmas e dos professores já envolvidos."""
        turmas = {k[0] for k in livres}
        profs = {a[2] for k in livres for a in unidades[k]}
        profs |= {p for k in livres for p in dados1.profs_uc[k[1]]}  # candidatos a substituir/receber
        return livres | {
            k for k, rows in unidades.items()
            if k[0] in turmas or any(a[2] in profs for a in rows)
        }


    def incremental(dados1, h0, limite_s=60):
        t0 = time.perf_counter()
        unidades, inv = aulas_afetadas(dados1, h0)
        ref = {(a[0], a[1], a[3], a[4], a[5]): a[2] for rows in unidades.values() for a in rows}
        n1 = expandir(dados1, unidades, inv)
        n2 = expandir(dados1, unidades, n1)
        niveis = [("0: só afetadas", inv), ("1: + turmas/profs afetados", n1), ("2: vizinhança de 2 saltos", n2),
                  ("3: tudo livre (hint)", set(unidades))]
        log, vistos = [], []
        for nome, livres in niveis:
            if any(livres == v for v in vistos):  # igual a um nível já tentado (e falhado)
                continue
            vistos.append(livres)
            fixas = [a for k, rows in unidades.items() if k not in livres for a in rows]
            h1, info = correr(dados1, fixas, "manter", ref, dica=(nome[0] == "3"), limite_s=limite_s)
            log.append({"nível": nome, "unidades livres": len(livres), "estado": info["estado"],
                        "build (s)": round(info["t_build"], 3), "solve (s)": round(info["t_solve"], 3)})
            if h1 is not None:
                return h1, {"t_total": time.perf_counter() - t0, "log": log, "afetadas": len(inv)}
        return None, {"t_total": time.perf_counter() - t0, "log": log, "afetadas": len(inv)}

    return (incremental,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Passo 1: `H0` a partir de `dados/`
    """)
    return


@app.cell
def _(carregar, correr):
    dados0 = carregar("dados/")
    H0, info0 = correr(dados0, objetivo="o1", limite_s=120)
    print("H0:", info0)
    return H0, dados0, info0


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Passo 2: `H1` a partir de `dados_v2/`, três maneiras

    - **A. Do zero:** resolver `dados_v2/` sem usar `H0` (só viabilidade, a variante mais barata de resolver do zero).
    - **B. Global com hint:** modelo completo, `H0` como ponto de partida e objetivo "manter".
    - **C. Incremental:** o método descrito acima.
    """)
    return


@app.cell
def _(H0, carregar, correr, diferencas, incremental, pd, time, validar):
    dados1 = carregar("dados_v2/")

    def comparar(nome, d1, h0, limite_s=120):
        ref0 = {(a[0], a[1], a[3], a[4], a[5]): a[2] for a in h0}
        linhas, saidas, logs = [], {}, {}
        t = time.perf_counter()
        a, ia = correr(d1, limite_s=limite_s)
        saidas["A. do zero"] = (a, ia["estado"], time.perf_counter() - t)
        t = time.perf_counter()
        b, ib = correr(d1, objetivo="manter", ref=ref0, dica=True, limite_s=limite_s)
        saidas["B. global + hint"] = (b, ib["estado"], time.perf_counter() - t)
        c, ic = incremental(d1, h0, limite_s)
        saidas["C. incremental"] = (c, "ótima na vizinhança" if c else "sem solução", ic["t_total"])
        logs = ic["log"]
        for met, (h1, estado, seg) in saidas.items():
            if h1 is None:
                linhas.append({"cenário": nome, "método": met, "tempo (s)": round(seg, 3), "estado": estado})
                continue
            df = diferencas(d1, h0, h1)
            linhas.append({"cenário": nome, "método": met, "tempo (s)": round(seg, 3), "aulas alteradas": df["alteradas"],
                           "de": df["aulas_h0"], "só mudou professor": df["so_professor"],
                           "violações": len(validar(d1, h1)), "estado": estado})
        return pd.DataFrame(linhas), saidas, logs

    tab_v2, saidas_v2, log_v2 = comparar("dados_v2/", dados1, H0)
    H1_zero = saidas_v2["A. do zero"][0]
    H1_glob = saidas_v2["B. global + hint"][0]
    H1 = saidas_v2["C. incremental"][0]
    return H1, H1_glob, H1_zero, comparar, dados1, log_v2, tab_v2


@app.cell
def _(log_v2, mo, pd, tab_v2):
    mo.vstack([mo.md("**Resultados em `dados_v2/`**"), mo.ui.table(tab_v2, selection=None),
               mo.md("**Níveis tentados pelo método incremental**"), mo.ui.table(pd.DataFrame(log_v2), selection=None)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Outros tipos de alteração

    O mesmo código (`incremental`) sem mudanças. Os cenários são gerados a partir de `H0`: o professor com mais aulas, a sala mais usada, etc.
    """)
    return


@app.cell
def _(
    Counter, H0, comparar, dados0, nova_turma, pd, prof_disponivel,
    prof_indisponivel, sala_indisponivel, substituir_prof,
):
    _cp = Counter(a[2] for a in H0)
    _top = _cp.most_common(1)[0][0]
    _tempos_top = sorted({(a[3], a[4]) for a in H0 if a[2] == _top})[:2]
    _cs = Counter(a[5] for a in H0)
    _sala = _cs.most_common(1)[0][0]
    _com_exc = Counter(p for p, _, _ in dados0.indisp_prof).most_common(1)
    _exc_prof = _com_exc[0][0] if _com_exc else _top

    cenarios = {
        f"{_top} indisponível em {_tempos_top}": prof_indisponivel(dados0, _top, _tempos_top),
        f"{_exc_prof} fica disponível (sem exceções)": prof_disponivel(dados0, _exc_prof),
        f"sala {_sala} avariada (semana toda)": sala_indisponivel(dados0, _sala),
        "turma nova": nova_turma(dados0, "NOVA"),
        f"{_top} substituído por 'Substituto'": substituir_prof(dados0, _top, "Substituto"),
    }
    _tabs = []
    for _nome, _d1 in cenarios.items():
        _t, _, _ = comparar(_nome, _d1, H0)
        _tabs.append(_t)
    tab_cenarios = pd.concat(_tabs, ignore_index=True)
    tab_cenarios
    return cenarios, tab_cenarios


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Representação dos dados
    """)
    return


@app.cell
def _(H0, H1, H1_zero, mo):
    horarios = {"H0": H0, "H1 (incremental)": H1, "H1 (do zero)": H1_zero}
    versaoUi = mo.ui.dropdown(options=list(horarios), value="H1 (incremental)", label="Versão")
    versaoUi
    return horarios, versaoUi


@app.cell
def _(horarios, versaoUi):
    solucao = horarios[versaoUi.value]
    return (solucao,)


@app.cell
def _(COLS, mo, pd):
    def preparar_horario(solucao):
        return pd.DataFrame(solucao, columns=COLS).sort_values(["dia", "hora"]).reset_index(drop=True)


    def obter_turmas(horario_df):
        return sorted(horario_df["turma"].unique())


    def obter_professores(horario_df):
        return sorted(horario_df["professor"].unique())


    def criar_grelha(df, texto, D, H, dias_nomes, horas_nomes):
        df = df.copy()
        df["celula"] = df.apply(texto, axis=1)
        grelha = df.pivot_table(index="hora", columns="dia", values="celula", aggfunc=lambda x: " / ".join(x))
        grelha = grelha.reindex(index=range(H), columns=range(D)).fillna("")
        grelha.index = horas_nomes
        grelha.columns = dias_nomes
        grelha.index.name = "Hora"
        return grelha.reset_index()


    def criar_grelha_turma(horario_df, turma, D, H, dias_nomes, horas_nomes):
        df = horario_df[horario_df["turma"] == turma]
        return criar_grelha(df, lambda r: f"{r['disciplina']} ({r['sala']}) - {r['professor']}", D, H, dias_nomes, horas_nomes)


    def criar_grelha_professor(horario_df, professor, D, H, dias_nomes, horas_nomes):
        df = horario_df[horario_df["professor"] == professor]
        return criar_grelha(df, lambda r: f"{r['disciplina']} ({r['sala']}) - {r['turma']}", D, H, dias_nomes, horas_nomes)


    def criar_tabela(grelha_df, H):
        return mo.ui.table(grelha_df, selection=None, page_size=H)

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
    if solucao:
        horario_df = preparar_horario(solucao)
        lista_turmas = obter_turmas(horario_df)
        lista_professores = obter_professores(horario_df)
        turmaUi = mo.ui.dropdown(options=lista_turmas, value=lista_turmas[0], label="Turma")
        professorUi = mo.ui.dropdown(options=lista_professores, value=lista_professores[0], label="Professor")
    else:
        horario_df = None
        turmaUi = None
        professorUi = None

    mo.vstack([turmaUi, professorUi]) if turmaUi is not None else mo.md("⚠️ Sem solução disponível")
    return horario_df, professorUi, turmaUi


@app.cell(hide_code=True)
def _(D, H, criar_grelha_professor, criar_grelha_turma, criar_tabela, horario_df, mo, professorUi, turmaUi):
    def render_horarios():
        if horario_df is None or turmaUi is None or professorUi is None:
            return mo.md("A aguardar solução...")
        dias_nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
        horas_nomes = [f"{8 + h}:00" for h in range(H)]
        g_t = criar_grelha_turma(horario_df, turmaUi.value, D, H, dias_nomes, horas_nomes)
        g_p = criar_grelha_professor(horario_df, professorUi.value, D, H, dias_nomes, horas_nomes)
        return mo.vstack([mo.md("### Horário da Turma"), criar_tabela(g_t, H),
                          mo.md("### Horário do Professor"), criar_tabela(g_p, H)])

    render_horarios()
    return


if __name__ == "__main__":
    app.run()