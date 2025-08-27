import os, pickle
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, Javascript

# =========================
# Config
# =========================
CONFIG = {
    "state_file": "#Evaluation.pkl",
    "input_folder_path": "Unique/Evaluation",
    "output_folder_path": "Outputs",
    "prompt_folder_path": "Prompts",
    
    "widgets": {
        "input_drop": {
            "type": "dropdown",
            "label": "Input:",
            "options": lambda: os.listdir(CONFIG["input_folder_path"]),
        },
        "prompt_drop": {
            "type": "dropdown",
            "label": "Prompt:",
            "options": lambda: os.listdir(CONFIG["prompt_folder_path"]),
        },
        "API_drop": {
            "type": "dropdown",
            "label": "API Key:",
            "options": [
                "AIzaSyDaHS-8h6GJkyVPhoX4svvYeBTTVLNO-2w",
                "AIzaSyD81vpriaNcvCyGOxy3TRR0w_njxgPJYfE",
                "AIzaSyCsQo1gnYSLELV9flyPkYgHBdEvz7lqPjk",
                "AIzaSyAJ7QFBJtozfyooguHAqsJsLO0a2L--tKo",
                "AIzaSyBPjyMfHkS9OW3h7G0kmLSQkWQMfqfX5v0",
                "AIzaSyA4HvCdIc4gGK4YCBlWS3vfXGjY3y9Zadg",
            ],
        },
        "model_drop": {
            "type": "dropdown",
            "label": "Model:",
            "options": ["gemini-1.5-flash", "gemini-2.0-flash-exp"],
        },
        "article_drop": {
            "type": "dropdown",
            "label": "Article:",
            "options": [],
        },
        "summary_drop": {
            "type": "dropdown",
            "label": "Summary:",
            "options": [],
        },
        "start_data": {
            "type": "text",
            "label": "Start:",
            "placeholder": "MIN START ID: 1",
        },
        "end_data": {
            "type": "text",
            "label": "End:",
            "placeholder": "END ID",
        },
        "export_drop": {
            "type": "dropdown",
            "label": "Export XLSX ?",
            "options": ["YES", "NO"],
        }
    }
}

# =========================
# State management
# =========================
def save_state(widgets_dict):
    state = {}
    for k, w in widgets_dict.items():
        if isinstance(w, widgets.Dropdown) and w.value not in w.options:
            state[k] = w.options[0] if w.options else None
        else:
            state[k] = w.value
    with open(CONFIG["state_file"], "wb") as f:
        pickle.dump(state, f)


def load_state():
    if os.path.exists(CONFIG["state_file"]):
        with open(CONFIG["state_file"], "rb") as f:
            return pickle.load(f)
    return {}

# =========================
# Widget factory
# =========================
def make_widget(name, cfg, state):
    if cfg["type"] == "dropdown":
        options = cfg["options"]() if callable(cfg["options"]) else cfg["options"]
        value = state.get(name, options[0] if options else None)
        if value not in options:
            value = options[0] if options else None
        return widgets.Dropdown(
            options=options,
            description=cfg["label"],
            value=value,
            layout=widgets.Layout(width="50%"),
        )
    elif cfg["type"] == "text":
        return widgets.Text(
            description=cfg["label"],
            placeholder=cfg.get("placeholder", ""),
            value=state.get(name, ""),
            layout=widgets.Layout(width="50%"),
        )


# =========================
# Excel utils
# =========================
def load_xlsx_columns(file_path):
    try:
        df = pd.read_excel(file_path)
        return df.columns.tolist()
    except Exception as e:
        print(f"Error loading xlsx file: {e}")
        return []

# =========================
# UI Builder
# =========================
def build_ui():
    state = load_state()
    widgets_dict = {name: make_widget(name, cfg, state) 
                    for name, cfg in CONFIG["widgets"].items()}
    
    def update_dropdowns(change):
        input_file = os.path.join(CONFIG["input_folder_path"], widgets_dict["input_drop"].value)
        columns = load_xlsx_columns(input_file)
        
        widgets_dict["article_drop"].options = columns
        widgets_dict["summary_drop"].options = columns

        # Chọn giá trị state nếu còn trong columns
        state_article = load_state().get("article_drop")
        state_summary = load_state().get("summary_drop")
        
        if state_article in columns:
            widgets_dict["article_drop"].value = state_article
        else:
            widgets_dict["article_drop"].value = columns[0] if columns else None

        if state_summary in columns:
            widgets_dict["summary_drop"].value = state_summary
        else:
            widgets_dict["summary_drop"].value = columns[0] if columns else None

        try:
            data = pd.read_excel(input_file)
            widgets_dict["end_data"].placeholder = f"MAX END ID: {len(data)}"
        except Exception as e:
            print(f"Error loading file: {e}")

    
    widgets_dict["input_drop"].observe(update_dropdowns, names="value")
    update_dropdowns(None)

    save_button = widgets.Button(description="Save State", button_style="success")
    run_button = widgets.Button(description="Run All Below", button_style="primary")

    save_button.on_click(lambda b: save_state(widgets_dict))
    run_button.on_click(lambda b: (save_state(widgets_dict), display(Javascript("Jupyter.notebook.execute_cells_below()"))))

    range_data   = widgets.HBox([widgets_dict["input_drop"], widgets_dict["prompt_drop"]])
    range_model  = widgets.HBox([widgets_dict["API_drop"], widgets_dict["model_drop"]])
    range_column = widgets.HBox([widgets_dict["article_drop"], widgets_dict["summary_drop"]])
    range_rows   = widgets.HBox([widgets_dict["start_data"], widgets_dict["end_data"]])
    button_box   = widgets.HBox([save_button, run_button], layout=widgets.Layout(width="50%", justify_content="space-between"))
    footer_display = widgets.HBox([button_box, widgets_dict["export_drop"]])

    display(range_data, range_model, range_column, range_rows, footer_display)
    return widgets_dict
