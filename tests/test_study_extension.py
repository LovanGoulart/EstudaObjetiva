"""Testes de integração da versão 2.0. Requer Flask instalado."""
import importlib,unittest

class StudyExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod=importlib.import_module('app')
        cls.app=cls.mod.app
    def setUp(self):
        self.client=self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as session:self.csrf=session['csrf']
    def request(self,method,path,data=None):
        return getattr(self.client,method)(path,json=data or {},headers={'X-CSRF-Token':self.csrf})
    def test_native_quiz_correct_weighting(self):
        exams=self.client.get('/api/real-exams').get_json()['exams']
        self.assertEqual(len([e for e in exams if e['kind']=='native']),2)
        resp=self.request('post','/api/real-exams/simulado-inédito-2027/attempts')
        self.assertEqual(resp.status_code,201)
        attempt=resp.get_json()['attempt']; self.assertEqual(len(attempt['questions']),40)
        self.assertNotIn('answer',attempt['questions'][0])
        official=self.mod.REAL_EXAMS['simulado-inédito-2027']
        answers={str(i):q['answer'] for i,q in enumerate(official['questions'],1)}
        self.assertEqual(self.request('patch',f'/api/real-exams/attempts/{attempt["id"]}',{'answers':answers}).status_code,200)
        finish=self.request('post',f'/api/real-exams/attempts/{attempt["id"]}/finish').get_json()['attempt']
        self.assertEqual(finish['totals']['pontos'],100)
        self.assertEqual(finish['totals']['maximo'],100)
        self.assertEqual(finish['totals']['acerto'],40)
        self.assertTrue(finish['correction'][0]['explanation'])
    def test_notes_and_lessons(self):
        self.assertEqual(self.request('patch','/api/question-notes/guaraniacu-2024/1',{'note':'Refazer pela banca'}).status_code,200)
        notes=self.client.get('/api/question-notes/guaraniacu-2024').get_json()['notes']
        self.assertTrue(any(x['note']=='Refazer pela banca' for x in notes))
        lessons=self.client.get('/api/lesson-plans').get_json()['lessons']
        self.assertEqual(len(lessons),19)
        id=lessons[0]['id']
        self.assertEqual(self.request('patch',f'/api/lesson-plans/{id}',{'done':True,'notes':'Feito'}).status_code,200)
        self.assertEqual(next(x for x in self.client.get('/api/lesson-plans').get_json()['lessons'] if x['id']==id)['done'],True)
    def test_files_and_stats(self):
        docs=self.client.get('/api/library').get_json()['documents']
        self.assertGreaterEqual(len(docs),2)
        self.assertEqual(self.client.get('/library/edital-2026').status_code,200)
        self.assertEqual(self.client.get('/exam-pages/guaraniacu-2024/2').status_code,200)
        self.assertEqual(self.client.get('/api/evolution').status_code,200)
    def test_backup_v2_contains_notes(self):
        b=self.client.get('/api/backup').get_json()
        self.assertIn('question_notes',b)
        self.assertIn('lesson_progress',b)

if __name__=='__main__':unittest.main()
