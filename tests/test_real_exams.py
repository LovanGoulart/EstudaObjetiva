"""Testes da nova área de provas reais. Executar: python -m unittest discover -s tests -v"""
import importlib,os,tempfile,unittest
from pathlib import Path

class RealExamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        os.environ['DATABASE_PATH']=str(Path(cls.temp.name)/'provas.db')
        os.environ['SECRET_KEY']='chave-testes-local'
        cls.module=importlib.import_module('app')
        cls.app=cls.module.app
    @classmethod
    def tearDownClass(cls):pass  # Manter banco de testes enquanto os módulos compartilham o import app
    def setUp(self):
        self.client=self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as session:self.csrf=session['csrf']
    def call(self,method,path,payload=None):
        return getattr(self.client,method)(path,json=payload or {},headers={'X-CSRF-Token':self.csrf})
    def test_catalog_and_pdf(self):
        exams=self.client.get('/api/real-exams').get_json()['exams']
        self.assertEqual(len(exams),11)
        self.assertEqual(sum(e['gabarito'] is not None for e in exams),10)
        self.assertEqual(self.client.get('/exam-files/guaraniacu-2024').status_code,200)
        self.assertEqual(self.client.get('/exam-files/guaraniacu-2024').headers['X-Frame-Options'],'SAMEORIGIN')
    def test_save_finish_and_retake(self):
        start=self.call('post','/api/real-exams/guaraniacu-2024/attempts')
        self.assertEqual(start.status_code,201)
        attempt=start.get_json()['attempt']['id']
        self.assertEqual(self.call('patch',f'/api/real-exams/attempts/{attempt}',{'answers':{'1':'A','2':'B'}}).status_code,200)
        result=self.call('post',f'/api/real-exams/attempts/{attempt}/finish').get_json()['attempt']
        self.assertTrue(result['finished'])
        self.assertEqual(len(result['correction']),40)
        self.assertEqual(sum(result['totals'][k] for k in ('acerto','erro','branco','anulada')),40)
        self.assertEqual(self.call('patch',f'/api/real-exams/attempts/{attempt}',{'answers':{}}).status_code,400)
        self.assertNotEqual(attempt,self.call('post','/api/real-exams/guaraniacu-2024/attempts').get_json()['attempt']['id'])
    def test_candiota_without_gabarito(self):
        attempt=self.call('post','/api/real-exams/candiota-2023/attempts').get_json()['attempt']['id']
        result=self.call('post',f'/api/real-exams/attempts/{attempt}/finish').get_json()['attempt']
        self.assertIsNone(result['correction'])
        self.assertIsNone(result['totals'])
    def test_backup_contains_attempts(self):
        self.call('post','/api/real-exams/portao-2019/attempts')
        self.assertIn('real_exam_attempts',self.client.get('/api/backup').get_json())
if __name__=='__main__':unittest.main()
