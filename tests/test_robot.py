import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from src.robot import ROOT, ViaCEP, LookupFailure, normalize_cep, process

class RobotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def run_batch(self, **kwargs):
        return process(output_dir=self.root/'out', logs_dir=self.root/'logs', **kwargs)
    def test_demo_fifteen_and_decisions(self):
        r = self.run_batch(mode='demo')
        self.assertEqual(r['resumo'],dict(total=15,apto=10,pendente=4,duplicado=1,falha_consulta=0,prioridade_alta=3))
        self.assertEqual(r['itens'][0]['logradouro'],'Praça da Sé')
        self.assertEqual(r['itens'][10]['status'],'duplicado')
        self.assertIn('não encontrado',r['itens'][13]['motivo'])
        self.assertEqual(json.loads((self.root/'out/resultado.json').read_text())['execucao'],r['execucao'])
    def test_rerun_does_not_accumulate(self):
        a=self.run_batch(mode='demo'); b=self.run_batch(mode='demo')
        self.assertEqual(len(b['itens']),15)
        self.assertNotEqual(a['execucao'],b['execucao'])
        self.assertEqual(len(list((self.root/'logs').glob('*.jsonl'))),2)
    def test_retry_recovers(self):
        calls=[]
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): return b'{"cep":"01001-000","localidade":"Sao Paulo","uf":"SP","logradouro":"Praca da Se"}'
        def opener(*args,**kwargs):
            calls.append(1)
            if len(calls)<3: raise URLError('test')
            return Response()
        events=[]
        client=ViaCEP(opener=opener,sleeper=lambda _:None,audit=lambda **kw:events.append(kw))
        client.lookup('01001000');client.lookup('01001000')
        self.assertEqual(len(calls),3)
        self.assertEqual(len(events),2)
    def test_failure_is_visible_and_batch_continues(self):
        def fail(*args,**kwargs): raise URLError('test')
        client=ViaCEP(mode='falha',opener=fail,sleeper=lambda _:None)
        r=self.run_batch(mode='falha',client=client)
        self.assertEqual(r['resumo']['falha_consulta'],11)
        self.assertEqual(r['resumo']['pendente'],3)
        self.assertEqual(r['resumo']['total'],15)
    def test_missing_and_bad_csv_keep_prior_snapshot(self):
        prior=self.run_batch(mode='demo')
        bad=self.root/'bad.csv'; bad.write_text('coluna_errada\nvalor\n')
        for file in (bad,self.root/'missing.csv'):
            with self.assertRaises(ValueError): self.run_batch(input_path=file,mode='demo')
        self.assertEqual(json.loads((self.root/'out/resultado.json').read_text())['execucao'],prior['execucao'])
        self.assertTrue(any('falha_lote' in p.read_text() for p in (self.root/'logs').glob('*.jsonl')))
    def test_cep_validation(self):
        self.assertEqual(normalize_cep('01001-000'),'01001000')
        for value in ('', '12A45','010010000','01001 000'):
            with self.assertRaises(ValueError): normalize_cep(value)
    def test_audit_omits_address_and_free_text(self):
        self.run_batch(mode='demo')
        log=next((self.root/'logs').glob('*.jsonl')).read_text()
        for text in ('Praça da Sé','referência de teste','Buraco dificulta'):
            self.assertNotIn(text,log)
    def test_incomplete_and_mismatching_api_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): return b'{"cep":"11111-111","localidade":"Teste","uf":"SP"}'
        with self.assertRaises(LookupFailure):
            ViaCEP(opener=lambda *a,**kw:Response(),sleeper=lambda _:None).lookup('01001000')

if __name__=='__main__': unittest.main(verbosity=2)
