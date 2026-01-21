import streamlit as st
from data.preprocessing import *
from chatbot.tools import load_response


with st.expander("Latest analysis"):
    st.markdown(load_response())

# multihorizon predictions


