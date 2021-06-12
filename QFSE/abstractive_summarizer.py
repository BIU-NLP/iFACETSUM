import json
import os
from typing import List

import requests


class HuggingFaceSummarizer:
    def __init__(self, model_name):  # bart-large-cnn
        api_token = os.getenv("API_TOKEN")
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.url = f"https://api-inference.huggingface.co/models/{model_name}"

    def summarize(self, sentences) -> List[str]:
        from QFSE.Utilities import get_item

        inputs = [". ".join([sent.text for sent in sentences])]
        summary_sents = []

        query_api = False

        if query_api:
            try:
                summary_sents = [x['summary_text'] for x in self.query(inputs)]
            except:
                query_api = False

        if not query_api:
            model, tokenizer = get_item("abstract_summarizer")
            inputs = tokenizer(inputs, max_length=1024, return_tensors="pt")

            # Generate Summary
            summary_ids = model.generate(inputs['input_ids'], num_beams=2, early_stopping=True)
            summary_sents = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=False) for g in summary_ids]

        # Bart doesn't split the sentences
        nlp = get_item("spacy")
        # summary_sents = [sent for summary_sent in summary_sents for sent in nlp(summary_sent).sents]
        summary_sents = [nlp(summary_sent) for summary_sent in summary_sents]

        return summary_sents

    def query(self, payload):
        data = json.dumps(payload)
        response = requests.request("POST", self.url, headers=self.headers, data=data)
        return json.loads(response.content.decode("utf-8"))
