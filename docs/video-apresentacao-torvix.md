# Video de apresentacao do Torvix Tracker

Arquivo base:

```text
C:\Users\neyva\Desktop\Cap Cut Vídeos Salvos\0501 (1).mp4
```

Saida gerada:

```text
dist\TorvixTracker_Apresentacao_16x9.mp4
```

## Conceito

Video curto em 16:9 para apresentar o Torvix Tracker usando o proprio material gravado:

- gameplay em ETS2/ATS para mostrar imersao;
- janela do app para mostrar camera, telemetria, ajustes e saidas;
- dissolves curtos entre cortes para manter continuidade;
- musica instrumental de fundo gerada localmente;
- textos grandes, diretos e prontos para redes sociais ou para incorporar no site.

## Timeline

| Tempo final | Trecho do video original | Texto principal | Texto secundario |
| --- | --- | --- | --- |
| 00:00-00:07.7 | 00:18-00:26 | Torvix Tracker | Rastreamento por webcam para ETS2 e ATS |
| 00:07.7-00:15.3 | 01:10-01:18 | Sua camera vira controle | Cabeca e olhar capturados em tempo real |
| 00:15.3-00:23.9 | 01:50-01:59 | Ajuste fino de movimento | Deadzone, suavizacao, resposta e curvas |
| 00:23.9-00:32.4 | 02:21-02:30 | Olhe para espelhos e curvas | Mais imersao sem hardware caro |
| 00:32.4-00:41.0 | 03:10-03:19 | Perfis e calibracao | Centralize, ajuste e salve seu jeito de jogar |
| 00:41.0-00:49.4 | 04:30-04:39 | Saida para simuladores | FreeTrack, TrackIR compativel e Mouse Look |
| 00:49.4-00:59.0 | 05:20-05:30 | Pronto para rodar | Pagamento unico de R$ 19,99 no site |

## Geracao

Rode:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_presentation_video.ps1
```

Para usar outro arquivo de origem:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_presentation_video.ps1 -Source "C:\caminho\video.mp4"
```

## Ajustes recomendados no CapCut

- Trocar a trilha sintetica por uma musica licenciada, se quiser um acabamento mais comercial.
- Adicionar voz narrada lendo os textos principais, se quiser um video mais comercial.
- Exportar uma segunda versao em 9:16 para Reels/TikTok/Shorts.
- Trocar o ultimo texto por uma URL final quando o dominio definitivo estiver decidido.
