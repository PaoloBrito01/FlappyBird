import pygame
import random
import os
import json
import paho.mqtt.client as mqtt

pygame.init()

# --- Configurações MQTT ---
broker = "broker.emqx.io"
port = 1883
mqtt_topic = "flappybird2player/game"
client_id = f'player-{random.randint(0, 100000)}'

# --- Escolha do jogador local ---
# Ao iniciar, escolha se este processo será o player 1 (vermelho) ou player 2 (azul).
# Digite '1' para P1 (vermelho) ou '2' para P2 (azul).
choice = input("Escolha seu player (1 = vermelho, 2 = azul): ").strip()
is_player1 = True if choice == '1' else False

# estado remoto armazenado (por cor)
remote_states = {
    'red': None,
    'blue': None
}

# estado global do jogo
game_state = 'start_screen'

# Callback MQTT

def on_connect(client, userdata, flags, reasonCode, properties=None):
    if reasonCode == 0:
        print("MQTT conectado!")
        client.subscribe(mqtt_topic)
    else:
        print(f"Falha de conexão MQTT: {reasonCode}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        # debug
        print("Recebido MQTT:", data)

        # ignora minhas próprias mensagens
        if data.get("player_id") == client_id:
            return

        color = data.get("color")
        if color in ('red', 'blue'):
            # grava o estado remoto para ser usado no loop principal (interpolação segura)
            remote_states[color] = data

        # sincroniza estado do jogo (se alguém mandar game_over)
        if data.get("game_state") == 'game_over':
            global game_state
            game_state = 'game_over'

    except Exception as e:
        print("Erro processando mensagem MQTT:", e)


# --- Configurações do jogo ---
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
message_font = pygame.font.Font('SuperMario.ttf', 60) 
text_font = pygame.font.Font('SuperMario.ttf', 40)  
score_font = pygame.font.Font('SuperMario.ttf', 20)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT = 45, 30 
PIPE_WIDTH = 50 

try:
    bird_img_red = pygame.image.load(os.path.join('.', 'RedBird.png')).convert_alpha()
    bird_img_blue = pygame.image.load(os.path.join('.', 'Yellow_bird.png')).convert_alpha() 
    bird_img_red = pygame.transform.scale(bird_img_red, (BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT))
    bird_img_blue = pygame.transform.scale(bird_img_blue, (BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT))
    pipe_img = pygame.image.load(os.path.join('.', 'Pipe.png')).convert_alpha()
    BIRD_WIDTH, BIRD_HEIGHT = BIRD_DEFAULT_WIDTH, BIRD_DEFAULT_HEIGHT
except pygame.error as e:
    print(f"ATENÇÃO: Erro ao carregar imagens! Usando formas simples. Erro: {e}")
    bird_img_red, bird_img_blue, pipe_img = None, None, None
    BIRD_WIDTH, BIRD_HEIGHT = 30, 30

PIPE_GAP = 200
GRAVITY = 0.5
JUMP_STRENGTH = -10
PIPE_SPEED = 3

last_mqtt_send = 0  # controla a taxa de envio
INTERPOLATION_SPEED = 0.2  # velocidade de interpolação do player remoto

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
        margin_x = int(self.width * 0.45)
        margin_y = int(self.height * 0.10)
        return pygame.Rect(
            self.x - self.width // 2 + margin_x,
            self.y - self.height // 2 + margin_y,
            self.width - 2 * margin_x,
            self.height - 2 * margin_y
        )

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
    COLLISION_MARGIN = 5

    for pipe in pipes:
        pipe_rect_top = pygame.Rect(pipe.x + COLLISION_MARGIN, 0, pipe.width - 2 * COLLISION_MARGIN, pipe.y_top_end)
        pipe_rect_bottom = pygame.Rect(pipe.x + COLLISION_MARGIN, pipe.y_top_end + PIPE_GAP, pipe.width - 2 * COLLISION_MARGIN, HEIGHT - (pipe.y_top_end + PIPE_GAP))
        if bird_rect.colliderect(pipe_rect_top) or bird_rect.colliderect(pipe_rect_bottom):
            bird.is_alive = False
            return True
        if not pipe.passed and bird.x > pipe.x + PIPE_WIDTH:
            pipe.passed = True
            bird.score += 1
    return False


def reset_game():
    global pipes1, pipes2, spawn_pipe_timer, game_state
    player1.reset()
    player2.reset()
    pipes1 = []
    pipes2 = []
    spawn_pipe_timer = 0
    game_state = 'playing'


def check_out_of_bounds(player1, player2):
    global game_state
    for bird in (player1, player2):
        if bird.y - bird.height // 2 < 0 or bird.y + bird.height // 2 > HEIGHT:
            bird.is_alive = False
    if not player1.is_alive and not player2.is_alive:
        game_state = 'game_over'

# Inicializa jogadores e pipes
player1 = Bird(100, HEIGHT // 2, bird_img_red, RED)
player2 = Bird(100, HEIGHT // 2, bird_img_blue, BLUE)

pipes1 = []
pipes2 = []
spawn_pipe_timer = 0

game_state = 'start_screen'

# Define quem é local e referência convenience
player_local = player1 if is_player1 else player2
player_remote = player2 if is_player1 else player1
local_color = 'red' if is_player1 else 'blue'
remote_color = 'blue' if is_player1 else 'red'

# Teclas
jump_keys = {pygame.K_w: player1, pygame.K_UP: player2}
clock = pygame.time.Clock()

# MQTT Client
client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker, port)
client.loop_start()

print(f"Cliente MQTT id={client_id} | Você é {'P1 (vermelho)' if is_player1 else 'P2 (azul)'}")

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            client.loop_stop()
            client.disconnect()
            exit()
        if game_state in ('start_screen', 'game_over') and event.type == pygame.KEYDOWN:
            reset_game()
        elif game_state == 'playing' and event.type == pygame.KEYDOWN and event.key in jump_keys:
            # permite controlar seu pássaro usando a tecla correta (W para vermelho, UP para azul)
            jump_keys[event.key].jump()

    if game_state == 'playing':
        # movimento local
        player_local.move()
        check_out_of_bounds(player1, player2)

        # geração e movimento de pipes (mantido igual para os dois jogos)
        spawn_pipe_timer += 1
        if spawn_pipe_timer >= 120:
            pipe_height = random.randint(100, HEIGHT - PIPE_GAP - 100)
            pipes1.append(Pipe(WIDTH, pipe_height))
            pipes2.append(Pipe(WIDTH, pipe_height))
            spawn_pipe_timer = 0

        for pipe in pipes1:
            pipe.move()
        for pipe in pipes2:
            pipe.move()

        pipes1 = [pipe for pipe in pipes1 if pipe.x + PIPE_WIDTH > 0]
        pipes2 = [pipe for pipe in pipes2 if pipe.x + PIPE_WIDTH > 0]

        check_collision(player1, pipes1)
        check_collision(player2, pipes2)

        if not player1.is_alive and not player2.is_alive:
            game_state = 'game_over'

        # -------- MQTT: envio do estado local --------
        current_time = pygame.time.get_ticks()
        if current_time - last_mqtt_send > 50:
            my_state = {
                "player_id": client_id,
                "color": local_color,
                "y": player_local.y,
                "score": player_local.score,
                "alive": player_local.is_alive,
                "game_state": game_state
            }
            client.publish(mqtt_topic, json.dumps(my_state))
            last_mqtt_send = current_time

        # -------- Aplicar estado remoto (interpolação) --------
        remote = remote_states.get(remote_color)
        if remote is not None:
            target_y = remote.get('y', player_remote.y)
            # interpolação suave
            player_remote.y += (target_y - player_remote.y) * INTERPOLATION_SPEED
            player_remote.score = remote.get('score', player_remote.score)
            player_remote.is_alive = remote.get('alive', player_remote.is_alive)
            if remote.get('game_state') == 'game_over':
                game_state = 'game_over'

    # ---------- Renderização ----------
    screen.fill((135, 206, 235))  # SKY_BLUE

    if game_state == 'start_screen':
        start_y = HEIGHT // 2 - 140
        line_spacing = 60
        title_text = message_font.render("Flappy Bird 2-Player!", True, BLACK)
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, start_y)))

        screen.blit(text_font.render("P1 (Vermelho): W", True, RED), text_font.render("P1 (Vermelho): W", True, RED).get_rect(center=(WIDTH // 2, start_y + line_spacing)))
        screen.blit(text_font.render("P2 (Azul): Seta para Cima", True, BLUE), text_font.render("P2 (Azul): Seta para Cima", True, BLUE).get_rect(center=(WIDTH // 2, start_y + 2 * line_spacing)))
        screen.blit(text_font.render("Pressione qualquer tecla para começar", True, BLACK), text_font.render("Pressione qualquer tecla para começar", True, BLACK).get_rect(center=(WIDTH // 2, start_y + 3 * line_spacing)))

    elif game_state == 'playing':
        for pipe in pipes1: pipe.draw(screen)
        for pipe in pipes2: pipe.draw(screen)
        player1.draw(screen)
        player2.draw(screen)
        screen.blit(score_font.render(f"P1: {player1.score}", True, RED), (10, 10))
        screen.blit(score_font.render(f"P2: {player2.score}", True, BLUE), (10, 40))
        if not player1.is_alive:
            screen.blit(text_font.render("P1 Fora!", True, RED), (WIDTH // 2 - 50, HEIGHT // 4))
        if not player2.is_alive:
            screen.blit(text_font.render("P2 Fora!", True, BLUE), (WIDTH // 2 - 50, HEIGHT // 4))

    else:  # game_over
        winner_text = "Empate!"
        if player1.score > player2.score: winner_text = "O Jogador 1 VENCEU!"
        elif player2.score > player1.score: winner_text = "O Jogador 2 VENCEU!"
        screen.blit(text_font.render(f"P1 Pontos: {player1.score}", True, RED), text_font.render(f"P1 Pontos: {player1.score}", True, RED).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100)))
        screen.blit(text_font.render(f"P2 Pontos: {player2.score}", True, BLUE), text_font.render(f"P2 Pontos: {player2.score}", True, BLUE).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50)))
        screen.blit(message_font.render(winner_text, True, BLACK), message_font.render(winner_text, True, BLACK).get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)))
        screen.blit(text_font.render("Pressione qualquer tecla para jogar de novo", True, BLACK), text_font.render("Pressione qualquer tecla para jogar de novo", True, BLACK).get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120)))

    pygame.display.flip()
    clock.tick(60)
