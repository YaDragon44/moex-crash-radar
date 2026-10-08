import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import morning_make_delivery as delivery
import personal_morning_dashboard as morning


class MakeDeliveryTests(unittest.TestCase):
    def response(self, output, status='1'):
        return Mock(status_code=200, json=Mock(return_value={
            'status': status, 'executionId': 'execution-1', 'outputs': output}))

    def test_confirmed_recipient_and_payload(self):
        output = {'status': 'sent', 'message_id': '123', 'chat_id': '77'}
        with patch.object(delivery.requests, 'post', return_value=self.response(output)) as post:
            self.assertEqual(delivery.send_via_make('secret', '77', 'exact\ntext'), (123, 'execution-1'))
            payload = post.call_args.kwargs['json']['data']
            self.assertEqual(payload['morning_chat_id'], '77')
            self.assertEqual(payload['kind'], 'morning_greeting')
            self.assertEqual(payload['text'], 'exact\ntext')

    def test_unconfirmed_outputs_do_not_pass(self):
        for output in (None, {'status': 'rejected'},
                       {'status': 'sent', 'message_id': '123', 'chat_id': 'other'},
                       {'status': 'sent', 'message_id': '', 'chat_id': '77'}):
            with self.subTest(output=output), patch.object(delivery.requests, 'post', return_value=self.response(output)):
                with self.assertRaises(delivery.DeliveryUncertain):
                    delivery.send_via_make('secret', '77', 'text')

    def test_timeout_never_retries_post(self):
        with patch.object(delivery.requests, 'post', side_effect=delivery.requests.Timeout) as post:
            with self.assertRaises(delivery.DeliveryUncertain):
                delivery.send_via_make('secret', '77', 'text')
            self.assertEqual(post.call_count, 1)

    def test_pending_marker_blocks_second_run(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            os.chdir(directory)
            try:
                with patch.dict(os.environ, {'MAKE_API_TOKEN': 'secret', 'TELEGRAM_CHAT_ID': '77'}, clear=True), \
                     patch.object(morning, 'weather_block', return_value='weather'), \
                     patch.object(morning, 'finance_block', return_value='finance'), \
                     patch.object(morning, 'send_via_make', side_effect=delivery.DeliveryUncertain('unknown')) as send:
                    self.assertEqual(morning.main(), 1)
                    self.assertEqual(morning.main(), 1)
                    self.assertEqual(send.call_count, 1)
                    state = json.loads(Path('artifacts/morning_dashboard_state.json').read_text())
                    self.assertIn('pending_date', state['77'])
            finally:
                os.chdir(previous)

    def test_delivery_saved_before_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            os.chdir(directory)
            try:
                morning.save_state('artifacts/morning_dashboard_state.json', {'77': {'message_id': 5, 'delivered_date': '2000-01-01'}})
                def check_delete(*args):
                    state = json.loads(Path('artifacts/morning_dashboard_state.json').read_text())
                    self.assertEqual(state['77']['message_id'], 123)
                with patch.dict(os.environ, {'MAKE_API_TOKEN': 'secret', 'TELEGRAM_CHAT_ID': '77', 'TELEGRAM_BOT_TOKEN': 'old-secret'}, clear=True), \
                     patch.object(morning, 'weather_block', return_value='weather'), \
                     patch.object(morning, 'finance_block', return_value='finance'), \
                     patch.object(morning, 'send_via_make', return_value=(123, 'execution-1')) as send, \
                     patch.object(morning, 'telegram_delete', side_effect=check_delete):
                    self.assertEqual(morning.main(), 0)
                    self.assertEqual(morning.main(), 0)
                    self.assertEqual(send.call_count, 1)
            finally:
                os.chdir(previous)
