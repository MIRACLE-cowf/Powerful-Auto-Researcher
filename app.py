import asyncio
import os
import threading
import time
import uuid
import logging
from typing import Any

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for
import spotipy
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from spotipy.oauth2 import SpotifyClientCredentials
import math

from PAR.main import build_PAR_graph
from jpop_translate import run_translate
from search import run_tavily_search, run_brave_search

load_dotenv()
app = Flask(__name__)
socketio = SocketIO(app, server_options={'cors_allowed_origin': '*'})





# Spotify API 자격 증명 설정
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

# Spotify 클라이언트 설정
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# MongoDB 연결
library_collection = MongoClient(host=os.getenv('MONGODB_URI')).get_database('song').get_collection('JPOP')

ITEMS_PER_PAGE = 20  # 페이지당 항목 수

par_tasks = {}


def run_async_task(task_id):
    print(f'Running task {task_id}')
    asyncio.run(run_par_task(task_id))

PAR_STAGES = {
    'transform_new_query': 5,
    'multi_query_generator': 10,
    'retrieve_vector_db': 10,
    'grade_each_documents': 15,
    'THLO': 20,
    'Composable_Search': 25,
    'Generate_Conclusion': 10,
    'Generate': 5
}
TOTAL_PROGRESS = sum(PAR_STAGES.values())


@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join')
def on_join(data):
    task_id = data['task_id']
    join_room(task_id)
    print(f'Client joined room: {task_id}')
    emit('joined', {'task_id': task_id}, )

@socketio.on('leave')
def on_leave(data):
    task_id = data['task_id']
    leave_room(task_id)
    print(f'Client left room: {task_id}')


@socketio.on('start_par')
def handle_start_par(data):
    query = data['query']
    task_id = str(uuid.uuid4())
    par_tasks[task_id] = {
        'status': 'running',
        'progress': 0,
        'query': query,
        'completed_stages': [],
        'current_stage': ''
    }

    join_room(task_id)
    emit('par_started', {'task_id': task_id}, )
    socketio.start_background_task(run_async_task, task_id)


@socketio.on('resume_par')
def handle_resume_par(data):
    task_id = data['task_id']
    print(f'Resuming task {task_id}')
    if task_id in par_tasks:
        print('par_Status_update')
        emit('par_status_update', par_tasks[task_id])
    else:
        print('par_error')
        emit('par_error', {'error': 'PAR task not found'})


@socketio.on('get_par_status')
def handle_get_par_status(data):
    task_id = data['task_id']
    if task_id in par_tasks:
        print('par_status_update')
        emit('par_status_update', par_tasks[task_id])
    else:
        print('par_error')
        emit('par_error', {'error': 'PAR task not found'})


@socketio.on('cancel_par')
def handle_cancel_par(data):
    task_id = data['task_id']
    if task_id in par_tasks:
        # 여기에 PAR 작업을 취소하는 로직 추가
        del par_tasks[task_id]
        emit('par_cancelled', {'task_id': task_id})
    else:
        emit('par_error', {'error': 'PAR task not found'})


async def update_task_status(task_id, node_name: str):
    if task_id in par_tasks:
        if 'completed_stages' not in par_tasks[task_id]:
            par_tasks[task_id]['completed_stages'] = []
        if node_name not in par_tasks[task_id]['completed_stages']:
            par_tasks[task_id]['completed_stages'].append(node_name)

        completed_stages = par_tasks[task_id]['completed_stages']
        progress = sum(PAR_STAGES[s] for s in completed_stages)
        par_tasks[task_id]['progress'] = int((progress / TOTAL_PROGRESS) * 100)
        par_tasks[task_id]['current_stage'] = node_name

    print(f"par_status_update: {par_tasks[task_id]}")
    socketio.emit('par_status_update', par_tasks[task_id])


async def run_par_task(task_id):
    print(f'Task {task_id} started')
    try:
        par_graph = build_PAR_graph()
        query = par_tasks[task_id]['query']

        async def callback(node_name: str, _result: Any = None):
            print(f'callback called node_name: {node_name}')
            if node_name == "user_input":
                par_tasks[task_id]['awaiting_input'] = True
                par_tasks[task_id]['input_data'] = _result
                socketio.emit('par_input_required', {'task_id': task_id, 'input_data': _result})

                while par_tasks[task_id].get('user_response') is None:
                    await asyncio.sleep(1)
                user_response = par_tasks[task_id]['user_response']
                del par_tasks[task_id]['user_response']
                del par_tasks[task_id]['awaiting_input']
                return user_response
            else:
                print(f'callback called node_name is not user_input')
                try:
                    await update_task_status(task_id, node_name)
                except Exception as e:
                    print(f"Error updateing task status: {e}")


        inputs = {
            "user_question": query,
            "callback": callback
        }

        result = await par_graph.ainvoke(inputs, config={})

        par_tasks[task_id]['result'] = result
        par_tasks[task_id]['status'] = 'completed'
        par_tasks[task_id]['progress'] = 100
        socketio.emit('par_completed', {'task_id': task_id, 'result': result})
    except Exception as e:
        par_tasks[task_id]['status'] = 'error'
        par_tasks[task_id]['error'] = str(e)
        socketio.emit('par_error', {'task_id': task_id, 'error': str(e)})


# @app.route('/start_par', methods=['POST'])
# def start_par():
#     query = request.json.get('query', '')
#     print(f"Starting PAR with query: {query}")
#     task_id = str(uuid.uuid4())  # 고유한 작업 ID 생성
#     par_tasks[task_id] = {
#         'status': 'running',
#         'progress': 0,
#         'query': query,
#         'completed_stages': [],
#         'current_stage': ''
#     }
#
#     # 백그라운드에서 PAR 작업 시작
#     # threading.Thread(target=run_par_task, args=(task_id,)).start()
#     threading.Thread(target=run_async_task, args=(task_id, )).start()
#
#     return jsonify({'task_id': task_id})


@socketio.on('par_input')
def handle_par_input(data):
    task_id = data['task_id']
    user_response = data['response']
    if task_id in par_tasks and par_tasks[task_id].get('awaiting_input'):
        par_tasks[task_id]['user_response'] = user_response
        emit('par_input_received', {'task_id': task_id})


@app.route('/par_status/<task_id>')
def par_status(task_id):
    if task_id in par_tasks:
        return jsonify({
            'status': par_tasks[task_id].get('status', 'running'),
            'progress': par_tasks[task_id].get('progress', 0),
            'current_stage': par_tasks[task_id].get('current_stage', ''),
            'completed_stages': par_tasks[task_id].get('completed_stages', []),
            'error': par_tasks[task_id].get('error', ''),
            'awaiting_input': par_tasks[task_id].get('awaiting_input', False),
            'input_data'    : par_tasks[task_id].get('input_data', {})
        })
    return jsonify({'status': 'not found'}), 404


@app.route('/par_input/<task_id>', methods=["POST"])
def par_input(task_id):
    if task_id in par_tasks and par_tasks[task_id].get('awaiting_input'):
        user_response = request.json.get('response')
        par_tasks[task_id]['user_response'] = user_response
        return jsonify({'status': 'input received'})
    return jsonify({'status': 'input not expected'}), 400


def search_tracks(query, search_type='track', offset=0, limit=ITEMS_PER_PAGE):
    if search_type == 'artist':
        results = sp.search(q=query, type='artist', limit=1)
        if results['artists']['items']:
            artist_id = results['artists']['items'][0]['id']
            results = sp.artist_top_tracks(artist_id)
            tracks = results['tracks']
        else:
            return [], 0
    else:
        results = sp.search(q=query, type='track', limit=limit, offset=offset)
        tracks = results['tracks']['items']

    total = len(tracks) if search_type == 'artist' else results['tracks']['total']

    data = []
    for track in tracks:
        artist = track['artists'][0]['name']
        title = track['name']
        album = track['album']['name']
        image_url = track['album']['images'][0]['url'] if track['album']['images'] else 'No Image'

        data.append({
            'id'       : track['id'],
            'artist'   : artist,
            'title'    : title,
            'album'    : album,
            'image_url': image_url,
        })

    return data, total


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    search_type = request.form['search_type']
    return redirect(url_for('search_results', query=query, search_type=search_type, page=1))


@app.route('/search_results')
def search_results():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'track')
    page = int(request.args.get('page', 1))
    offset = (page - 1) * ITEMS_PER_PAGE

    results, total = search_tracks(query, search_type, offset)
    total_pages = math.ceil(total / ITEMS_PER_PAGE)

    return render_template('results.html',
                           results=results,
                           query=query,
                           page=page,
                           total_pages=total_pages,
                           max=max,
                           min=min)


@app.route('/track/<track_id>')
def get_track_info(track_id):
    track = sp.track(track_id)
    lyrics = "가사를 가져오는 데 실패했습니다."

    print(f"track id: {track_id}")

    print(f"title: {track['name']}")
    print(f"artist: {track['artists'][0]['name']}")

    return jsonify({
        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else '',
        'title'    : track['name'],
        'artist'   : track['artists'][0]['name'],
        'lyrics'   : lyrics
    })


@app.route('/my_library')
def my_library():
    return render_template('my_library.html')


@app.route('/api/library')
def get_library():
    library_tracks = list(library_collection.find({}, {'_id': 0}))
    return jsonify(library_tracks)


@app.route('/api/library/add', methods=['POST'])
def add_to_library():
    track_id = request.form['track_id']
    track = sp.track(track_id)

    library_track = {
        'id'       : track_id,
        'title'    : track['name'],
        'artist'   : track['artists'][0]['name'],
        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else '',
        'lyrics'   : ''
    }

    print(f"Library_Track: ${library_track}")

    library_collection.update_one({'id': track_id}, {'$set': library_track}, upsert=True)
    return jsonify({'success': True})


@app.route('/api/library/update_lyrics', methods=['POST'])
def update_lyrics():
    track_id = request.form['track_id']
    lyrics = request.form['lyrics']

    result = library_collection.update_one(
        {'id': track_id},
        {
            '$set'  : {'lyrics': lyrics},
            '$unset': {'translated_lyrics': ''}  # 원본 가사가 변경되면 번역된 가사 초기화
        }
    )

    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})


@app.route('/api/library/translate', methods=['POST'])
def translate_lyrics():
    track_id = request.form['track_id']
    track = library_collection.find_one({'id': track_id})
    print(track)

    if not track or not track.get('lyrics'):
        return jsonify({'success': False, 'error': 'Lyrics not found'})

    try:
        # TODO(몽고 DB 업데이트 및 텍스트 임베딩 해 벡터 DB 저장까지)
        translated_lyrics = run_translate(track)
        library_collection.update_one({'id': track_id}, {'$set': {'translated_lyrics': translated_lyrics}})

        return jsonify({'success': True, 'translated_lyrics': translated_lyrics})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'success': False, 'error': 'Translation failed'})


@app.route('/api/library/<track_id>')
def get_track_from_library(track_id):
    track = library_collection.find_one({'id': track_id}, {'_id': 0})
    if track:
        return jsonify(track)
    else:
        return jsonify({'error': 'Track not found'}), 404


@app.route('/api/library/update_translated_lyrics', methods=['POST'])
def update_translated_lyrics():
    track_id = request.form['track_id']
    lyrics = request.form['lyrics']

    result = library_collection.update_one({'id': track_id}, {'$set': {'translated_lyrics': lyrics}})

    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})


@app.route('/api/library/regenerate_translation', methods=['POST'])
def regenerate_translation():
    track_id = request.form['track_id']
    track = library_collection.find_one({'id': track_id})

    if not track or not track.get('lyrics'):
        return jsonify({'success': False, 'error': 'Original lyrics not found'})


    try:
        translated_lyrics = run_translate(track)
        library_collection.update_one({'id': track_id}, {'$set': {'translated_lyrics': translated_lyrics}})

        return jsonify({'success': True, 'translated_lyrics': translated_lyrics})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'success': False, 'error': 'Translation failed'})


@app.route('/web_search')
def web_search():
    query = request.args.get('q', '')
    return render_template('web_search_results.html', query=query)


# New route for Google search API
@app.route('/api/search/google')
def google_search():
    query = request.args.get('q', '')
    # Implement Google search logic here
    # This is a placeholder implementation
    results = [
        {"title": "Google Result 1", "url": "http://example.com/1", "description": "This is the first Google result."},
        {"title": "Google Result 2", "url": "http://example.com/2", "description": "This is the second Google result."},
        {"title": "Google Result 3", "url": "http://example.com/3", "description": "This is the third Google result."}
    ]
    return jsonify(results)

# New route for Tavily search API
@app.route('/api/search/tavily')
def tavily_search():
    query = request.args.get('q', '')
    results = run_tavily_search(query=query)
    return jsonify(results)


# New route for Brave search API
@app.route('/api/search/brave')
def brave_search():
    query = request.args.get('q', '')
    results = run_brave_search(query=query)
    return jsonify(results)


# New route for LLM chat
@app.route('/api/chat', methods=['POST'])
def llm_chat():
    message = request.json.get('message', '')
    # Implement LLM chat logic here
    # This is a placeholder implementation
    response = f"This is a dummy response from the LLM for the message: {message}"
    return jsonify({"response": response})


@app.route('/par_search')
def par_search():
    query = request.args.get('q', '')
    task_id = request.args.get('task_id', '')
    return render_template('par_search_results.html', query=query, task_id=task_id)


if __name__ == '__main__':
    app.run(debug=True)

