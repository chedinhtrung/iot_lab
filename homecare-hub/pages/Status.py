import streamlit as st
from sysinfo.sysinfo import * 
from datetime import datetime

sys_info = get_system_status()

for item in sys_info:
    with st.expander(item["name"]):
        last_invoke = item.get("last_invoke")
        if last_invoke is not None:
            last_invoke = datetime.fromtimestamp(last_invoke/1000).isoformat()

        st.markdown(f"""Last invoke: {last_invoke or "Never"}""")
        
        with st.expander("Subs"):
            for sub in item.get("subs"):
                st.markdown(sub)

        events = item.get("events")
        for event in events:
            with st.expander("Ready"):
                for ready in event.get("ready"): 
                    st.markdown(ready)
            
            with st.expander("Waiting"):
                for waiting in event.get("waiting"): 
                    st.markdown(waiting)

