import unittest
from research.proxy_tokenizer import ENCODER,token_count


class ProxyTokenizerTests(unittest.TestCase):
    def test_source_reserved_strings_are_ordinary_literal_text(self):
        text='Quoted source: <|endoftext|> then <|fim_prefix|> remains literal.'
        tokens=ENCODER.encode(text)
        self.assertEqual(ENCODER.decode(tokens),text)
        self.assertEqual(token_count(text),len(tokens))

    def test_previously_valid_text_has_identical_tokens(self):
        import tiktoken
        old=tiktoken.get_encoding('cl100k_base')
        for text in ['normal source text','{"owner":"example","valid_at":2}','Evidence with ordinary Unicode: 北京']:
            self.assertEqual(ENCODER.encode(text),old.encode(text))
