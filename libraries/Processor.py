import os
import re
import time
import json
import pandas as pd
import google.generativeai as genai


class SummaryEvaluator:
    def __init__(self, config: dict):
        self.config = config

        # Setup Gemini
        genai.configure(api_key=self.config["api_key"])
        with open(f"Prompts/{self.config['prompt']}", "r", encoding="utf-8") as f:
            self.evaluation_prompt = f.read()

        self.model = genai.GenerativeModel(
            self.config["model_name"],
            system_instruction=self.evaluation_prompt
        )

        # Load data
        self.data = pd.read_excel(self.config["input_path"])

    def evaluate_summary(self, article, summary):
        user_prompt = f"""
        Hãy đánh giá văn bản tóm tắt dưới đây dựa trên văn bản gốc được cung cấp:
        Văn bản gốc:
        {article}
        
        Văn bản tóm tắt:
        {summary}
        """

        overall_prompt = self.evaluation_prompt + "\n" + user_prompt
        try:
            response = self.model.generate_content(
                overall_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    top_p=0.9,
                    top_k=50
                )
            )
            return response.text
        except Exception:
            return None

    @staticmethod
    def fix_nested_quotes(json_str):
        def replace_nested_quotes(match):
            key, value = match.groups()
            fixed_value = value.strip()
            if fixed_value.startswith('"') and fixed_value.endswith('"'):
                inner_content = fixed_value[1:-1]
                if ('\\"' not in inner_content and '"' in inner_content) or ('\\"' in inner_content and '"' not in inner_content):
                    inner_content = inner_content.replace('"', '\\"')
                fixed_value = f'"{inner_content}"'
            return f'{key}: {fixed_value}'

        return re.sub(r'(\"[^"]+\"): (.*?)(?=\n|$)', replace_nested_quotes, json_str)

    def decode_fix(self, result, article, summary):
        retries = 0
        while retries < 3:
            try:
                json_match = re.search(r'```json\n(\{.*?\})\n```', result, flags=re.DOTALL)
                json_str = json_match.group(1) if json_match else result.strip()
                json_str = self.fix_nested_quotes(json_str)

                print("Attempt:", retries + 1)
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                retries += 1
                print(f"Decode Error! Attempt: {retries} - {e}")
                result = self.evaluate_summary(article, summary)

        print("Failed to decode JSON!")
        return result

    def run(self):
        output_data = []
        fail_num = 0
        fail_streak = 0

        for index, row in self.data.iloc[self.config["start"] - 1:self.config["end"]].iterrows():
            print(f"EVALUATING SUMMARY {index+1} ...")

            article = row[self.config["article_row"]]
            summary = row[self.config["summary_row"]]

            result = self.evaluate_summary(article, summary)
            print("Raw result:", result)

            attempt = 0
            while result is None and attempt < 10:
                attempt += 1
                wait_time = 11 - attempt
                print(f"Attempt: {attempt}. {wait_time}s...")
                time.sleep(wait_time)
                result = self.evaluate_summary(article, summary)
                print("Raw result:", result)

            if result is None:
                print(f"Summary {index+1} Failed to process. Skipping...")
                fail_num += 1
                fail_streak += 1
                if fail_streak >= 3:
                    print("Fail = 3: Skipping all...")
                    break
            else:
                fail_streak = 0
                print("Process successfully")
                result = re.sub(r'\*', '', result)

                decoded_result = self.decode_fix(result, article, summary)
                try:
                    decoded_result_str = json.dumps(decoded_result, ensure_ascii=False)
                    decoded_result_str = re.sub(r'\s+', ' ', decoded_result_str).strip()
                    decoded_result = json.loads(decoded_result_str)
                except Exception:
                    decoded_result = None

                print(f"Article: {article}")
                print(f"Summary: {summary}")
                print(f"Result: {decoded_result}")
                print("-" * 10)

            output_data.append({
                "Index": f"{index+1:05}",
                "Article": article,
                "Summary": summary,
                "Result": decoded_result
            })

        print(f"Evaluate Finished!")
        print(f"Fail: {fail_num}")
        return output_data
