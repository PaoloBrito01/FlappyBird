import pygame
import random
import os
import json
import paho.mqtt.client as mqtt
import base64
import cv2
import numpy as np

pygame.init()

# MQTT Config
broker = "broker.emqx.io"
topic_state = "flappy/state"
topic_cmd   = "flappy/commands"

client = mqtt.Client()
client.connect(broker, 1883)
client.loop_start()

# Game Config
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird Host")

WHITE, BLACK, RED, BLUE = (255,255,255), (0,0,0), (255,0,0), (0,0,255)

BIRD_WIDTH, BIRD_HEIGHT = 45, 30
PIPE_WIDTH, PIPE_GAP = 70, 200
GRAVITY, JUMP_STRENGTH, PIPE_SPEED = 0.5, -10, 3

clock = pygame.time.Clock()
game_state = "start_screen"

# Load images
try:
    bird_img_red = pygame.image.load("RedBird.png").convert_alpha()
    bird_img_red = pygame.transform.scale(bird_img_red, (BIRD_WIDTH, BIRD_HEIGHT))
    bird_img_blue = pygame.image.load("Yellow_bird.png").convert_alpha()
    bird_img_blue = pygame.transform.scale(bird_img_blue, (BIRD_WIDTH, BIRD_HEIGHT))
    pipe_img = pygame.image.load("Pipe.png").convert_alpha()
except:
    bird_img_red = bird_img_blue = pipe_img = None

# Classes
class Bird:
    def __init__(self, x, y, image, color):
        self.x, self.y = x, y
        self.image, self.color = image, color
        self.width, self.height = BIRD_WIDTH, BIRD_HEIGHT
        self.reset()

    def reset(self):
        self.y = HEIGHT//2
        self.velocity = 0
        self.score = 0
        self.is_alive = True

    def jump(self):
        if self.is_alive:
            self.velocity = JUMP_STRENGTH

    def move(self):
        if self.is_alive:
            self.velocity += GRAVITY
            self.y += self.velocity

    def draw(self, screen):
        if self.image and self.is_alive:
            screen.blit(self.image, (self.x - self.width//2, int(self.y) - self.height//2))
        elif self.is_alive:
            pygame.draw.circle(screen, self.color, (self.x, int(self.y)), self.width//2)

    def get_rect(self):
        return pygame.Rect(self.x-self.width//2, self.y-self.height//2, self.width, self.height)

class Pipe:
    def __init__(self, x, y_top_end):
        self.x, self.y_top_end = x, y_top_end
        self.passed = False

    def move(self): self.x -= PIPE_SPEED

    def draw(self, screen):
        if pipe_img:
            top = pygame.transform.scale(pipe_img, (PIPE_WIDTH, self.y_top_end))
            bottom = pygame.transform.scale(pipe_img, (PIPE_WIDTH, HEIGHT - (self.y_top_end + PIPE_GAP)))
            bottom = pygame.transform.flip(bottom, False, True)
            screen.blit(top, (self.x, self.y_top_end - top.get_height()))
            screen.blit(bottom, (self.x, self.y_top_end + PIPE_GAP))
        else:
            pygame.draw.rect(screen, BLACK, (self.x, 0, PIPE_WIDTH, self.y_top_end))
            pygame.draw.rect(screen, BLACK, (self.x, self.y_top_end+PIPE_GAP, PIPE_WIDTH, HEIGHT))

# Game Objects
player1 = Bird(200, HEIGHT//2, bird_img_red, RED)
player2 = Bird(200, HEIGHT//2, bird_img_blue, BLUE)
pipes, spawn_timer = [], 0

# Commands from client
def on_message(client, userdata, msg):
    global game_state
    data = json.loads(msg.payload.decode())
    if data.get("player_id") == "player2":
        if data["action"] == "jump": player2.jump()
        if data["action"] == "reset": reset_game()
client.on_message = on_message
client.subscribe(topic_cmd)

def reset_game():
    global pipes, spawn_timer, game_state
    player1.reset()
    player2.reset()
    pipes, spawn_timer = [], 0
    game_state = "playing"

def check_collision(bird):
    if not bird.is_alive: return
    rect = bird.get_rect()
    for pipe in pipes:
        top_rect = pygame.Rect(pipe.x, 0, PIPE_WIDTH, pipe.y_top_end)
        bottom_rect = pygame.Rect(pipe.x, pipe.y_top_end+PIPE_GAP, PIPE_WIDTH, HEIGHT-(pipe.y_top_end+PIPE_GAP))
        if rect.colliderect(top_rect) or rect.colliderect(bottom_rect):
            bird.is_alive = False
        if not pipe.passed and bird.x > pipe.x+PIPE_WIDTH:
            pipe.passed = True
            bird.score += 1

def publish_frame():
    surface = pygame.display.get_surface()
    frame = pygame.surfarray.array3d(surface)
    frame = np.rot90(frame)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    frame_b64 = base64.b64encode(buffer).decode("utf-8")

    state = {
        "frame": frame_b64,
        "p1_score": player1.score,
        "p2_score": player2.score,
        "game_state": game_state
    }
    client.publish(topic_state, json.dumps(state))

# Main Loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if game_state in ("start_screen","game_over") and event.type == pygame.KEYDOWN:
            reset_game()
        elif game_state=="playing" and event.type==pygame.KEYDOWN and event.key==pygame.K_w:
            player1.jump()

    if game_state == "playing":
        player1.move(); player2.move()
        spawn_timer += 1
        if spawn_timer >= 90:
            pipes.append(Pipe(WIDTH, random.randint(100, HEIGHT-PIPE_GAP-100)))
            spawn_timer = 0
        for pipe in pipes: pipe.move()
        pipes = [p for p in pipes if p.x+PIPE_WIDTH>0]
        check_collision(player1); check_collision(player2)
        if not player1.is_alive and not player2.is_alive: game_state = "game_over"

    # Draw
    screen.fill((135,206,235))
    for pipe in pipes: pipe.draw(screen)
    player1.draw(screen); player2.draw(screen)
    pygame.display.flip()

    # Publish frame to client
    publish_frame()
    clock.tick(30)  # limit FPS

pygame.quit()
client.loop_stop()
client.disconnect()
