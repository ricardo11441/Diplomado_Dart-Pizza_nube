from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3, hashlib, hmac, secrets, os, json
from datetime import datetime, timedelta, timezone
from typing import Optional

BASE=Path(__file__).resolve().parent
DB=Path(os.getenv('DART_DB', BASE.parent/'data'/'dartpizza.db'))
DB.parent.mkdir(parents=True,exist_ok=True)
if os.getenv('APP_ENV') == 'production' and len(os.getenv('JWT_SECRET', '')) < 32:
 raise RuntimeError('En producción debes configurar JWT_SECRET con al menos 32 caracteres aleatorios.')
app=FastAPI(title='Dart Pizza AI API',version='1.0.0')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def pw_hash(p):
 salt=secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),240000).hex(); return f'{salt}${digest}'
def pw_ok(p,stored):
 try:
  salt,d=stored.split('$'); return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),240000).hex(),d)
 except: return False

def init():
 c=db(); c.executescript('''
 CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'cliente',active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,description TEXT DEFAULT '',price REAL NOT NULL,stock INTEGER NOT NULL DEFAULT 100,active INTEGER NOT NULL DEFAULT 1,image TEXT DEFAULT '🍕');
 CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), customer TEXT NOT NULL,total REAL NOT NULL,status TEXT NOT NULL DEFAULT 'recibido',items TEXT NOT NULL,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,unit TEXT NOT NULL,quantity REAL NOT NULL,min_quantity REAL NOT NULL);
 CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY,ingredient_id INTEGER REFERENCES inventory(id),kind TEXT NOT NULL,quantity REAL NOT NULL,note TEXT,created_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT NOT NULL,detail TEXT,created_at TEXT NOT NULL);
 ''')
 if not c.execute('select 1 FROM users LIMIT 1').fetchone():
  now=datetime.now(timezone.utc).isoformat()
  seed_demo=os.getenv('DART_SEED_DEMO','true').lower() in ('1','true','yes')
  if seed_demo:
   c.execute('insert into users(name,email,password,role,created_at) values(?,?,?,?,?)',('Administrador','admin@dartpizza.local',pw_hash('Admin123!'),'admin',now))
   c.execute('insert into users(name,email,password,role,created_at) values(?,?,?,?,?)',('Empleado Demo','empleado@dartpizza.local',pw_hash('Empleado123!'),'empleado',now))
   c.execute('insert into users(name,email,password,role,created_at) values(?,?,?,?,?)',('Cliente Demo','cliente@dartpizza.local',pw_hash('Cliente123!'),'cliente',now))
  else:
   admin_email=os.getenv('ADMIN_EMAIL','').strip().lower()
   admin_password=os.getenv('ADMIN_PASSWORD','')
   admin_name=os.getenv('ADMIN_NAME','Administrador').strip() or 'Administrador'
   if not admin_email or len(admin_password)<12:
    c.close()
    raise RuntimeError('Configura ADMIN_EMAIL y ADMIN_PASSWORD (mínimo 12 caracteres) para crear el administrador inicial.')
   c.execute('insert into users(name,email,password,role,created_at) values(?,?,?,?,?)',(admin_name,admin_email,pw_hash(admin_password),'admin',now))
 if not c.execute('select 1 FROM products LIMIT 1').fetchone():
  products=[('Dart Pepperoni','Pizza','Pepperoni, mozzarella y salsa de tomate',28000,40,'🍕'),('Margarita','Pizza','Mozzarella, tomate y albahaca',24000,40,'🍕'),('Hawaiana','Pizza','Jamón, piña y mozzarella',27000,35,'🍍'),('Cuatro Quesos','Pizza','Mezcla de cuatro quesos',32000,25,'🧀'),('Gaseosa 400 ml','Bebidas','Bebida fría',5000,100,'🥤'),('Pan de ajo','Acompañamientos','Porción de pan de ajo',9000,50,'🥖')]
  c.executemany('insert into products(name,category,description,price,stock,image) values(?,?,?,?,?,?)',products)
 if not c.execute('select 1 FROM inventory LIMIT 1').fetchone():
  for n,u,q,m in [('Mozzarella','kg',18,5),('Pepperoni','kg',8,2),('Harina','kg',30,8),('Tomate','kg',12,3),('Piña','kg',6,2),('Jamón','kg',7,2)]: c.execute('insert into inventory(name,unit,quantity,min_quantity) values(?,?,?,?)',(n,u,q,m))
 c.commit(); c.close()
init()

class Login(BaseModel): email:str; password:str
class Register(BaseModel): name:str; email:str; password:str=Field(min_length=8)
class OrderIn(BaseModel): items:list[dict]; customer:Optional[str]=None
class StatusIn(BaseModel): status:str
class ProductIn(BaseModel): name:str; category:str; description:str=''; price:float=Field(gt=0); stock:int=Field(ge=0); image:str='🍕'
class StockIn(BaseModel): quantity:float=Field(gt=0); kind:str='entrada'; note:str='Ajuste manual'
class ChatIn(BaseModel): question:str

def token_for(uid):
 exp=int((datetime.now(timezone.utc)+timedelta(hours=12)).timestamp()); raw=f'{uid}.{exp}'; sig=hmac.new(os.getenv('JWT_SECRET','dev-secret-change-me').encode(),raw.encode(),hashlib.sha256).hexdigest(); return f'{raw}.{sig}'
def current(authorization:Optional[str]=Header(None)):
 if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Inicia sesión para continuar')
 try:
  uid,exp,sig=authorization[7:].split('.'); raw=f'{uid}.{exp}'; expected=hmac.new(os.getenv('JWT_SECRET','dev-secret-change-me').encode(),raw.encode(),hashlib.sha256).hexdigest()
  if int(exp)<int(datetime.now(timezone.utc).timestamp()) or not hmac.compare_digest(sig,expected): raise ValueError()
 except: raise HTTPException(401,'Sesión inválida o expirada')
 c=db(); u=c.execute('select id,name,email,role,active from users where id=?',(uid,)).fetchone(); c.close()
 if not u or not u['active']: raise HTTPException(401,'Cuenta inactiva')
 return dict(u)
def roles(*allowed):
 def dep(u=Depends(current)):
  if u['role'] not in allowed: raise HTTPException(403,'No tienes permisos para esta operación')
  return u
 return dep
def audit(u,action,detail=''):
 c=db(); c.execute('insert into audit(user_id,action,detail,created_at) values(?,?,?,?)',(u['id'],action,detail,datetime.now(timezone.utc).isoformat())); c.commit(); c.close()

@app.get('/')
def home(): return FileResponse(BASE/'static'/'index.html')
@app.get('/api/health')
def health(): return {'status':'ok','database':'sqlite','time':datetime.now(timezone.utc).isoformat()}
@app.post('/api/auth/login')
def login(x:Login):
 c=db(); u=c.execute('select * from users where email=?',(x.email.lower(),)).fetchone(); c.close()
 if not u or not pw_ok(x.password,u['password']) or not u['active']: raise HTTPException(401,'Correo o contraseña incorrectos')
 return {'access_token':token_for(u['id']),'user':{'id':u['id'],'name':u['name'],'email':u['email'],'role':u['role']}}
@app.post('/api/auth/register')
def register(x:Register):
 c=db()
 try: cur=c.execute('insert into users(name,email,password,role,created_at) values(?,?,?,?,?)',(x.name,x.email.lower(),pw_hash(x.password),'cliente',datetime.now(timezone.utc).isoformat())); c.commit(); uid=cur.lastrowid
 except sqlite3.IntegrityError: c.close(); raise HTTPException(409,'Ese correo ya está registrado')
 c.close(); return {'access_token':token_for(uid),'user':{'id':uid,'name':x.name,'email':x.email,'role':'cliente'}}
@app.get('/api/auth/me')
def me(u=Depends(current)): return u
@app.get('/api/products')
def products(u=Depends(current)):
 c=db(); rows=c.execute('select * from products where active=1 order by category,name').fetchall(); c.close(); return [dict(r) for r in rows]
@app.post('/api/products')
def add_product(x:ProductIn,u=Depends(roles('admin'))):
 c=db(); cur=c.execute('insert into products(name,category,description,price,stock,image) values(?,?,?,?,?,?)',(x.name,x.category,x.description,x.price,x.stock,x.image)); c.commit(); item=c.execute('select * from products where id=?',(cur.lastrowid,)).fetchone(); c.close(); audit(u,'producto_creado',x.name); return dict(item)
@app.put('/api/products/{pid}')
def edit_product(pid:int,x:ProductIn,u=Depends(roles('admin'))):
 c=db(); cur=c.execute('update products set name=?,category=?,description=?,price=?,stock=?,image=? where id=?',(x.name,x.category,x.description,x.price,x.stock,x.image,pid)); c.commit(); c.close()
 if not cur.rowcount: raise HTTPException(404,'Producto no encontrado')
 audit(u,'producto_actualizado',str(pid)); return {'ok':True}
@app.get('/api/orders')
def orders(u=Depends(current)):
 c=db(); rows=c.execute('select * from orders '+('where user_id=? ' if u['role']=='cliente' else '')+'order by id desc', (u['id'],) if u['role']=='cliente' else ()).fetchall(); c.close(); return [{**dict(r),'items':json.loads(r['items'])} for r in rows]
@app.post('/api/orders')
def create_order(x:OrderIn,u=Depends(current)):
 if not x.items: raise HTTPException(400,'El carrito está vacío')
 c=db(); total=0; clean=[]
 for it in x.items:
  p=c.execute('select * from products where id=? and active=1',(it.get('product_id'),)).fetchone(); qty=int(it.get('quantity',1))
  if not p or qty<1 or qty>50: c.close(); raise HTTPException(400,'Producto o cantidad no válida')
  if p['stock']<qty: c.close(); raise HTTPException(409,f'Sin existencias suficientes: {p["name"]}')
  total+=p['price']*qty; clean.append({'product_id':p['id'],'name':p['name'],'quantity':qty,'unit_price':p['price'],'notes':str(it.get('notes',''))[:250]})
 for it in clean: c.execute('update products set stock=stock-? where id=?',(it['quantity'],it['product_id']))
 cur=c.execute('insert into orders(user_id,customer,total,status,items,created_at) values(?,?,?,?,?,?)',(u['id'],x.customer or u['name'],total,'recibido',json.dumps(clean,ensure_ascii=False),datetime.now(timezone.utc).isoformat())); c.commit(); oid=cur.lastrowid; c.close(); audit(u,'pedido_creado',str(oid)); return {'id':oid,'total':total,'status':'recibido'}
@app.patch('/api/orders/{oid}/status')
def status(oid:int,x:StatusIn,u=Depends(roles('admin','empleado'))):
 allowed=['recibido','en_preparacion','listo','en_camino','entregado','cancelado']
 if x.status not in allowed: raise HTTPException(400,'Estado no válido')
 c=db(); cur=c.execute('update orders set status=? where id=?',(x.status,oid)); c.commit(); c.close()
 if not cur.rowcount: raise HTTPException(404,'Pedido no encontrado')
 audit(u,'estado_pedido',f'{oid}:{x.status}'); return {'ok':True}
@app.get('/api/inventory')
def inventory(u=Depends(roles('admin','empleado'))):
 c=db(); rows=c.execute('select * from inventory order by name').fetchall(); c.close(); return [dict(r) for r in rows]
@app.post('/api/inventory/{iid}/movement')
def movement(iid:int,x:StockIn,u=Depends(roles('admin'))):
 if x.kind not in ('entrada','salida','ajuste'): raise HTTPException(400,'Movimiento no válido')
 c=db(); row=c.execute('select * from inventory where id=?',(iid,)).fetchone()
 if not row: c.close(); raise HTTPException(404,'Ingrediente no encontrado')
 new=row['quantity']+x.quantity if x.kind=='entrada' else row['quantity']-x.quantity if x.kind=='salida' else x.quantity
 if new<0: c.close(); raise HTTPException(400,'Existencia insuficiente')
 c.execute('update inventory set quantity=? where id=?',(new,iid)); c.execute('insert into movements(ingredient_id,kind,quantity,note,created_at) values(?,?,?,?,?)',(iid,x.kind,x.quantity,x.note,datetime.now(timezone.utc).isoformat())); c.commit(); c.close(); return {'ok':True,'quantity':new}
@app.get('/api/analytics/summary')
def summary(u=Depends(roles('admin'))):
 c=db(); total=c.execute("select coalesce(sum(total),0) n from orders where status!='cancelado'").fetchone()['n']; count=c.execute("select count(*) n from orders where status!='cancelado'").fetchone()['n']; pending=c.execute("select count(*) n from orders where status in ('recibido','en_preparacion')").fetchone()['n']; avg=total/count if count else 0; top=c.execute("select json_each.value->>'name' name,sum(cast(json_each.value->>'quantity' as integer)) qty from orders,json_each(orders.items) where orders.status!='cancelado' group by name order by qty desc limit 5").fetchall(); daily=c.execute("select substr(created_at,1,10) day,sum(total) revenue,count(*) orders from orders where status!='cancelado' group by day order by day desc limit 7").fetchall(); low=c.execute('select count(*) n from inventory where quantity<=min_quantity').fetchone()['n']; c.close(); return {'revenue':round(total,2),'orders':count,'pending':pending,'average_ticket':round(avg,2),'low_stock':low,'top_products':[dict(x) for x in top],'daily':[dict(x) for x in reversed(daily)]}
@app.get('/api/analytics/insights')
def insights(u=Depends(roles('admin'))):
 s=summary(u); out=[]
 if s['orders']<5: out.append({'priority':'media','title':'Construir historial de ventas','evidence':f'Hay {s["orders"]} pedidos registrados.','recommendation':'Registra las ventas reales durante varias semanas antes de tomar decisiones predictivas.'})
 if s['low_stock']: out.append({'priority':'alta','title':'Revisar ingredientes con existencias bajas','evidence':f'{s["low_stock"]} ingredientes están en o por debajo del mínimo.','recommendation':'Revisa el inventario y registra entradas antes de aceptar compras que dependan de esos insumos.'})
 if s['top_products']: out.append({'priority':'media','title':'Asegurar disponibilidad de los productos líderes','evidence':'Productos líderes calculados a partir de pedidos no cancelados.','recommendation':'Verifica que los ingredientes de los productos más vendidos estén abastecidos.'})
 return {'source':'SQLite / pedidos registrados','period':'Todo el historial disponible','insights':out or [{'priority':'baja','title':'Sin alertas críticas','evidence':'No se detectaron condiciones automáticas de alerta.','recommendation':'Continúa registrando operaciones para mejorar el análisis.'}]}
@app.post('/api/ai/chat')
def chat(x:ChatIn,u=Depends(roles('admin'))):
 s=summary(u); q=x.question.lower(); answer=f"Con los datos registrados hay {s['orders']} pedidos no cancelados, ingresos acumulados de ${s['revenue']:,.0f} y ticket promedio de ${s['average_ticket']:,.0f}. Hay {s['pending']} pedidos pendientes y {s['low_stock']} ingredientes en nivel bajo."
 if 'producto' in q or 'vend' in q:
  names=', '.join(f"{p['name']} ({p['qty']} unidades)" for p in s['top_products']) or 'aún no hay suficientes pedidos'; answer+=f' Productos destacados: {names}.'
 if s['orders']<5: answer+=' La muestra es pequeña; no es responsable generar pronósticos todavía.'
 answer+=' Este análisis usa consultas determinísticas sobre la base de datos. Para respuestas generativas se puede configurar Ollama; no se han inventado datos.'
 audit(u,'consulta_ai',x.question[:200]); return {'answer':answer,'based_on':'Pedidos e inventario de la base local','metrics':s}
@app.get('/api/users')
def users(u=Depends(roles('admin'))):
 c=db(); rows=c.execute('select id,name,email,role,active,created_at from users order by id').fetchall(); c.close(); return [dict(r) for r in rows]
@app.get('/api/audit')
def audit_log(u=Depends(roles('admin'))):
 c=db(); rows=c.execute('select a.*,u.name user_name from audit a left join users u on u.id=a.user_id order by a.id desc limit 100').fetchall(); c.close(); return [dict(r) for r in rows]
