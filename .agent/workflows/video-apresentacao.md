---
description: Criar video curto de apresentacao do Torvix Tracker a partir de gameplay/demo gravado.
---

# /video-apresentacao - Video do Torvix Tracker

$ARGUMENTS

---

## Objetivo

Gerar um video curto em 16:9 usando um MP4 gravado do Torvix Tracker em acao.
O resultado deve alternar gameplay e interface do app, com textos claros sobre
rastreamento por webcam, ajustes, calibracao e saida para simuladores.
O script tambem aplica dissolves curtos entre os cortes e mistura uma trilha
instrumental sintetica de fundo com o audio original em volume reduzido.

## Comando principal

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_presentation_video.ps1
```

Para trocar o video base:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_presentation_video.ps1 -Source "C:\caminho\video.mp4"
```

## Saida esperada

```text
dist\TorvixTracker_Apresentacao_16x9.mp4
```

## Validacao

1. Confirmar se o arquivo MP4 foi gerado.
2. Conferir duracao aproximada de 1 minuto.
3. Verificar se os textos aparecem no rodape sem cobrir informacoes importantes.
4. Abrir o video e checar se os cortes mostram gameplay e interface do app.
5. Conferir se as transicoes estao suaves e se a musica de fundo nao cobre o audio original.

## Referencia

A timeline editavel fica em:

```text
docs\video-apresentacao-torvix.md
```
