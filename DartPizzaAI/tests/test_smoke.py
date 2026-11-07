"""Pruebas de humo: ejecutar con `python -m unittest discover -s tests`."""
import unittest
from fastapi.testclient import TestClient
from app.main import app

class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.client=TestClient(app)
    def login(self,email='admin@dartpizza.local',password='Admin123!'):
        r=self.client.post('/api/auth/login',json={'email':email,'password':password}); self.assertEqual(r.status_code,200); return {'Authorization':'Bearer '+r.json()['access_token']}
    def test_health(self): self.assertEqual(self.client.get('/api/health').json()['status'],'ok')
    def test_admin_login_and_products(self):
        h=self.login(); self.assertGreater(len(self.client.get('/api/products',headers=h).json()),0)
    def test_client_cannot_access_admin_analytics(self):
        h=self.login('cliente@dartpizza.local','Cliente123!'); self.assertEqual(self.client.get('/api/analytics/summary',headers=h).status_code,403)
    def test_order_flow(self):
        h=self.login('cliente@dartpizza.local','Cliente123!'); products=self.client.get('/api/products',headers=h).json(); p=next(x for x in products if x['stock']>0)
        r=self.client.post('/api/orders',headers=h,json={'items':[{'product_id':p['id'],'quantity':1}]}); self.assertEqual(r.status_code,200); self.assertGreater(r.json()['total'],0)
if __name__=='__main__': unittest.main()
