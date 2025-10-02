import pygame
import random
import os
import json
import paho.mqtt.client as mqtt

pygame.init()

# MQTT Config
broker = "broker.emqx.io"
port = 1883
mqtt_topic_state = "flappybird2player/state"
mqtt_topic_input = "flappybird2player/input"

# Jogo Config
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird - HOST")

message_font = pygame.font.Font('SuperMario.ttf', 60) 
title_font = pygame.font.Font('SuperMario.ttf', 80)  
text_font = pygame.font.Font('SuperMario.ttf', 40)  
score_font = pygame.font.Font('SuperMario.ttf', 20)

WHITE = (255,255,255)
BLACK = (0,0,0)
RED = (255,0,0)
BLUE = (0,0,255)

BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT = 45, 30 
PIPE_WIDTH = 50 
PIPE_GAP = 200
GRAVITY = 0.5
JUMP_STRENGTH = -10
PIPE_SPEED = 3

try:
    bird_img_red = pygame.image.load(os.path.join('.', 'RedBird.png')).convert_alpha()
    bird_img_blue = pygame.image.load(os.path.join('.', 'Yellow_bird.png')).convert_alpha()
    bird_img_red = pygame.transform.scale(bird_img_red, (BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT))
    bird_img_blue = pygame.transform.scale(bird_img_blue, (BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT))
    pipe_img = pygame.image.load(os.path.join('.', 'Pipe.png')).convert_alpha()
    BIRD_WIDTH, BIRD_HEIGHT = BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT
except pygame.error:
    bird_img_red, bird_img_blue, pipe_img = None, None, None
    BIRD_WIDTH, BIRD_HEIGHT = 30, 30

class Bird:
    def __init__(self, x, y, image, color):
        self.x, self.initial_y = x, y
        self.y = y
        self.image = image
        self.color = color
        self.width = BIRD_WIDTH
        self.height = BIRD_HEIGHT
        self.reset()

    def reset(self):
        self.y = self.initial_y
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
        if self.is_alive and self.image:
            screen.blit(self.image, (self.x - self.width // 2, int(self.y) - self.height // 2))
        elif self.is_alive:
            pygame.draw.circle(screen, self.color, (self.x, int(self.y)), self.width // 2)

    def get_rect(self):
        return pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)

class Pipe:
    def __init__(self, x, y_top_end):
        self.x = x
        self.y_top_end = y_top_end
        self.passed = False
        self.width = PIPE_WIDTH
        if pipe_img:
            self.image_top = pygame.transform.scale(pipe_img, (PIPE_WIDTH, self.y_top_end))
            bottom_height = HEIGHT - (self.y_top_end + PIPE_GAP)
            bottom_pipe = pygame.transform.scale(pipe_img, (PIPE_WIDTH, bottom_height))
            self.image_bottom = pygame.transform.flip(bottom_pipe, False, True)
        else:
            self.image_top = None
            self.image_bottom = None

    def move(self):
        self.x -= PIPE_SPEED

    def draw(self, screen):
        if self.image_top and self.image_bottom:
            screen.blit(self.image_top, (self.x, self.y_top_end - self.image_top.get_height()))
            screen.blit(self.image_bottom, (self.x, self.y_top_end + PIPE_GAP))
        else:
            pygame.draw.rect(screen, BLACK, (self.x, 0, self.width, self.y_top_end))
            pygame.draw.rect(screen, BLACK, (self.x, self.y_top_end + PIPE_GAP, self.width, HEIGHT - (self.y_top_end + PIPE_GAP)))

def check_collision(bird, pipes):
    if not bird.is_alive:
        return False
    bird_rect = bird.get_rect()
    for pipe in pipes:
        pipe_rect_top = pygame.Rect(pipe.x, 0, pipe.width, pipe.y_top_end)
        pipe_rect_bottom = pygame.Rect(pipe.x, pipe.y_top_end + PIPE_GAP, pipe.width, HEIGHT - (pipe.y_top_end + PIPE_GAP))
        if bird_rect.colliderect(pipe_rect_top) or bird_rect.colliderect(pipe_rect_bottom):
            bird.is_alive = False
            return True
        if not pipe.passed and bird.x > pipe.x + PIPE_WIDTH:
            pipe.passed = True
            bird.score += 1
    return False

def reset_game():
    global pipes, spawn_pipe_timer, game_state
    player1.reset()
    player2.reset()
    pipes = []
    spawn_pipe_timer = 0
    game_state = 'playing'

# MQTT
def on_message(client, userdata, msg):
    global player2
    data = json.loads(msg.payload.decode())
    if data.get("action") == "jump":
        player2.jump()

client = mqtt.Client()
client.on_message = on_message
client.connect(broker, port)
client.subscribe(mqtt_topic_input)
client.loop_start()

# Inicializa players
player1 = Bird(100, HEIGHT//2, bird_img_red, RED)
player2 = Bird(100, HEIGHT//2, bird_img_blue, BLUE)
pipes = []
spawn_pipe_timer = 0
game_state = 'start_screen'
clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); exit()
        if game_state in ('start_screen','game_over') and event.type == pygame.KEYDOWN:
            reset_game()
        elif game_state == 'playing' and event.type == pygame.KEYDOWN and event.key == pygame.K_w:
            player1.jump()

    if game_state == 'playing':
        player1.move()
        player2.move()
        spawn_pipe_timer += 1
        if spawn_pipe_timer >= 120:
            pipe_height = random.randint(100, HEIGHT - PIPE_GAP - 100)
            pipes.append(Pipe(WIDTH, pipe_height))
            spawn_pipe_timer = 0
        for pipe in pipes: pipe.move()
        pipes = [p for p in pipes if p.x + PIPE_WIDTH > 0]
        check_collision(player1, pipes)
        check_collision(player2, pipes)
        if not player1.is_alive and not player2.is_alive:
            game_state = 'game_over'

        # Publica estado
        game_state_data = {
            "game_state": game_state,
            "player1": {"y": player1.y, "score": player1.score, "alive": player1.is_alive},
            "player2": {"y": player2.y, "score": player2.score, "alive": player2.is_alive},
            "pipes": [{"x": p.x, "y_top_end": p.y_top_end} for p in pipes]
        }
        client.publish(mqtt_topic_state, json.dumps(game_state_data))

    # ---------- Render ----------
    screen.fill((135,206,235))
    if game_state == 'start_screen':
        text = title_font.render("Flappy Bird 2P - HOST", True, BLACK)
        screen.blit(text, text.get_rect(center=(WIDTH//2, HEIGHT//2)))
    elif game_state == 'playing':
        for pipe in pipes: pipe.draw(screen)
        player1.draw(screen); player2.draw(screen)
        screen.blit(score_font.render(f"P1: {player1.score}", True, RED), (10,10))
        screen.blit(score_font.render(f"P2: {player2.score}", True, BLUE), (10,40))
    else:
        winner = "Empate!"
        if player1.score > player2.score: winner = "P1 venceu!"
        elif player2.score > player1.score: winner = "P2 venceu!"
        screen.blit(text_font.render(winner, True, BLACK), (WIDTH//2-100, HEIGHT//2))
    pygame.display.flip()
    clock.tick(60)
