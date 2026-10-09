import urllib.request, json

base = 'http://localhost:8000'

# 1. Health
r = urllib.request.urlopen(base + '/health')
health = json.loads(r.read())
print('HEALTH:', health)

# 2. Extract
req_body = json.dumps({'text': 'Plan a 5-night Dubai trip for 2 adults, budget 150000, 4-star hotel, balanced'}).encode()
req = urllib.request.Request(base + '/api/requirements/extract', req_body, {'Content-Type': 'application/json'})
ext = json.loads(urllib.request.urlopen(req).read())
r2 = ext['requirement']
print(f"EXTRACT  confidence={round(ext['overall_confidence'],2)}  dest={r2['destination']}  nights={r2['nights']}  budget={r2['budget']}")

# 3. Recommend
body = json.dumps({'requirement': r2, 'use_mmr': True, 'top_k': 5}).encode()
recs_r = urllib.request.Request(base + '/api/recommendations', body, {'Content-Type': 'application/json'})
recs = json.loads(urllib.request.urlopen(recs_r).read())
items = recs['items']
print(f"RECS  {len(items)} hotels  hard_filter_survivors={recs['candidates_after_hard_filters']}  latency={recs['latency_ms']}ms")
for it in items:
    cat = it['category']
    name = it['name']
    stars = it['star_rating']
    total = it['estimated_total']
    score = it['scores']['final']
    print(f"  [{cat:22s}]  {name:35s}  {stars}*  est={total:,.0f}  score={score}")

# 4. Quote
top = items[0]
trip = {'requirement': r2, 'hotel_id': top['hotel_id'], 'activity_ids': [], 'transfer_type': 'private'}
body = json.dumps(trip).encode()
q_r = urllib.request.Request(base + '/api/quote/generate', body, {'Content-Type': 'application/json'})
q = json.loads(urllib.request.urlopen(q_r).read())
p = q['pricing']
print(f"\nQUOTE  total={p['total']:,.0f}  margin={p['gross_margin']:,.0f}  margin_rate={round(p.get('margin_rate',0)*100,1)}%  ready_to_send={q['ready_to_send']}")
print("  Validation:", [v['check'] + '=' + v['status'] for v in q['validation']])
if q.get('budget_optimizer', {}).get('suggested_hotel'):
    bo = q['budget_optimizer']
    print(f"  BudgetOptimiser: switch to {bo['suggested_hotel']['name']} saves {bo['savings']:,.0f}")

# 5. Modify
body = json.dumps({'trip': trip, 'command': 'make it more relaxed'}).encode()
mod_r = urllib.request.Request(base + '/api/trip/modify', body, {'Content-Type': 'application/json'})
mod = json.loads(urllib.request.urlopen(mod_r).read())
delta = mod.get('delta', {})
print(f"\nMODIFY  note={mod['note']}  changed={mod['changed']}  price_delta={delta.get('price')}  margin_delta={delta.get('margin')}")
