import asyncio
import json
import threading
import time

import requests
import websockets

BASE = 'http://localhost:8000'


def register(email, name, role, password='password123'):
    r = requests.post(f'{BASE}/api/auth/register/', json={
        'email': email, 'name': name, 'role': role, 'password': password,
    })
    if r.status_code not in (200, 201, 400):
        r.raise_for_status()
    return r.json()


def login(email, password='password123'):
    r = requests.post(f'{BASE}/api/auth/login/', json={'email': email, 'password': password})
    r.raise_for_status()
    return r.json()['access']


def api(method, path, token, **kwargs):
    headers = {'Authorization': f'Bearer {token}'}
    r = getattr(requests, method)(f'{BASE}/api/{path}', headers=headers, **kwargs)
    r.raise_for_status()
    return r.json()


def ws_listener(token, expedition_id, label, stop_event):
    async def _listen():
        uri = f'ws://localhost:8000/ws/expeditions/{expedition_id}/?token={token}'
        async with websockets.connect(uri) as ws:
            print(f'  [{label}] WS connected')
            while not stop_event.is_set():
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    print(f'  [{label}] EVENT: {data["type"]} → {data["payload"]}')
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break

    asyncio.run(_listen())


def start_listener(token, expedition_id, label, stop_event):
    t = threading.Thread(target=ws_listener, args=(token, expedition_id, label, stop_event), daemon=True)
    t.start()
    return t


def main():
    print('registering users...')
    register('chief@demo.com', 'Chief Alice', 'chief')
    register('user1@demo.com', 'User_1', 'member')
    register('user2@demo.com', 'User_2', 'member')

    chief_token = login('chief@demo.com')
    m1_token = login('user1@demo.com')
    m2_token = login('user2@demo.com')

    m1_id = api('get', 'auth/me/', m1_token)['id']
    m2_id = api('get', 'auth/me/', m2_token)['id']

    exp = api('post', 'expeditions/', chief_token, json={
        'title': 'Arctic Demo Expedition',
        'description': 'Demo run',
        'start_at': '2026-05-01T00:00:00Z',
        'capacity': 5,
    })
    exp_id = exp['id']
    print(f'created expedition #{exp_id}, status={exp["status"]}')

    stop = threading.Event()
    start_listener(chief_token, exp_id, 'chief', stop)
    time.sleep(0.5)

    api('post', f'expeditions/{exp_id}/invite/', chief_token, json={'user_id': m1_id})
    api('post', f'expeditions/{exp_id}/invite/', chief_token, json={'user_id': m2_id})
    time.sleep(0.3)

    start_listener(m1_token, exp_id, 'member1', stop)
    time.sleep(0.5)

    api('post', f'expeditions/{exp_id}/confirm/', m1_token)
    api('post', f'expeditions/{exp_id}/confirm/', m2_token)
    time.sleep(0.3)

    r = api('post', f'expeditions/{exp_id}/set-ready/', chief_token)
    print(f'status → {r["status"]}')
    time.sleep(0.3)

    r = api('post', f'expeditions/{exp_id}/set-active/', chief_token)
    print(f'status → {r["status"]}')
    time.sleep(0.3)

    r = api('post', f'expeditions/{exp_id}/set-finished/', chief_token)
    print(f'status → {r["status"]}')
    time.sleep(0.5)

    stop.set()


if __name__ == '__main__':
    main()
