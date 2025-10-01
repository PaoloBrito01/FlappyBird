# Prova P1- Jogo distribuído simples:

Este projeto tem como objetivo desenvolver um esqueleto de jogo distribuído, onde a comunicação entre os jogadores é feita através de um serviço de filas. A proposta é criar um ambiente simples onde dois jogadores podem jogar Flappy Bird simultaneamente, com os movimentos sendo sincronizados em tempo real via MQTT. Além disso, é possível configurar um broker local com o Mosquitto ou utilizar um broker público para testes.

## Comunicação MQTT

O jogo utiliza tópicos MQTT para transmitir os movimentos e estados dos jogadores.

Cada jogador publica e assina mensagens em um mesmo canal (flappybird2player/game), garantindo uma visão compartilhada do jogo.

As mensagens trafegam em formato JSON, contendo informações como posição do pássaro, pontuação, estado de vida e estado do jogo.

### Instalando dependências:

Execute os seguintes comandos para instalação das bibliotecas nescessárias

```
pip install pygame paho-mqtt
```

```
pip install pygame
```

## Executando o programa:

Execute o seguinte comando para iniciar o jogo

```
python .\Flappy.py
```

## Construído com:

Mencione as ferramentas que você usou para criar seu projeto

* [Mosquitto](https://mosquitto.org/download/) - O framework web usado
* [Pygame](https://www.pygame.org/docs/) - Módulo de videogame
* [MQTT](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html) - Protocolo de mensagens

## Autores:

* **Desenvolvedor** - *João Schweitzer* - https://github.com/J-Schweitzer
* **Desenvolvedor** - *Pierina Kessler   * - https://github.com/PaoloBrito01
* **Desenvolvedor** - *Paolo Brito    * - https://github.com/PaoloBrito01



