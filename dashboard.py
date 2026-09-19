import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

from streamlit_autorefresh import st_autorefresh

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import os
import re
import time

from dotenv import load_dotenv
import ollama


# ===========================================================
# CONFIGURATION
# ===========================================================

load_dotenv()



# ============================================================
# CONFIGURATION OLLAMA
# ============================================================

OLLAMA_MODEL = "gemma3:latest"



DB_PATH = "wis2_monitor.db"

# Timezone de référence pour "aujourd'hui" / "hier" / dates sans année
LOCAL_TZ = ZoneInfo("Africa/Casablanca")

# Première date pour laquelle des données existent (utilisée comme borne
# par défaut quand aucune date n'est détectée dans la question)
DATA_START_DATE = datetime(2026, 8, 20, tzinfo=LOCAL_TZ)


# ===========================================================
# STREAMLIT
# ===========================================================

st.set_page_config(
    page_title="WIS2 Monitoring Dashboard",
    page_icon="🌍",
    layout="wide"
)



# Actualisation toutes les 15 minutes
st_autorefresh(
    interval=900000,
    key="refresh"
)

st.title("🌍 WIS2 Monitoring Dashboard")

st.caption(
    f"Dernière mise à jour : "
    f"{pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}"
)

st.markdown(
    "Analyse des événements WIS2 enregistrés dans SQLite."
)


# ===========================================================
# COULEURS
# ===========================================================

COLOR_MAP = {
    "DEBUG": "#3498db",
    "INFO": "#2ecc71",
    "WARNING": "#f39c12",
    "ERROR": "#e74c3c",
    "CRITICAL": "#8e0000"
}


SEVERITY_ORDER = {
    "DEBUG": 1,
    "INFO": 2,
    "WARNING": 3,
    "ERROR": 4,
    "CRITICAL": 5
}


# ===========================================================
# COORDONNÉES DES CENTRES WIS2
# ===========================================================

WIS2_LOCATIONS = {

    # =======================================================
    # AMÉRIQUE / CARAÏBES
    # =======================================================

    "bb-barbadosmetservices": (13.1939, -59.5432),

    "bz-nms": (17.2510, -88.7590),

    "ca-eccc-msc": (45.4215, -75.6972),
    "ca-eccc-msc-global-discovery-catalogue": (45.4215, -75.6972),
    "ca-eccc-global-discovery-catalogue": (45.4215, -75.6972),

    "cl-meteochile": (-33.4489, -70.6693),

    "co-ideam": (4.7110, -74.0721),

    "cr-imn": (9.9281, -84.0907),

    "cu-insmet": (23.1136, -82.3666),

    "cv-inmg": (14.9331, -23.5133),

    "do-indomet": (18.4861, -69.9312),

    "hn-cenaos": (14.0723, -87.1921),

    "mx-smn": (19.4326, -99.1332),

    "pa-imhpa": (8.9824, -79.5199),

    "sr-metservice": (5.8520, -55.2038),

    "tt-trin-met": (10.6596, -61.5086),

    "us-noaa-global-broker": (38.9072, -77.0369),

    "us-ucsd-scripps-ldl": (32.7157, -117.1611),

    "ve-inameh": (10.4170, -66.8750),


    # =======================================================
    # AMÉRIQUE DU SUD
    # =======================================================

    "br-inmet": (-15.7939, -47.8828),
    "br-inmet-global-broker": (-15.7939, -47.8828),

    "ec-inamhi": (-0.1807, -78.4678),


    # =======================================================
    # AFRIQUE DE L'OUEST
    # =======================================================

    "bj-meteobenin": (6.3703, 2.3912),

    "ci-sodexam": (5.3364, -4.0267),

    "gh-gmet": (5.6037, -0.1870),

    "gn-anm": (9.6412, -13.5784),
    "gn-meteo-guinee-conakry": (9.6412, -13.5784),

    "ml-malimeteo": (12.6392, -8.0029),

    "sn-anacim": (14.7167, -17.4677),

    "tg-anamet": (6.1375, 1.2123),


    # =======================================================
    # AFRIQUE CENTRALE
    # =======================================================

    "cm-meteocameroon": (3.8480, 11.5021),

    # République du Congo
    "cg-met": (-4.2634, 15.2429),

    "td-anam": (12.1348, 15.0557),

    # Burundi
    "bi-igebu": (-3.3731, 29.9189),

    "rw-rma": (-1.9441, 30.0619),


    # =======================================================
    # AFRIQUE DE L'EST
    # =======================================================

    "dj-anm": (11.5880, 43.1456),

    "ke-meteo": (-1.2921, 36.8219),

    "mw-dccms": (-13.9626, 33.7741),

    "mz-inam": (-25.9692, 32.5732),

    "sc-seychelles-met": (-4.6191, 55.4513),

    "tz-tma": (-6.7924, 39.2083),


    # =======================================================
    # AFRIQUE AUSTRALE
    # =======================================================

    "za-weathersa": (-25.7479, 28.2293),

    "zm-zmd": (-15.3875, 28.3228),

    "zw-msd": (-17.8292, 31.0522),


    # =======================================================
    # AFRIQUE DU NORD
    # =======================================================

    # Maroc - Direction Générale de la Météorologie
    "ma-marocmeteo": (33.9716, -6.8498),


    # =======================================================
    # EUROPE
    # =======================================================

    "be-rmib": (50.9014, 4.4844),

    "bg-nimh": (42.6977, 23.3219),

    "cy-dom": (35.1856, 33.3823),

    "de-dwd-global-cache": (50.7374, 7.0982),
    "de-dwd-global-discovery-catalogue": (50.7374, 7.0982),

    "fr-ifremer-argo": (48.3904, -4.4861),

    "fr-meteofrance": (48.8566, 2.3522),
    "fr-meteofrance-global-broker": (48.8566, 2.3522),

    "int-ecmwf": (51.4260, -0.9760),

    "int-eumetsat": (49.6290, 6.1540),

    "it-meteoam": (41.9028, 12.4964),

    "pl-imgw": (52.2297, 21.0122),

    "rs-rhmz": (44.7866, 20.4489),

    "uk-metoffice": (50.7184, -3.5339),


    # =======================================================
    # MOYEN-ORIENT
    # =======================================================

    "ir-irimo": (35.6892, 51.3890),

    "sa-ncm": (24.7136, 46.6753),
    "sa-ncm-global-cache": (24.7136, 46.6753),


    # =======================================================
    # ASIE
    # =======================================================

    "bn-bdmd": (4.9031, 114.9398),

    "cn-cma": (39.9042, 116.4074),
    "cn-cma-global-broker": (39.9042, 116.4074),
    "cn-cma-global-cache": (39.9042, 116.4074),
    "cn-cma-global-discovery-catalogue": (39.9042, 116.4074),
    "cn-cma-global-gateway": (39.9042, 116.4074),
    "cn-cma-global-monitor": (39.9042, 116.4074),

    "id-bmkg": (-6.1525, 106.8470),

    "jp-jma": (35.6762, 139.6503),
    "jp-jma-global-cache": (35.6762, 139.6503),

    "kg-kyrgyzhydromet": (42.8746, 74.5698),

    "kr-kma": (36.4800, 127.0000),
    "kr-kma-global-cache": (36.4800, 127.0000),

    "my-metmalaysia": (3.1390, 101.6869),

    "np-nepalmet": (27.7172, 85.3240),

    "ph-pagasa": (14.6488, 121.0509),

    "sg-mss": (1.3521, 103.8198),
    "sg-mss-asmc": (1.3521, 103.8198),


    # =======================================================
    # PACIFIQUE
    # =======================================================

    "ck-metservice": (-21.2367, -159.7777),

    "nu-metservice": (-19.0544, -169.8672),

    "nz-metservice": (-41.2866, 174.7756),

    "tk-metservice": (-9.2000, -171.8500),


    # =======================================================
    # CENTRES / SERVICES INTERNATIONAUX
    # =======================================================

    "data-metoffice-noaa-global-cache": (51.4964, -0.1224),

    "org-woudc": (43.6532, -79.3832),

}
# ===========================================================
# CHARGEMENT DES DONNÉES
# ===========================================================

@st.cache_data(ttl=10)
def load_data():

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        id,
        subject,
        source,
        severity,
        content_title,
        content_description,
        event_time,
        received_at,
        validation_errors
    FROM wme_events
    """

    df = pd.read_sql(query, conn)

    conn.close()

    if df.empty:
        return df

    df["received_at"] = pd.to_datetime(
        df["received_at"],
        utc=True,
        errors="coerce"
    )

    # Pour les graphiques
    df["received_at"] = df["received_at"].dt.tz_localize(None)

    df["date"] = df["received_at"].dt.date
    df["hour"] = df["received_at"].dt.hour
    df["day_name"] = df["received_at"].dt.day_name()

    return df


df_original = load_data()


if df_original.empty:

    st.warning("⚠️ Aucune donnée disponible dans SQLite.")

    st.info(
        "Vérifiez que wis2_monitor.py écoute bien le broker "
        "et enregistre les événements."
    )

    st.stop()


# Liste des centres connus (subject + source), utilisée par le chatbot
# pour reconnaître un identifiant de centre cité dans une question.
KNOWN_CENTRES = sorted(
    set(df_original["subject"].dropna())
    | set(df_original["source"].dropna())
)


# ===========================================================
# DATE DU JOUR - MAROC
# ===========================================================

def _today_bounds_utc():

    morocco_now = datetime.now(
        ZoneInfo("Africa/Casablanca")
    )

    start_local = morocco_now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    end_local = start_local + timedelta(days=1)

    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    return (
        start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        morocco_now
    )


# ===========================================================
# SIDEBAR
# ===========================================================

st.sidebar.title("⚙️ Filtres")

centres = sorted(
    df_original["subject"]
    .dropna()
    .unique()
)

selected_centres = st.sidebar.multiselect(
    "Centre WIS2",
    centres,
    default=centres
)


severities = sorted(
    df_original["severity"]
    .dropna()
    .unique()
)

selected_severity = st.sidebar.multiselect(
    "Sévérité",
    severities,
    default=severities
)


date_min = df_original["received_at"].min().date()
date_max = df_original["received_at"].max().date()


selected_dates = st.sidebar.date_input(
    "Période",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max
)


# ===========================================================
# APPLICATION DES FILTRES
# ===========================================================

df = df_original.copy()

df = df[
    df["subject"].isin(selected_centres)
]

df = df[
    df["severity"].isin(selected_severity)
]


if len(selected_dates) == 2:

    start_date = pd.to_datetime(
        selected_dates[0]
    )

    end_date = (
        pd.to_datetime(selected_dates[1])
        + pd.Timedelta(days=1)
    )

    df = df[
        (df["received_at"] >= start_date)
        &
        (df["received_at"] < end_date)
    ]


# ===========================================================
# NORMALISATION DES CENTRES WIS2
# ===========================================================

def normalize_wis2_center(subject):

    if pd.isna(subject):
        return None

    centre = str(subject).strip().lower()

    # Suppression des suffixes Global Services
    suffixes = [
        "-global-broker",
        "-global-cache",
        "-global-monitor",
        "-global-discovery-catalogue",
        "-global-gateway"
    ]

    for suffix in suffixes:
        if centre.endswith(suffix):
            centre = centre[:-len(suffix)]
            break

    return centre


# Identifiant normalisé
df["center_id"] = df["subject"].apply(
    normalize_wis2_center
)


# ===========================================================
# RECHERCHE DES COORDONNÉES
# ===========================================================

def get_coordinates(center_id):

    if center_id in WIS2_LOCATIONS:
        return WIS2_LOCATIONS[center_id]

    return (None, None)


df[["lat", "lon"]] = df["center_id"].apply(
    lambda x: pd.Series(
        get_coordinates(x)
    )
)


# ===========================================================
# CENTRES NON LOCALISÉS
# ===========================================================

unknown_centres = sorted(
    set(
        df.loc[
            df["lat"].isna() | df["lon"].isna(),
            "subject"
        ].dropna()
    )
)


if unknown_centres:

    st.warning(
        f"⚠️ {len(unknown_centres)} centre(s) WIS2 "
        "non localisé(s)"
    )

    with st.expander(
        "🔎 Voir les centres non localisés"
    ):

        for centre in unknown_centres:

            st.write(
                f"• `{centre}`"
            )


# ===========================================================
# KPIs
# ===========================================================

st.subheader("📈 Vue d'ensemble")

col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "📄 Total événements",
    len(df)
)


col2.metric(
    "🏢 Centres WIS2",
    df["subject"].nunique()
)


col3.metric(
    "📡 Sources",
    df["source"].nunique()
)


col4.metric(
    "🚨 Critiques",
    len(
        df[
            df["severity"] == "CRITICAL"
        ]
    )
)


# ===========================================================
# STATISTIQUES SIDEBAR
# ===========================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "📊 Statistiques"
)

st.sidebar.write(
    f"Total : {len(df)}"
)

st.sidebar.write(
    f"Centres : {df.subject.nunique()}"
)

st.sidebar.write(
    f"Sources : {df.source.nunique()}"
)

st.sidebar.write(
    f"INFO : {(df.severity == 'INFO').sum()}"
)

st.sidebar.write(
    f"WARNING : {(df.severity == 'WARNING').sum()}"
)

st.sidebar.write(
    f"ERROR : {(df.severity == 'ERROR').sum()}"
)

st.sidebar.write(
    f"CRITICAL : {(df.severity == 'CRITICAL').sum()}"
)


# ===========================================================
# EXPORT CSV
# ===========================================================

csv = df.to_csv(
    index=False
).encode("utf-8")


st.sidebar.markdown("---")

st.sidebar.subheader(
    "📥 Export"
)


st.sidebar.download_button(
    label="📄 Télécharger le CSV",
    data=csv,
    file_name="wme_events.csv",
    mime="text/csv"
)


# ===========================================================
# GRAPHIQUES
# ===========================================================

if df.empty:

    st.info(
        "Aucun événement ne correspond "
        "aux filtres sélectionnés."
    )

else:

    # -------------------------------------------------------
    # 1. Sévérité
    # -------------------------------------------------------

    severity = (
        df.groupby("severity")
        .size()
        .reset_index(name="Nombre")
    )

    fig = px.pie(
        severity,
        names="severity",
        values="Nombre",
        title="Répartition des événements par niveau de sévérité",
        color="severity",
        color_discrete_map=COLOR_MAP
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # -------------------------------------------------------
    # 2. Nombre d'événements par centre WIS2
    # -------------------------------------------------------

    center = (
    df.groupby("subject")
    .size()
    .reset_index(name="Nombre")
    .sort_values("Nombre", ascending=False)
    )

    # Garder seulement les 15 centres les plus actifs
    center_top = center.head(15)

    fig = px.bar(
    center_top,
    x="Nombre",
    y="subject",
    orientation="h",
    title="Top 15 des centres WIS2 par nombre d'événements",
    text="Nombre"
    )

    fig.update_traces(
    textposition="outside"
   )

    fig.update_layout(
    yaxis={
        "categoryorder": "total ascending"
    },
    height=600
    )

    st.plotly_chart(
    fig,
    use_container_width=True
    )


    # -------------------------------------------------------
    # 3. Evolution
    # -------------------------------------------------------

    # -------------------------------------------------------
    # 3. Évolution des événements dans le temps
    # -------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

    df_timeline = pd.read_sql_query("""
    SELECT received_at
    FROM wme_events
    WHERE received_at IS NOT NULL
    """, conn)

    conn.close()

    #  Conversion UTC → Casablanca
    df_timeline["received_at"] = pd.to_datetime(
    df_timeline["received_at"],
    utc=True,
    errors="coerce"
    )

    df_timeline["date"] = (
    df_timeline["received_at"]
    .dt.tz_convert("Africa/Casablanca")
    .dt.date
    )

    timeline = (
    df_timeline
    .dropna(subset=["date"])
    .groupby("date")
    .size()
    .reset_index(name="Nombre")
    )

    timeline["date"] = pd.to_datetime(timeline["date"])

    fig = px.line(
    timeline,
    x="date",
    y="Nombre",
    markers=True,
    title="Évolution des événements dans le temps"
    )

    fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Nombre d'événements",
    hovermode="x unified"
    )

    st.plotly_chart(
    fig,
    use_container_width=True
    )

    # -------------------------------------------------------
    # 4. Répartition horaire
    # -------------------------------------------------------

    hour = (
        df.groupby("hour")
        .size()
        .reset_index(name="Nombre")
    )

    fig = px.bar(
        hour,
        x="hour",
        y="Nombre",
        title="Répartition horaire"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # -------------------------------------------------------
    # 5. Heatmap
    # -------------------------------------------------------

    heat = (
        df.groupby(
            ["day_name", "hour"]
        )
        .size()
        .reset_index(name="Nombre")
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    heat["day_name"] = pd.Categorical(
        heat["day_name"],
        categories=days,
        ordered=True
    )

    pivot = (
        heat
        .pivot(
            index="day_name",
            columns="hour",
            values="Nombre"
        )
        .fillna(0)
    )

    pivot = pivot.reindex(days)

    fig = px.imshow(
        pivot,
        aspect="auto",
        title="Heatmap Jour × Heure",
        labels={
            "x": "Heure",
            "y": "Jour",
            "color": "Nombre"
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # -------------------------------------------------------
    # 6. Top 10 centres CRITICAL
    # -------------------------------------------------------

    critical = (
        df[
            df.severity == "CRITICAL"
        ]
        .groupby("subject")
        .size()
        .reset_index(name="Nombre")
        .sort_values(
            "Nombre",
            ascending=False
        )
        .head(10)
    )

    fig = px.bar(
        critical,
        x="Nombre",
        y="subject",
        orientation="h",
        title="Top 10 des centres générant des événements critiques"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # -------------------------------------------------------
    # 7. Types d'événements
    # -------------------------------------------------------

    titles = (
        df.groupby("content_title")
        .size()
        .reset_index(name="Nombre")
        .sort_values(
            "Nombre",
            ascending=False
        )
        .head(10)
    )

    fig = px.bar(
        titles,
        x="Nombre",
        y="content_title",
        orientation="h",
        title="Top 10 des types d'événements"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # -------------------------------------------------------
    # 8. Sévérité par centre
    # -------------------------------------------------------

    stack = (
        df.groupby(
            ["subject", "severity"]
        )
        .size()
        .reset_index(name="Nombre")
    )

    fig = px.bar(
        stack,
        x="subject",
        y="Nombre",
        color="severity",
        color_discrete_map=COLOR_MAP,
        title="Répartition par catégorie de sévérité et par centre",
        barmode="stack"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # -------------------------------------------------------
    # 9. Derniers événements
    # -------------------------------------------------------

    st.divider()

    st.subheader(
        "📋 Derniers événements"
    )

    st.dataframe(
        df.sort_values(
            "received_at",
            ascending=False
        )[
            [
                "received_at",
                "subject",
                "severity",
                "content_title"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


    # ===========================================================
# 10. CARTE MONDIALE DES CENTRES WIS2
# ===========================================================

st.divider()

st.subheader(
    "🌍 Carte mondiale des centres WIS2"
)


# ===========================================================
# PRÉPARATION DES DONNÉES
# ===========================================================

map_source_df = df.dropna(
    subset=["lat", "lon"]
).copy()


if map_source_df.empty:

    st.info(
        "Aucun centre WIS2 localisé "
        "pour la sélection actuelle."
    )

else:

    # -------------------------------------------------------
    # Nombre d'événements par centre
    # -------------------------------------------------------

    count_df = (
        map_source_df
        .groupby(
            [
                "center_id",
                "subject",
                "lat",
                "lon"
            ]
        )
        .size()
        .reset_index(
            name="Nombre"
        )
    )


    # -------------------------------------------------------
    # Sévérité dominante
    # -------------------------------------------------------

    map_source_df["severity_rank"] = (
        map_source_df["severity"]
        .map(SEVERITY_ORDER)
        .fillna(0)
    )


    severity_df = (
        map_source_df
        .sort_values(
            "severity_rank"
        )
        .groupby(
            [
                "center_id",
                "subject",
                "lat",
                "lon"
            ],
            as_index=False
        )
        .last()
    )


    severity_df = severity_df[
        [
            "center_id",
            "subject",
            "lat",
            "lon",
            "severity"
        ]
    ]


    # -------------------------------------------------------
    # Fusion
    # -------------------------------------------------------

    map_df = count_df.merge(
        severity_df,
        on=[
            "center_id",
            "subject",
            "lat",
            "lon"
        ],
        how="left"
    )


    # =======================================================
    # CARTE
    # =======================================================

    fig = px.scatter_geo(
        map_df,

        lat="lat",
        lon="lon",

        size="Nombre",

        color="severity",

        hover_name="subject",

        hover_data={
            "center_id": True,
            "Nombre": True,
            "severity": True,
            "lat": False,
            "lon": False
        },

        size_max=35,

        color_discrete_map=COLOR_MAP,

        projection="natural earth"
    )


    # =======================================================
    # STYLE DES MARKERS
    # =======================================================

    fig.update_traces(
        marker=dict(
            line=dict(
                width=1,
                color="black"
            ),
            opacity=0.85
        )
    )


    # =======================================================
    # CONFIGURATION DE LA CARTE
    # =======================================================

    fig.update_geos(

        showland=True,

        landcolor="rgb(235,235,235)",

        showcountries=True,

        countrycolor="gray",

        showcoastlines=True,

        coastlinecolor="gray",

        showocean=True,

        oceancolor="rgb(220,235,245)",

        showlakes=True,

        lakecolor="rgb(220,235,245)",

        projection_type="natural earth",

        fitbounds="locations"
    )


    # =======================================================
    # LAYOUT
    # =======================================================

    fig.update_layout(

        height=700,

        
        margin=dict(
            l=0,
            r=0,
            t=50,
            b=0
        ),

        legend_title_text="Sévérité"
    )


    # =======================================================
    # AFFICHAGE
    # =======================================================

    st.plotly_chart(
        fig,
        use_container_width=True
    )


   

# ===========================================================
# ===========================================================
# 🤖 ASSISTANT IA WIS2 — PIPELINE INTELLIGENT




# -----------------------------------------------------------
# 1. ANALYSE DE LA QUESTION : extraction date / centre / sévérité
# -----------------------------------------------------------

_STOPWORDS_FR = {
    "que", "qu", "se", "passe", "t", "il", "avec", "de", "des", "les", "le",
    "la", "un", "une", "y", "a", "est", "ce", "quels", "quelles", "quel",
    "quelle", "sont", "pour", "chez", "sur", "dans", "du", "au", "aux",
    "et", "ou", "en", "d", "l", "s", "n", "c", "je", "tu", "elle",
    "nous", "vous", "ils", "elles", "moi", "montre", "montrer", "donne",
    "donner", "liste", "lister", "afficher", "affiche", "existe",
}


def extract_keywords(question):
    """
    Extrait les mots-clés pertinents d'une question, en priorité les
    identifiants de centre WIS2 (motif "xx-yyyy", ex: cn-cma), sinon les
    mots significatifs (hors mots vides français).
    """
    q_lower = question.lower()

    raw_matches = re.findall(r"\b[a-z]{2,4}(?:-[a-z0-9]+)+\b", q_lower)
    centre_ids = [
        m for m in raw_matches
        if all(len(part) >= 2 for part in m.split("-")[1:])
    ]
    if centre_ids:
        return centre_ids

    words = re.findall(r"[a-zàâäéèêëïîôöùûüç0-9]+", q_lower)
    keywords = [w for w in words if w not in _STOPWORDS_FR and len(w) > 2]

    return keywords or [question]


def _day_bounds_utc(local_dt):
    """Bornes UTC [début, fin) de la journée locale contenant local_dt."""
    start_local = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def extract_date_filter(question):
    """
    Détecte une référence temporelle dans la question et retourne
    (start_utc_str, end_utc_str, label) ou None si aucune date détectée.

    Couvre : "aujourd'hui" / "ce jour", "hier", "cette semaine",
    dates explicites "21/08", "20/08/2026", plages "du X au Y",
    "depuis X jusqu'à maintenant".
    """
    q = question.lower()
    now_local = datetime.now(LOCAL_TZ)

    if re.search(r"\baujourd'?hui\b|\btoday\b|\bce jour\b", q):
        s, e = _day_bounds_utc(now_local)
        return s, e, "aujourd'hui"

    if re.search(r"\bhier\b|\byesterday\b", q):
        s, e = _day_bounds_utc(now_local - timedelta(days=1))
        return s, e, "hier"

    if re.search(r"\bcette semaine\b|\bthis week\b", q):
        start_of_week = now_local - timedelta(days=now_local.weekday())
        s, _ = _day_bounds_utc(start_of_week)
        _, e = _day_bounds_utc(now_local)
        return s, e, "cette semaine"

    if re.search(r"\bdepuis le d[ée]but\b|\btoutes les donn[ée]es\b|\bdepuis 20/?08\b", q):
        s, _ = _day_bounds_utc(DATA_START_DATE)
        _, e = _day_bounds_utc(now_local)
        return s, e, "depuis le début des données (20/08/2026)"

    date_pattern = r"(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?"
    matches = re.findall(date_pattern, q)

    def to_local_date(m):
        day, month, year = m
        year = int(year) if year else now_local.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, int(month), int(day), tzinfo=LOCAL_TZ)
        except ValueError:
            return None

    if matches:
        dates = [d for d in (to_local_date(m) for m in matches) if d]

        if dates:
            wants_until_now = re.search(
                r"jusqu'?[aà] maintenant|jusqu'?[aà] aujourd'?hui", q
            )

            if wants_until_now:
                s, _ = _day_bounds_utc(dates[0])
                _, e = _day_bounds_utc(now_local)
                label = f"du {dates[0].strftime('%d/%m/%Y')} à aujourd'hui"
                return s, e, label

            if len(dates) >= 2:
                start_d, end_d = sorted(dates)
                s, _ = _day_bounds_utc(start_d)
                _, e = _day_bounds_utc(end_d)
                label = f"du {start_d.strftime('%d/%m/%Y')} au {end_d.strftime('%d/%m/%Y')}"
                return s, e, label

            s, e = _day_bounds_utc(dates[0])
            label = f"le {dates[0].strftime('%d/%m/%Y')}"
            return s, e, label

    return None


def extract_centre(question):
    """Détecte un identifiant de centre WIS2 cité dans la question."""
    q = question.lower()

    for centre in sorted(KNOWN_CENTRES, key=len, reverse=True):
        if centre and centre.lower() in q:
            return centre

    raw_matches = re.findall(r"\b[a-z]{2,4}(?:-[a-z0-9]+)+\b", q)
    for m in raw_matches:
        if all(len(part) >= 2 for part in m.split("-")[1:]):
            return m

    return None


def extract_severity(question):
    """Détecte une sévérité citée dans la question (FR/EN)."""
    q = question.lower()
    mapping = [
        (r"\bcritical\b|\bcritiques?\b", "CRITICAL"),
        (r"\berrors?\b|\berreurs?\b", "ERROR"),
        (r"\bwarnings?\b|\bavertissements?\b", "WARNING"),
        (r"\binfos?\b", "INFO"),
        (r"\bdebug\b", "DEBUG"),
    ]
    for pattern, sev in mapping:
        if re.search(pattern, q):
            return sev
    return None


def extract_event_title(question):
    """Isole le nom de l'événement après le mot 'événement' dans la question."""
    m = re.search(r"[ée]v[ée]nement[s]?\s*[:\-]?\s*(.+)", question, re.IGNORECASE)
    if m:
        return m.group(1).strip(" ?.!\"'«»")
    return question.strip(" ?.!\"'«»")


def detect_intent(question):
    """
    Détermine l'intention de la question.
    """

    q = question.lower().strip()

    # --------------------------------------------------------
    # EXPLICATION D'UN ÉVÉNEMENT WIS2
    # --------------------------------------------------------
    if re.search(
        r"explique|explication|c'est quoi|c’est quoi|"
        r"que signifie|que veut dire|signification|définition|"
        r"pourquoi|à quoi correspond",
        q
    ):
        # Si la question contient une demande d'explication
        # et qu'elle ressemble à un événement WIS2 connu
        if find_wis2_knowledge(question):
            return "explain_event"

        # Même sans correspondance exacte, on peut considérer
        # "Explique l'événement ..." comme une demande d'explication
        if re.search(r"[ée]v[ée]nement", q):
            return "explain_event"

    # --------------------------------------------------------
    # AUJOURD'HUI
    # --------------------------------------------------------
    if (
        re.search(r"\baujourd'hui\b|\baujourd’hui\b|\bce jour\b", q)
        and "combien" in q
    ):
        return "today_count"

    # --------------------------------------------------------
    # HIER
    # --------------------------------------------------------
    if (
        re.search(r"\bhier\b", q)
        and "combien" in q
    ):
        return "yesterday_count"

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------
    if (
        "critical" in q
        or "critique" in q
        or "critiques" in q
    ) and "combien" in q:
        return "critical_count"

    # --------------------------------------------------------
    # STATISTIQUES PAR SÉVÉRITÉ
    # --------------------------------------------------------
    if (
        "répartition" in q
        or "repartition" in q
        or "statistiques par sévérité" in q
        or "statistiques des sévérités" in q
    ):
        return "severity_stats"

    # --------------------------------------------------------
    # TOP CENTRES
    # --------------------------------------------------------
    has_centre = "centre" in q

    has_plus = (
        "plus" in q
        or "maximum" in q
        or "max" in q
        or "top" in q
    )

    has_events = re.search(
        r"[ée]v[ée]nements?",
        q
    )

    if has_centre and has_plus and has_events:

        if (
            "quel centre" in q
            or "quel est le centre" in q
            or "quel est le centre qui" in q
        ):
            return "top_centre_single"

        return "top_centres_list"

    # --------------------------------------------------------
    # ÉVÉNEMENT LE PLUS FRÉQUENT
    # --------------------------------------------------------
    if (
        "plus fréquent" in q
        or "plus frequents" in q
        or "fréquent" in q
        or "frequent" in q
    ):
        return "top_titles"

        # --------------------------------------------------------
    # ÉVÉNEMENTS D'UN CENTRE
    # --------------------------------------------------------
    if (
        re.search(r"[ée]v[ée]nements?", q)
        and (
            "concerne" in q
            or "concernent" in q
            or "pour" in q
            or "du centre" in q
        )
    ):
        return "centre_events"
    # --------------------------------------------------------
    # STATISTIQUES D'UN CENTRE
    # --------------------------------------------------------
    if (
        "statistique" in q
        or "statistiques" in q
        or re.search(r"\bstats?\b", q)
    ):
        return "stats_centre"

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------
    if (
        "combien" in q
        and not re.search(
            r"aujourd'hui|aujourd’hui|hier|critical|critique",
            q
        )
        and not has_centre
    ):
        return "count"

    # --------------------------------------------------------
    # LISTE DES ÉVÉNEMENTS
    # --------------------------------------------------------
    if re.search(
        r"\bliste\b|\bmontre\b|\baffiche\b|"
        r"quels événements|quelles événements|"
        r"donne moi les événements|donne-moi les événements",
        q
    ):
        return "list_events"

    return "generic"

def analyze_question(question):
    """
    ÉTAPE "Analyse de la question" du pipeline : extrait date, centre,
    sévérité et intention, avec une continuité conversationnelle simple
    (référence implicite "ce centre" / "cette date" -> dernier contexte
    connu de la session).
    """
    date_filter = extract_date_filter(question)
    centre = extract_centre(question)
    severity = extract_severity(question)
    intent = detect_intent(question)

    q = question.lower()

    if not centre and re.search(r"\bce(?:t)? centre\b|\bce dernier\b", q):
        centre = st.session_state.get("last_centre")

    if not date_filter and re.search(r"\bce jour-l[àa]\b|\bcette date\b|\bm[êe]me jour\b", q):
        date_filter = st.session_state.get("last_date_filter")

    if centre:
        st.session_state["last_centre"] = centre
    if date_filter:
        st.session_state["last_date_filter"] = date_filter

    return {
        "intent": intent,
        "date_filter": date_filter,
        "centre": centre,
        "severity": severity,
    }


def describe_filters(filters):
    bits = []
    if filters.get("date_filter"):
        bits.append(filters["date_filter"][2])
    if filters.get("centre"):
        bits.append(f"centre = {filters['centre']}")
    if filters.get("severity"):
        bits.append(f"sévérité = {filters['severity']}")
    return ", ".join(bits) if bits else "aucun filtre particulier (toutes les données)"


# -----------------------------------------------------------
# 2. REQUÊTES SQLITE : "Résultats exacts"
# -----------------------------------------------------------

def _base_where(filters, include_centre=True):
    where = []
    params = []

    if filters.get("date_filter"):
        start, end, _ = filters["date_filter"]
        where.append("received_at >= ? AND received_at < ?")
        params.extend([start, end])

    if include_centre and filters.get("centre"):
        where.append("(LOWER(subject) LIKE ? OR LOWER(source) LIKE ?)")
        term = f"%{filters['centre'].lower()}%"
        params.extend([term, term])

    if filters.get("severity"):
        where.append("severity = ?")
        params.append(filters["severity"])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    return where_sql, params


def run_count(filters):
    where_sql, params = _base_where(filters)
    conn = sqlite3.connect(DB_PATH)
    total = pd.read_sql(
        f"SELECT COUNT(*) AS n FROM wme_events {where_sql}", conn, params=params
    ).iloc[0]["n"]
    conn.close()
    return int(total)


def run_top_centres(filters, limit=10):
    where_sql, params = _base_where(filters, include_centre=False)
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT subject, COUNT(*) AS nombre
        FROM wme_events
        {where_sql}
        GROUP BY subject
        ORDER BY nombre DESC
        LIMIT ?
    """
    df_res = pd.read_sql(query, conn, params=params + [limit])
    conn.close()
    return df_res


def run_top_titles(filters, limit=10):
    where_sql, params = _base_where(filters, include_centre=True)
    extra = "content_title IS NOT NULL"
    where_sql = (where_sql + " AND " + extra) if where_sql else "WHERE " + extra
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT content_title, COUNT(*) AS nombre
        FROM wme_events
        {where_sql}
        GROUP BY content_title
        ORDER BY nombre DESC
        LIMIT ?
    """
    df_res = pd.read_sql(query, conn, params=params + [limit])
    conn.close()
    return df_res


def run_centre_stats(filters):
    where_sql, params = _base_where(filters, include_centre=True)

    conn = sqlite3.connect(DB_PATH)

    query = f"""
        SELECT severity, COUNT(*) AS nombre
        FROM wme_events
        {where_sql}
        GROUP BY severity
        ORDER BY nombre DESC
    """

    df_res = pd.read_sql(query, conn, params=params)
    conn.close()

    # Sévérité dominante selon la hiérarchie :
    # DEBUG < INFO < WARNING < ERROR < CRITICAL
    if not df_res.empty:
        severity_rank = (
            df_res["severity"]
            .map(SEVERITY_ORDER)
            .fillna(0)
        )

        dominant_severity = df_res.loc[
            severity_rank.idxmax(),
            "severity"
        ]
    else:
        dominant_severity = None

    return df_res, dominant_severity


def run_query(filters, limit=200):
    where_sql, params = _base_where(filters, include_centre=True)
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT subject, source, severity, content_title, content_description,
               event_time, received_at
        FROM wme_events
        {where_sql}
        ORDER BY received_at DESC
        LIMIT ?
    """
    df_res = pd.read_sql(query, conn, params=params + [limit])
    conn.close()
    return df_res


def run_explain_query(snippet):
    term = f"%{snippet.lower()}%"
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT subject, source, severity, content_title, content_description,
               event_time, received_at
        FROM wme_events
        WHERE LOWER(content_title) LIKE ?
        ORDER BY received_at DESC
        LIMIT 20
    """
    df_res = pd.read_sql(query, conn, params=(term,))
    conn.close()

    if df_res.empty:
        keywords = extract_keywords(snippet)
        conditions = " OR ".join(["LOWER(content_title) LIKE ?"] * len(keywords))
        params = [f"%{kw}%" for kw in keywords]
        conn = sqlite3.connect(DB_PATH)
        query2 = f"""
            SELECT subject, source, severity, content_title, content_description,
                   event_time, received_at
            FROM wme_events
            WHERE {conditions}
            ORDER BY received_at DESC
            LIMIT 20
        """
        df_res = pd.read_sql(query2, conn, params=params)
        conn.close()

    return df_res


def dataframe_to_context(df_events, max_rows=15):
    """Formate un DataFrame (événements bruts OU résultats agrégés) en texte
    lisible pour Gemini, colonne par colonne, quel que soit son schéma."""
    if df_events is None or df_events.empty:
        return "Aucun résultat."

    lines = []
    for _, row in df_events.head(max_rows).iterrows():
        line = " | ".join(f"{col}: {row[col]}" for col in df_events.columns)
        lines.append(f"- {line}")

    remaining = len(df_events) - max_rows
    if remaining > 0:
        lines.append(f"... ({remaining} résultat(s) supplémentaire(s) non affiché(s))")

    return "\n".join(lines)


# -----------------------------------------------------------
# 3. DISPATCH : construit le contexte "résultats exacts" selon l'intention
# -----------------------------------------------------------

def build_context(question, filters):
    intent = filters["intent"]
    parts = [f"Filtres détectés automatiquement : {describe_filters(filters)}"]

    if intent == "count":
        total = run_count(filters)
        parts.append(f"Nombre EXACT d'événements correspondant aux filtres : {total}")

    elif intent == "top_centre_single":
        top = run_top_centres(filters, limit=1)
        if top.empty:
            parts.append("Aucun centre trouvé pour ces filtres.")
        else:
            row = top.iloc[0]
            parts.append(
                f"Centre avec le plus d'événements : {row['subject']} "
                f"({row['nombre']} événements)"
            )

    elif intent == "top_centres_list":
        top = run_top_centres(filters, limit=10)
        parts.append("Classement des centres par nombre d'événements (top 10) :")
        parts.append(dataframe_to_context(top))

    elif intent == "top_titles":
        top = run_top_titles(filters, limit=10)
        parts.append("Types d'événements les plus fréquents (top 10) :")
        parts.append(dataframe_to_context(top))

    elif intent == "stats_centre":
        if not filters.get("centre"):
            parts.append(
                "Aucun centre n'a été identifié dans la question ni dans "
                "l'historique de conversation : demande au préalable de "
                "préciser le centre WIS2 concerné."
            )
        else:
            stats_df, dominant_severity = run_centre_stats(filters)

            total = int(stats_df["nombre"].sum()) if not stats_df.empty else 0

            parts.append(
              f"Statistiques pour le centre {filters['centre']} "
              f"(total : {total} événements) :"
            )

            parts.append(dataframe_to_context(stats_df))

            if dominant_severity:
              parts.append(
               f"Sévérité dominante selon la hiérarchie "
               f"(DEBUG < INFO < WARNING < ERROR < CRITICAL) : "
               f"{dominant_severity}"
            )

    elif intent == "explain_event":
        snippet = extract_event_title(question)
        results = run_explain_query(snippet)
        if results.empty:
            parts.append(
                f"Aucun événement ne correspond au titre recherché : « {snippet} »."
            )
        else:
            parts.append(
                f"Occurrences trouvées pour l'événement « {snippet} » "
                f"({len(results)} au total) :"
            )
            parts.append(dataframe_to_context(results))

    else:  # list_events / generic
        results = run_query(filters)
        parts.append(f"Nombre d'événements trouvés : {len(results)}")
        if not results.empty:
            parts.append(dataframe_to_context(results))

    return "\n".join(parts)


# -----------------------------------------------------------
# # 4. APPEL OLLAMA — LLM LOCAL
# -----------------------------------------------------------

SYSTEM_INSTRUCTIONS = """
Tu es un assistant professionnel spécialisé dans la supervision de
l'infrastructure WIS2 (WMO Information System 2.0).

Règles strictes :
- Réponds TOUJOURS en français, de façon claire et professionnelle.
- Utilise UNIQUEMENT les informations présentes dans les "RÉSULTATS EXACTS"
  fournis ci-dessous. Ces chiffres proviennent directement d'une requête
  SQLite : ne les recalcule pas, ne les arrondis pas, ne les invente jamais.
- Si les résultats sont vides ou insuffisants pour répondre, dis-le
  explicitement plutôt que de fabriquer une réponse.
- Si la question demande une comparaison, base-la uniquement sur les
  chiffres fournis.
- Sois concis : réponds directement à la question posée, puis ajoute au
  besoin 1-2 phrases de contexte utile (ex: sévérité dominante, centre le
  plus actif), sans dérouler toutes les données brutes si elles ont déjà
  été résumées.
"""

# ============================================================
# 📚 BASE DE CONNAISSANCES WIS2
# ============================================================

WIS2_KNOWLEDGE_BASE = {

    "WIS2 Notification Message not compliant with the defined schema": {
        "description": (
            "Une notification WIS2 a été reçue mais sa structure ne respecte "
            "pas le schéma de notification WIS2 attendu."
        ),
        "cause": (
            "Le message peut contenir un champ obligatoire manquant, "
            "un type de donnée incorrect, une structure JSON invalide ou "
            "une valeur qui ne respecte pas les règles du schéma WIS2."
        ),
        "impact": (
            "La notification peut être rejetée ou ignorée par les composants "
            "WIS2 concernés. Cela peut empêcher la bonne annonce ou la "
            "découverte d'une donnée."
        ),
        "action": (
            "Vérifier le contenu JSON de la notification, le schéma utilisé "
            "et les champs obligatoires. Identifier le centre qui produit "
            "les notifications non conformes et corriger la génération "
            "des messages."
        ),
        "severity": "ERROR"
    },

    "Missing Metadata record for data announced in WIS2 Notification Message": {
        "description": (
            "Une notification WIS2 annonce une donnée mais le système "
            "ne trouve pas le registre de métadonnées correspondant."
        ),
        "cause": (
            "La donnée annoncée peut ne pas avoir de métadonnées disponibles, "
            "le lien vers les métadonnées peut être incorrect ou le registre "
            "de métadonnées peut être inaccessible."
        ),
        "impact": (
            "Les utilisateurs ou services WIS2 peuvent recevoir l'annonce "
            "sans disposer des informations nécessaires pour comprendre, "
            "découvrir ou exploiter correctement la donnée."
        ),
        "action": (
            "Vérifier que la donnée possède un enregistrement de métadonnées "
            "valide et que l'identifiant ou le lien utilisé dans la notification "
            "correspond bien à cet enregistrement."
        ),
        "severity": "ERROR"
    },

    "wis2.ncm.gov.sa": {
        "description": (
            "Événement associé à la cible ou au service WIS2 "
            "wis2.ncm.gov.sa."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème concernant "
            "cette cible WIS2."
        ),
        "impact": (
            "Selon le contexte de l'événement, le service peut être "
            "inaccessible ou présenter un problème de disponibilité."
        ),
        "action": (
            "Vérifier la disponibilité du service, la connectivité réseau "
            "et l'état du service WIS2 concerné."
        ),
        "severity": "ERROR"
    },

    "WCMP2 ETS report": {
        "description": (
            "Rapport ETS du WCMP2 utilisé pour suivre certains éléments "
            "de conformité ou d'évaluation d'un composant WIS2."
        ),
        "cause": (
            "Il s'agit principalement d'un rapport généré dans le cadre "
            "des tests ou de l'évaluation WCMP2."
        ),
        "impact": (
            "Cet événement est généralement informatif et permet de suivre "
            "les résultats ou l'état des tests."
        ),
        "action": (
            "Consulter le contenu du rapport pour identifier les éventuels "
            "tests échoués ou points nécessitant une correction."
        ),
        "severity": "INFO"
    },

    "WCMP2 KPI report": {
        "description": (
            "Rapport contenant des indicateurs KPI liés au suivi "
            "des performances ou de la conformité WCMP2."
        ),
        "cause": (
            "Le rapport est généré dans le cadre du monitoring et de "
            "l'évaluation des composants WIS2."
        ),
        "impact": (
            "Il permet de suivre l'état et les performances des composants "
            "sur la base d'indicateurs mesurables."
        ),
        "action": (
            "Analyser les KPI afin d'identifier les indicateurs présentant "
            "des valeurs anormales ou nécessitant une amélioration."
        ),
        "severity": "INFO"
    },

    "Disconnected WIS2 Node from one Global Broker": {
        "description": (
            "Un nœud WIS2 n'est plus connecté à l'un des Global Brokers "
            "auxquels il devrait être connecté."
        ),
        "cause": (
            "La connexion MQTT peut avoir été interrompue, le broker peut "
            "être indisponible ou un problème réseau peut empêcher la connexion."
        ),
        "impact": (
            "Le nœud peut perdre temporairement une partie de sa capacité "
            "à publier ou recevoir des informations via le Global Broker concerné."
        ),
        "action": (
            "Vérifier la connectivité réseau, l'état du broker, les identifiants "
            "MQTT et les logs du nœud WIS2."
        ),
        "severity": "WARNING"
    },

    "Disconnected WIS2 Node from multiple Global Brokers": {
        "description": (
            "Un nœud WIS2 est déconnecté de plusieurs Global Brokers."
        ),
        "cause": (
            "Plusieurs connexions aux Global Brokers ont été interrompues, "
            "potentiellement à cause d'un problème réseau, d'une configuration "
            "incorrecte ou d'une indisponibilité des brokers."
        ),
        "impact": (
            "La disponibilité et la redondance du nœud WIS2 sont réduites."
        ),
        "action": (
            "Vérifier immédiatement la connectivité du nœud, les connexions MQTT "
            "et l'état des différents Global Brokers."
        ),
        "severity": "ERROR"
    },

    "Disconnected WIS2 Node from all Global Brokers": {
        "description": (
            "Le nœud WIS2 a perdu toutes ses connexions aux Global Brokers."
        ),
        "cause": (
            "Une panne réseau, une panne du nœud, un problème de configuration "
            "MQTT ou une indisponibilité des Global Brokers peut provoquer "
            "cette situation."
        ),
        "impact": (
            "Le nœud est isolé du réseau Global WIS2 et peut ne plus être "
            "capable de publier ou recevoir correctement les notifications."
        ),
        "action": (
            "Traiter cet événement comme prioritaire : vérifier la disponibilité "
            "du nœud, le réseau, les connexions MQTT, les certificats ou "
            "identifiants et l'état des Global Brokers."
        ),
        "severity": "CRITICAL"
    },

    "WIS2 Notification Message published on a invalid topic": {
        "description": (
            "Une notification WIS2 a été publiée sur un topic MQTT "
            "qui ne respecte pas le topic attendu."
        ),
        "cause": (
            "Le topic peut être mal configuré, mal construit ou ne pas "
            "respecter les règles de publication WIS2."
        ),
        "impact": (
            "La notification peut ne pas être correctement routée, traitée "
            "ou découverte par les composants WIS2."
        ),
        "action": (
            "Vérifier le topic MQTT utilisé par le producteur et le comparer "
            "avec le topic WIS2 attendu."
        ),
        "severity": "ERROR"
    },

    "WCMP2 access failure": {
        "description": (
            "Le monitoring n'a pas réussi à accéder à une ressource "
            "ou un service utilisé dans le cadre de WCMP2."
        ),
        "cause": (
            "Le service peut être indisponible, le réseau inaccessible, "
            "ou la ressource peut retourner une erreur."
        ),
        "impact": (
            "Les tests ou contrôles WCMP2 concernés ne peuvent pas être "
            "exécutés correctement."
        ),
        "action": (
            "Vérifier la disponibilité de la ressource, la connectivité "
            "réseau et les réponses HTTP du service."
        ),
        "severity": "ERROR"
    },

    "Target wis2.ncm.gov.sa:443 is down": {
        "description": (
            "La cible wis2.ncm.gov.sa sur le port HTTPS 443 "
            "n'est pas accessible."
        ),
        "cause": (
            "Le serveur peut être arrêté, inaccessible sur le réseau, "
            "ou le service HTTPS peut ne pas répondre."
        ),
        "impact": (
            "Le service HTTPS de cette cible n'est momentanément pas disponible."
        ),
        "action": (
            "Vérifier la disponibilité du serveur, le port 443, "
            "la connectivité réseau et le service HTTPS."
        ),
        "severity": "ERROR"
    },

    "Target www.wis-jma.go.jp:443 is down": {
        "description": (
            "La cible www-wis-jma.go.jp sur le port HTTPS 443 "
            "n'est pas accessible."
        ),
        "cause": (
            "Le serveur ou le service HTTPS peut être temporairement "
            "indisponible ou inaccessible."
        ),
        "impact": (
            "Le service HTTPS surveillé n'est pas disponible au moment "
            "du contrôle."
        ),
        "action": (
            "Vérifier la disponibilité du serveur, le réseau, le port 443 "
            "et le service HTTPS."
        ),
        "severity": "ERROR"
    },

    "wis2data.kma.go.kr": {
        "description": (
            "Événement associé au service ou à la cible WIS2 "
            "wis2data.kma.go.kr."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème "
            "lié à cette cible."
        ),
        "impact": (
            "La disponibilité ou le fonctionnement du service surveillé "
            "peut être affecté."
        ),
        "action": (
            "Vérifier la disponibilité du service et les logs associés."
        ),
        "severity": "ERROR"
    },

    "wis2.dwd.de": {
        "description": (
            "Événement associé au service ou à la cible WIS2 wis2.dwd.de."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème "
            "concernant cette cible."
        ),
        "impact": (
            "Le service peut présenter un problème de disponibilité "
            "ou de fonctionnement."
        ),
        "action": (
            "Vérifier la disponibilité du service et les logs du composant."
        ),
        "severity": "ERROR"
    },

    "globalbroker.meteo.fr": {
        "description": (
            "Événement associé au Global Broker WIS2 "
            "globalbroker.meteo.fr."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème "
            "lié au Global Broker."
        ),
        "impact": (
            "Une dégradation du broker peut affecter la circulation "
            "des notifications WIS2."
        ),
        "action": (
            "Vérifier la disponibilité du broker, la connexion MQTT "
            "et les logs du service."
        ),
        "severity": "ERROR"
    },

    "www.wis-jma.go.jp": {
        "description": (
            "Événement associé au service WIS-JMA japonais."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème "
            "concernant cette cible."
        ),
        "impact": (
            "La disponibilité du service surveillé peut être affectée."
        ),
        "action": (
            "Vérifier la disponibilité du serveur et du service HTTPS."
        ),
        "severity": "ERROR"
    },

    "gc.wis.cma.cn": {
        "description": (
            "Événement associé au service WIS de la CMA chinoise "
            "gc.wis.cma.cn."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème "
            "lié à cette cible."
        ),
        "impact": (
            "Une indisponibilité peut affecter l'accès au service surveillé."
        ),
        "action": (
            "Vérifier la disponibilité du service, le réseau et les logs."
        ),
        "severity": "ERROR"
    },

    "wis2broker.globaldata.nws.noaa.gov": {
        "description": (
            "Événement associé au Global Broker WIS2 de NOAA."
        ),
        "cause": (
            "Le monitoring a détecté une activité ou un problème "
            "lié à ce broker."
        ),
        "impact": (
            "Un problème du broker peut affecter la circulation "
            "des notifications WIS2."
        ),
        "action": (
            "Vérifier la disponibilité du broker et les connexions MQTT."
        ),
        "severity": "ERROR"
    }
}

# ============================================================
# 🔎 RECHERCHE DANS LA BASE DE CONNAISSANCES
# ============================================================

def find_wis2_knowledge(question):
    """
    Recherche directement un événement connu dans la base
    de connaissances WIS2.
    """

    question_lower = question.lower().strip()

    # Recherche exacte / partielle
    for event_name, knowledge in WIS2_KNOWLEDGE_BASE.items():

        if event_name.lower() in question_lower:

            return event_name, knowledge

    # Recherche plus souple par mots-clés
    best_match = None
    best_score = 0

    for event_name, knowledge in WIS2_KNOWLEDGE_BASE.items():

        words = [
            w for w in re.findall(
                r"[a-z0-9]+",
                event_name.lower()
            )
            if len(w) > 3
        ]

        score = sum(
            1 for word in words
            if word in question_lower
        )

        if score > best_score:
            best_score = score
            best_match = (event_name, knowledge)

    # Au moins 2 mots significatifs doivent correspondre
    if best_match and best_score >= 2:
        return best_match

    return None

# ============================================================
# 📖 EXPLICATION DIRECTE D'UN ÉVÉNEMENT WIS2
# ============================================================

def explain_wis2_event(question):

    result = find_wis2_knowledge(question)

    if not result:
        return None

    event_name, knowledge = result

    # Récupération du nombre réel dans SQLite
    conn = sqlite3.connect(DB_PATH)

    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS nombre
            FROM wme_events
            WHERE LOWER(content_title) = LOWER(?)
            """,
            (event_name,)
        ).fetchone()

    finally:
        conn.close()

    count = row[0] if row else 0

    return f"""
### 📖 {event_name}

**Occurrences dans le monitoring :** {count:,}

**🔎 Description**

{knowledge["description"]}

**⚠️ Cause probable**

{knowledge["cause"]}

**📡 Impact**

{knowledge["impact"]}

**🛠️ Action recommandée**

{knowledge["action"]}

**Niveau généralement associé :** `{knowledge["severity"]}`
"""
# ============================================================
# OLLAMA — LLM LOCAL
# ============================================================

def ask_ollama(question, context):

    prompt = f"""
Tu es un assistant professionnel spécialisé dans
la supervision de l'infrastructure WIS2.

Tu dois répondre en français.

RÈGLES STRICTES :

1. Utilise uniquement les informations contenues dans
   la section RÉSULTATS EXACTS.

2. Les nombres provenant de SQLite sont exacts.
   Ne les invente jamais.

3. Ne crée aucune information qui n'est pas présente
   dans les résultats.

4. Si les résultats sont insuffisants, indique-le clairement.

5. Réponds de manière concise et professionnelle.

RÉSULTATS EXACTS :

{context}

QUESTION :

{question}
"""

    try:

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTIONS
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.1
            }
        )

        return response["message"]["content"]

    except Exception as e:

        raise RuntimeError(
            f"Impossible de contacter Ollama : {e}"
        )
# ============================================================
# CONNEXION SQLITE
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_centre_events(filters, limit=20):
    """
    Retourne les événements d'un centre directement depuis SQLite.
    """

    conn = get_db_connection()

    try:
        centre = filters.get("centre")

        if not centre:
            return []

        rows = conn.execute("""
            SELECT
                content_title,
                severity,
                COUNT(*) AS nombre
            FROM wme_events
            WHERE LOWER(subject) LIKE LOWER(?)
               OR LOWER(source) LIKE LOWER(?)
            GROUP BY content_title, severity
            ORDER BY nombre DESC
            LIMIT ?
        """, (
            f"%{centre}%",
            f"%{centre}%",
            limit
        )).fetchall()

        return rows

    finally:
        conn.close()
# ============================================================
# RÉPONSE DIRECTE DEPUIS SQLITE
# ============================================================

def direct_sqlite_answer(question, filters, context):
    """
    Répond directement aux questions statistiques à partir de SQLite.

    OLLAMA n'est PAS utilisé pour ces intentions.
    """

    intent = filters.get("intent", "")

    # --------------------------------------------------------
    # TOP CENTRES
    # --------------------------------------------------------

    if intent == "top_centres_list":

        conn = get_db_connection()

        try:
            rows = conn.execute("""
                SELECT
                    subject,
                    COUNT(*) AS nombre
                FROM wme_events
                WHERE subject IS NOT NULL
                  AND TRIM(subject) != ''
                GROUP BY subject
                ORDER BY nombre DESC
                LIMIT 10
            """).fetchall()

        finally:
            conn.close()

        if not rows:
            return "Aucun événement trouvé dans la base de données."

        answer = "### 🏆 Centres ayant généré le plus d'événements\n\n"

        for i, row in enumerate(rows, start=1):
            answer += (
                f"**{i}. {row['subject']}** — "
                f"{row['nombre']:,} événements\n"
            )

        return answer


    # --------------------------------------------------------
    # NOMBRE D'ÉVÉNEMENTS AUJOURD'HUI
    # --------------------------------------------------------

    if intent == "today_count":

        conn = get_db_connection()

        try:
            row = conn.execute("""
                SELECT COUNT(*) AS nombre
                FROM wme_events
                WHERE date(received_at) = date('now', 'localtime')
            """).fetchone()

        finally:
            conn.close()

        nombre = row["nombre"]

        return (
            f"### 📊 Événements reçus aujourd'hui\n\n"
            f"Nous avons reçu **{nombre:,} événements** aujourd'hui."
        )


    # --------------------------------------------------------
    # NOMBRE D'ÉVÉNEMENTS HIER
    # --------------------------------------------------------

    if intent == "yesterday_count":

        conn = get_db_connection()

        try:
            row = conn.execute("""
                SELECT COUNT(*) AS nombre
                FROM wme_events
                WHERE date(received_at) =
                      date('now', 'localtime', '-1 day')
            """).fetchone()

        finally:
            conn.close()

        nombre = row["nombre"]

        return (
            f"### 📊 Événements reçus hier\n\n"
            f"Nous avons reçu **{nombre:,} événements** hier."
        )


    # --------------------------------------------------------
    # NOMBRE D'ÉVÉNEMENTS CRITICAL
    # --------------------------------------------------------

    if intent == "critical_count":

        conn = get_db_connection()

        try:
            row = conn.execute("""
                SELECT COUNT(*) AS nombre
                FROM wme_events
                WHERE UPPER(severity) = 'CRITICAL'
            """).fetchone()

        finally:
            conn.close()

        nombre = row["nombre"]

        return (
            f"### 🔴 Événements CRITICAL\n\n"
            f"La base contient **{nombre:,} événements CRITICAL**."
        )


    # --------------------------------------------------------
    # STATISTIQUES PAR SÉVÉRITÉ
    # --------------------------------------------------------

    if intent == "severity_stats":

        conn = get_db_connection()

        try:
            rows = conn.execute("""
                SELECT
                    severity,
                    COUNT(*) AS nombre
                FROM wme_events
                GROUP BY severity
                ORDER BY nombre DESC
            """).fetchall()

        finally:
            conn.close()

        if not rows:
            return "Aucune donnée disponible."

        answer = "### 📊 Répartition des événements par sévérité\n\n"

        for row in rows:
            severity = row["severity"] or "UNKNOWN"
            nombre = row["nombre"]

            answer += f"- **{severity}** : {nombre:,}\n"

        return answer


    # --------------------------------------------------------
    # NOMBRE TOTAL D'ÉVÉNEMENTS
    # --------------------------------------------------------

    if intent == "count":

      # Utilise les filtres détectés :
      # date, centre, sévérité...
      nombre = run_count(filters)

      filtre_description = describe_filters(filters)

      return (
        f"### 📊 Total des événements\n\n"
        f"Pour **{filtre_description}**, "
        f"nous avons **{nombre:,} événements**."
      )

    #
    if intent == "stats_centre":
      if not filters.get("centre"):
        return "⚠️ Aucun centre WIS2 n'a été identifié dans votre question."

      stats_df, dominant_severity = run_centre_stats(filters)

      if stats_df.empty:
        return (
            f"### 📊 Statistiques de {filters['centre']}\n\n"
            "Aucun événement trouvé pour ce centre."
        )

      total = int(stats_df["nombre"].sum())

      answer = (
        f"### 📊 Statistiques du centre **{filters['centre']}**\n\n"
        f"**Total :** {total:,} événements\n\n"
        f"**Répartition par sévérité :**\n\n"
      )

      for _, row in stats_df.iterrows():
        severity = row["severity"] or "UNKNOWN"
        nombre = int(row["nombre"])
        answer += f"- **{severity}** : {nombre:,}\n"

      answer += (
        f"\n🔴 **Sévérité dominante : {dominant_severity}**"
      )

      return answer
    # --------------------------------------------------------
    # ÉVÉNEMENTS D'UN CENTRE
    # --------------------------------------------------------

    if intent == "centre_events":

        centre = filters.get("centre")

        if not centre:
            return (
                "⚠️ Aucun centre WIS2 n'a été identifié "
                "dans votre question."
            )

        rows = run_centre_events(filters, limit=20)

        if not rows:
            return (
                f"### 📋 Événements de {centre}\n\n"
                "Aucun événement trouvé pour ce centre."
            )

        answer = (
            f"### 📋 Événements concernant **{centre}**\n\n"
        )

        total = sum(row["nombre"] for row in rows)

        answer += (
            f"**Nombre total d'événements :** {total:,}\n\n"
        )

        answer += "**Types d'événements détectés :**\n\n"

        for row in rows:
            title = row["content_title"] or "Sans titre"
            severity = row["severity"] or "UNKNOWN"
            nombre = row["nombre"]

            answer += (
                f"- **{title}** — "
                f"{nombre:,} fois — `{severity}`\n"
            )

        return answer
    
    return None


# ============================================================
# FALLBACK OLLAMA
# ============================================================

def ask_ollama_with_fallback(question, context, filters):

    # ========================================================
    # 1. EXPLICATION DIRECTE DEPUIS LA BASE DE CONNAISSANCES
    # ========================================================

    if filters.get("intent") == "explain_event":

        knowledge_answer = explain_wis2_event(question)

        if knowledge_answer is not None:
            return knowledge_answer

    # ========================================================
    # 2. RÉPONSE DIRECTE SQLITE
    # ========================================================

    direct_answer = direct_sqlite_answer(
        question,
        filters,
        context
    )

    if direct_answer is not None:
        return direct_answer

    # ========================================================
    # 3. OLLAMA
    # ========================================================

    try:

        return ask_ollama(
            question,
            context
        )

    # ========================================================
    # 4. FALLBACK SQLITE
    # ========================================================

    except Exception:

        return (
            "⚠️ **Ollama est momentanément indisponible.**\n\n"
            "J'ai utilisé directement les données de la base "
            "SQLite pour vous fournir les informations disponibles.\n\n"
            "---\n\n"
            f"{context}"
        )


# ============================================================
# INTERFACE CHATBOT
# ============================================================

st.divider()

# ------------------------------------------------------------
# CHATBOT DANS UN EXPANDER
# ------------------------------------------------------------

with st.expander("🤖 Assistant IA WIS2", expanded=False):

    st.caption(
        "Posez une question sur les centres WIS2 et les événements "
        "enregistrés depuis le 20/08/2026."
    )

    st.caption(
        "Exemples : "
        "« Combien d'événements avons-nous reçus aujourd'hui ? », "
        "« Quels sont les centres qui ont généré le plus d'événements ? », "
        "« Explique l'événement ... »"
    )

    # ========================================================
    # INPUT UTILISATEUR
    # ========================================================
    
    question = st.chat_input(
            "Posez une question sur les événements WIS2..."
    )

    # ========================================================
    # HISTORIQUE DU CHAT
    # ========================================================

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ========================================================
    # CONTENEUR DU CHAT
    # ========================================================

    chat_container = st.container(
        height=600,
        border=True
    )

    # ========================================================
    # AFFICHAGE DES MESSAGES
    # ========================================================

    with chat_container:

        for message in st.session_state.messages:

            with st.chat_message(message["role"]):

                st.markdown(
                    message["content"]
                )

    

    # ========================================================
    # TRAITEMENT DE LA QUESTION
    # ========================================================

    if question:

        # ----------------------------------------------------
        # MESSAGE UTILISATEUR
        # ----------------------------------------------------

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        # ----------------------------------------------------
        # ANALYSE DE LA QUESTION
        # ----------------------------------------------------

        try:

            filters = analyze_question(question)

        except Exception as e:

            filters = {
                "intent": "unknown"
            }

            st.error(
                f"⚠️ Impossible d'analyser la question : {e}"
            )

        # ----------------------------------------------------
        # SQLITE → CONTEXT
        # ----------------------------------------------------

        try:

            context = build_context(
                question,
                filters
            )

        except Exception as e:

            context = (
                "Impossible de récupérer les données SQLite :\n"
                f"{e}"
            )

        # ----------------------------------------------------
        # RÉPONSE
        # ----------------------------------------------------

        with st.spinner(
            "🔎 Analyse des données WIS2..."
        ):

            answer = ask_ollama_with_fallback(
                question,
                context,
                filters
            )

        # ----------------------------------------------------
        # SAUVEGARDE RÉPONSE
        # ----------------------------------------------------

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        # ----------------------------------------------------
        # RAFRAÎCHISSEMENT
        # ----------------------------------------------------

        st.rerun()

