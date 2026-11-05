import os
os.environ.setdefault('JWT_SECRET','test-secret-long-enough-for-local-tests-123456789')
os.environ.setdefault('DATABASE_URL','sqlite://')
from fastapi.testclient import TestClient
from app.main import app
from app.main_state import engine
from app.db import Base

Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
client=TestClient(app)

def token():
    r=client.post('/api/auth/register',json={'email':'test@example.com','password':'strong-password','display_name':'Test'})
    assert r.status_code==200, r.text
    return r.json()['access_token']

def test_health():
    assert client.get('/health').json()['status']=='healthy'

def test_full_practice_flow():
    t=token(); h={'Authorization':f'Bearer {t}'}
    assert client.get('/api/auth/me',headers=h).status_code==200
    cases=client.get('/api/cases',headers=h).json(); assert len(cases)>=1
    s=client.post('/api/sessions',headers=h,json={'module':'case','case_ref':cases[0]['id']})
    assert s.status_code==200,s.text
    sid=s.json()['id']
    turn=client.post(f'/api/sessions/{sid}/turn',headers=h,json={'message':'I would first structure revenue into price and volume, then investigate costs and test the largest hypothesis.'})
    assert turn.status_code==200,turn.text
    ev=client.post(f'/api/sessions/{sid}/evaluate',headers=h)
    assert ev.status_code==200,ev.text
    assert len(ev.json()['dimensions'])==7
    assert client.get('/api/profile',headers=h).json()['sessions']==1


def test_progressive_reveal_over_api():
    t = client.post('/api/auth/register', json={'email': 'reveal@example.com', 'password': 'strong-password'}).json()['access_token']
    h = {'Authorization': f'Bearer {t}'}
    s = client.post('/api/sessions', headers=h, json={'module': 'case', 'case_ref': 'profitability_coffee'}).json()
    assert 'fact_pool' not in s['case'] and not any('Fixed costs' in f for f in s['case']['facts'])
    r = client.post(f"/api/sessions/{s['id']}/turn", headers=h, json={'message': 'I would split costs into fixed and variable.'}).json()
    assert any('Fixed costs' in f for f in r['new_facts']) and any('Fixed costs' in f for f in r['case_facts'])
    assert 'Here is the data you asked for' in r['reply']
