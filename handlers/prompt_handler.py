import os
import csv
import json
import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

class PromptHandler:
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / "prompt"
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        self.csv_dir = Path(__file__).parent.parent / "problem_example"
        
        self.question_format_prompt_path = self.template_dir / "question_format.jinja"
        self.article_revision_path = self.template_dir / "article_revision.jinja"
        self.article_format_path = self.template_dir / "article_format.jinja"
        
        with open(self.question_format_prompt_path, 'r', encoding='utf-8') as f:
            self.question_format_prompt = f.read()
            
        with open(self.article_revision_path, 'r', encoding='utf-8') as f:
            self.article_revision_prompt = f.read()
            
        with open(self.article_format_path, 'r', encoding='utf-8') as f:
            self.article_format_prompt = f.read()
            
        # self.problem_types = self.get_available_templates()
        
    def _load_csv_data(self, csv_file_name):
        csv_path = self.csv_dir / csv_file_name
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
        data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(row)
                
        return data
    
    def generate_prompt(self, template_name, csv_name=None):
        template = self.env.get_template(f"{template_name}.jinja")
        
        context = {}
        
        if csv_name:
            try:
                csv_data = self._load_csv_data(f"{csv_name}.csv")
                context['examples'] = csv_data
            except FileNotFoundError:
                print(f"Warning: CSV file {csv_name}.csv not found, continuing without examples")
        
        rendered_prompt = template.render(**context)
        
        return rendered_prompt
    
    def get_available_csv_files(self):
        csv_files = []
        for file in self.csv_dir.glob("*.csv"):
            csv_files.append(file.stem)
        return csv_files
    
    def prepare_question_prompt(self, problem_type, current_article, difficulty=None):
        prompt = self.generate_prompt(
            problem_type,
            csv_name=problem_type
        )
        
        context = {
            "prompt": prompt,
            "generated_article": current_article
        }
        
        # if difficulty:
        #     context["difficulty"] = difficulty
            
        integrated_prompt = self.question_format_prompt.format(**context)
        
        return integrated_prompt
        
    def prepare_article_revision_prompt(self, article_content, message):
        return self.article_revision_prompt.format(
            generated_article=article_content,
            message=message
        )
        
    def prepare_article_format_prompt(self, article_content, message):
        return self.article_format_prompt.format(
            generated_article=article_content,
            message=message,
            textbox_content=article_content
        )


