from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CommentariesTest(unittest.TestCase):
    def test_all_officially_keyed_questions_have_comments(self):
        catalog=json.loads((ROOT/'exam_assets/catalog.json').read_text(encoding='utf-8'))
        explained=json.loads((ROOT/'exam_assets/question_explanations.json').read_text(encoding='utf-8'))['exams']
        count=0
        for exam in catalog:
            if not exam.get('answers'):
                self.assertNotIn(exam['id'],explained)
                continue
            notes=explained[exam['id']]
            self.assertEqual(len(notes),len(exam['answers']))
            self.assertEqual([n['question'] for n in notes],list(range(1,len(notes)+1)))
            self.assertTrue(all(len(x['explanation'])>24 for x in notes))
            count+=len(notes)
        self.assertEqual(count,330)

if __name__=='__main__':unittest.main()
