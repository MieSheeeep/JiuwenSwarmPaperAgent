"""Count arbitrary source text literally, never interpreting reserved token spellings."""
import tiktoken


class OrdinaryTextTokenizer:
    def __init__(self):self.encoder=tiktoken.get_encoding('cl100k_base')
    def encode(self,text):return self.encoder.encode(text,disallowed_special=())
    def decode(self,tokens):return self.encoder.decode(tokens)


ENCODER=OrdinaryTextTokenizer()


def token_count(text):return len(ENCODER.encode(text))
