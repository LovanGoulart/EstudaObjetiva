"""Integração entre Banco de provas e tela Simulados.
Execute: python -m unittest discover -s tests -v
"""
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path

class AutoSimuladosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ['DATABASE_PATH'] = str(Path(cls.tmp.name) / 'estudos.db')
        os.environ['SECRET_KEY'] = 'test-only-automatic-results'
        cls.module = importlib.import_module('app')
        cls.client = cls.module.app.test_client()
        cls.client.get('/')
        with cls.client.session_transaction() as session:
            cls.csrf = session['csrf']

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_finished_attempt_appears_automatically_without_manual_exam(self):
        source = next(e for e in self.module.REAL_EXAMS.values()
                      if e.get('kind') == 'native')
        before = self.client.get('/api/bootstrap').get_json()
        manual_count = len(before['exams'])
        started = self.client.post(
            f"/api/real-exams/{source['id']}/attempts",
            json={}, headers={'X-CSRF-Token': self.csrf}
        )
        self.assertEqual(started.status_code, 201)
        attempt_id = started.get_json()['attempt']['id']
        finished = self.client.post(
            f'/api/real-exams/attempts/{attempt_id}/finish',
            json={}, headers={'X-CSRF-Token': self.csrf}
        )
        self.assertEqual(finished.status_code, 200)
        after = self.client.get('/api/bootstrap').get_json()
        result = next(x for x in after['real_results'] if x['id'] == attempt_id)
        self.assertEqual(result['name'], source['name'])
        self.assertEqual(result['maximo'], 100)
        self.assertEqual(len(after['exams']), manual_count)

if __name__ == '__main__':
    unittest.main()
