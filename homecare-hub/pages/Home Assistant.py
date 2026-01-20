from openai import OpenAI, AuthenticationError
import streamlit as st
from chatbot.chatbot import ChatBot

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"

st.title("Home Assistant")
st.markdown("""
            A chatbot powered by OpenAI that allows you to talk to your data. 

            You can ask it any question on the data, and it will query the database and answer.
           """)

if "openai_key" not in st.session_state:
    st.session_state.openai_key = openai_api_key

elif st.session_state.openai_key != openai_api_key:
    st.session_state.openai_key = openai_api_key
    if "bot" in st.session_state:
        st.session_state.bot = ChatBot(openai_api_key)

if "bot" not in st.session_state:
    st.session_state.bot = ChatBot(openai_api_key)

else:
    for msg in st.session_state.bot.messages:
        if msg["role"] == "system": 
            continue
        st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("e.g What time did I go to sleep last night?"):
    #if not openai_api_key:
     #   st.info("Please add your OpenAI API key to continue.")
     #   st.stop()

    st.chat_message("user").write(prompt)
    try:
        response = st.session_state.bot.chat(prompt)
        st.chat_message("assistant").write(response)

    except AuthenticationError:
        st.info("Invalid authentication key. Please try again.")
        st.stop()

