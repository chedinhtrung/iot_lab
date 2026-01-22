import streamlit as st

def run():
    st.set_page_config(
        page_title="Homecare Hub"
    )
    st.title("Homecare Hub")
    st.write("Welcome to my Homecare Hub")

    st.markdown(
        """
            I really cannot learn a new JS framework and this is not a frontend development course, so have fun
            with this UI :)
            Please note that this unit functions as the combination of homecare-hub (frontend) and sif-viz (backend) all in one.
        """
    )

if __name__ == "__main__":
    run()