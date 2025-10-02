import pygame
import json
import base64
import cv2
import numpy as np
import paho.mqtt.client as mqtt

pygame.init()
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird Client")

broker = "broker.emqx.io"
topic_state = "flappy/state"
topic_cmd   = "flappy/commands"

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    frame_b64 = data["frame"]
    img_data = base64.b64decode(frame_b64)
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)
    surf = pygame.surfarray.make_surface(frame)
    screen.blit(surf, (0, 0))
    pygame.display.flip()

def send_command(action):
    cmd = {"player_id":"player2","action":action}
    client.publish(topic_cmd, json.dumps(cmd))

client = mqtt.Client()
client.on_message = on_message
client.connect(broker, 1883)
client.subscribe(topic_state)
client.loop_start()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: send_command("jump")
            if event.key == pygame.K_r: send_command("reset")

pygame.quit()
client.loop_stop()
client.disconnect()
