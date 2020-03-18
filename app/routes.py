import json
from threading import Thread
import time

from flask import request, url_for, jsonify, abort, Response, render_template
from flask_socketio import emit


import numpy as np
import paho.mqtt.subscribe as subscribe

from app import app, socketio


model = None
thread = None

classes = {
    0: "Outside",
    1: "Inside"
}


def predict(rssi):
    d1,d2,d3 = rssi
    all_device = np.array([[d1,d2,d3]])
    predicted = app.config.model.predict_classes(all_device)[0][0]

    return classes.get(predicted)


def extract(mqtt_msg):
    msg = mqtt_msg
    board_no = int(msg.topic.split('/')[-1])
    json_str = str(msg.payload.decode('ascii')).replace('\x00', '')
    data = json.loads(json_str)

    return board_no, data["data"]


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    CLIENT_ID = app.config.get('MQTT_CLIENT_ID')
    NETPIE_TOKEN = app.config.get('MQTT_TOKEN')
    board = [-99,-99,-99]
    while True:
        count += 1
        msg = subscribe.simple('@msg/taist2020/board/#', hostname='mqtt.netpie.io', port=1883, client_id=CLIENT_ID, auth={'username':NETPIE_TOKEN, 'password':None}, keepalive=600)
        board_no, rssi = extract(msg)
        board[board_no-1] = rssi

        predicted = predict(board)

        socketio.emit('my response',
                     {'data': predicted, 'board_1': board[0], 'board_2': board[1], 'board_3': board[2]},
                      namespace='/test')


@app.before_first_request
def load_model():
    print("Loading model")
    from keras.models import load_model
    app.config.model = load_model(app.config.get("MODEL_FILE"))


@app.route('/')
def index():
    global thread
    if thread is None:
        thread = Thread(target=background_thread)
        thread.daemon = True
        thread.start()
    return render_template('index.html')

@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my connected', {'data': 'Connected!!'})

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')
