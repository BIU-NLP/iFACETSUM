import json
import os
from typing import List

import requests
import torch


class HuggingFaceSummarizer:
    def __init__(self, model_name):  # bart-large-cnn
        api_token = os.getenv("API_TOKEN")
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.url = f"https://api-inference.huggingface.co/models/{model_name}"

    def _remove_dot_from_sentence(self, sent_text):
        return sent_text[:-1] if sent_text.endswith(".") else sent_text

    def summarize(self, sentences) -> List[str]:
        from QFSE.Utilities import get_item

        # Sort sentences to avoid the summary from changing if input is too long. Sorting by sent_idx prefers multiple documents over the same one
        sentences_sorted = sorted(sentences, key=lambda sent: sent.sentIndex)
        inputs = [". ".join([self._remove_dot_from_sentence(sent.text) for sent in sentences_sorted])]
        summary_sents = []

        query_api = False

        if query_api:
            try:
                summary_sents = [x['summary_text'] for x in self.query(inputs)]
            except:
                query_api = False

        if not query_api:
            abstract_summarizer_model_name = get_item("abstract_summarizer_model_name")
            model, tokenizer = get_item("abstract_summarizer")
            if "bart" in abstract_summarizer_model_name:
                inputs = tokenizer(inputs, max_length=1024, return_tensors="pt")

                # Generate Summary
                summary_ids = model.generate(inputs['input_ids'], num_beams=2, early_stopping=True)
                summary_sents = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=False) for g in summary_ids]
            else:
                input_ids = tokenizer(inputs[0], return_tensors="pt").input_ids
                global_attention_mask = torch.zeros_like(input_ids)
                # set global_attention_mask on first token
                global_attention_mask[:, 0] = 1

                sequences = model.generate(input_ids, global_attention_mask=global_attention_mask, num_beams=2, max_length=500, early_stopping=True).sequences

                summary_sents = tokenizer.batch_decode(sequences, skip_special_tokens=True, clean_up_tokenization_spaces=False)

        # Bart doesn't split the sentences
        nlp = get_item("spacy")
        # summary_sents = [sent for summary_sent in summary_sents for sent in nlp(summary_sent).sents]
        summary_sents = [nlp(summary_sent) for summary_sent in summary_sents]

        return summary_sents

    def query(self, payload):
        data = json.dumps(payload)
        response = requests.request("POST", self.url, headers=self.headers, data=data)
        return json.loads(response.content.decode("utf-8"))
