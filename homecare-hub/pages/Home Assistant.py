from openai import OpenAI, AuthenticationError
import streamlit as st
from chatbot.chatbot import ChatBot
from uuid import uuid4
from chatbot.tools import save_response
from chatbot.secret import *

st.title("Home Assistant")
st.markdown("""
            A chatbot powered by OpenAI that allows you to talk to your data. 

            You can ask it any question on the data, and it will query the database and answer.
           """)

if "bot" not in st.session_state:
    st.session_state.bot = ChatBot(KEY)

else:
    for key, msg in enumerate(st.session_state.bot.messages):
        if msg["role"] == "system": 
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if st.button("💾 Save", key=key):
                    save_response(msg["content"])
                    st.toast("Saved!")

if prompt := st.chat_input("e.g What time did I go to sleep last night?"):
    #if not openai_api_key:
     #   st.info("Please add your OpenAI API key to continue.")
     #   st.stop()
    st.chat_message("user").write(prompt)
    try:
        response = st.session_state.bot.chat(prompt)

        with st.chat_message("assistant"):
            st.markdown(response["content"])
            if st.button("💾 Save", key=len(st.session_state.bot.messages)-1):
                save_response(msg["content"])
                st.toast("Saved!")

    except AuthenticationError:
        st.info("Invalid authentication key. Please try again.")
        st.stop()

