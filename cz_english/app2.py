import gradio as gr


def add_textbox(choice, textboxes):
    """Adds a new textbox with a remove button."""
    textboxes.append(choice)  # Append new text
    return textboxes

def remove_textbox(index, textboxes):
    """Removes a textbox by index."""
    # print(index)
    # print(type(index))
    # index = int(index)
    # if 0 <= index < len(textboxes):
    # textboxes.pop(2)  # Remove the specific textbox
    return textboxes


with gr.Blocks() as demo:
    gr.Markdown("### Click a button to create a new textbox with a remove button:")
    state = gr.State([])  # Stores the list of textboxes

    @gr.render(inputs=state)
    def update_ui(textboxes):
        """Generates UI dynamically based on textboxes list."""
        for i, text in enumerate(textboxes):
            with gr.Row():  # Row layout for textbox + remove button
                gr.Textbox(value=text, interactive=True)
                gr.Button("❌", elem_id=f"remove-{i}").click(remove_textbox, inputs=[gr.Number(value=i, interactive=False, render=False), state], outputs=state)

    
    with gr.Row():
        btn1 = gr.Button("Option 1")
        btn2 = gr.Button("Option 2")
        btn3 = gr.Button("Option 3")

    text_container = gr.Column()  # Holds dynamically added textboxes

    # Button click handlers (adding new textboxes)
    btn1.click(add_textbox, inputs=[btn1, state], outputs=state)
    btn2.click(add_textbox, inputs=[btn2, state], outputs=state)
    btn3.click(add_textbox, inputs=[btn3, state], outputs=state)

demo.launch()
