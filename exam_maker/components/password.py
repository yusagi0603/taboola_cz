import gradio as gr
from exam_maker.config import CORRECT_PASSWORD  # Import directly in the Password module

class Password:
    def __init__(self):
        self.correct_password = CORRECT_PASSWORD  # Use the imported constant
        self._define_components()

    def _define_components(self):
        self.password_popup = None
        self.password_input = gr.Textbox(
            label="請輸入密碼",
            type="password",
            render=False
        )
        self.submit_button = gr.Button("提交", render=False)
        self.error_message = gr.Textbox(
            label="",
            visible=False,
            interactive=False,
            render=False
        )

    def check_password(self, input_password):
        if input_password == self.correct_password:
            return gr.update(visible=False), gr.update(visible=True), ""
        else:
            return gr.update(visible=True), gr.update(visible=False), gr.update(value="Wrong Password. Please Retry. hint: channel name", visible=True)

    def render(self):
        with gr.Group(visible=True) as self.password_popup:
            with gr.Column(elem_classes="password-box-with-margin"):
                gr.Markdown("## Welcome", elem_classes="header-text")
                self.password_input.render()
                self.submit_button.render()
                self.error_message.render()
        
        return self.password_popup, self.password_input, self.submit_button, self.error_message
