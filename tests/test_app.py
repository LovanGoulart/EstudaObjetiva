"""Run after: pip install -r requirements.txt; python -m unittest discover -s tests -v"""
import importlib,os,tempfile,unittest
from pathlib import Path

class StudyAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        os.environ['DATABASE_PATH']=str(Path(cls.temp.name)/'app.db')
        os.environ['SECRET_KEY']='test-secret-only'
        cls.module=importlib.import_module('app')
        cls.app=cls.module.app
    @classmethod
    def tearDownClass(cls):pass  # Mantém banco até o fim do conjunto de testes
    def setUp(self):
        self.client=self.app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as s:
            self.csrf=s['csrf']
    def send(self,url,method='patch',data=None,token=True):
        headers={'X-CSRF-Token':self.csrf} if token else {}
        return getattr(self.client,method)(url,json=data or {},headers=headers)
    def test_page_and_seed(self):
        self.assertEqual(self.client.get('/').status_code,200)
        obj=self.client.get('/api/bootstrap').get_json()
        self.assertEqual(len(obj['subjects']),5)
        self.assertEqual(len(obj['topics']),181)
        self.assertGreaterEqual(len(obj['planner']),12)
    def test_flexible_planner(self):
        before=self.client.get('/api/bootstrap').get_json()['planner']
        self.assertTrue(all('day' not in item for item in before))
        r=self.send('/api/planner','post',{'focus':'Revisar DNS quando puder'})
        self.assertEqual(r.status_code,201)
        after=self.client.get('/api/bootstrap').get_json()['planner']
        goal=next(item for item in after if item['focus']=='Revisar DNS quando puder')
        self.assertEqual(self.send('/api/planner/'+str(goal['id']),data={'done':True,'notes':'Feito sem data fixa'}).status_code,200)
        self.assertEqual(self.send('/api/planner/'+str(goal['id']),'delete',{}).status_code,405)
        self.assertTrue(any(item['id']==goal['id'] for item in self.client.get('/api/bootstrap').get_json()['planner']))
    def test_csrf_rejects_unauthorized_writes(self):
        self.assertEqual(self.send('/api/topics/1',data={'status':'done'},token=False).status_code,403)
    def test_topic_progress_notes_and_reviews(self):
        r=self.send('/api/topics/1',data={'status':'done','notes':'Estudei roteadores'})
        self.assertEqual(r.status_code,200)
        j=self.client.get('/api/bootstrap').get_json()
        topic=next(t for t in j['topics'] if t['id']==1)
        self.assertEqual(topic['notes'],'Estudei roteadores')
        self.assertEqual(topic['status'],'done')
        self.assertEqual(len([x for x in j['revisions'] if x['topic_id']==1]),3)
        self.send('/api/topics/1',data={'status':'pending'})
        self.assertFalse([x for x in self.client.get('/api/bootstrap').get_json()['revisions'] if x['topic_id']==1])
    def test_score_and_minutes(self):
        self.assertEqual(self.send('/api/sessions','post',{'day':'2026-12-05','minutes':120,'subject_id':1,'kind':'Teoria'}).status_code,201)
        self.assertEqual(self.send('/api/exams','post',{'day':'2026-12-05','name':'Simulado','port':9,'mat':7,'ger':5,'leg':5,'esp':10}).status_code,201)
        j=self.client.get('/api/bootstrap').get_json()
        self.assertEqual(j['exams'][0]['score'],92)
        self.assertEqual(j['sessions'][0]['minutes'],120)
    def test_backup(self):
        response=self.client.get('/api/backup')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.get_json()['version'],1)

if __name__=='__main__':unittest.main()
