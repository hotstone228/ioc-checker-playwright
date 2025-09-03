from fastapi.testclient import TestClient
from ioc_checker.main import app

client = TestClient(app)

def test_parse_separates_uri_from_fqdn():
    text = 'visit http://example.com and example.org or email test@example.com'
    resp = client.post('/parse', json={'text': text})
    data = resp.json()
    assert 'uri' in data and 'http://example.com' in data['uri']
    assert 'fqdn' in data and 'example.org' in data['fqdn']
    assert 'email' in data and 'test@example.com' in data['email']
