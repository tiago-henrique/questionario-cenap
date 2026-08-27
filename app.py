"""
Dashboard - Questionário de Percepção sobre Atividades de Pesquisa
FAMERP / FUNFARME - CENAP
"""
import io
import re
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Percepção sobre Pesquisa | CENAP",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#0B5D6B"
SECONDARY = "#159895"
ACCENT = "#F4A259"
LIKERT_COLORS = ["#C7373F", "#E5A03B", "#B0B0B0", "#7CB9A8", "#0B5D6B"]
DICT_PATH = Path(__file__).parent / "data_dictionary.csv"

CUSTOM_CSS = f"""
<style>
    .main {{ background-color: #F7F9FA; }}
    [data-testid="stMetric"] {{
        background: white;
        border: 1px solid #E3E8EA;
        border-radius: 10px;
        padding: 14px 16px 6px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    [data-testid="stMetricLabel"] {{ color: #5A6B70; font-weight: 500; }}
    h1, h2, h3 {{ color: {PRIMARY}; }}
    .block-container {{ padding-top: 1.5rem; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: #EDF2F3;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {PRIMARY} !important;
        color: white !important;
    }}
    .demo-banner {{
        background: #FFF3E0;
        border: 1px solid {ACCENT};
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

LIKERT_ORDER = [
    "Discordo totalmente",
    "Discordo parcialmente",
    "Nem concordo nem discordo",
    "Concordo parcialmente",
    "Concordo totalmente",
]

@st.cache_data
def load_dictionary(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df

def parse_choices(raw: str) -> dict:
    """'1, Sim | 0, Não' -> {'1': 'Sim', '0': 'Não'}"""
    if pd.isna(raw) or not str(raw).strip():
        return {}
    mapping = {}
    for part in str(raw).split("|"):
        part = part.strip()
        if not part:
            continue
        code, _, label = part.partition(",")
        mapping[code.strip()] = label.strip()
    return mapping


@st.cache_data
def build_field_meta(dict_df: pd.DataFrame) -> dict:
    meta = {}
    for _, row in dict_df.iterrows():
        var = row["Variable / Field Name"].strip()
        meta[var] = {
            "label": row["Field Label"],
            "type": row["Field Type"],
            "choices": parse_choices(row.get("Choices, Calculations, OR Slider Labels", "")),
            "note": row.get("Field Note", ""),
        }
    return meta


dict_df = load_dictionary(DICT_PATH)
FIELD_META = build_field_meta(dict_df)

CHECKBOX_FIELDS = [v for v, m in FIELD_META.items() if m["type"] == "checkbox"]
LIKERT_FIELDS = [
    v for v, m in FIELD_META.items()
    if m["type"] == "dropdown" and set(m["choices"].values()) == set(LIKERT_ORDER)
]
YESNO_FIELDS = [
    v for v, m in FIELD_META.items()
    if m["type"] == "radio" and set(m["choices"].values()) <= {"Sim", "Não"}
]


@st.cache_data
def generate_demo_data(n=180, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    vinculo_codes = list(FIELD_META["vinculo_institucional"]["choices"].keys())
    vinculo_p = [0.28, 0.24, 0.10, 0.06, 0.08, 0.05, 0.06, 0.05, 0.08]
    categoria_codes = list(FIELD_META["categoria_profissional"]["choices"].keys())
    categoria_p = [0.16, 0.14, 0.16, 0.14, 0.18, 0.12, 0.06, 0.04]

    setores = [
        "Clínica Médica", "Cirurgia", "Pediatria", "UTI Adulto", "Oncologia",
        "Ginecologia e Obstetrícia", "Ortopedia", "Laboratório de Análises Clínicas",
        "Radiologia", "Enfermagem", "Administração", "Ambulatório",
    ]

    for i in range(n):
        vinculo = rng.choice(vinculo_codes, p=vinculo_p)
        categoria = rng.choice(categoria_codes, p=categoria_p)
        participa = rng.choice(["0", "1"], p=[0.55, 0.45])
        publicou = rng.choice(["0", "1"], p=[0.6, 0.4]) if participa == "0" else rng.choice(["0", "1"], p=[0.25, 0.75])
        eventos = rng.choice(["0", "1"], p=[0.35, 0.65])
        apresentou = rng.choice(["0", "1"], p=[0.5, 0.5]) if eventos == "1" else "0"

        def likert(bias=0):
            weights = np.array([0.08, 0.12, 0.15, 0.30, 0.35])
            weights = np.clip(weights + bias, 0.01, None)
            weights = weights / weights.sum()
            return str(rng.choice([1, 2, 3, 4, 5], p=weights))

        conhece_cenap = likert(bias=-0.05 if categoria in ["5", "3"] else 0.05)
        utilizou = rng.choice(["0", "1"], p=[0.55, 0.45]) if conhece_cenap in ["4", "5"] else rng.choice(["0", "1"], p=[0.85, 0.15])

       

        obst_opts = list(FIELD_META["obstaculos_pesquisa"]["choices"].keys())
        obst_choice = rng.choice(obst_opts, size=rng.integers(1, 4), replace=False)
        for c in obst_opts:
            row[f"obstaculos_pesquisa___{c}"] = "1" if c in obst_choice else "0"

        mot_opts = list(FIELD_META["motivacao_pesquisa"]["choices"].keys())
        mot_choice = rng.choice(mot_opts, size=rng.integers(1, 4), replace=False)
        for c in mot_opts:
            row[f"motivacao_pesquisa___{c}"] = "1" if c in mot_choice else "0"

        rows.append(row)

    return pd.DataFrame(rows)


def normalize_code(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return s
    except (ValueError, TypeError):
        return s


def decode_series(series: pd.Series, field: str, na_label: str = "Não informado") -> pd.Series:
    """Decodifica os códigos usando o dicionário de dados.

    Valores ausentes/vazios são rotulados como `na_label` em vez de descartados,
    para que apareçam como categoria própria nas contagens e gráficos.
    """
    choices = FIELD_META.get(field, {}).get("choices", {})
    if not choices:
        return series.fillna(na_label).replace("", na_label)

    def _map(x):
        code = normalize_code(x)
        if code == "":
            return na_label
        return choices.get(code, x)

    return series.map(_map)


def checkbox_summary(df: pd.DataFrame, field: str) -> pd.DataFrame:
    choices = FIELD_META[field]["choices"]
    counts = {}
    for code, label in choices.items():
        col = f"{field}___{code}"
        if col in df.columns:
            counts[label] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).sum()
    out = pd.DataFrame({"Opção": list(counts.keys()), "Respostas": list(counts.values())})
    return out.sort_values("Respostas", ascending=True)


def likert_distribution(df: pd.DataFrame, field: str) -> pd.DataFrame:
    decoded = decode_series(df[field], field)
    counts = decoded.value_counts().reindex(LIKERT_ORDER, fill_value=0)
    pct = (counts / counts.sum() * 100).round(1)
    return pd.DataFrame({"Resposta": LIKERT_ORDER, "Contagem": counts.values, "Percentual": pct.values})


def agreement_score(df: pd.DataFrame, field: str) -> float:
    """% que concorda parcial ou totalmente (código 4 ou 5)."""
    vals = pd.to_numeric(df[field], errors="coerce")
    valid = vals.dropna()
    if len(valid) == 0:
        return np.nan
    return round((valid.isin([4, 5]).sum() / len(valid)) * 100, 1)


def yesno_pct(df: pd.DataFrame, field: str) -> float:
    vals = df[field].map(normalize_code)
    valid = vals[vals.isin(["0", "1"])]
    if len(valid) == 0:
        return np.nan
    return round((valid == "1").sum() / len(valid) * 100, 1)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_redcap_records(api_url: str, api_token: str) -> pd.DataFrame:
    """Busca os registros de resposta via REDCap API (content='record', formato CSV)."""
    data = {
        "token": api_token,
        "content": "record",
        "format": "csv",
        "type": "flat",
        "rawOrLabel": "raw",
        "returnFormat": "csv",
    }
    r = requests.post(api_url, data=data, timeout=30)
    if r.status_code != 200:
        raise ValueError(f"HTTP {r.status_code}: {r.text[:300]}")
    if r.text.strip().startswith("<") or '"error"' in r.text[:200].lower():
        raise ValueError(f"REDCap retornou um erro: {r.text[:300]}")
    return pd.read_csv(io.StringIO(r.text))


REDCAP_API_URL = st.secrets.get("REDCAP_API_URL", "")
REDCAP_API_TOKEN = st.secrets.get("REDCAP_API_TOKEN", "")

st.sidebar.markdown("## 📁 Fonte de dados — API do REDCap")
if REDCAP_API_URL:
#    st.sidebar.caption(f"`{REDCAP_API_URL}`")
    fetch_clicked = st.sidebar.button("🔄 Atualizar dados do REDCap", use_container_width=True)

if fetch_clicked:
    st.cache_data.clear()

using_demo = False
raw_df = None
api_error = None

if REDCAP_API_URL and REDCAP_API_TOKEN:
    try:
        with st.spinner("Buscando dados do REDCap..."):
            raw_df = fetch_redcap_records(REDCAP_API_URL, REDCAP_API_TOKEN)
        st.sidebar.success(f"{len(raw_df)} registro(s) carregado(s) do REDCap.")
    except Exception as e:
        api_error = str(e)
else:
    st.sidebar.warning(
        "Credenciais não configuradas. Preencha REDCAP_API_URL e REDCAP_API_TOKEN "
        "em `.streamlit/secrets.toml`."
    )

if raw_df is None:
    using_demo = True
    raw_df = generate_demo_data()

if api_error:
    st.sidebar.error(f"Falha ao buscar dados do REDCap: {api_error}")

df = raw_df.copy()

st.sidebar.markdown("---")
st.sidebar.markdown("## 🔎 Filtros")

def multiselect_decoded(label, field, df):
    choices = FIELD_META[field]["choices"]
    if field not in df.columns:
        return None
    options = sorted(set(decode_series(df[field], field).dropna()) - {""})
    selected = st.sidebar.multiselect(label, options, default=options)
    return selected

sel_vinculo = multiselect_decoded("Unidade / Vínculo institucional", "vinculo_institucional", df)
sel_categoria = multiselect_decoded("Categoria profissional", "categoria_profissional", df)

filtered = df.copy()
if sel_vinculo is not None:
    filtered = filtered[decode_series(filtered["vinculo_institucional"], "vinculo_institucional").isin(sel_vinculo)]
if sel_categoria is not None:
    filtered = filtered[decode_series(filtered["categoria_profissional"], "categoria_profissional").isin(sel_categoria)]

st.sidebar.markdown("---")
st.sidebar.caption(f"**{len(filtered)}** de **{len(df)}** respondentes selecionados")

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:14px; margin-bottom:0;">
        <div style="font-size:2.2rem;">🔬</div>
        <div>
            <h1 style="margin-bottom:0;">Percepção sobre Atividades de Pesquisa</h1>
            <p style="color:#5A6B70; margin-top:2px;">FAMERP / FUNFARME — Centro de Apoio à Pesquisa e Publicação (CENAP)</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if api_error:
    st.markdown(
        f'<div class="demo-banner" style="background:#FDECEA; border-color:#C7373F;">'
        f'❌ Não foi possível buscar os dados do REDCap: <code>{api_error}</code><br>'
        f'Exibindo dados de demonstração enquanto isso.</div>',
        unsafe_allow_html=True,
    )
elif using_demo:
    st.markdown(
        '<div class="demo-banner">⚠️ Exibindo <b>dados de demonstração</b> (simulados) para ilustrar o dashboard. '
        'Preencha REDCAP_API_URL e REDCAP_API_TOKEN em <code>.streamlit/secrets.toml</code> para carregar os dados reais.</div>',
        unsafe_allow_html=True,
    )

if filtered.empty:
    st.warning("Nenhum respondente corresponde aos filtros selecionados.")
    st.stop()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Respondentes", len(filtered))
k2.metric("Participam de pesquisa", f"{yesno_pct(filtered, 'participa_pesquisa')}%")
k3.metric("Publicaram (últ. 5 anos)", f"{yesno_pct(filtered, 'publicacao_cinco_anos')}%")
k4.metric("Concordam c/ importância da pesquisa", f"{agreement_score(filtered, 'importancia_pesquisa_inovacao')}%")
k5.metric("Já utilizaram o CENAP", f"{yesno_pct(filtered, 'utilizou_cenap')}%")

st.markdown("")

tab_perfil, tab_pesquisa, tab_obstaculos, tab_cenap, tab_comentarios = st.tabs(
    ["👥 Perfil dos Respondentes", "📊 Pesquisa & Publicação", "🚧 Obstáculos & Motivação",
     "🏛️ Avaliação do CENAP", "💬 Comentários"]
)

with tab_perfil:
    c1, c2 = st.columns(2)

    with c1:
        vinc = decode_series(filtered["vinculo_institucional"], "vinculo_institucional").value_counts()
        fig = px.bar(
            vinc.sort_values(ascending=True), orientation="h",
            title="Unidade do complexo FAMERP/FUNFARME",
            color_discrete_sequence=[PRIMARY],
            labels={"value": "Respondentes", "index": ""},
        )
        fig.update_layout(showlegend=False, height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        cat = decode_series(filtered["categoria_profissional"], "categoria_profissional").value_counts()
        fig2 = px.pie(
            names=cat.index, values=cat.values,
            title="Categoria profissional",
            color_discrete_sequence=px.colors.sequential.Teal[::-1],
            hole=0.45,
        )
        fig2.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    if "setor_trabalho" in filtered.columns:
        setor_counts = filtered["setor_trabalho"].value_counts().head(12).sort_values(ascending=True)
        fig3 = px.bar(
            setor_counts, orientation="h",
            title="Setores de trabalho mais frequentes (top 12)",
            color_discrete_sequence=[SECONDARY],
            labels={"value": "Respondentes", "index": ""},
        )
        fig3.update_layout(showlegend=False, height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig3, use_container_width=True)

with tab_pesquisa:
    c1, c2, c3, c4 = st.columns(4)
    for col, field, label in [
        (c1, "participa_pesquisa", "Participa de projeto de pesquisa"),
        (c2, "publicacao_cinco_anos", "Publicou nos últimos 5 anos"),
        (c3, "eventos_cientificos", "Participa de eventos científicos"),
        (c4, "apresentacao_trabalho_evento", "Apresentou trabalho em evento"),
    ]:
        pct = yesno_pct(filtered, field)
        col.metric(label, f"{pct}%")

    st.markdown("#### Percepções sobre a pesquisa científica")
    c1, c2 = st.columns(2)
    for col, field, title in [
        (c1, "importancia_pesquisa_inovacao", "Pesquisa é importante p/ assistência, ensino e inovação"),
        (c2, "pesquisa_desenvolvimento_profissional", "Pesquisa contribuiu p/ meu desenvolvimento profissional"),
    ]:
        dist = likert_distribution(filtered, field)
        fig = px.bar(
            dist, x="Percentual", y=["" for _ in range(len(dist))], color="Resposta",
            orientation="h", text=dist["Percentual"].map(lambda v: f"{v}%"),
            color_discrete_sequence=LIKERT_COLORS,
            category_orders={"Resposta": LIKERT_ORDER},
            title=title,
        )
        fig.update_layout(
            barmode="stack", height=200, showlegend=(col == c2),
            legend=dict(orientation="h", yanchor="bottom", y=-0.6),
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis_title="% de respondentes", yaxis_title="",
        )
        col.plotly_chart(fig, use_container_width=True)

    if filtered["evento_apresentado"].astype(str).str.strip().replace("nan", "").ne("").any():
        st.markdown("#### Eventos científicos mencionados")
        eventos = filtered["evento_apresentado"].dropna().astype(str)
        eventos = eventos[eventos.str.strip() != ""]
        if not eventos.empty:
            ev_counts = eventos.value_counts().head(10).sort_values(ascending=True)
            fig4 = px.bar(
                ev_counts, orientation="h", color_discrete_sequence=[ACCENT],
                labels={"value": "Menções", "index": ""},
            )
            fig4.update_layout(showlegend=False, height=350, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig4, use_container_width=True)

with tab_obstaculos:
    c1, c2 = st.columns(2)
    with c1:
        obst = checkbox_summary(filtered, "obstaculos_pesquisa")
        fig = px.bar(
            obst, x="Respostas", y="Opção", orientation="h",
            title="Principais obstáculos para desenvolver pesquisas",
            color_discrete_sequence=["#C7373F"],
            text="Respostas",
        )
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        mot = checkbox_summary(filtered, "motivacao_pesquisa")
        fig2 = px.bar(
            mot, x="Respostas", y="Opção", orientation="h",
            title="O que mais motivaria o desenvolvimento de pesquisas",
            color_discrete_sequence=[SECONDARY],
            text="Respostas",
        )
        fig2.update_layout(height=460, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.caption("Cada respondente podia selecionar até três opções em cada pergunta.")

with tab_cenap:
    c1, c2, c3 = st.columns(3)
    c1.metric("Conhece as atividades do CENAP", f"{agreement_score(filtered, 'conhecimento_cenap')}%")
    c2.metric("Já utilizou os serviços", f"{yesno_pct(filtered, 'utilizou_cenap')}%")
    c3.metric("Considera o CENAP importante p/ a instituição", f"{agreement_score(filtered, 'papel_cenap_instituicao')}%")

    st.markdown("#### Satisfação com o CENAP")
    cenap_fields = [
        ("atendimento_cenap", "Qualidade do atendimento"),
        ("orientacoes_cenap", "Clareza das orientações"),
        ("servicos_cenap", "Satisfação geral com os serviços"),
    ]
    for field, title in cenap_fields:
        dist = likert_distribution(filtered, field)
        fig = px.bar(
            dist, x="Percentual", y=["" for _ in range(len(dist))], color="Resposta",
            orientation="h", text=dist["Percentual"].map(lambda v: f"{v}%"),
            color_discrete_sequence=LIKERT_COLORS,
            category_orders={"Resposta": LIKERT_ORDER},
            title=title,
        )
        fig.update_layout(
            barmode="stack", height=180,
            showlegend=(field == "servicos_cenap"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.9),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title="% de respondentes", yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Conhecimento e uso do CENAP, por categoria profissional")
    cross = filtered.copy()
    cross["categoria_profissional"] = decode_series(cross["categoria_profissional"], "categoria_profissional")
    cross["utilizou_cenap"] = decode_series(cross["utilizou_cenap"], "utilizou_cenap")
    cross_tab = (
        cross.groupby(["categoria_profissional", "utilizou_cenap"]).size().reset_index(name="Respostas")
    )
    fig5 = px.bar(
        cross_tab, x="categoria_profissional", y="Respostas", color="utilizou_cenap",
        barmode="group", color_discrete_map={"Sim": PRIMARY, "Não": "#C7373F"},
        labels={"categoria_profissional": "Categoria profissional", "utilizou_cenap": "Já utilizou o CENAP?"},
    )
    fig5.update_layout(height=420, xaxis_tickangle=-25, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig5, use_container_width=True)

with tab_comentarios:
    comments = filtered["comentarios_sugestoes"].dropna().astype(str)
    comments = comments[comments.str.strip() != ""]
    st.markdown(f"#### {len(comments)} comentário(s) recebido(s)")
    if comments.empty:
        st.info("Nenhum comentário registrado para os filtros selecionados.")
    else:
        for c in comments:
            st.markdown(
                f"""<div style="background:white; border-left:4px solid {PRIMARY};
                border-radius:6px; padding:10px 14px; margin-bottom:8px;
                box-shadow:0 1px 3px rgba(0,0,0,0.04);">💬 {c}</div>""",
                unsafe_allow_html=True,
            )

st.caption("Dashboard construído por Tiago Henrique para o Centro de Apoio à Pesquisa e Publicação (CENAP) — FAMERP/FUNFARME. 2026")
