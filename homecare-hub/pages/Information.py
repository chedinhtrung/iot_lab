import streamlit as st
from data.preprocessing import *
from chatbot.tools import load_response
import requests
from config import *
import json 

import plotly.express as px

# multihorizon predictions

resp = requests.get(MODEL_SERVICE, json={})
data = resp.json()
print(data)

st.set_page_config(page_title="Information", layout="wide")

st.title("Model predictions")

labels = [f"{int(time)} min" for time in data["horizons"]]
classes = data["rooms"]
probs = data["probabilities"]

df = pd.DataFrame(probs, columns=classes)
df.insert(0, "label", labels)

plot_df = df.copy()


plot_classes = classes

long_df = plot_df.melt(
    id_vars=["label"],
    value_vars=plot_classes,
    var_name="class",
    value_name="prob",
)

fig = px.bar(
    long_df,
    y="label",
    x="prob",
    color="class",
    orientation="h",
)

fig.update_traces(
    hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:.1%}<extra></extra>"
)

fig.update_layout(
    barmode="stack",
    xaxis_title="Probability",
    yaxis_title="",
    xaxis=dict(tickformat=".0%", range=[0, 1]),
    legend=dict(
        title="",
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    height=max(420, 34 * len(labels) + 200),
    margin=dict(l=60, r=20, t=60, b=40),
)

fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig, use_container_width=True)


with st.expander("Latest analysis"):
    st.markdown(load_response())



