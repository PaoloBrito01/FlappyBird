import pygame
import json
import paho.mqtt.client as mqtt

pygame.init()

# MQTT
broker = "broker.emqx.io"
port = 1883
mqtt_topic_state = "flappybird2player/state"
mqtt_topic_input = "flappybird2player/input"

WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird - CLIENT")

text_font = pygame.font.Font('SuperMario.ttf', 40)  
score_font = pygame.font.Font('SuperMario.ttf', 20)

RED = (255,0,0)
BLUE = (0,0,255)
BLACK = (0,0,0)

game_state = "waiting"
player1 = {"y": HEIGHT//2, "score": 0, "alive": True}
player2 = {"y": HEIGHT//2, "score": 0, "alive": True}
pipes = []

# MQTT Callbacks
def on_message(client, userdata, msg):
    global game_state, player1, player2, pipes
    data = json.loads(msg.payload.decode())
    game_state = data["game_state"]
    player1 = data["player1"]
    player2 = data["player2"]
    pipes = data["pipes"]

client = mqtt.Client()
client.on_message = on_message
client.connect(broker, port)
client.subscribe(mqtt_topic_state)
client.loop_start()

clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); exit()
        if game_state == "playing" and event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            client.publish(mqtt_topic_input, json.dumps({"action":"jump"}))

    # ---------- Render ----------
    screen.fill((135,206,235))
    if game_state == "waiting":
        text = text_font.render("Aguardando HOST iniciar...", True, BLACK)
        screen.blit(text, text.get_rect(center=(WIDTH//2, HEIGHT//2)))
    elif game_state == "playing":
        for p in pipes:
            pygame.draw.rect(screen, BLACK, (p["x"], 0, 50, p["y_top_end"]))
            pygame.draw.rect(screen, BLACK, (p["x"], p["y_top_end"]+200, 50, HEIGHT-(p["y_top_end"]+200)))
        if player1["alive"]:
            pygame.draw.circle(screen, RED, (100, int(player1["y"])), 15)
        if player2["alive"]:
            pygame.draw.circle(screen, BLUE, (200, int(player2["y"])), 15)
        screen.blit(score_font.render(f"P1: {player1['score']}", True, RED), (10,10))
        screen.blit(score_font.render(f"P2: {player2['score']}", True, BLUE), (10,40))
    else:
        text = text_font.render("Fim de jogo!", True, BLACK)
        screen.blit(text, text.get_rect(center=(WIDTH//2, HEIGHT//2)))
    pygame.display.flip()
    clock.tick(60)
