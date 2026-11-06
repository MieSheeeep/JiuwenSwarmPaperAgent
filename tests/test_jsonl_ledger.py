import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.jsonl_ledger import read_jsonl, append_durable, configure_gateway_ledger


class JsonlLedgerTests(unittest.TestCase):
    def test_unicode_line_separators_are_content_not_record_boundaries(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'calls.jsonl'
            row={'output':'first\u2028second\u2029third\u0085fourth'}
            path.write_text(json.dumps(row,ensure_ascii=False)+'\n',encoding='utf-8')
            self.assertEqual(read_jsonl(path),[row])
            append_durable(path,row)
            self.assertEqual(read_jsonl(path),[row,row])

    def test_actual_partial_record_is_still_fail_closed(self):
        from research.model_gateway import UnknownSpend
        with TemporaryDirectory() as d:
            path=Path(d)/'calls.jsonl';path.write_text('{"output":"unfinished',encoding='utf-8')
            with self.assertRaises(UnknownSpend):read_jsonl(path)

    def test_safe_codec_is_used_by_existing_gateway_without_source_changes(self):
        import research.model_gateway as gateway
        configure_gateway_ledger()
        self.assertIs(gateway.read_jsonl,read_jsonl)
        self.assertIs(gateway.append_durable,append_durable)
