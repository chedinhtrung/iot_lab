import streamlit as st
from todos.todos_crud_functions import *

st.set_page_config(page_title="To-do list", page_icon=":memo:")

# Declare alias for st.session_state, just for convenience.
state = st.session_state


if "todos" not in state:
    state.todos = get_todos()


def remove_todo(i):
    state.todos[i].delete()
    state.todos.pop(i)


def add_todo():
    todo = Todo(text=state.new_item_text, priority=state.priority)
    state.todos.append(todo)
    state.new_item_text = ""
    todo.push_to_influx()


def check_todo(i, new_value):
    state.todos[i].is_done = new_value


def delete_all_checked():
    for todo in state.todos:
        if not todo.is_done:
            todo.delete()
    state.todos = [t for t in state.todos if not t.is_done]


with st.container(horizontal_alignment="center"):
    st.title(
        ":orange[:material/checklist:] To-do list",
        width="content",
        anchor=False,
    )

with st.form(key="new_item_form", border=False):
    with st.container(
        horizontal=True,
        vertical_alignment="bottom",
    ):
        st.text_input(
            "New item",
            label_visibility="collapsed",
            placeholder="Name",
            key="new_item_text",
        )

        st.number_input(
            "Priority (0 = Highest)",
            label_visibility="visible",
            key="priority",
            min_value=0,
            max_value=10,
            step=1
        )

        st.form_submit_button(
            "Add",
            icon=":material/add:",
            on_click=add_todo,
        )

if state.todos:
    with st.container(gap=None, border=True):
        for i, todo in enumerate(state.todos):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.checkbox(
                    todo.text,
                    value=todo.is_done,
                    width="stretch",
                    on_change=check_todo,
                    args=[i, not todo.is_done],
                    key=f"todo-chk-{todo.uid}",
                )
                st.text(f"Priority {todo.priority}")
                st.text(f"{todo.timestamp}")
                st.button(
                    ":material/delete:",
                    type="tertiary",
                    on_click=remove_todo,
                    args=[i],
                    key=f"delete_{i}",
                )

    with st.container(horizontal=True, horizontal_alignment="center"):
        st.button(
            ":small[Delete all checked]",
            icon=":material/delete_forever:",
            type="tertiary",
            on_click=delete_all_checked,
        )

else:
    st.info("No to-do items. Go fly a kite! :material/family_link:")